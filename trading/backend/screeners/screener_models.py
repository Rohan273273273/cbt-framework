from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class ScreenerResult:
    symbol: str
    rel_volume: float
    atr_pct: float
    rsi: float
    momentum_score: float
    composite_score: float
    trend: str          # bullish | bearish | neutral
    catalyst: str = ""


@dataclass
class NewsEvent:
    headline: str
    source: str
    url: str
    timestamp: datetime
    sentiment: str      # bullish | bearish | neutral
    confidence: float
    impact_score: float
    high_impact: bool
    affected: List[str] = field(default_factory=list)
