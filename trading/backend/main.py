import logging
import sys

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.websockets import WebSocket

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──────────────────────────────────────────────────────────────
    logger.info("Starting CBT Trading Terminal...")

    # Numba JIT warm-up (prevents cold-start latency on first backtest)
    try:
        import numpy as np
        sys.path.insert(0, "/app/cbt_engine")
        from templates.fast.backtest import run_backtest_loop
        run_backtest_loop(
            np.ones(20, dtype=np.float64), np.ones(20, dtype=np.float64),
            np.ones(20, dtype=np.float64), np.ones(20, dtype=np.float64),
            np.zeros(20, dtype=np.float64), np.zeros(20, dtype=np.float64),
            1000.0, 0.01, 1.0, 0.02, 0.04, 0.001, 0.001, 0.0005, 1,
        )
        logger.info("Numba JIT warm-up complete")
    except Exception as e:
        logger.warning(f"Numba warm-up skipped: {e}")

    # Load ML models
    try:
        from ml.lgbm_selector import load_model as load_lgbm
        from ml.river_updater import load_model as load_river
        load_lgbm()
        load_river()
        logger.info("ML models loaded")
    except Exception as e:
        logger.warning(f"ML model load: {e}")

    # Seed Neo4j strategy nodes
    try:
        from knowledge.graph_builder import seed_strategies
        seed_strategies()
        logger.info("Neo4j strategy nodes seeded")
    except Exception as e:
        logger.warning(f"Neo4j seed: {e}")

    # Start Alpaca heartbeat
    try:
        from gateway.alpaca_gateway import gateway
        gateway.start_heartbeat()
        logger.info("Alpaca heartbeat started")
    except Exception as e:
        logger.warning(f"Alpaca heartbeat: {e}")

    # Start scheduler
    from scheduler import setup_scheduler
    setup_scheduler()

    logger.info("CBT Trading Terminal READY")
    yield

    # ── Shutdown ─────────────────────────────────────────────────────────────
    from scheduler import scheduler
    scheduler.shutdown(wait=False)
    from knowledge.neo4j_client import close
    close()
    logger.info("Shutdown complete")


app = FastAPI(title="CBT Trading Terminal", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── REST routes ───────────────────────────────────────────────────────────────
from api.routes.market import router as market_router
from api.routes.orders import router as orders_router
from api.routes.screener import router as screener_router
from api.routes.backtest import router as backtest_router
from api.routes.settings import router as settings_router

app.include_router(market_router)
app.include_router(orders_router)
app.include_router(screener_router)
app.include_router(backtest_router)
app.include_router(settings_router)

# ── WebSocket endpoints ───────────────────────────────────────────────────────
from api.routes.knowledge import router as knowledge_router
app.include_router(knowledge_router)

from api.websocket.price_stream import ws_prices
from api.websocket.agent_log_stream import ws_agent_log
from api.websocket.order_stream import order_stream_ws


@app.websocket("/ws/prices")
async def websocket_prices(websocket: WebSocket):
    await ws_prices(websocket)


@app.websocket("/ws/agents")
async def websocket_agents(websocket: WebSocket):
    await ws_agent_log(websocket)


@app.websocket("/ws/orders")
async def websocket_orders(websocket: WebSocket):
    await order_stream_ws(websocket)


@app.get("/health")
def health():
    return {"status": "ok"}
