from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


# ====================== Address / Users ======================

@dataclass
class Address:
    street: Optional[str]
    street_number: Optional[str]
    postal_code: Optional[str]
    city: Optional[str]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Address":
        if not data:
            return cls(None, None, None, None)
        return cls(
            street=data.get("street"),
            street_number=data.get("street_number"),
            postal_code=data.get("postal_code"),
            city=data.get("city"),
        )


@dataclass
class UserInfo:
    id: int
    email: str
    first_name: str
    last_name: str
    phone_number: Optional[str]
    is_owner: bool

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UserInfo":
        return cls(
            id=data.get("id"),
            email=data.get("email"),
            first_name=data.get("first_name"),
            last_name=data.get("last_name"),
            phone_number=data.get("phone_number"),
            is_owner=data.get("is_owner", False),
        )


@dataclass
class UserLink:
    user: UserInfo
    is_admin: bool

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UserLink":
        return cls(
            user=UserInfo.from_dict(data.get("user", {})),
            is_admin=data.get("is_admin", False),
        )


# ====================== Details / Device ======================

@dataclass
class Device:
    # Pola zgodne z RAW (null -> Optional)
    fv: Optional[str]
    hv: Optional[str]
    id: str
    ip: Optional[str]
    type: str
    product: str
    apiLevel: Optional[str]
    universe: Optional[int]
    categories: List[int]
    deviceName: str
    availableFv: Optional[str]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Device":
        if not data:
            # Minimalny obiekt, jeśli API kiedyś zwróci pustkę
            return cls(
                fv=None,
                hv=None,
                id="",
                ip=None,
                type="",
                product="",
                apiLevel=None,
                universe=None,
                categories=[],
                deviceName="",
                availableFv=None,
            )
        return cls(
            fv=data.get("fv"),
            hv=data.get("hv"),
            id=data.get("id", ""),
            ip=data.get("ip"),
            type=data.get("type", ""),
            product=data.get("product", ""),
            apiLevel=data.get("apiLevel"),
            universe=data.get("universe"),
            categories=list(data.get("categories", []) or []),
            deviceName=data.get("deviceName", ""),
            availableFv=data.get("availableFv"),
        )


@dataclass
class Details:
    device: Device

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Details":
        return cls(
            device=Device.from_dict((data or {}).get("device", {})),
        )


# ====================== User Settings / Notifications ======================

@dataclass
class MarketingCommunication:
    push_notification_enabled: bool
    email_notification_enabled: bool

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MarketingCommunication":
        return cls(
            push_notification_enabled=bool(data.get("push_notification_enabled", False)),
            email_notification_enabled=bool(data.get("email_notification_enabled", False)),
        )


@dataclass
class Marketing:
    marketing_communication: MarketingCommunication

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Marketing":
        return cls(
            marketing_communication=MarketingCommunication.from_dict(
                (data or {}).get("marketing_communication", {})
            )
        )


@dataclass
class NextDayPriceSummary:
    push_notification_enabled: bool
    email_notification_enabled: bool

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NextDayPriceSummary":
        return cls(
            push_notification_enabled=bool(data.get("push_notification_enabled", False)),
            email_notification_enabled=bool(data.get("email_notification_enabled", False)),
        )


@dataclass
class PriceAlerts:
    next_day_price_summary: NextDayPriceSummary

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PriceAlerts":
        return cls(
            next_day_price_summary=NextDayPriceSummary.from_dict(
                (data or {}).get("next_day_price_summary", {})
            )
        )


@dataclass
class NotificationsSettings:
    marketing: Marketing
    price_alerts: PriceAlerts

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NotificationsSettings":
        return cls(
            marketing=Marketing.from_dict((data or {}).get("marketing", {})),
            price_alerts=PriceAlerts.from_dict((data or {}).get("price_alerts", {})),
        )


@dataclass
class UserSettings:
    notifications_settings: NotificationsSettings

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UserSettings":
        return cls(
            notifications_settings=NotificationsSettings.from_dict(
                (data or {}).get("notifications_settings", {})
            )
        )


# ====================== Meter ======================

@dataclass
class Meter:
    id: int
    meter_id: str
    name: str
    status: str
    shippingorder: Optional[int]
    is_prosument: bool
    pv_installation_power: Optional[float]
    has_api_key: bool
    wallet_billable: bool
    has_bess: bool
    has_ev: bool
    has_hvac: bool
    property_contract_status: str
    address: Address
    users: List[UserLink]
    details: Details
    user_settings: UserSettings

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Meter":
        return cls(
            id=data.get("id"),
            meter_id=data.get("meter_id", ""),
            name=data.get("name"),
            status=data.get("status"),
            shippingorder=data.get("shippingorder"),
            is_prosument=data.get("is_prosument", False),
            pv_installation_power=data.get("pv_installation_power"),
            has_api_key=data.get("has_api_key", False),
            wallet_billable=data.get("wallet_billable", False),
            has_bess=data.get("has_bess", False),
            has_ev=data.get("has_ev", False),
            has_hvac=data.get("has_hvac", False),
            property_contract_status=data.get("property_contract_status", ""),
            address=Address.from_dict(data.get("address")),
            users=[UserLink.from_dict(u) for u in data.get("users", [])],
            details=Details.from_dict(data.get("details", {})),
            user_settings=UserSettings.from_dict(data.get("user_settings", {})),
        )