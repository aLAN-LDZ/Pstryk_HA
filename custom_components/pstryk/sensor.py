from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.const import EntityCategory, UnitOfEnergy
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from .const import DOMAIN, DATA_COORDINATOR

# Bezpiecznie wykrywamy klasę urządzenia "monetarną".
# W starszych wersjach HA mogło jej nie być – wtedy po prostu nie ustawiamy device_class.
try:
    _MONETARY = SensorDeviceClass.MONETARY
except Exception:
    _MONETARY = None


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
) -> None:
    """Rejestruje encje dla danego wpisu (ConfigEntry).

    Pobiera koordynatora z hass.data[DOMAIN][entry_id] i tworzy zestaw encji:
      - diagnostyczne: User ID, Last API Fetch
      - ENERGY (kWh) – dzienne sumy: zużycie (fae), sprzedaż (rae), bilans
      - COST (PLN) – dzienny koszt prądu (fae_total_cost + atrybuty)

    Encje dziedziczą po CoordinatorEntity, więc ich stan aktualizuje się
    automatycznie, gdy coordinator.data się zmieni (po refreshu).
    """
    store = hass.data[DOMAIN][entry.entry_id]
    coordinator = store[DATA_COORDINATOR]

    entities: list[SensorEntity] = [
        PstrykUserIdSensor(entry, coordinator),
        PstrykLastFetchSensor(entry, coordinator),
        PstrykPrimaryMeterIdSensor(entry, coordinator),
        PstrykPrimaryMeterIpSensor(entry, coordinator),

        # ENERGY (kWh) – dzienne sumy (z coordinator.data["per_meter"][<id>]["power_usage_totals"])
        PstrykDailyFaeUsageSensor(entry, coordinator),
        PstrykDailyRaeTotalSensor(entry, coordinator),
        PstrykDailyEnergyBalanceSensor(entry, coordinator),

        # COST (PLN) – dzienna suma (z coordinator.data["per_meter"][<id>]["power_cost_totals"])
        PstrykDailyFaeCostSensor(entry, coordinator),
    ]
    # True -> od razu zainicjuj update (coordinator already has first_refresh)
    async_add_entities(entities, True)


class _BasePstrykSensor(CoordinatorEntity, SensorEntity):
    """Baza dla encji Pstryk.

    Wspólne elementy:
      - powiązanie z koordynatorem,
      - device_info integracji (wszystkie encje grupują się pod jednym urządzeniem "Pstryk"),
      - helpery do wyciągania:
          * _primary_meter_id(): ID „głównego” licznika (pierwszy z listy),
          * _usage_totals(): dict z totals dla zużycia,
          * _cost_totals(): dict z totals dla kosztów.

    Uwaga: „główny” licznik to po prostu pierwszy z listy meters zwróconej przez koordynatora.
    Jeśli kiedyś zechcesz wspierać wiele liczników na encję, dodaj parametr/konfigurację wyboru.
    """

    _attr_has_entity_name = True  # pozwala używać zgrabnych nazw bez prefiksu integracji

    def __init__(self, entry: ConfigEntry, coordinator) -> None:
        super().__init__(coordinator)
        self._entry = entry

    @property
    def device_info(self):
        """Grupuje wszystkie encje pod jednym „urządzeniem” w HA."""
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": "Pstryk",
            "manufacturer": "Pstryk",
            "model": "Cloud API",
        }

    # --- Helpers do odczytu danych z coordinator.data ---

    def _primary_meter_id(self) -> Optional[int]:
        """Zwraca ID pierwszego licznika z listy `coordinator.data["meters"]`.

        Zwracane obiekty meters pochodzą z biblioteki (mogą być klasami), więc
        obsługujemy oba przypadki: dict (API raw) lub obiekt z atrybutem .id.
        """
        data: dict[str, Any] = self.coordinator.data or {}
        meters = data.get("meters") or []
        if not meters:
            return None
        m0 = meters[0]
        return m0.get("id") if isinstance(m0, dict) else getattr(m0, "id", None)

    def _primary_meter_id_str(self) -> Optional[str]:
        """Zwraca stringowy meter_id pierwszego licznika (np. 'c0cdd60db658')."""
        data: dict[str, Any] = self.coordinator.data or {}
        meters = data.get("meters") or []
        if not meters:
            return None
        m0 = meters[0]
        return m0.get("meter_id") if isinstance(m0, dict) else getattr(m0, "meter_id", None)

    def _primary_meter_ip_addr(self) -> Optional[str]:
        """Zwraca IP pierwszego licznika (details.device.ip) lub None, gdy brak danych."""
        data: dict[str, Any] = self.coordinator.data or {}
        meters = data.get("meters") or []
        if not meters:
            return None
        m0 = meters[0]
        return getattr(m0.details.device, "ip", None)
    
    def _usage_totals(self) -> Optional[dict[str, float]]:
        """Zwraca słownik totals dla dziennego zużycia energii lub None, gdy brak danych."""
        data: dict[str, Any] = self.coordinator.data or {}
        mid = self._primary_meter_id()
        if mid is None:
            return None
        pm = (data.get("per_meter") or {}).get(mid) or {}
        totals = pm.get("power_usage_totals")
        return totals if isinstance(totals, dict) else None

    def _cost_totals(self) -> Optional[dict[str, float]]:
        """Zwraca słownik totals dla dziennych kosztów energii lub None, gdy brak danych."""
        data: dict[str, Any] = self.coordinator.data or {}
        mid = self._primary_meter_id()
        if mid is None:
            return None
        pm = (data.get("per_meter") or {}).get(mid) or {}
        totals = pm.get("power_cost_totals")
        return totals if isinstance(totals, dict) else None


class PstrykUserIdSensor(_BasePstrykSensor):
    """Sensor diagnostyczny – ID użytkownika (z coordinator.data["user_id"])."""

    _attr_name = "User ID"
    _attr_icon = "mdi:account"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, entry: ConfigEntry, coordinator) -> None:
        super().__init__(entry, coordinator)
        self._attr_unique_id = f"{entry.entry_id}_user_id"

    @property
    def native_value(self) -> Optional[int]:
        """Zwraca user_id z koordynatora.

        Historycznie był plan „user_info”, ale koordynator już tego nie używa,
        więc sprawdzamy tylko 'user_id'.
        """
        data: dict[str, Any] = self.coordinator.data or {}
        return data.get("user_id")


class PstrykLastFetchSensor(_BasePstrykSensor):
    """Sensor diagnostyczny – timestamp ostatniego udanego pobrania z API."""

    _attr_name = "Last API Fetch"
    _attr_icon = "mdi:clock-check"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, entry: ConfigEntry, coordinator) -> None:
        super().__init__(entry, coordinator)
        self._attr_unique_id = f"{entry.entry_id}_last_fetch"

    @property
    def native_value(self) -> Optional[datetime]:
        """Zwraca `datetime` w UTC z pola 'ts_utc' (ISO-8601) snapshotu koordynatora.

        HA oczekuje tu obiektu datetime z tzinfo; jeśli string był bez strefy, dociągamy UTC.
        """
        data: dict[str, Any] = self.coordinator.data or {}
        ts = data.get("ts_utc")
        if not ts:
            return None
        try:
            dt = datetime.fromisoformat(ts)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except Exception:
            return None


class _BaseEnergyTodaySensor(_BasePstrykSensor):
    """Baza dla dziennych sensorów ENERGY (kWh)."""

    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_state_class = SensorStateClass.TOTAL
    _attr_icon = "mdi:lightning-bolt"

    @property
    def extra_state_attributes(self):
        """Dodatkowe atrybuty: okno czasu (UTC ISO) użyte przy liczeniu dziennych wartości."""
        data: dict[str, Any] = self.coordinator.data or {}
        windows = data.get("windows") or {}
        usage = windows.get("usage")
        if isinstance(usage, (list, tuple)) and len(usage) == 2:
            return {"window_start": usage[0], "window_end": usage[1]}
        return None


class PstrykDailyFaeUsageSensor(_BaseEnergyTodaySensor):
    """Dzisiejsze zużycie energii (fae_total_usage, kWh)."""

    _attr_name = "Dzisiejsze Zużycie Prądu"

    def __init__(self, entry: ConfigEntry, coordinator) -> None:
        super().__init__(entry, coordinator)
        self._attr_unique_id = f"{entry.entry_id}_daily_fae_total_usage"

    @property
    def native_value(self) -> Optional[float]:
        totals = self._usage_totals()
        if not totals:
            return None
        return float(totals.get("fae_total_usage", 0))


class PstrykDailyRaeTotalSensor(_BaseEnergyTodaySensor):
    """Dzisiejsza energia oddana (sprzedaż, rae_total, kWh)."""

    _attr_name = "Dzisiejsza Sprzedaż Prądu"

    def __init__(self, entry: ConfigEntry, coordinator) -> None:
        super().__init__(entry, coordinator)
        self._attr_unique_id = f"{entry.entry_id}_daily_rae_total"

    @property
    def native_value(self) -> Optional[float]:
        totals = self._usage_totals()
        if not totals:
            return None
        return float(totals.get("rae_total", 0))


class PstrykDailyEnergyBalanceSensor(_BaseEnergyTodaySensor):
    """Dzisiejsze zbilansowane zużycie (fae_total_usage - rae_total, kWh)."""

    _attr_name = "Dzisiejsze Zbilansowane Zużycie Prądu"

    def __init__(self, entry: ConfigEntry, coordinator) -> None:
        super().__init__(entry, coordinator)
        self._attr_unique_id = f"{entry.entry_id}_daily_energy_balance"

    @property
    def native_value(self) -> Optional[float]:
        totals = self._usage_totals()
        if not totals:
            return None
        return float(totals.get("energy_balance", 0))


class PstrykDailyFaeCostSensor(_BasePstrykSensor):
    """Dzisiejszy koszt energii (PLN) + wybrane atrybuty kosztowe."""

    _attr_name = "Dzisiejszy Koszt Prądu"
    _attr_state_class = SensorStateClass.TOTAL
    _attr_icon = "mdi:cash"

    def __init__(self, entry: ConfigEntry, coordinator) -> None:
        super().__init__(entry, coordinator)
        self._attr_unique_id = f"{entry.entry_id}_daily_fae_total_cost"
        # jednostka walutowa
        self._attr_native_unit_of_measurement = "PLN"
        # ustaw klasę monetarną, jeśli występuje w tej wersji HA (wpływa na formatowanie w UI)
        if _MONETARY is not None:
            self._attr_device_class = _MONETARY

    @property
    def native_value(self) -> Optional[float]:
        """Główna wartość – fae_total_cost (PLN) z totals."""
        totals = self._cost_totals()
        if not totals:
            return None
        val = totals.get("fae_total_cost")
        return None if val is None else float(val)

    @property
    def extra_state_attributes(self) -> Optional[dict[str, Any]]:
        """Atrybuty dodatkowe: rozbicie kosztów + okno czasu (UTC ISO)."""
        totals = self._cost_totals()
        if not totals:
            return None

        attrs = {
            "Dzisiejszy Koszt Dystrybucji": totals.get("total_dist_cost_net"),
            "Dzisiejszy Podatek VAT": totals.get("total_vat"),
            "Dzisiejszy Koszt Prądu z Serwisem": totals.get("total_energy_cost_with_service"),
        }

        # Dodaj również okno czasu (spójnie z sensorami energii, ale dla 'cost').
        data: dict[str, Any] = self.coordinator.data or {}
        window = (data.get("windows") or {}).get("cost")
        if isinstance(window, (list, tuple)) and len(window) == 2:
            attrs["window_start"] = window[0]
            attrs["window_end"] = window[1]
        return attrs
    
class PstrykPrimaryMeterIdSensor(_BasePstrykSensor):
    """Sensor diagnostyczny – stringowy meter_id pierwszego licznika."""

    _attr_name = "Meter ID"
    _attr_icon = "mdi:identifier"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, entry: ConfigEntry, coordinator) -> None:
        super().__init__(entry, coordinator)
        self._attr_unique_id = f"{entry.entry_id}_primary_meter_id_str"

    @property
    def native_value(self) -> Optional[str]:
        return self._primary_meter_id_str()
    
class PstrykPrimaryMeterIpSensor(_BasePstrykSensor):
    """Sensor diagnostyczny – IP pierwszego licznika."""

    _attr_name = "Meter IP Address"
    _attr_icon = "mdi:network"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, entry: ConfigEntry, coordinator) -> None:
        super().__init__(entry, coordinator)
        self._attr_unique_id = f"{entry.entry_id}_primary_meter_ip_addr"

    @property
    def native_value(self) -> Optional[str]:
        return self._primary_meter_ip_addr()