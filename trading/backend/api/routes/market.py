from fastapi import APIRouter, HTTPException
from data.market_data_service import get_latest_candles, get_live_price
from config import settings

router = APIRouter(prefix="/api/market", tags=["market"])


@router.get("/candles/{symbol}")
def get_candles(symbol: str, timeframe: str = "1h", limit: int = 200):
    df = get_latest_candles(symbol, timeframe, limit)
    if df.is_empty():
        raise HTTPException(404, f"No data for {symbol} {timeframe}")
    return df.to_dicts()


@router.get("/prices")
def get_all_prices():
    prices = {}
    for sym in settings.crypto_symbol_list:
        p = get_live_price(sym)
        prices[sym] = p if p is not None else "—"
    return prices


@router.get("/account")
def get_account():
    from gateway.alpaca_gateway import gateway
    return gateway.get_account()


@router.get("/positions")
def get_positions():
    from gateway.alpaca_gateway import gateway
    return gateway.get_positions()
