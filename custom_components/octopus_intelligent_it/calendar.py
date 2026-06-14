"""Calendar platform for the Octopus Intelligent (Italia) integration."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import homeassistant.util.dt as dt_util
from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import OctopusDataUpdateCoordinator
from .entity import OctopusDeviceEntity


def _parse_dispatch(
    node: dict[str, Any],
) -> tuple[datetime, datetime, float, str] | None:
    """Parse a single plannedDispatches node into (start, end, delta, source).

    Returns ``None`` if any required field is missing or unparseable.
    """
    try:
        raw_start: str | None = node.get("start")
        raw_end: str | None = node.get("end")
        raw_delta: str | None = node.get("delta")
        if raw_start is None or raw_end is None or raw_delta is None:
            return None

        start = datetime.fromisoformat(raw_start)
        if start.tzinfo is None:
            start = start.replace(tzinfo=UTC)

        end = datetime.fromisoformat(raw_end)
        if end.tzinfo is None:
            end = end.replace(tzinfo=UTC)

        delta = float(raw_delta)
        source: str = (node.get("meta") or {}).get("source") or ""
        return start, end, delta, source
    except (ValueError, TypeError):
        return None


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Octopus Intelligent (Italia) calendar entities from a config entry."""
    coordinator: OctopusDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[OctopusDeviceEntity] = [
        OctopusChargingPlanCalendar(coordinator, device_id)
        for device_id in coordinator.data
    ]
    async_add_entities(entities)


class OctopusChargingPlanCalendar(OctopusDeviceEntity, CalendarEntity):
    """Calendar showing Octopus-planned smart-charging dispatch windows."""

    _attr_translation_key = "charging_plan"

    def __init__(
        self, coordinator: OctopusDataUpdateCoordinator, device_id: str
    ) -> None:
        super().__init__(coordinator, device_id, "charging_plan")

    def _events(self) -> list[CalendarEvent]:
        """Return all parseable dispatch events sorted by start time."""
        events: list[CalendarEvent] = []
        for node in self._device_data.dispatches:
            parsed = _parse_dispatch(node)
            if parsed is None:
                continue
            start, end, delta, source = parsed
            events.append(
                CalendarEvent(
                    start=start,
                    end=end,
                    summary=f"Smart charge {delta:+.2f} kWh",
                    description=source,
                )
            )
        events.sort(key=lambda e: e.start)
        return events

    @property
    def event(self) -> CalendarEvent | None:
        """Return the active event if any, else the next upcoming event."""
        now = dt_util.utcnow()
        upcoming: CalendarEvent | None = None
        for evt in self._events():
            if evt.start <= now < evt.end:
                return evt
            if evt.start > now and upcoming is None:
                upcoming = evt
        return upcoming

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime,
        end_date: datetime,
    ) -> list[CalendarEvent]:
        """Return events whose window overlaps [start_date, end_date]."""
        return [
            evt
            for evt in self._events()
            if evt.start < end_date and evt.end > start_date
        ]
