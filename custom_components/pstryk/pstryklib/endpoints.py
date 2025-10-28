from dataclasses import dataclass

@dataclass(frozen=True)
class Endpoints:
    base: str = "https://api.pstryk.pl"
    api_prefix: str = "/api"
    auth_prefix: str = "/auth"

    def _join(self, prefix: str, *parts: str, trailing_slash: bool = True) -> str:
        parts_clean = [self.base.rstrip("/"), prefix.strip("/"), *[p.strip("/") for p in parts]]
        url = "/".join(parts_clean)
        return url + ("/" if trailing_slash and not url.endswith("/") else "")

    # --------- generic ---------
    def api(self, *parts: str, trailing_slash: bool = True) -> str:
        return self._join(self.api_prefix, *parts, trailing_slash=trailing_slash)

    def auth(self, *parts: str, trailing_slash: bool = True) -> str:
        return self._join(self.auth_prefix, *parts, trailing_slash=trailing_slash)

    # --------- auth ---------
    @property
    def token(self) -> str:
        return self.auth("token", trailing_slash=True)

    @property
    def token_refresh(self) -> str:
        return self.auth("token", "refresh", trailing_slash=True)

    # --------- meters ---------
    def meter_list(self) -> str:
        return self.api("meter", trailing_slash=True)

    # --------- alerts ---------
    def full_price_alerts(self, meter_id: int) -> str:
        return self.api("full-price-alerts", str(meter_id), trailing_slash=False)

    # --------- pricing ---------
    def pricing_buy(self) -> str:
        return self.api("pricing", trailing_slash=True)

    def pricing_sell(self) -> str:
        return self.api("prosumer-pricing", trailing_slash=True)

    # --------- power usage ---------
    def power_usage(self, meter_id: int) -> str:
        return self.api("meter-data", str(meter_id), "power-usage", trailing_slash=True)

    # --------- NEW: power cost ---------
    def power_cost(self, meter_id: int) -> str:
        # GET /api/meter-data/{meter_id}/power-cost/
        return self.api("meter-data", str(meter_id), "power-cost", trailing_slash=True)
