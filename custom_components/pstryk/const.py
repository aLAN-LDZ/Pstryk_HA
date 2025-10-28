from __future__ import annotations
from homeassistant.const import Platform

DOMAIN = "pstryk"

PLATFORMS: list[Platform] = [Platform.SENSOR]

# entry.data
CONF_EMAIL = "email"
CONF_USER_ID = "user_id"
CONF_ACCESS = "access"
CONF_REFRESH = "refresh"

# hass.data klucze
DATA_CLIENT = "client"
DATA_COORDINATOR = "coordinator"
DATA_UNSUB = "unsub"  # do odpinania timera