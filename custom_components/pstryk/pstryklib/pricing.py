from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


# ===== Ramki cenowe =====

@dataclass
class BuyPriceFrame:
    price_net: Optional[float]
    price_gross: Optional[float]
    dist_price: Optional[float]
    service_price: Optional[float]
    base_price: Optional[float]
    vat_component: Optional[float]
    excise_component: Optional[float]
    full_price: Optional[float]
    start: Optional[str]          # ISO8601
    end: Optional[str]            # ISO8601
    is_cheap: bool
    is_expensive: bool
    is_live: Optional[bool] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BuyPriceFrame":
        return cls(
            price_net=data.get("price_net"),
            price_gross=data.get("price_gross"),
            dist_price=data.get("dist_price"),
            service_price=data.get("service_price"),
            base_price=data.get("base_price"),
            vat_component=data.get("vat_component"),
            excise_component=data.get("excise_component"),
            full_price=data.get("full_price"),
            start=data.get("start"),
            end=data.get("end"),
            is_cheap=bool(data.get("is_cheap", False)),
            is_expensive=bool(data.get("is_expensive", False)),
            is_live=data.get("is_live"),
        )


@dataclass
class SellPriceFrame:
    price_net: Optional[float]
    price_gross: Optional[float]
    dist_price: Optional[float]
    service_price: Optional[float]
    base_price: Optional[float]
    vat_component: Optional[float]
    excise_component: Optional[float]
    full_price: Optional[float]
    start: Optional[str]          # ISO8601
    end: Optional[str]            # ISO8601
    is_cheap: bool
    is_expensive: bool
    is_live: Optional[bool] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SellPriceFrame":
        return cls(
            price_net=data.get("price_net"),
            price_gross=data.get("price_gross"),
            dist_price=data.get("dist_price"),
            service_price=data.get("service_price"),
            base_price=data.get("base_price"),
            vat_component=data.get("vat_component"),
            excise_component=data.get("excise_component"),
            full_price=data.get("full_price"),
            start=data.get("start"),
            end=data.get("end"),
            is_cheap=bool(data.get("is_cheap", False)),
            is_expensive=bool(data.get("is_expensive", False)),
            is_live=data.get("is_live"),
        )


# ===== Obiekty top-level z avg + ramkami =====

@dataclass
class PricingBuy:
    price_net_avg: Optional[float]
    price_gross_avg: Optional[float]
    frames: List[BuyPriceFrame]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PricingBuy":
        frames = [BuyPriceFrame.from_dict(f) for f in data.get("frames", [])]
        return cls(
            price_net_avg=data.get("price_net_avg"),
            price_gross_avg=data.get("price_gross_avg"),
            frames=frames,
        )


@dataclass
class PricingSell:
    price_net_avg: Optional[float]
    price_gross_avg: Optional[float]
    frames: List[SellPriceFrame]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PricingSell":
        frames = [SellPriceFrame.from_dict(f) for f in data.get("frames", [])]
        return cls(
            price_net_avg=data.get("price_net_avg"),
            price_gross_avg=data.get("price_gross_avg"),
            frames=frames,
        )
