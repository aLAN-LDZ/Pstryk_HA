from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple, Optional
from datetime import datetime

HourRange = Tuple[str, str]  # np. ("07:00", "11:00")

@dataclass
class FullPriceAlert:
    day: str                     # "2025-10-13" (trzymamy RAW string jak chcesz)
    low_price_threshold: Optional[float]
    high_price_threshold: Optional[float]
    expensive_hours: List[HourRange]
    cheap_hours: List[HourRange]
    created_at: str              # ISO string "2025-10-12T10:00:07.083793Z"

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "FullPriceAlert":
        def _ranges(x: Any) -> List[HourRange]:
            # JSON ma listy dwuelementowe ["HH:MM", "HH:MM"]
            return [(a, b) for a, b in x] if isinstance(x, list) else []

        return cls(
            day=d.get("day"),
            low_price_threshold=d.get("low_price_threshold"),
            high_price_threshold=d.get("high_price_threshold"),
            expensive_hours=_ranges(d.get("expensive_hours", [])),
            cheap_hours=_ranges(d.get("cheap_hours", [])),
            created_at=d.get("created_at"),
        )
