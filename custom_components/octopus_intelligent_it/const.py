"""Constants for the Octopus Intelligent (Italia) integration."""

from __future__ import annotations

from homeassistant.const import Platform

DOMAIN = "octopus_intelligent_it"

DEFAULT_GRAPHQL_URL = "https://api.oeit-kraken.energy/v1/graphql/"

CONF_REFRESH_TOKEN = "refresh_token"
CONF_REFRESH_EXPIRES_AT = "refresh_expires_at"
CONF_ACCOUNT_NUMBER = "account_number"
CONF_GRAPHQL_URL = "graphql_url"
CONF_SCAN_INTERVAL = "scan_interval"

DEFAULT_SCAN_INTERVAL = 300  # seconds

DAYS_OF_WEEK = [
    "MONDAY",
    "TUESDAY",
    "WEDNESDAY",
    "THURSDAY",
    "FRIDAY",
    "SATURDAY",
    "SUNDAY",
]

MANUFACTURER = "Octopus Energy"

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.SELECT,
    Platform.TIME,
    Platform.NUMBER,
]
