"""Time platform for the Octopus Intelligent (Italia) integration.

Exposes one time entity per device representing the target readiness time,
applied uniformly across all schedule days.
"""

from __future__ import annotations

import logging
from datetime import time as dt_time
from typing import Any

from homeassistant.components.time import TimeEntity
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
    """Set up Octopus Intelligent (Italia) time entities from a config entry."""
    coordinator: OctopusDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[OctopusDeviceEntity] = []
    for device_id in coordinator.data:
        entities.append(OctopusScheduleTimeEntity(coordinator, device_id))

    async_add_entities(entities)


class OctopusScheduleTimeEntity(OctopusDeviceEntity, TimeEntity):
    """Time entity for the target readiness time, applied to all schedule days."""

    def __init__(
        self,
        coordinator: OctopusDataUpdateCoordinator,
        device_id: str,
    ) -> None:
        super().__init__(coordinator, device_id, "target_time")
        self._attr_translation_key = "target_time"

    @property
    def native_value(self) -> dt_time | None:
        """Return the current target time from the first schedule entry."""
        schedules: list[dict[str, Any]] = self._device_data.preferences.get(
            "schedules", []
        )
        if not schedules:
            return None
        raw = schedules[0].get("time")
        if raw is None:
            return None
        return self._parse_time(raw)

    async def async_set_value(self, value: dt_time) -> None:
        """Set the target time for all days."""
        # Client-side validation against schedule settings
        settings = self._device_data.settings
        schedule_settings_list: list[dict[str, Any]] = settings.get(
            "scheduleSettings", []
        )
        if schedule_settings_list:
            sched_setting = schedule_settings_list[0]
            time_from = self._parse_time(sched_setting.get("timeFrom", "00:00:00"))
            time_to = self._parse_time(sched_setting.get("timeTo", "23:59:00"))
            time_step: int = int(sched_setting.get("timeStep", 30))

            if time_from and time_to and (value < time_from or value > time_to):
                _LOGGER.warning(
                    "Requested time %s is outside allowed range [%s, %s]",
                    value,
                    time_from,
                    time_to,
                )

            # Validate step alignment (minutes must be a multiple of timeStep)
            total_minutes = value.hour * 60 + value.minute
            from_minutes = (time_from.hour * 60 + time_from.minute) if time_from else 0
            if time_step > 0 and (total_minutes - from_minutes) % time_step != 0:
                _LOGGER.warning(
                    "Requested time %s does not align with %d-minute step",
                    value,
                    time_step,
                )

        await self.coordinator.async_set_device_preferences(
            self._device_id,
            time=value.strftime("%H:%M"),
        )

    @staticmethod
    def _parse_time(raw: str) -> dt_time | None:
        """Parse an HH:MM or HH:MM:SS string into a datetime.time object."""
        if not raw:
            return None
        try:
            parts = raw.split(":")
            hour = int(parts[0])
            minute = int(parts[1]) if len(parts) > 1 else 0
            return dt_time(hour=hour, minute=minute)
        except (ValueError, IndexError):
            return None
