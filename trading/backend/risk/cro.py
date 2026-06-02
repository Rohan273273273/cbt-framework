"""
CRO — Chief Risk Officer. Hard limits enforced via atomic Redis Lua scripts.
Nothing trades without passing through here first.
"""
import logging
from datetime import datetime, timezone
from typing import Tuple

import redis

from config import settings

logger = logging.getLogger(__name__)
_redis = redis.from_url(settings.redis_url, decode_responses=True)

# Lua: atomic check-and-increment to prevent TOCTOU race
_LUA_CHECK_AND_ADD = _redis.register_script("""
local key = KEYS[1]
local limit = tonumber(ARGV[1])
local amount = tonumber(ARGV[2])
local ttl = tonumber(ARGV[3])
local current = tonumber(redis.call('GET', key) or '0')
if current + amount > limit then
    return 0
end
redis.call('INCRBYFLOAT', key, amount)
if redis.call('TTL', key) == -1 then
    redis.call('EXPIRE', key, ttl)
end
return 1
""")

SECONDS_IN_DAY = 86400
SECONDS_IN_WEEK = 604800


def _day_key() -> str:
    return f"cro:daily_loss:{datetime.now(timezone.utc).strftime('%Y%m%d')}"


def _week_key() -> str:
    from datetime import timedelta
    today = datetime.now(timezone.utc)
    monday = today - timedelta(days=today.weekday())
    return f"cro:weekly_loss:{monday.strftime('%Y%m%d')}"


def check_order(symbol: str, side: str, notional: float,
                account_equity: float) -> Tuple[bool, str]:
    """
    Validates an order against all CRO hard limits.
    Returns (approved, reason).
    """
    # 1. Min RR enforced upstream by strategy engine — not checked here
    # 2. Per-trade risk
    trade_risk_pct = (notional / account_equity) * 100
    if trade_risk_pct > settings.cro_max_trade_risk_pct:
        return False, f"Trade risk {trade_risk_pct:.2f}% > limit {settings.cro_max_trade_risk_pct}%"

    # 3. Max open positions
    open_count = int(_redis.get("cro:open_positions") or 0)
    if open_count >= settings.cro_max_open_positions:
        return False, f"Max open positions {settings.cro_max_open_positions} reached"

    # 4. Daily loss limit (atomic)
    daily_loss_limit = account_equity * settings.cro_max_daily_loss_pct / 100
    allowed = _LUA_CHECK_AND_ADD(
        keys=[_day_key()],
        args=[daily_loss_limit, notional * 0.01, SECONDS_IN_DAY]  # assume worst case 1%
    )
    if not allowed:
        return False, f"Daily loss limit {settings.cro_max_daily_loss_pct}% reached — halted for today"

    # 5. Weekly drawdown limit (atomic)
    weekly_loss_limit = account_equity * settings.cro_max_weekly_drawdown_pct / 100
    allowed = _LUA_CHECK_AND_ADD(
        keys=[_week_key()],
        args=[weekly_loss_limit, notional * 0.01, SECONDS_IN_WEEK]
    )
    if not allowed:
        return False, f"Weekly drawdown {settings.cro_max_weekly_drawdown_pct}% reached — halted until Monday"

    return True, "approved"


def record_trade_open(symbol: str):
    _redis.incr("cro:open_positions")


def record_trade_close(symbol: str, pnl: float, account_equity: float):
    _redis.decr("cro:open_positions")
    if pnl < 0:
        loss = abs(pnl)
        _redis.incrbyfloat(_day_key(), loss)
        _redis.incrbyfloat(_week_key(), loss)


def get_daily_used_pct(account_equity: float) -> float:
    used = float(_redis.get(_day_key()) or 0)
    return (used / account_equity) * 100 if account_equity else 0.0


def get_status(account_equity: float) -> dict:
    return {
        "daily_loss_pct": get_daily_used_pct(account_equity),
        "daily_limit_pct": settings.cro_max_daily_loss_pct,
        "open_positions": int(_redis.get("cro:open_positions") or 0),
        "max_positions": settings.cro_max_open_positions,
        "halted_today": get_daily_used_pct(account_equity) >= settings.cro_max_daily_loss_pct,
    }
