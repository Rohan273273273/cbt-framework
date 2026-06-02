from fastapi import APIRouter
from risk.cro import get_status
from risk.watchdog import get_all_states
from ml.river_updater import get_trade_count
from ml.lgbm_selector import _model
from gateway.alpaca_gateway import gateway
from config import settings

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("")
def get_settings():
    account = {}
    try:
        account = gateway.get_account()
    except Exception:
        pass

    equity = account.get("equity", 1000.0)
    return {
        "mode": "PAPER" if settings.paper else "LIVE",
        "active_market": settings.active_market,
        "symbols": settings.crypto_symbol_list,
        "cro": get_status(equity),
        "watchdog": get_all_states(),
        "ml": {
            "lgbm_loaded": _model is not None,
            "river_trades": get_trade_count(),
            "confidence_threshold": settings.ml_confidence_threshold,
        },
        "account": account,
    }
