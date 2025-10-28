from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class PowerCostFrame:
    start: Optional[str]
    end: Optional[str]
    fae_cost: Optional[float]
    var_dist_cost_net: Optional[float]
    fix_dist_cost_net: Optional[float]
    energy_cost_net: Optional[float]
    service_cost_net: Optional[float]
    excise: Optional[float]
    vat: Optional[float]
    energy_sold_value: Optional[float]
    energy_balance_value: Optional[float]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PowerCostFrame":
        # konwersje na float z bezpiecznym defaultem
        def f(x): 
            try:
                return float(x)
            except Exception:
                return 0.0 if x in (None, "") else x

        return cls(
            start=data.get("start"),
            end=data.get("end"),
            fae_cost=f(data.get("fae_cost")),
            var_dist_cost_net=f(data.get("var_dist_cost_net")),
            fix_dist_cost_net=f(data.get("fix_dist_cost_net")),
            energy_cost_net=f(data.get("energy_cost_net")),
            service_cost_net=f(data.get("service_cost_net")),
            excise=f(data.get("excise")),
            vat=f(data.get("vat")),
            energy_sold_value=f(data.get("energy_sold_value")),
            energy_balance_value=f(data.get("energy_balance_value")),
        )


@dataclass
class PowerCostDay:
    """
    Model jednego „dnia” kosztów:
      - frames: lista godzinowych ramek,
      - pola total_* z podsumowaniami z API (na dole JSON-a).
    """
    frames: List[PowerCostFrame]
    fae_total_cost: Optional[float]
    total_energy_sold_value: Optional[float]
    total_energy_balance_value: Optional[float]
    total_sales_cost_net: Optional[float]
    total_service_cost_net: Optional[float]
    total_dist_cost_net: Optional[float]
    total_excise: Optional[float]
    total_vat: Optional[float]
    total_energy_cost_with_service: Optional[float]
    total_var_dist_cost_net: Optional[float]
    total_fix_dist_cost_net: Optional[float]
    total_energy_cost_net: Optional[float]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PowerCostDay":
        def f(x):
            try:
                return float(x)
            except Exception:
                return None if x is None else x

        frames = [PowerCostFrame.from_dict(fra) for fra in (data.get("frames") or []) if isinstance(fra, dict)]
        return cls(
            frames=frames,
            fae_total_cost=f(data.get("fae_total_cost")),
            total_energy_sold_value=f(data.get("total_energy_sold_value")),
            total_energy_balance_value=f(data.get("total_energy_balance_value")),
            total_sales_cost_net=f(data.get("total_sales_cost_net")),
            total_service_cost_net=f(data.get("total_service_cost_net")),
            total_dist_cost_net=f(data.get("total_dist_cost_net")),
            total_excise=f(data.get("total_excise")),
            total_vat=f(data.get("total_vat")),
            total_energy_cost_with_service=f(data.get("total_energy_cost_with_service")),
            total_var_dist_cost_net=f(data.get("total_var_dist_cost_net")),
            total_fix_dist_cost_net=f(data.get("total_fix_dist_cost_net")),
            total_energy_cost_net=f(data.get("total_energy_cost_net")),
        )