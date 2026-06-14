"""Sensor platform for the Octopus Intelligent (Italia) integration."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import homeassistant.util.dt as dt_util
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import OctopusDataUpdateCoordinator
from .entity import OctopusDeviceEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Octopus Intelligent (Italia) sensors from a config entry."""
    coordinator: OctopusDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[OctopusDeviceEntity] = []
    for device_id in coordinator.data:
        entities.extend(
            [
                OctopusNextChargeSensor(coordinator, device_id),
                OctopusProviderSensor(coordinator, device_id),
                OctopusGridExportSensor(coordinator, device_id),
                OctopusTargetTypeSensor(coordinator, device_id),
                OctopusAlertsCountSensor(coordinator, device_id),
                OctopusLatestAlertMessageSensor(coordinator, device_id),
                OctopusLatestAlertPublishedAtSensor(coordinator, device_id),
            ]
        )

    async_add_entities(entities)


class OctopusNextChargeSensor(OctopusDeviceEntity, SensorEntity):
    """Sensor reporting the start time of the next planned smart-charge window."""

    _attr_translation_key = "next_charge"
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(
        self, coordinator: OctopusDataUpdateCoordinator, device_id: str
    ) -> None:
        super().__init__(coordinator, device_id, "next_charge")
        self._resolved: tuple[datetime, datetime, dict] | None = (
            self._next_dispatch_node()
        )

    def _handle_coordinator_update(self) -> None:
        """Resolve the next dispatch node once per coordinator update."""
        self._resolved = self._next_dispatch_node()
        super()._handle_coordinator_update()

    def _next_dispatch_node(self) -> tuple[datetime, datetime, dict] | None:
        """Return (start_dt, end_dt, node) for the earliest dispatch whose end is in the future.

        Parses both start and end as ISO datetimes (with UTC fallback for naive
        timestamps). Sorts candidates by parsed start and returns the winning
        tuple, or ``None`` if no such dispatch exists.
        """
        now = dt_util.utcnow()
        candidates: list[tuple[datetime, datetime, dict]] = []
        for node in self._device_data.dispatches:
            raw_start = node.get("start")
            raw_end = node.get("end")
            if raw_start is None or raw_end is None:
                continue
            try:
                end_dt = datetime.fromisoformat(raw_end)
                if end_dt.tzinfo is None:
                    end_dt = end_dt.replace(tzinfo=UTC)
                if end_dt <= now:
                    continue
                start_dt = datetime.fromisoformat(raw_start)
                if start_dt.tzinfo is None:
                    start_dt = start_dt.replace(tzinfo=UTC)
                candidates.append((start_dt, end_dt, node))
            except (ValueError, TypeError):
                continue
        if not candidates:
            return None
        candidates.sort(key=lambda t: t[0])
        return candidates[0]

    @property
    def native_value(self) -> datetime | None:
        """Return the start of the earliest dispatch whose end is still in the future."""
        if self._resolved is None:
            return None
        start_dt, _end_dt, _node = self._resolved
        return start_dt

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return energy_kwh and end time for the next dispatch slot."""
        if self._resolved is None:
            return None
        _start_dt, end_dt, node = self._resolved
        raw_delta = node.get("delta")
        return {
            "energy_kwh": float(raw_delta) if raw_delta is not None else None,
            "end": end_dt,
        }


class OctopusProviderSensor(OctopusDeviceEntity, SensorEntity):
    """Sensor reporting the device integration provider (e.g. TESLA_V2)."""

    _attr_translation_key = "provider"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self, coordinator: OctopusDataUpdateCoordinator, device_id: str
    ) -> None:
        super().__init__(coordinator, device_id, "provider")

    @property
    def native_value(self) -> str | None:
        return self._device_data.device.get("provider")


class OctopusGridExportSensor(OctopusDeviceEntity, SensorEntity):
    """Sensor reporting the grid export preference value."""

    _attr_translation_key = "grid_export"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self, coordinator: OctopusDataUpdateCoordinator, device_id: str
    ) -> None:
        super().__init__(coordinator, device_id, "grid_export")

    @property
    def native_value(self) -> str | None:
        return self._device_data.preferences.get("gridExport")


class OctopusTargetTypeSensor(OctopusDeviceEntity, SensorEntity):
    """Sensor reporting the charging target type (e.g. ABSOLUTE_STATE_OF_CHARGE)."""

    _attr_translation_key = "target_type"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self, coordinator: OctopusDataUpdateCoordinator, device_id: str
    ) -> None:
        super().__init__(coordinator, device_id, "target_type")

    @property
    def native_value(self) -> str | None:
        return self._device_data.preferences.get("targetType")


class OctopusAlertsCountSensor(OctopusDeviceEntity, SensorEntity):
    """Sensor reporting the total number of active device alerts."""

    _attr_translation_key = "alerts_count"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_native_unit_of_measurement = None
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self, coordinator: OctopusDataUpdateCoordinator, device_id: str
    ) -> None:
        super().__init__(coordinator, device_id, "alerts_count")

    @property
    def native_value(self) -> int:
        return len(self._device_data.alerts)


class OctopusLatestAlertMessageSensor(OctopusDeviceEntity, SensorEntity):
    """Sensor reporting the message of the most recent device alert."""

    _attr_translation_key = "latest_alert_message"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self, coordinator: OctopusDataUpdateCoordinator, device_id: str
    ) -> None:
        super().__init__(coordinator, device_id, "latest_alert_message")

    @property
    def native_value(self) -> str | None:
        alerts = self._device_data.alerts
        if not alerts:
            return None
        sorted_alerts = sorted(
            alerts,
            key=lambda a: a.get("publishedAt") or "",
            reverse=True,
        )
        return sorted_alerts[0].get("message")


class OctopusLatestAlertPublishedAtSensor(OctopusDeviceEntity, SensorEntity):
    """Sensor reporting the timestamp of the most recent device alert."""

    _attr_translation_key = "latest_alert_published_at"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self, coordinator: OctopusDataUpdateCoordinator, device_id: str
    ) -> None:
        super().__init__(coordinator, device_id, "latest_alert_published_at")

    @property
    def native_value(self) -> datetime | None:
        alerts = self._device_data.alerts
        if not alerts:
            return None
        sorted_alerts = sorted(
            alerts,
            key=lambda a: a.get("publishedAt") or "",
            reverse=True,
        )
        raw = sorted_alerts[0].get("publishedAt")
        if raw is None:
            return None
        try:
            dt = datetime.fromisoformat(raw)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=UTC)
            return dt
        except (ValueError, TypeError):
            return None
