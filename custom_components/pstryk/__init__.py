from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_utc_time_change

# Stałe i „klucze” współdzielone w integracji:
# - DOMAIN: nazwa domeny integracji (np. "pstryk")
# - PLATFORMS: lista platform HA, które rejestrujemy (np. ["sensor"])
# - CONF_*: nazwy pól przechowywanych w entry.data (tokeny, user_id)
# - DATA_*: klucze do słownika hass.data[DOMAIN][entry_id]
from .const import (
    DOMAIN,
    PLATFORMS,
    CONF_USER_ID,
    CONF_ACCESS,
    CONF_REFRESH,
    DATA_CLIENT,
    DATA_COORDINATOR,
    DATA_UNSUB,
)

# Koordynator to warstwa „cache + harmonogram” z HA (DataUpdateCoordinator),
# do której podłączają się encje (np. sensory), aby pobierać z niej aktualne dane.
from .coordinator import PstrykCoordinator

# Klient HTTP do Pstryk API. Potrafi:
# - zbudować się z tokenów (from_tokens)
# - odświeżyć access_token (refresh_access)
# - samodzielnie retry’ować request po 401 (w _get_json)
from .pstryklib.pstryk_api_client import PstrykApiClient


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Minimalny setup integracji na starcie HA.

    Wywoływany wcześnie, przed wczytaniem config entries.
    W tej integracji nic tu nie robimy — zwracamy True, aby HA wiedział, że „setup” się powiódł.
    """
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Główna inicjalizacja JEDNEGO wpisu konfiguracyjnego (ConfigEntry).

    Co się tu dzieje (kolejność kroków):
    1) Przygotowanie przestrzeni w hass.data i lok. store na uchwyty tej instancji.
    2) Odczyt tokenów i user_id z entry.data zapisanych przez config_flow.
    3) Jeśli tokenów brakuje — inicjujemy reauth i PRZERYWAMY setup (return False).
    4) Tworzymy klienta API z tokenów.
    5) Wykonujemy „opportunistic refresh” access_token na starcie (jeśli refresh_token ważny).
       - jeżeli access się zmienił, aktualizujemy entry.data (persist).
       - jeśli refresh się nie uda (np. refresh_token wygasł) — odpalamy reauth i PRZERYWAMY setup.
    6) Tworzymy koordynatora + robimy pierwsze odświeżenie danych.
    7) Rejestrujemy zegarowy callback (UTC) na HH:59:30, który żąda odświeżenia koordynatora.
       Uwaga: to idzie w UTC — przy DST offset względem czasu lokalnego się zmienia.
    8) Odkładamy uchwyty (client, coordinator, unsub) do hass.data[DOMAIN][entry_id].
    9) Forwardujemy setup platform (np. sensor.py).
    """

    # 1) Struktura pamięci dla tej instancji wpisu (entry)
    hass.data.setdefault(DOMAIN, {})
    store: dict[str, Any] = {}

    # 2) Dane konfiguracyjne zapisane przez config_flow (tokeny, user_id)
    data = entry.data or {}
    access = data.get(CONF_ACCESS)
    refresh = data.get(CONF_REFRESH)
    user_id = data.get(CONF_USER_ID)

    # 3) Jeśli nie mamy kompletu tokenów — nie uruchamiamy pół-aktywnej integracji.
    #    Wywołujemy reauth flow i kończymy. Po udanym reauth HA ponownie spróbuje setup_entry.
    if not access or not refresh:
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": "reauth", "entry_id": entry.entry_id},
                data=entry.data,
            )
        )
        return False

    # 4) Budujemy klienta z tokenów. Klient sam umie odświeżyć access przy 401.
    client = PstrykApiClient.from_tokens(access=access, refresh=refresh, user_id=user_id)

    # 5) „Opportunistic refresh”: na starcie odśwież access_token (o ile refresh_token jeszcze żyje).
    #    Dzięki temu od początku mamy „świeży” access i unikamy 401 przy pierwszych callach koordynatora.
    try:
        old_access = access
        await client.refresh_access()
        if client.access_token and client.access_token != old_access:
            # Zapisz nowy access do entry.data (persist na dysk), opcjonalnie user_id jeśli backend zwrócił.
            new_data = dict(data)
            new_data[CONF_ACCESS] = client.access_token
            new_data[CONF_USER_ID] = client.user_id
            hass.config_entries.async_update_entry(entry, data=new_data)
    except Exception:
        # Jeżeli tu wpadniemy, to najczęściej znaczy: refresh_token wygasł / jest nieprawidłowy.
        # Uruchamiamy reauth i NIE podnosimy integracji (return False). Po reauth HA znów zawoła setup_entry.
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": "reauth", "entry_id": entry.entry_id},
                data=entry.data,
            )
        )
        return False

    # 6) Koordynator pobiera dane z API i udostępnia je encjom. Pierwsze odświeżenie na starcie.
    coordinator = PstrykCoordinator(hass, client)
    await coordinator.async_config_entry_first_refresh()

    # 7) Harmonogram odświeżeń: celowo „tuż przed” zmianą doby (xx:59:30 UTC),
    @callback
    async def _on_tick(now: datetime) -> None:
        # Ręcznie wołamy koordynatora o refresh. Sam coordinator decyduje co i jak pobrać.
        await coordinator.async_request_refresh()

    unsub = async_track_utc_time_change(
        hass,
        _on_tick,
        minute=59,
        second=30,
    )

    # 8) Odkładamy uchwyty do hass.data, żeby inne moduły (np. sensor.py) mogły ich użyć.
    #    store trzymamy „per entry”, aby przy wielu licznikach każde entry miało własne zasoby.
    store[DATA_CLIENT] = client
    store[DATA_COORDINATOR] = coordinator
    store[DATA_UNSUB] = unsub
    hass.data[DOMAIN][entry.entry_id] = store

    # 9) Rejestrujemy platformy (np. tworzenie sensorów). HA zawoła odpowiednie pliki (sensor.py itd.).
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Sprzątanie po danym wpisie (ConfigEntry) przy wyłączaniu/usuwaniu integracji.

    Kroki:
    1) Wyjmij store dla tego entry z hass.data[DOMAIN].
    2) Odsubskrybuj timer (jeśli był zarejestrowany).
    3) Poproś HA o unload platform (usunie encje z UI i zatrzyma ich aktualizacje).
    4) Zamknij klienta HTTP (zamyka sesję aiohttp).
    5) Zwróć True/False czy unload platform się powiódł.
    """

    # 1) Zdejmujemy uchwyty ze wspólnej przestrzeni. .pop() zwróci pusty dict, jeśli nie znajdzie.
    store = hass.data.get(DOMAIN, {}).pop(entry.entry_id, {})

    # 2) Zdejmujemy harmonogram (jeśli był).
    unsub = store.get(DATA_UNSUB)
    if callable(unsub):
        unsub()

    # 3) Odłącz platformy (np. sensory). Jeśli HA zwróci False — coś nie poszło.
    ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    # 4) Zamknij klienta (sesję HTTP). Defensywnie: jeśli klienta nie ma — pomiń.
    client = store.get(DATA_CLIENT)
    try:
        await client.aclose()
    except Exception:
        pass

    # 5) Zwracamy wynik unloadu platform. Jeśli False — HA może spróbować ponownie.
    return ok