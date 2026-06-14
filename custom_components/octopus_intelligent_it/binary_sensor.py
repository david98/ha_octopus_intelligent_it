"""Binary sensor platform for the Octopus Intelligent (Italia) integration."""

from __future__ import annotations

from datetime import UTC, datetime

import homeassistant.util.dt as dt_util
from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
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
    """Set up Octopus Intelligent (Italia) binary sensors from a config entry."""
    coordinator: OctopusDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[OctopusDeviceEntity] = []
    for device_id in coordinator.data:
        entities.extend(
            [
                OctopusSuspendedBinarySensor(coordinator, device_id),
                OctopusChargingDurationCappedBinarySensor(coordinator, device_id),
                OctopusHasAlertsBinarySensor(coordinator, device_id),
                OctopusSmartChargingBinarySensor(coordinator, device_id),
            ]
        )

    async_add_entities(entities)


class OctopusSuspendedBinarySensor(OctopusDeviceEntity, BinarySensorEntity):
    """Binary sensor indicating whether the device is currently suspended."""

    _attr_translation_key = "suspended"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self, coordinator: OctopusDataUpdateCoordinator, device_id: str
    ) -> None:
        super().__init__(coordinator, device_id, "suspended")

    @property
    def is_on(self) -> bool:
        return bool(
            self._device_data.device.get("status", {}).get("isSuspended", False)
        )


_CAPPED_TRUE_VALUES: frozenset[object] = frozenset({"TRUE", "CAPPED", True})


class OctopusChargingDurationCappedBinarySensor(
    OctopusDeviceEntity, BinarySensorEntity
):
    """Binary sensor indicating whether the charging duration is capped."""

    _attr_translation_key = "charging_duration_capped"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self, coordinator: OctopusDataUpdateCoordinator, device_id: str
    ) -> None:
        super().__init__(coordinator, device_id, "charging_duration_capped")

    @property
    def is_on(self) -> bool:
        value = self._device_data.preferences.get("isChargingDurationCapped")
        return value in _CAPPED_TRUE_VALUES


class OctopusHasAlertsBinarySensor(OctopusDeviceEntity, BinarySensorEntity):
    """Binary sensor indicating whether the device has any active alerts."""

    _attr_translation_key = "has_alerts"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self, coordinator: OctopusDataUpdateCoordinator, device_id: str
    ) -> None:
        super().__init__(coordinator, device_id, "has_alerts")

    @property
    def is_on(self) -> bool:
        return len(self._device_data.alerts) > 0


class OctopusSmartChargingBinarySensor(OctopusDeviceEntity, BinarySensorEntity):
    """Binary sensor that is on while a planned smart-charge window is active."""

    _attr_translation_key = "smart_charging"
    _attr_device_class = BinarySensorDeviceClass.BATTERY_CHARGING

    def __init__(
        self, coordinator: OctopusDataUpdateCoordinator, device_id: str
    ) -> None:
        super().__init__(coordinator, device_id, "smart_charging")

    @property
    def is_on(self) -> bool:
        """Return True if the current time falls within any dispatch window."""
        now = dt_util.utcnow()
        for node in self._device_data.dispatches:
            raw_start = node.get("start")
            raw_end = node.get("end")
            if raw_start is None or raw_end is None:
                continue
            try:
                start_dt = datetime.fromisoformat(raw_start)
                if start_dt.tzinfo is None:
                    start_dt = start_dt.replace(tzinfo=UTC)
                end_dt = datetime.fromisoformat(raw_end)
                if end_dt.tzinfo is None:
                    end_dt = end_dt.replace(tzinfo=UTC)
                if start_dt <= now < end_dt:
                    return True
            except (ValueError, TypeError):
                continue
        return False
