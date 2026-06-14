"""Data update coordinator for the Octopus Intelligent (Italia) integration."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DAYS_OF_WEEK
from .kraken_client import KrakenAuthError, KrakenClient, KrakenError
from .queries import (
    GET_SMART_FLEX_DEVICE_ALERTS,
    GET_SMART_FLEX_DEVICE_PREFERENCE_SETTINGS,
    GET_SMART_FLEX_DEVICE_PREFERENCES,
    GET_SMART_FLEX_DEVICES,
    GET_SMART_FLEX_PLANNED_DISPATCHES,
    SET_SMART_FLEX_DEVICE_PREFERENCES,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class DeviceData:
    """Aggregated data for a single SmartFlex device."""

    device: dict[str, Any]
    preferences: dict[str, Any]
    settings: dict[str, Any]
    alerts: list[dict[str, Any]] = field(default_factory=list)
    dispatches: list[dict[str, Any]] = field(default_factory=list)


class OctopusDataUpdateCoordinator(DataUpdateCoordinator[dict[str, DeviceData]]):
    """Coordinator that polls all SmartFlex devices on an Octopus account."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: KrakenClient,
        account_number: str,
        scan_interval: int,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"Octopus Intelligent IT ({account_number})",
            update_interval=timedelta(seconds=scan_interval),
        )
        self._client = client
        self._account_number = account_number

    async def _async_fetch_dispatches(self) -> list[dict[str, Any]]:
        """Fetch the account-level planned dispatches, isolated from the main poll.

        Returns an empty list on any error so that a rejected or absent query
        never raises ``UpdateFailed``.
        """
        try:
            result = await self._client.graphql(
                GET_SMART_FLEX_PLANNED_DISPATCHES,
                variables={"accountNumber": self._account_number},
                operation_name="GetSmartFlexPlannedDispatches",
            )
            return result.get("plannedDispatches") or []
        except Exception as err:
            _LOGGER.debug("planned dispatches unavailable: %s", err)
            return []

    async def _async_update_data(self) -> dict[str, DeviceData]:
        """Fetch all device data in parallel and merge into a keyed dict."""
        try:
            devices_result, prefs_result, alerts_result = await asyncio.gather(
                self._client.graphql(
                    GET_SMART_FLEX_DEVICES,
                    variables={
                        "accountNumber": self._account_number,
                        "deviceId": None,
                    },
                    operation_name="GetSmartFlexDevices",
                ),
                self._client.graphql(
                    GET_SMART_FLEX_DEVICE_PREFERENCES,
                    variables={
                        "accountNumber": self._account_number,
                        "deviceId": None,
                    },
                    operation_name="GetSmartFlexDevicePreferences",
                ),
                self._client.graphql(
                    GET_SMART_FLEX_DEVICE_ALERTS,
                    variables={"accountNumber": self._account_number},
                    operation_name="GetSmartFlexDeviceAlerts",
                ),
            )
        except KrakenAuthError as err:
            raise ConfigEntryAuthFailed(
                "Octopus IT credentials expired or invalid"
            ) from err
        except KrakenError as err:
            raise UpdateFailed(f"Octopus IT API error: {err}") from err
        except Exception as err:
            raise UpdateFailed(f"Unexpected error: {err}") from err

        raw_devices: list[dict[str, Any]] = devices_result.get("devices", [])
        raw_prefs: list[dict[str, Any]] = prefs_result.get("devices", [])
        raw_alerts: list[dict[str, Any]] = alerts_result.get("devices", [])

        # Index by device id
        prefs_by_id = {d["id"]: d.get("preferences", {}) for d in raw_prefs}
        alerts_by_id = {d["id"]: d.get("alerts", []) for d in raw_alerts}

        # Fetch per-device preference settings (requires explicit deviceId)
        settings_tasks = {
            dev["id"]: self._client.graphql(
                GET_SMART_FLEX_DEVICE_PREFERENCE_SETTINGS,
                variables={
                    "accountNumber": self._account_number,
                    "deviceId": dev["id"],
                },
                operation_name="GetSmartFlexDevicePreferenceSettings",
            )
            for dev in raw_devices
        }
        try:
            settings_results = await asyncio.gather(*settings_tasks.values())
        except KrakenAuthError as err:
            raise ConfigEntryAuthFailed(
                "Octopus IT credentials expired or invalid"
            ) from err
        except KrakenError as err:
            raise UpdateFailed(
                f"Octopus IT API error fetching settings: {err}"
            ) from err
        except Exception as err:
            raise UpdateFailed(f"Unexpected error fetching settings: {err}") from err

        settings_by_id: dict[str, dict[str, Any]] = {}
        for device_id, result in zip(
            settings_tasks.keys(), settings_results, strict=True
        ):
            devices_in_result: list[dict[str, Any]] = result.get("devices", [])
            settings_by_id[device_id] = (
                devices_in_result[0].get("preferenceSetting", {})
                if devices_in_result
                else {}
            )

        # Fetch planned dispatches once for the account (isolated — never raises UpdateFailed)
        dispatches_list = await self._async_fetch_dispatches()

        return {
            dev["id"]: DeviceData(
                device=dev,
                preferences=prefs_by_id.get(dev["id"], {}),
                settings=settings_by_id.get(dev["id"], {}),
                alerts=alerts_by_id.get(dev["id"], []),
                dispatches=dispatches_list,
            )
            for dev in raw_devices
        }

    async def async_set_device_preferences(
        self,
        device_id: str,
        *,
        mode: str | None = None,
        unit: str | None = None,
        time: str | None = None,
        max_charge: float | None = None,
    ) -> None:
        """Write updated preferences for a device, then request a data refresh.

        Args:
            device_id: The SmartFlex device ID to update.
            mode: Optional new mode (e.g. ``"CHARGE"``).
            unit: Optional new unit (e.g. ``"PERCENTAGE"``).
            time: Optional new target time in ``HH:MM`` format, applied to all days.
            max_charge: Optional new maximum charge value, applied to all days.
        """
        if self.data is None or device_id not in self.data:
            raise UpdateFailed(f"No data for device {device_id}")

        device_data = self.data[device_id]
        current_prefs = device_data.preferences

        new_mode = mode if mode is not None else current_prefs.get("mode")
        new_unit = unit if unit is not None else current_prefs.get("unit")

        # Determine canonical time and max from override or current first schedule entry
        current_schedules: list[dict[str, Any]] = current_prefs.get("schedules", [])
        first_entry: dict[str, Any] = current_schedules[0] if current_schedules else {}

        canonical_time_raw: str | None = (
            time if time is not None else first_entry.get("time")
        )
        if canonical_time_raw is not None:
            # Normalise to HH:MM (strip seconds if present)
            canonical_time: str | None = (
                canonical_time_raw[:5]
                if len(canonical_time_raw) >= 5
                else canonical_time_raw
            )
        else:
            canonical_time = None

        canonical_max: float | None = max_charge
        if canonical_max is None:
            raw = first_entry.get("max")
            try:
                canonical_max = float(raw) if raw is not None else None
            except (TypeError, ValueError):
                canonical_max = None

        # Build a uniform 7-entry schedule — every day gets identical {time, max}, no min
        schedule_inputs: list[dict[str, Any]] = []
        for day in DAYS_OF_WEEK:
            entry: dict[str, Any] = {"dayOfWeek": day}
            if canonical_time is not None:
                entry["time"] = canonical_time
            if canonical_max is not None:
                entry["max"] = canonical_max
            schedule_inputs.append(entry)

        mutation_input: dict[str, Any] = {
            "deviceId": device_id,
            "schedules": schedule_inputs,
        }
        if new_mode is not None:
            mutation_input["mode"] = new_mode
        if new_unit is not None:
            mutation_input["unit"] = new_unit

        try:
            await self._client.graphql(
                SET_SMART_FLEX_DEVICE_PREFERENCES,
                variables={"input": mutation_input},
                operation_name="SetSmartFlexDevicePreferences",
            )
        except KrakenAuthError as err:
            raise ConfigEntryAuthFailed(
                "Octopus IT credentials expired or invalid"
            ) from err
        except KrakenError as err:
            raise UpdateFailed(
                f"Failed to set preferences for {device_id}: {err}"
            ) from err

        await self.async_request_refresh()
