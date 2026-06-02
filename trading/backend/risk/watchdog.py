"""
Watchdog — per-strategy state machine stored in Redis.
States: NORMAL → REDUCED → PAUSED
"""
import json
import logging
from datetime import datetime, timezone
from typing import Dict

import redis
import psycopg2
from config import settings

logger = logging.getLogger(__name__)
_redis = redis.from_url(settings.redis_url, decode_responses=True)

STRATEGIES = ["volume_profile", "amd_session", "liquidity_sweep", "order_blocks_fvg"]

STATE_NORMAL = "NORMAL"
STATE_REDUCED = "REDUCED"
STATE_PAUSED = "PAUSED"

# Thresholds
LOSSES_TO_REDUCE = 3
LOSSES_TO_PAUSE = 2   # additional losses after REDUCED
WINS_TO_RESUME = 3


def _key(strategy: str) -> str:
    return f"watchdog:{strategy}"


def _counter_key(strategy: str) -> str:
    return f"watchdog:streak:{strategy}"


def get_state(strategy: str) -> str:
    return _redis.hget(_key(strategy), "state") or STATE_NORMAL


def get_all_states() -> Dict[str, str]:
    return {s: get_state(s) for s in STRATEGIES}


def get_size_multiplier(strategy: str) -> float:
    state = get_state(strategy)
    if state == STATE_PAUSED:
        return 0.0
    if state == STATE_REDUCED:
        return 0.5
    return 1.0


def record_outcome(strategy: str, won: bool):
    """Call after every trade close to update state machine."""
    current_state = get_state(strategy)
    streak_raw = _redis.hget(_key(strategy), "streak") or "0"
    streak = int(streak_raw)

    if won:
        new_streak = max(0, streak + 1) if streak >= 0 else 1
    else:
        new_streak = min(0, streak - 1) if streak <= 0 else -1

    _redis.hset(_key(strategy), mapping={"streak": new_streak})

    new_state = current_state
    reason = ""

    if current_state == STATE_NORMAL and new_streak <= -LOSSES_TO_REDUCE:
        new_state = STATE_REDUCED
        reason = f"{LOSSES_TO_REDUCE} consecutive losses"

    elif current_state == STATE_REDUCED:
        if new_streak <= -(LOSSES_TO_REDUCE + LOSSES_TO_PAUSE):
            new_state = STATE_PAUSED
            reason = f"{LOSSES_TO_REDUCE + LOSSES_TO_PAUSE} consecutive losses"
        elif new_streak >= WINS_TO_RESUME:
            new_state = STATE_NORMAL
            reason = f"{WINS_TO_RESUME} consecutive wins"

    elif current_state == STATE_PAUSED and new_streak >= WINS_TO_RESUME:
        new_state = STATE_NORMAL
        reason = f"Recovered: {WINS_TO_RESUME} consecutive wins"

    if new_state != current_state:
        _redis.hset(_key(strategy), "state", new_state)
        logger.info(f"Watchdog [{strategy}]: {current_state} → {new_state} ({reason})")
        _log_transition(strategy, current_state, new_state, reason, abs(new_streak))


def _log_transition(strategy: str, from_state: str, to_state: str,
                    reason: str, count: int):
    try:
        conn = psycopg2.connect(settings.timescale_url)
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO watchdog_history
                       (ts, strategy, from_state, to_state, reason, consecutive_count)
                       VALUES (%s, %s, %s, %s, %s, %s)""",
                    (datetime.now(timezone.utc), strategy,
                     from_state, to_state, reason, count)
                )
        conn.close()
    except Exception as e:
        logger.error(f"Watchdog log write failed: {e}")


def reset_strategy(strategy: str):
    _redis.delete(_key(strategy))
    logger.info(f"Watchdog [{strategy}] manually reset to NORMAL")
