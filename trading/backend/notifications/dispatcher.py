"""Routes alerts to configured notification channels."""
import logging
import os
from dataclasses import dataclass
from enum import Enum
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


class AlertLevel(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class Alert:
    title: str
    message: str
    level: AlertLevel = AlertLevel.INFO
    strategy: Optional[str] = None
    symbol: Optional[str] = None
    pnl: Optional[float] = None


LEVEL_COLORS = {
    AlertLevel.INFO: 0x26A69A,
    AlertLevel.WARNING: 0xF0B90B,
    AlertLevel.CRITICAL: 0xEF5350,
}


async def _send_discord(alert: Alert, webhook_url: str) -> None:
    color = LEVEL_COLORS.get(alert.level, 0x787B86)
    fields = []
    if alert.strategy:
        fields.append({"name": "Strategy", "value": alert.strategy, "inline": True})
    if alert.symbol:
        fields.append({"name": "Symbol", "value": alert.symbol, "inline": True})
    if alert.pnl is not None:
        sign = "+" if alert.pnl >= 0 else ""
        fields.append({"name": "P&L", "value": f"{sign}${alert.pnl:.2f}", "inline": True})

    payload = {
        "embeds": [
            {
                "title": alert.title,
                "description": alert.message,
                "color": color,
                "fields": fields,
            }
        ]
    }
    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.post(webhook_url, json=payload)
        if resp.status_code not in (200, 204):
            logger.warning("Discord webhook returned %d", resp.status_code)


async def dispatch(alert: Alert) -> None:
    """Send alert to all configured channels."""
    webhook = os.getenv("DISCORD_WEBHOOK_URL", "")
    if webhook:
        try:
            await _send_discord(alert, webhook)
        except Exception as exc:
            logger.warning("Discord dispatch failed: %s", exc)
    else:
        logger.info("[%s] %s — %s", alert.level.value.upper(), alert.title, alert.message)


async def trade_placed(symbol: str, strategy: str, direction: str, qty: float) -> None:
    await dispatch(Alert(
        title=f"Trade Placed — {symbol}",
        message=f"{direction.upper()} {qty} via {strategy}",
        level=AlertLevel.INFO,
        strategy=strategy,
        symbol=symbol,
    ))


async def trade_closed(symbol: str, strategy: str, pnl: float) -> None:
    level = AlertLevel.INFO if pnl >= 0 else AlertLevel.WARNING
    await dispatch(Alert(
        title=f"Trade Closed — {symbol}",
        message=f"P&L: {'+'if pnl>=0 else ''}${pnl:.2f}",
        level=level,
        strategy=strategy,
        symbol=symbol,
        pnl=pnl,
    ))


async def cro_halt(reason: str) -> None:
    await dispatch(Alert(
        title="CRO HALT — Trading Suspended",
        message=reason,
        level=AlertLevel.CRITICAL,
    ))


async def watchdog_state_change(strategy: str, old_state: str, new_state: str) -> None:
    level = AlertLevel.CRITICAL if new_state == "PAUSED" else AlertLevel.WARNING
    await dispatch(Alert(
        title=f"Watchdog: {strategy} → {new_state}",
        message=f"State changed from {old_state} to {new_state}",
        level=level,
        strategy=strategy,
    ))
