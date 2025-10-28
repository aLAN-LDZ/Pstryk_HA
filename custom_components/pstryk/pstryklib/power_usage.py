from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class PowerUsageFrame:
    start: str          # ISO Zulu
    end: str            # ISO Zulu
    fae_usage: float    # kWh: pobór z sieci
    rae: float          # kWh: oddanie do sieci (prosument)
    energy_balance: float  # kWh: fae_usage - rae

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "PowerUsageFrame":
        return cls(
            start=d.get("start"),
            end=d.get("end"),
            fae_usage=float(d.get("fae_usage", 0) or 0),
            rae=float(d.get("rae", 0) or 0),
            energy_balance=float(d.get("energy_balance", 0) or 0),
        )


@dataclass
class PowerUsageDay:
    """
    Model jednego „dnia” z API power-usage:
      - frames: lista ramek godzinowych,
      - fae_total_usage: suma poboru (kWh),
      - rae_total: suma oddania (kWh),
      - energy_balance: bilans (kWh, może być ujemny).
    """
    frames: List[PowerUsageFrame]
    fae_total_usage: float
    rae_total: float
    energy_balance: float

    @classmethod
    def from_api_dict(cls, d: Dict[str, Any]) -> "PowerUsageDay":
        frames_raw = (d or {}).get("frames") or []
        frames = [PowerUsageFrame.from_dict(i) for i in frames_raw if isinstance(i, dict)]
        return cls(
            frames=frames,
            fae_total_usage=float((d or {}).get("fae_total_usage", 0) or 0),
            rae_total=float((d or {}).get("rae_total", 0) or 0),
            energy_balance=float((d or {}).get("energy_balance", 0) or 0),
        )