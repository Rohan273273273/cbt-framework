import asyncio
import json
from typing import Set

from fastapi import WebSocket, WebSocketDisconnect

_connections: Set[WebSocket] = set()


async def ws_prices(websocket: WebSocket):
    await websocket.accept()
    _connections.add(websocket)
    try:
        while True:
            await asyncio.sleep(1)
            # Keep connection alive; prices broadcast via broadcast_price()
    except WebSocketDisconnect:
        _connections.discard(websocket)


async def broadcast_price(symbol: str, price: float, ts: str):
    msg = json.dumps({"type": "price", "symbol": symbol, "price": price, "ts": ts})
    dead = set()
    for ws in _connections.copy():
        try:
            await ws.send_text(msg)
        except Exception:
            dead.add(ws)
    _connections -= dead
