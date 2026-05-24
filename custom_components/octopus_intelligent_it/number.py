"""Number platform for the Octopus Intelligent (Italia) integration.

Exposes one number entity per device for the maximum charge target,
applied uniformly across all schedule days.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import OctopusDataUpdateCoordinator
from .entity import OctopusDeviceEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Octopus Intelligent (Italia) number entities from a config entry."""
    coordinator: OctopusDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[OctopusDeviceEntity] = []
    for device_id in coordinator.data:
        entities.append(OctopusScheduleMaxNumber(coordinator, device_id))

    async_add_entities(entities)


def _unit_of_measurement(unit: str | None) -> str:
    return "kWh" if unit == "KILOWATT_HOURS" else "%"


class OctopusScheduleMaxNumber(OctopusDeviceEntity, NumberEntity):
    """Number entity for the maximum charge target, applied to all schedule days."""

    _attr_mode = NumberMode.BOX

    def __init__(
        self,
        coordinator: OctopusDataUpdateCoordinator,
        device_id: str,
    ) -> None:
        super().__init__(coordinator, device_id, "max_charge")
        self._attr_translation_key = "max_charge"

    @property
    def _sched_setting(self) -> dict[str, Any]:
        settings = self._device_data.settings
        sl: list[dict[str, Any]] = settings.get("scheduleSettings", [])
        return sl[0] if sl else {}

    @property
    def native_unit_of_measurement(self) -> str:
        unit = self._device_data.preferences.get("unit")
        return _unit_of_measurement(unit)

    @property
    def native_min_value(self) -> float:
        return float(self._sched_setting.get("min", 0))

    @property
    def native_max_value(self) -> float:
        return float(self._sched_setting.get("max", 100))

    @property
    def native_step(self) -> float:
        return float(self._sched_setting.get("step", 1))

    @property
    def native_value(self) -> float | None:
        schedules: list[dict[str, Any]] = self._device_data.preferences.get(
            "schedules", []
        )
        if not schedules:
            return None
        val = schedules[0].get("max")
        return float(val) if val is not None else None

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.async_set_device_preferences(
            self._device_id,
            max_charge=value,
        )
