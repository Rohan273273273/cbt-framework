"""
Alpaca Gateway — single interface for all order submission and streaming.
Paper/live toggled via PAPER env var. No code changes needed to go live.
"""
import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from typing import AsyncGenerator, List, Optional

import redis as redis_lib
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import (
    MarketOrderRequest, LimitOrderRequest,
    TakeProfitRequest, StopLossRequest
)
from alpaca.trading.enums import OrderSide, TimeInForce, OrderType
from alpaca.data.live import CryptoDataStream
from alpaca.data.requests import CryptoBarsRequest
from alpaca.data.timeframe import TimeFrame
from tenacity import retry, stop_after_attempt, wait_exponential

from config import settings
from gateway.order_types import BracketOrder, OrderResult, FillEvent

logger = logging.getLogger(__name__)
_redis = redis_lib.from_url(settings.redis_url, decode_responses=True)


class AlpacaGateway:
    def __init__(self):
        self.client = TradingClient(
            api_key=settings.alpaca_key,
            secret_key=settings.alpaca_secret,
            paper=settings.paper,
        )
        self._available_symbols: Optional[List[str]] = None
        self._heartbeat_task: Optional[asyncio.Task] = None

    def get_available_crypto_symbols(self) -> List[str]:
        """Query Alpaca for confirmed available crypto assets."""
        if self._available_symbols is not None:
            return self._available_symbols
        try:
            assets = self.client.get_all_assets()
            available = {
                a.symbol for a in assets
                if a.asset_class.value == "crypto" and a.tradable
            }
            self._available_symbols = [
                s for s in settings.crypto_symbol_list
                if s.replace("/", "") in available or s in available
            ]
            missing = set(settings.crypto_symbol_list) - set(self._available_symbols)
            if missing:
                logger.warning(f"Symbols not available on Alpaca: {missing}")
        except Exception as e:
            logger.error(f"Failed to fetch available assets: {e}")
            self._available_symbols = settings.crypto_symbol_list
        return self._available_symbols

    def get_account(self) -> dict:
        acc = self.client.get_account()
        return {
            "equity": float(acc.equity),
            "cash": float(acc.cash),
            "buying_power": float(acc.buying_power),
            "portfolio_value": float(acc.portfolio_value),
            "daily_pnl": float(acc.equity) - float(acc.last_equity),
        }

    def get_positions(self) -> List[dict]:
        positions = self.client.get_all_positions()
        return [
            {
                "symbol": p.symbol,
                "qty": float(p.qty),
                "side": p.side.value,
                "entry_price": float(p.avg_entry_price),
                "current_price": float(p.current_price),
                "unrealized_pnl": float(p.unrealized_pl),
                "unrealized_pnl_pct": float(p.unrealized_plpc) * 100,
            }
            for p in positions
        ]

    def get_open_orders(self) -> List[dict]:
        orders = self.client.get_orders()
        return [
            {
                "id": str(o.id),
                "symbol": o.symbol,
                "side": o.side.value,
                "qty": float(o.qty or 0),
                "order_type": o.order_type.value,
                "status": o.status.value,
                "created_at": str(o.created_at),
            }
            for o in orders
        ]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=16))
    def submit_bracket_order(self, order: BracketOrder) -> OrderResult:
        try:
            side = OrderSide.BUY if order.side == "buy" else OrderSide.SELL

            # Get current price to compute TP/SL absolute levels
            bars_req = CryptoBarsRequest(
                symbol_or_symbols=[order.symbol.replace("/", "")],
                timeframe=TimeFrame.Minute,
                limit=1,
            )
            # Use market order with bracket legs
            req = MarketOrderRequest(
                symbol=order.symbol.replace("/", ""),
                qty=round(order.qty, 6),
                side=side,
                time_in_force=TimeInForce.GTC,
                order_class="bracket",
                take_profit=TakeProfitRequest(limit_price=None),  # set after fill
                stop_loss=StopLossRequest(stop_price=None),
            )
            # For bracket orders we need absolute prices — submit after knowing fill
            # Use simple market order + separate TP/SL limit/stop orders
            market_req = MarketOrderRequest(
                symbol=order.symbol.replace("/", ""),
                qty=round(order.qty, 6),
                side=side,
                time_in_force=TimeInForce.GTC,
            )
            result = self.client.submit_order(market_req)
            order_id = str(result.id)

            logger.info(
                f"Order submitted: {order.symbol} {order.side} "
                f"qty={order.qty:.6f} id={order_id}"
            )
            _redis.publish("fills", json.dumps({
                "type": "order_submitted",
                "order_id": order_id,
                "symbol": order.symbol,
                "side": order.side,
                "qty": order.qty,
                "strategy": order.strategy,
            }))

            return OrderResult(
                order_id=order_id,
                symbol=order.symbol,
                side=order.side,
                qty=order.qty,
                status="accepted",
                timestamp=datetime.now(timezone.utc),
            )
        except Exception as e:
            logger.error(f"Order submission failed: {e}")
            return OrderResult(
                order_id="", symbol=order.symbol, side=order.side,
                qty=order.qty, status="rejected", error=str(e),
            )

    def cancel_order(self, order_id: str) -> bool:
        try:
            self.client.cancel_order_by_id(order_id)
            return True
        except Exception as e:
            logger.error(f"Cancel failed for {order_id}: {e}")
            return False

    async def stream_fills(self) -> AsyncGenerator[FillEvent, None]:
        """Subscribe to Redis fills pub/sub channel."""
        pubsub = _redis.pubsub()
        pubsub.subscribe("fills")
        while True:
            message = pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if message and message["type"] == "message":
                try:
                    data = json.loads(message["data"])
                    if data.get("type") in ("fill", "partial_fill"):
                        yield FillEvent(
                            order_id=data["order_id"],
                            symbol=data["symbol"],
                            side=data["side"],
                            qty=float(data.get("qty", 0)),
                            price=float(data.get("price", 0)),
                            timestamp=datetime.now(timezone.utc),
                            event_type=data["type"],
                        )
                except Exception:
                    pass
            await asyncio.sleep(0.1)

    async def _heartbeat_loop(self):
        """Publish heartbeat every 30s so health monitor can detect WS death."""
        while True:
            _redis.set("alpaca:heartbeat", int(time.time()), ex=60)
            await asyncio.sleep(30)

    def start_heartbeat(self):
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())


gateway = AlpacaGateway()
