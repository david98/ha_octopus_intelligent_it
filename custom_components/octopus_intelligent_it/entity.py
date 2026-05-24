"""Base entity class for the Octopus Intelligent (Italia) integration."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import DeviceData, OctopusDataUpdateCoordinator


class OctopusDeviceEntity(CoordinatorEntity[OctopusDataUpdateCoordinator]):
    """Base entity representing a single SmartFlex device.

    Subclasses set ``_key`` to a unique string that distinguishes multiple
    entities within the same device (e.g. ``"status"``, ``"monday_max"``).
    """

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: OctopusDataUpdateCoordinator,
        device_id: str,
        key: str,
    ) -> None:
        super().__init__(coordinator)
        self._device_id = device_id
        self._key = key
        self._attr_unique_id = f"{DOMAIN}_{device_id}_{key}"

    # ------------------------------------------------------------------
    # Device registry
    # ------------------------------------------------------------------

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information for the HA device registry."""
        device = self.coordinator.data[self._device_id].device

        name: str = device.get("name", self._device_id)
        device_type: str = device.get("deviceType", "")
        provider: str = device.get("provider", "")

        # For vehicles, use the vehicle make as the manufacturer
        make: str | None = device.get("make")
        manufacturer: str = make if make else MANUFACTURER

        return DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            name=name,
            manufacturer=manufacturer,
            model=f"{device_type} ({provider})" if provider else device_type,
            sw_version=device.get("integrationDeviceId"),
        )

    # ------------------------------------------------------------------
    # Availability
    # ------------------------------------------------------------------

    @property
    def available(self) -> bool:
        """Return True if the coordinator is healthy and has data for this device."""
        return (
            self.coordinator.last_update_success
            and self.coordinator.data is not None
            and self._device_id in self.coordinator.data
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @property
    def _device_data(self) -> DeviceData:
        """Return the aggregated data for this entity's device."""
        return self.coordinator.data[self._device_id]
