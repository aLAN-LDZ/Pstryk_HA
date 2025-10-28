import aiohttp
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from urllib.parse import urlencode

from .utils import decode_jwt, iso_utc
from .meters import Meter
from .full_price_alerts import FullPriceAlert
from .pricing import BuyPriceFrame, SellPriceFrame
from .power_usage import PowerUsageFrame, PowerUsageDay       
from .power_cost import PowerCostFrame, PowerCostDay 
from .endpoints import Endpoints


class PstrykApiClient:
    def __init__(self, email: Optional[str] = None, password: Optional[str] = None):
        self.email = email
        self.password = password
        self.session: Optional[aiohttp.ClientSession] = None

        self.ep = Endpoints(base="https://api.pstryk.pl")

        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.user_id: Optional[int] = None

        self.AccessIssuedAt: Optional[datetime] = None
        self.AccessExpires: Optional[datetime] = None
        self.RefreshIssuedAt: Optional[datetime] = None
        self.RefreshExpires: Optional[datetime] = None

    @classmethod
    def from_tokens(
        cls,
        access: str,
        refresh: str,
        user_id: Optional[int] = None,
    ) -> "PstrykApiClient":
        self = cls(email=None, password=None)
        self.access_token = access
        self.refresh_token = refresh
        self.user_id = user_id

        decoded_access: Dict[str, Any] = decode_jwt(access)
        self.AccessIssuedAt = datetime.fromtimestamp(decoded_access.get("iat", 0), tz=timezone.utc)
        self.AccessExpires  = datetime.fromtimestamp(decoded_access.get("exp", 0), tz=timezone.utc)

        decoded_refresh: Dict[str, Any] = decode_jwt(refresh)
        self.RefreshIssuedAt = datetime.fromtimestamp(decoded_refresh.get("iat", 0), tz=timezone.utc)
        self.RefreshExpires  = datetime.fromtimestamp(decoded_refresh.get("exp", 0), tz=timezone.utc)

        return self

    async def _ensure_session(self) -> None:
        if self.session is None:
            self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15))

    def _auth_headers(self) -> Dict[str, str]:
        if not self.access_token:
            raise RuntimeError("Brak access tokena — zaloguj się lub użyj from_tokens().")
        return {"Authorization": f"Bearer {self.access_token}"}

    async def refresh_access(self) -> None:
        await self._ensure_session()
        if not self.refresh_token:
            raise RuntimeError("Brak refresh tokena — nie mogę odświeżyć access tokena.")

        try:
            async with self.session.post(self.ep.token_refresh, json={"refresh": self.refresh_token}) as resp:
                text = await resp.text()
                if resp.status != 200:
                    raise RuntimeError(f"Refresh failed: HTTP {resp.status} - {text[:200]}")
                data = await resp.json()
        except aiohttp.ClientError as e:
            raise RuntimeError(f"Network error during refresh: {e}") from e

        new_access = data.get("access")
        if not new_access:
            raise RuntimeError(f"Refresh response without 'access': keys={list(data.keys())}")

        self.access_token = new_access
        decoded_access: Dict[str, Any] = decode_jwt(self.access_token)
        self.AccessIssuedAt = datetime.fromtimestamp(decoded_access.get("iat", 0), tz=timezone.utc)
        self.AccessExpires  = datetime.fromtimestamp(decoded_access.get("exp", 0), tz=timezone.utc)
        self.user_id = data.get("user_id")

    async def _get_json(self, url: str) -> Any:
        await self._ensure_session()

        async with self.session.get(url, headers=self._auth_headers()) as resp:
            if resp.status == 200:
                return await resp.json()
            if resp.status != 401:
                text = await resp.text()
                raise RuntimeError(f"GET {url} failed: HTTP {resp.status} - {text[:200]}")

        await self.refresh_access()
        async with self.session.get(url, headers=self._auth_headers()) as resp:
            if resp.status != 200:
                text = await resp.text()
                raise RuntimeError(f"GET(retry) {url} failed: HTTP {resp.status} - {text[:200]}")
            return await resp.json()

    # --- auth ---
    async def login(self) -> None:
        await self._ensure_session()
        if not self.email or not self.password:
            raise RuntimeError("Brak email/hasła: użyj login() tylko gdy tworzysz klienta z poświadczeń.")

        payload = {"email": self.email, "password": self.password}

        try:
            async with self.session.post(self.ep.token, json=payload) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    raise RuntimeError(f"Login failed: HTTP {resp.status} - {text[:200]}")
                data = await resp.json()
        except aiohttp.ClientError as e:
            raise RuntimeError(f"Network error during login: {e}") from e

        self.refresh_token = data.get("refresh")
        self.access_token = data.get("access")
        self.user_id = data.get("user_id")

        if not self.access_token or not self.refresh_token or self.user_id is None:
            raise RuntimeError(f"Unexpected login response keys: {list(data.keys())}")

        decoded_access: Dict[str, Any] = decode_jwt(self.access_token)
        self.AccessIssuedAt = datetime.fromtimestamp(decoded_access.get("iat", 0), tz=timezone.utc)
        self.AccessExpires = datetime.fromtimestamp(decoded_access.get("exp", 0), tz=timezone.utc)

        decoded_refresh: Dict[str, Any] = decode_jwt(self.refresh_token)
        self.RefreshIssuedAt = datetime.fromtimestamp(decoded_refresh.get("iat", 0), tz=timezone.utc)
        self.RefreshExpires = datetime.fromtimestamp(decoded_refresh.get("exp", 0), tz=timezone.utc)

    # ========== API ==========
    async def get_meters(self) -> list[Meter]:
        if not self.access_token:
            raise RuntimeError("Brak access tokena — zaloguj się lub użyj from_tokens().")
        url = self.ep.meter_list()
        data = await self._get_json(url)
        return [Meter.from_dict(item) for item in data]

    async def get_full_price_alerts(self, meter_id: int) -> list[FullPriceAlert]:
        if not self.access_token:
            raise RuntimeError("Brak access tokena — zaloguj się lub użyj from_tokens().")
        url = self.ep.full_price_alerts(meter_id)
        data = await self._get_json(url)
        return [FullPriceAlert.from_dict(item) for item in data]
    
    async def get_pricing_buy(
        self,
        meter_id: int,
        window_start: datetime,
        window_end: datetime,
        *,
        resolution: str = "hour",
    ) -> list[BuyPriceFrame]:
        if not self.access_token:
            raise RuntimeError("Brak access tokena — zaloguj się lub użyj from_tokens().")

        params = {
            "meter_id": meter_id,
            "window_start": iso_utc(window_start),
            "window_end": iso_utc(window_end),
            "resolution": resolution,
        }
        url = f"{self.ep.pricing_buy()}?{urlencode(params)}"
        data = await self._get_json(url)
        frames = (data or {}).get("frames") or []
        return [BuyPriceFrame.from_dict(item) for item in frames]

    async def get_pricing_sell(
        self,
        window_start: datetime,
        window_end: datetime,
        *,
        resolution: str = "hour",
    ) -> list[SellPriceFrame]:
        if not self.access_token:
            raise RuntimeError("Brak access tokena — zaloguj się lub użyj from_tokens().")

        params = {
            "window_start": iso_utc(window_start),
            "window_end": iso_utc(window_end),
            "resolution": resolution,
        }
        url = f"{self.ep.pricing_sell()}?{urlencode(params)}"
        data = await self._get_json(url)
        frames = (data or {}).get("frames") or []
        return [SellPriceFrame.from_dict(item) for item in frames]

    # --------- NEW: pobrana energia (lista ramek) ---------
    async def get_power_usage_hourly(
        self,
        meter_id: int,
        window_start: datetime,
        window_end: datetime,
        *,
        resolution: str = "hour",
    ) -> list[PowerUsageFrame]:
        """
        GET /api/meter-data/{meter_id}/power-usage/?resolution=hour&window_start=...&window_end=...
        Zwraca listę PowerUsageFrame (tak jak pricing_* zwraca listy ramek).
        """
        if not self.access_token:
            raise RuntimeError("Brak access tokena — zaloguj się lub użyj from_tokens().")

        params = {
            "resolution": resolution,
            "window_start": iso_utc(window_start),
            "window_end": iso_utc(window_end),
        }
        url = f"{self.ep.power_usage(meter_id)}?{urlencode(params)}"
        data = await self._get_json(url)
        frames = (data or {}).get("frames") or []
        return [PowerUsageFrame.from_dict(item) for item in frames]
    
    # --------- NEW: dzienne koszty z podsumowaniami ---------
    async def get_power_cost_day(
        self,
        meter_id: int,
        window_start: datetime,
        window_end: datetime,
        *,
        resolution: str = "hour",
    ) -> PowerCostDay:
        """
        Zwraca komplet: [frames] + wszystkie total_* z API (jak w przykładzie JSON).
        """
        if not self.access_token:
            raise RuntimeError("Brak access tokena — zaloguj się lub użyj from_tokens().")

        params = {
            "resolution": resolution,
            "window_start": iso_utc(window_start),
            "window_end": iso_utc(window_end),
        }
        url = f"{self.ep.power_cost(meter_id)}?{urlencode(params)}"
        data = await self._get_json(url)
        return PowerCostDay.from_dict(data or {})
    
    async def get_power_usage_day(
        self,
        meter_id: int,
        window_start: datetime,
        window_end: datetime,
        *,
        resolution: str = "hour",
    ) -> PowerUsageDay:
        """
        Zwraca komplet: [frames] + fae_total_usage, rae_total, energy_balance
        dokładnie tak, jak daje API w root JSON.
        """
        if not self.access_token:
            raise RuntimeError("Brak access tokena — zaloguj się lub użyj from_tokens().")

        params = {
            "resolution": resolution,
            "window_start": iso_utc(window_start),
            "window_end": iso_utc(window_end),
        }
        url = f"{self.ep.power_usage(meter_id)}?{urlencode(params)}"
        data = await self._get_json(url)
        return PowerUsageDay.from_api_dict(data or {})    
    
    # --------- NEW: naliczone koszty energii (lista ramek) ---------
    async def get_power_cost_hourly(
        self,
        meter_id: int,
        window_start: datetime,
        window_end: datetime,
        *,
        resolution: str = "hour",
    ) -> list[PowerCostFrame]:
        """
        GET /api/meter-data/{meter_id}/power-cost/?resolution=hour&window_start=...&window_end=...
        Zwraca listę PowerCostFrame (tak jak power-usage/pricing_* zwracają listy ramek).
        """
        if not self.access_token:
            raise RuntimeError("Brak access tokena — zaloguj się lub użyj from_tokens().")

        params = {
            "resolution": resolution,
            "window_start": iso_utc(window_start),
            "window_end": iso_utc(window_end),
        }
        url = f"{self.ep.power_cost(meter_id)}?{urlencode(params)}"
        data = await self._get_json(url)
        frames = (data or {}).get("frames") or []
        return [PowerCostFrame.from_dict(item) for item in frames]

    async def aclose(self) -> None:
        if self.session is not None:
            await self.session.close()
            self.session = None
