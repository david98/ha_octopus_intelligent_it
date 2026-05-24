"""Time platform for the Octopus Intelligent (Italia) integration.

Exposes one time entity per device per day of the week, representing
the target readiness time for that schedule slot.
"""

from __future__ import annotations

import logging
from datetime import time as dt_time

from homeassistant.components.time import TimeEntity
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
    """Set up Octopus Intelligent (Italia) time entities from a config entry."""
    coordinator: OctopusDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[OctopusDeviceEntity] = []
    for device_id in coordinator.data:
        for day in DAYS_OF_WEEK:
            entities.append(OctopusScheduleTimeEntity(coordinator, device_id, day))

    async_add_entities(entities)


class OctopusScheduleTimeEntity(OctopusDeviceEntity, TimeEntity):
    """Time entity for the target readiness time of a specific day schedule."""

    def __init__(
        self,
        coordinator: OctopusDataUpdateCoordinator,
        device_id: str,
        day: str,
    ) -> None:
        key = f"{day.lower()}_target_time"
        super().__init__(coordinator, device_id, key)
        self._day = day
        self._attr_translation_key = key

    @property
    def native_value(self) -> dt_time | None:
        """Return the current target time for this day."""
        schedules: list[dict] = self._device_data.preferences.get("schedules", [])
        for sched in schedules:
            if sched.get("dayOfWeek") == self._day:
                raw = sched.get("time")
                if raw is None:
                    return None
                return self._parse_time(raw)
        return None

    async def async_set_value(self, value: dt_time) -> None:
        """Set the target time for this day."""
        # Client-side validation against schedule settings
        settings = self._device_data.settings
        schedule_settings_list: list[dict] = settings.get("scheduleSettings", [])
        if schedule_settings_list:
            sched_setting = schedule_settings_list[0]
            time_from = self._parse_time(sched_setting.get("timeFrom", "00:00:00"))
            time_to = self._parse_time(sched_setting.get("timeTo", "23:59:00"))
            time_step: int = int(sched_setting.get("timeStep", 30))

            if time_from and time_to and (value < time_from or value > time_to):
                _LOGGER.warning(
                    "Requested time %s for %s is outside allowed range [%s, %s]",
                    value,
                    self._day,
                    time_from,
                    time_to,
                )

            # Validate step alignment (minutes must be a multiple of timeStep)
            total_minutes = value.hour * 60 + value.minute
            from_minutes = (time_from.hour * 60 + time_from.minute) if time_from else 0
            if time_step > 0 and (total_minutes - from_minutes) % time_step != 0:
                _LOGGER.warning(
                    "Requested time %s for %s does not align with %d-minute step",
                    value,
                    self._day,
                    time_step,
                )

        await self.coordinator.async_set_device_preferences(
            self._device_id,
            schedule_overrides={self._day: {"time": value.strftime("%H:%M")}},
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
