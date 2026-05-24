"""Number platform for the Octopus Intelligent (Italia) integration.

Exposes two number entities per device per day: one for the maximum charge
target and one for the minimum charge target (created only when the device
supports a minConstraint in its settings).
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DAYS_OF_WEEK, DOMAIN
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
        device_data = coordinator.data[device_id]
        settings = device_data.settings
        schedule_settings_list: list[dict[str, Any]] = settings.get(
            "scheduleSettings", []
        )
        sched_setting = schedule_settings_list[0] if schedule_settings_list else {}
        has_min_constraint = sched_setting.get("minConstraint") is not None

        for day in DAYS_OF_WEEK:
            entities.append(OctopusScheduleMaxNumber(coordinator, device_id, day))
            if has_min_constraint:
                entities.append(
                    OctopusScheduleMinNumber(coordinator, device_id, day)
                )

    async_add_entities(entities)


def _unit_of_measurement(unit: str | None) -> str:
    return "kWh" if unit == "KILOWATT_HOURS" else "%"


class OctopusScheduleMaxNumber(OctopusDeviceEntity, NumberEntity):
    """Number entity for the maximum charge target on a given day."""

    _attr_mode = NumberMode.BOX

    def __init__(
        self,
        coordinator: OctopusDataUpdateCoordinator,
        device_id: str,
        day: str,
    ) -> None:
        key = f"{day.lower()}_max"
        super().__init__(coordinator, device_id, key)
        self._day = day
        self._attr_translation_key = key

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
        for sched in schedules:
            if sched.get("dayOfWeek") == self._day:
                val = sched.get("max")
                return float(val) if val is not None else None
        return None

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.async_set_device_preferences(
            self._device_id,
            schedule_overrides={self._day: {"max": value}},
        )


class OctopusScheduleMinNumber(OctopusDeviceEntity, NumberEntity):
    """Number entity for the minimum charge target on a given day.

    Created only for devices that expose a minConstraint in their settings.
    """

    _attr_mode = NumberMode.BOX

    def __init__(
        self,
        coordinator: OctopusDataUpdateCoordinator,
        device_id: str,
        day: str,
    ) -> None:
        key = f"{day.lower()}_min"
        super().__init__(coordinator, device_id, key)
        self._day = day
        self._attr_translation_key = key

    @property
    def _min_constraint(self) -> dict[str, Any]:
        settings = self._device_data.settings
        sl: list[dict[str, Any]] = settings.get("scheduleSettings", [])
        sched_setting = sl[0] if sl else {}
        return sched_setting.get("minConstraint") or {}

    @property
    def native_unit_of_measurement(self) -> str:
        unit = self._device_data.preferences.get("unit")
        return _unit_of_measurement(unit)

    @property
    def native_min_value(self) -> float:
        return float(self._min_constraint.get("min", 0))

    @property
    def native_max_value(self) -> float:
        return float(self._min_constraint.get("max", 100))

    @property
    def native_step(self) -> float:
        settings = self._device_data.settings
        sl: list[dict[str, Any]] = settings.get("scheduleSettings", [])
        sched_setting = sl[0] if sl else {}
        return float(sched_setting.get("step", 1))

    @property
    def native_value(self) -> float | None:
        schedules: list[dict[str, Any]] = self._device_data.preferences.get(
            "schedules", []
        )
        for sched in schedules:
            if sched.get("dayOfWeek") == self._day:
                val = sched.get("min")
                return float(val) if val is not None else None
        return None

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.async_set_device_preferences(
            self._device_id,
            schedule_overrides={self._day: {"min": value}},
        )
