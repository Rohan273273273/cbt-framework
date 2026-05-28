from fastapi import APIRouter
from gateway.alpaca_gateway import gateway

router = APIRouter(prefix="/api/orders", tags=["orders"])


@router.get("")
def get_open_orders():
    return gateway.get_open_orders()


@router.delete("/{order_id}")
def cancel_order(order_id: str):
    ok = gateway.cancel_order(order_id)
    return {"cancelled": ok}
