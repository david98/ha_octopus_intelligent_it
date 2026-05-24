"""Sensor platform for the Octopus Intelligent (Italia) integration."""

from __future__ import annotations

from datetime import datetime, timezone

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
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
                OctopusStatusSensor(coordinator, device_id),
                OctopusProviderSensor(coordinator, device_id),
                OctopusGridExportSensor(coordinator, device_id),
                OctopusTargetTypeSensor(coordinator, device_id),
                OctopusAlertsCountSensor(coordinator, device_id),
                OctopusLatestAlertMessageSensor(coordinator, device_id),
                OctopusLatestAlertPublishedAtSensor(coordinator, device_id),
            ]
        )

    async_add_entities(entities)


class OctopusStatusSensor(OctopusDeviceEntity, SensorEntity):
    """Sensor reporting the current device status (e.g. LIVE, SUSPENDED)."""

    _attr_translation_key = "status"

    def __init__(
        self, coordinator: OctopusDataUpdateCoordinator, device_id: str
    ) -> None:
        super().__init__(coordinator, device_id, "status")

    @property
    def native_value(self) -> str | None:
        return self._device_data.device.get("status", {}).get("current")


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
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except (ValueError, TypeError):
            return None
