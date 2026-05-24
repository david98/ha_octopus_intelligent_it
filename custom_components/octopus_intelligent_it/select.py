"""Select platform for the Octopus Intelligent (Italia) integration."""

from __future__ import annotations

import logging

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import OctopusDataUpdateCoordinator
from .entity import OctopusDeviceEntity

_LOGGER = logging.getLogger(__name__)

_UNIT_OPTIONS = ["PERCENTAGE", "KILOWATT_HOURS"]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Octopus Intelligent (Italia) select entities from a config entry."""
    coordinator: OctopusDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[OctopusDeviceEntity] = []
    for device_id in coordinator.data:
        entities.extend(
            [
                OctopusModeSelect(coordinator, device_id),
                OctopusUnitSelect(coordinator, device_id),
            ]
        )

    async_add_entities(entities)


class OctopusModeSelect(OctopusDeviceEntity, SelectEntity):
    """Select entity for choosing the SmartFlex device operating mode."""

    _attr_translation_key = "mode"

    def __init__(
        self, coordinator: OctopusDataUpdateCoordinator, device_id: str
    ) -> None:
        super().__init__(coordinator, device_id, "mode")

    @property
    def options(self) -> list[str]:
        """Return allowed mode options from the preference settings."""
        setting = self._device_data.settings
        mode_setting = setting.get("mode")
        # The mode field in preferenceSetting is a single string (the allowed mode).
        # In practice, the API may list multiple modes; for now expose at least CHARGE.
        if mode_setting:
            return [mode_setting]
        return ["CHARGE"]

    @property
    def current_option(self) -> str | None:
        return self._device_data.preferences.get("mode")

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.async_set_device_preferences(
            self._device_id, mode=option
        )


class OctopusUnitSelect(OctopusDeviceEntity, SelectEntity):
    """Select entity for choosing the charging unit (% or kWh)."""

    _attr_translation_key = "unit"

    def __init__(
        self, coordinator: OctopusDataUpdateCoordinator, device_id: str
    ) -> None:
        super().__init__(coordinator, device_id, "unit")

    @property
    def options(self) -> list[str]:
        """Return unit options accepted by this device.

        Filters the global list against what the device settings declare.
        Falls back to the full list if no setting is present.
        """
        allowed_unit = self._device_data.settings.get("unit")
        if allowed_unit and allowed_unit in _UNIT_OPTIONS:
            return [allowed_unit]
        return _UNIT_OPTIONS

    @property
    def current_option(self) -> str | None:
        return self._device_data.preferences.get("unit")

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.async_set_device_preferences(
            self._device_id, unit=option
        )
