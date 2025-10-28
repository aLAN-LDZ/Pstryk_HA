from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

# Wspólne stałe używane w całej integracji:
# - DOMAIN: nazwa domeny integracji
# - CONF_EMAIL / CONF_USER_ID / CONF_ACCESS / CONF_REFRESH: klucze używane w entry.data
from .const import DOMAIN, CONF_EMAIL, CONF_USER_ID, CONF_ACCESS, CONF_REFRESH

# Klient do API Pstryk. W tym flow używamy go TYLKO do jednorazowego logowania,
# aby pozyskać tokeny i user_id (potem sesję zamykamy w finally).
from .pstryklib.pstryk_api_client import PstrykApiClient

# Schemat formularza pierwszego kroku (step_id="user"):
# - wymagamy email i password
STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required("email"): str,
        vol.Required("password"): str,
    }
)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Flow tworzenia wpisu konfiguracyjnego (ConfigEntry) dla integracji Pstryk.

    Ten flow uruchamia się, gdy użytkownik dodaje integrację w UI.
    Zakres odpowiedzialności:
    - zebrać od użytkownika email/hasło,
    - zalogować się do API, by otrzymać refresh/access tokeny oraz user_id,
    - zapisać te dane w `entry.data` (HA przechowuje je później na dysku),
    - NIE tworzyć długotrwałych połączeń (klient zamykamy w `finally`).
    """

    # Wersjonowanie flow — ułatwia przyszłe migracje entry:
    VERSION = 1

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        """Pierwszy (i jedyny) krok kreatora — prosi o email i hasło.

        Przebieg:
        1) Gdy brak user_input → pokaż formularz (email, password).
        2) Gdy input jest podany → waliduj i loguj do API:
           - ustaw unikalne ID wpisu na bazie emaila (by uniknąć duplikatów),
           - odpal `PstrykApiClient(email, password).login()` — otrzymasz tokeny i user_id,
           - utwórz `ConfigEntry` z danymi (email, user_id, access, refresh).
        3) W razie błędów logowania → pokaż formularz ponownie z `errors["base"] = "auth"`.
        4) W `finally` zawsze zamknij klienta (zamyka sesję HTTP).
        """
        # 1) Brak danych — wyświetlamy formularz w UI
        if user_input is None:
            return self.async_show_form(step_id="user", data_schema=STEP_USER_DATA_SCHEMA)

        # 2) Mamy dane z formularza — wyciągamy i wstępnie normalizujemy
        email: str = user_input["email"].strip()
        password: str = user_input["password"]

        # Ustal unikalność wpisu po emailu: "pstryk:<email>".
        # Jeśli już istnieje wpis o takim unique_id → przerwij (HA pokaże info, że już skonfigurowano).
        await self.async_set_unique_id(f"pstryk:{email.lower()}")
        self._abort_if_unique_id_configured()

        errors: dict[str, str] = {}

        # Tymczasowy klient do zalogowania i pozyskania tokenów.
        client = PstrykApiClient(email=email, password=password)

        try:
            # 3) Logowanie do API — jeśli się powiedzie, klient będzie miał:
            #    - client.access_token
            #    - client.refresh_token
            #    - client.user_id
            await client.login()

            # 4) Przygotuj dane do zapisania w ConfigEntry (persist w HA)
            data = {
                CONF_EMAIL: email,
                CONF_USER_ID: getattr(client, "user_id", None),
                CONF_ACCESS: getattr(client, "access_token", None),
                CONF_REFRESH: getattr(client, "refresh_token", None),
            }

            # 5) Zakończ flow utworzeniem wpisu. Tytuł pojawi się w UI.
            return self.async_create_entry(title=f"Pstryk ({email})", data=data)

        except Exception:
            # 6) Coś poszło nie tak (błędny login/hasło, problemy sieciowe lub inny błąd).
            #    Pokaż ponownie formularz z błędem bazowym "auth".
            errors["base"] = "auth"
            return self.async_show_form(
                step_id="user",
                data_schema=STEP_USER_DATA_SCHEMA,
                errors=errors,
            )
        finally:
            # 7) Niezależnie od wyniku — zamykamy klienta (zamyka sesję aiohttp).
            try:
                await client.aclose()
            except Exception:
                pass