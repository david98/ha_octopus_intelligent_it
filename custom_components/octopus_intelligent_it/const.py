"""Constants for the Octopus Intelligent (Italia) integration."""

from __future__ import annotations

import json
import pathlib

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


def _read_manifest_version() -> str:
    """Read the integration version from manifest.json at import time."""
    try:
        manifest = pathlib.Path(__file__).parent / "manifest.json"
        return json.loads(manifest.read_text())["version"]
    except Exception:
        return "unknown"


# Single User-Agent used for all Kraken API calls. Version is read from
# manifest.json so it stays in sync with release-please version bumps.
INTEGRATION_USER_AGENT = f"ha-octopus-intelligent-it/{_read_manifest_version()}"

# Client fingerprint extracted from the official Octopus Italia mobile app
# (iOS) network captures. Sent only on the login request (alongside
# INTEGRATION_USER_AGENT) as required by the Kraken API to authenticate the
# client. Not a user secret, but may need to be rotated if Octopus updates
# the mobile app or starts rejecting this value.
KRAKEN_FLAPJACK = "d87595aac6aff50a6012190b5a90161f4bd7afde5c0a0051b471054b39296d0e"
