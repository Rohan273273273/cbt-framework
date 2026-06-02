import asyncio
import json
from asyncio import Queue
from typing import Set

from fastapi import WebSocket, WebSocketDisconnect

_connections: Set[WebSocket] = set()
_log_queue: Queue = Queue(maxsize=500)


async def ws_agent_log(websocket: WebSocket):
    await websocket.accept()
    _connections.add(websocket)
    try:
        while True:
            await asyncio.sleep(0.5)
    except WebSocketDisconnect:
        _connections.discard(websocket)


async def broadcast_log(log_line: str):
    msg = json.dumps({"type": "agent_log", "message": log_line})
    dead = set()
    for ws in _connections.copy():
        try:
            await ws.send_text(msg)
        except Exception:
            dead.add(ws)
    _connections -= dead


def push_logs(logs: list):
    """Called after each agent cycle to broadcast all log lines."""
    import asyncio
    for line in logs:
        asyncio.create_task(broadcast_log(line))
