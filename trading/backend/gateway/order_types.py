from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class BracketOrder:
    symbol: str
    qty: float
    side: str           # buy | sell
    tp_pct: float       # take profit % from entry
    sl_pct: float       # stop loss % from entry
    strategy: str
    confidence: float
    time_in_force: str = "gtc"


@dataclass
class OrderResult:
    order_id: str
    symbol: str
    side: str
    qty: float
    status: str         # accepted | filled | rejected
    filled_avg_price: Optional[float] = None
    filled_qty: Optional[float] = None
    tp_order_id: Optional[str] = None
    sl_order_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    error: Optional[str] = None


@dataclass
class FillEvent:
    order_id: str
    symbol: str
    side: str
    qty: float
    price: float
    timestamp: datetime
    event_type: str     # fill | partial_fill | canceled
