"""Octopus Intelligent (Italia) Home Assistant integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import aiohttp_client

from .const import (
    CONF_ACCOUNT_NUMBER,
    CONF_GRAPHQL_URL,
    CONF_REFRESH_EXPIRES_AT,
    CONF_REFRESH_TOKEN,
    CONF_SCAN_INTERVAL,
    DEFAULT_GRAPHQL_URL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import OctopusDataUpdateCoordinator
from .kraken_client import KrakenClient

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Octopus Intelligent (Italia) from a config entry."""
    refresh_token: str = entry.data[CONF_REFRESH_TOKEN]
    refresh_expires_at: int | None = entry.data.get(CONF_REFRESH_EXPIRES_AT)
    account_number: str = entry.data[CONF_ACCOUNT_NUMBER]
    graphql_url: str = entry.data.get(CONF_GRAPHQL_URL, DEFAULT_GRAPHQL_URL)

    scan_interval: int = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)

    session = aiohttp_client.async_get_clientsession(hass)

    def _on_refresh_change(new_token: str, new_exp: int) -> None:
        """Persist a rotated refresh token back to the config entry."""
        _LOGGER.debug("Octopus IT refresh token rotated; persisting new token")
        hass.config_entries.async_update_entry(
            entry,
            data={
                **entry.data,
                CONF_REFRESH_TOKEN: new_token,
                CONF_REFRESH_EXPIRES_AT: new_exp,
            },
        )

    client = KrakenClient(
        session=session,
        graphql_url=graphql_url,
        refresh_token=refresh_token,
        refresh_expires_at=refresh_expires_at,
        on_refresh_token_change=_on_refresh_change,
    )

    coordinator = OctopusDataUpdateCoordinator(
        hass=hass,
        client=client,
        account_number=account_number,
        scan_interval=scan_interval,
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Reload the entry when options change (e.g. scan_interval updated)
    entry.async_on_unload(entry.add_update_listener(_async_reload_on_options_change))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload an Octopus Intelligent (Italia) config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok


async def _async_reload_on_options_change(
    hass: HomeAssistant, entry: ConfigEntry
) -> None:
    """Reload the config entry when options are updated."""
    await hass.config_entries.async_reload(entry.entry_id)
