from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone, date
from typing import Any, Optional

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .pstryklib.pstryk_api_client import PstrykApiClient
from .pstryklib.utils import iso_utc
from .time_utils import euwarsaw, local_day_window_utc, local_day_window_utc_ms

_LOGGER = logging.getLogger(__name__)

class PstrykCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Koordynator danych dla integracji Pstryk.

    Zadania koordynatora:
    - Trzyma odnośnik do klienta API (`self.client`).
    - W `_async_update_data()` pobiera komplet danych dla UI/sensorów:
      * informacje o użytkowniku,
      * listę liczników (meters),
      * okna czasowe (buy/sell/usage/cost) liczone dla DOBA LOKALNA → w UTC,
      * per licznik: alerty, pricing (kupno/sprzedaż), zużycie (ramki + sumy),
        koszty (ramki + sumy lub sumowanie lokalne jako fallback).
    - Zwraca spójny „snapshot” w postaci dictu, którym karmione są encje.

    Uwaga:
    - Sam koordynator NIE ma ustawionego `update_interval` — odświeżanie wyzwalane jest
      ręcznie timerem w `__init__.py` (xx:59:30 UTC) oraz na żądanie encji.
    - Klient PstrykApiClient samodzielnie odświeża access_token przy 401 (retry w `_get_json()`),
      więc `_async_update_data()` nie musi specjalnie obsługiwać odświeżania tokenów.
    """

    def __init__(self, hass: HomeAssistant, client: PstrykApiClient) -> None:
        """Inicjalizacja koordynatora.

        :param hass: Kontekst Home Assistant.
        :param client: Zainicjalizowany klient API (po stronie __init__.py budowany z tokenów).
        """
        super().__init__(hass, logger=_LOGGER, name="PstrykCoordinator")
        self.client = client

    async def _async_update_data(self) -> dict[str, Any]:
        """GŁÓWNA metoda pobierania danych.

        Wywoływana przez HA, gdy encje odświeżają dane lub gdy timer/triggery wywołają refresh.
        Zwraca słownik z kluczami:
          - ts_utc: znacznik czasu (ISO) wykonania pobrania (UTC),
          - user_id: ID użytkownika (z klienta lub user_info),
          - user_info: pełniejsza struktura o użytkowniku (jeśli dostępna),
          - meters: lista liczników (z API),
          - per_meter: dict[meter_id] -> dane szczegółowe (alerts, pricing, usage, cost),
          - windows: okna czasowe użyte do zapytań (buy/sell/usage/cost), w ISO (UTC).

        Każda sekcja danych jest odporna na wyjątki (try/except) — błąd jednej części
        nie zatrzymuje całej aktualizacji; logujemy debug i wstawiamy wartości puste/None.
        """
        # Bieżący czas w UTC (znacznik TS w wynikach) i data lokalna (dla wyznaczania doby).
        now_utc = datetime.now(timezone.utc)
        today_local = datetime.now(euwarsaw()).date()

        # -----------------------
        # 1) USER
        # -----------------------
        user_id: Optional[int] = getattr(self.client, "user_id", None)

        # -----------------------
        # 2) METERS
        # -----------------------
        meters: list[Any] = []
        try:
            meters = await self.client.get_meters()
        except Exception as e:
            _LOGGER.debug("meters fetch failed: %r", e)
            meters = []

        # -----------------------
        # 3) OKNA CZASOWE (UTC)
        # -----------------------
        # Dla pricing używamy [start, end) — pełna doba lokalna.
        buy_start, buy_end = local_day_window_utc(today_local)
        sell_start, sell_end = buy_start, buy_end

        # Dla usage/cost przyjmujemy zakres „zamknięty” końcem dnia o 1 ms — by nie zgubić końcówki.
        usage_start, usage_end = local_day_window_utc_ms(today_local)
        cost_start, cost_end = usage_start, usage_end

        # -----------------------
        # 4) PER-METER DANE
        # -----------------------
        per_meter: dict[int, dict[str, Any]] = {}

        for m in meters or []:
            # Ustal ID licznika — pomijamy obiekty bez identyfikatora.
            mid = getattr(m, "id", None)
            if mid is None:
                continue

            slot: dict[str, Any] = {}
            per_meter[mid] = slot

            # 4.1) ALERTY cenowe
            try:
                slot["alerts"] = await self.client.get_full_price_alerts(mid)
            except Exception as e:
                _LOGGER.debug("alerts fetch failed for meter %s: %r", mid, e)
                slot["alerts"] = None

            # 4.2) PRICING BUY (ceny zakupu energii)
            try:
                slot["pricing_buy"] = await self.client.get_pricing_buy(
                    meter_id=mid, window_start=buy_start, window_end=buy_end, resolution="hour"
                )
            except Exception as e:
                _LOGGER.debug("pricing_buy fetch failed for meter %s: %r", mid, e)
                slot["pricing_buy"] = None

            # 4.3) PRICING SELL (ceny sprzedaży/odsprzedaży)
            try:
                slot["pricing_sell"] = await self.client.get_pricing_sell(
                    window_start=sell_start, window_end=sell_end, resolution="hour"
                )
            except Exception as e:
                _LOGGER.debug("pricing_sell fetch failed for meter %s: %r", mid, e)
                slot["pricing_sell"] = None

            # 4.4) ZUŻYCIE ENERGII: ramki + sumy
            try:
                pud = await self.client.get_power_usage_day(
                    meter_id=mid, window_start=usage_start, window_end=usage_end, resolution="hour"
                )
                slot["power_usage_frames"] = pud.frames
                slot["power_usage_totals"] = {
                    "fae_total_usage": pud.fae_total_usage,
                    "rae_total": pud.rae_total,
                    "energy_balance": pud.energy_balance,
                }
            except Exception as e:
                _LOGGER.debug("power_usage_day fetch failed for meter %s: %r", mid, e)
                slot["power_usage_frames"] = None
                slot["power_usage_totals"] = None

            # 4.5) KOSZTY ENERGII: ramki + sumy
            try:
                pcd = await self.client.get_power_cost_day(
                    meter_id=mid, window_start=cost_start, window_end=cost_end, resolution="hour"
                )
                slot["power_cost_frames"] = pcd.frames
                slot["power_cost_totals"] = {
                    "fae_total_cost": pcd.fae_total_cost,
                    "total_energy_sold_value": pcd.total_energy_sold_value,
                    "total_energy_balance_value": pcd.total_energy_balance_value,
                    "total_sales_cost_net": pcd.total_sales_cost_net,
                    "total_service_cost_net": pcd.total_service_cost_net,
                    "total_dist_cost_net": pcd.total_dist_cost_net,
                    "total_excise": pcd.total_excise,
                    "total_vat": pcd.total_vat,
                    "total_energy_cost_with_service": pcd.total_energy_cost_with_service,
                    "total_var_dist_cost_net": pcd.total_var_dist_cost_net,
                    "total_fix_dist_cost_net": pcd.total_fix_dist_cost_net,
                    "total_energy_cost_net": pcd.total_energy_cost_net,
                }
            except Exception as e:
                _LOGGER.debug("power_cost_day fetch failed for meter %s: %r", mid, e)
                slot["power_cost_frames"] = None
                slot["power_cost_totals"] = None

        # -----------------------
        # 5) ZŁÓŻ I ZWRÓĆ SNAPSHOT
        # -----------------------
        return {
            "ts_utc": now_utc.isoformat(),   # znacznik czasu wykonania refreshu (UTC, ISO)
            "user_id": user_id,              # wywnioskowany ID użytkownika
            "meters": meters,                # lista liczników (obiekty biblioteki)
            "per_meter": per_meter,          # dane szczegółowe per licznik
            "windows": {                     # okna czasowe użyte do zapytań (ISO w UTC)
                "buy": (iso_utc(buy_start), iso_utc(buy_end)),
                "sell": (iso_utc(sell_start), iso_utc(sell_end)),
                "usage": (iso_utc(usage_start), iso_utc(usage_end)),
                "cost": (iso_utc(cost_start), iso_utc(cost_end)),
            },
        }