---
name: project-ha-integration
description: HA custom integration octopus_intelligent_it — architecture, recurring lint patterns, known issues found in first, second, and third review
metadata:
  type: project
---

This is a Home Assistant custom integration (HACS) for Octopus Energy Italia SmartFlex devices.
Located at custom_components/octopus_intelligent_it/.

**Lint tooling**: ruff and mypy are available at /Library/Frameworks/Python.framework/Versions/3.12/bin/. No pyproject.toml or ruff.toml — ruff runs with defaults (88-char line length). `homeassistant` package is NOT installed in the dev environment, so mypy reports a false-positive on `ConfigFlow(domain=...)` call-arg — this can be ignored.

**Issues FIXED in iteration 1 (May 2026)**:
- sensor.py: unused imports removed
- coordinator.py: falsy-value bug fixed (now uses `if mode is not None` guard)
- coordinator.py: `zip(strict=True)` added
- config_flow.py: `OctopusOptionsFlowHandler.__init__` removed (uses base class `self.config_entry`)
- config_flow.py: deferred import moved to module level
- binary_sensor.py: `isChargingDurationCapped` now uses `_CAPPED_TRUE_VALUES` frozenset
- kraken_client.py: JWT decode errors now logged at DEBUG level with `noqa: BLE001`
- const.py: `PLATFORMS` now typed as `list[Platform]`

**Issues FIXED in iteration 2 (May 2026)**:
- config_flow.py L156: `async_step_reauth` parameter typed as `Mapping[str, Any]` (was `dict[str, Any]`)
- kraken_client.py L157: Redundant ternary removed. Callback now passes `self._refresh_exp or 0` directly.
- sensor.py L111: `_attr_native_unit_of_measurement = None` + `SensorStateClass.MEASUREMENT` (was invalid "alerts" string)
- binary_sensor.py L65: `_attr_device_class = BinarySensorDeviceClass.PROBLEM` added to `OctopusChargingDurationCappedBinarySensor`

**Remaining open findings after iteration 2 (third review, May 2026)**:
- config_flow.py L157: `entry_data` parameter in `async_step_reauth` is unused. HA mandates the signature, so prefix with `_entry_data` per Python convention (ARG002 — not in ruff default ruleset, but good practice). `async_get_options_flow`'s `config_entry` is similarly unused by HA contract.
- sensor.py L140-145 / L165-170: Duplicate `sorted_alerts` logic across `OctopusLatestAlertMessageSensor` and `OctopusLatestAlertPublishedAtSensor` — NOT extracted to a shared helper. This was flagged in review 2 but NOT included in the fix plan for iteration 2. Remains MEDIUM.

**HA-specific patterns confirmed valid**:
- `_attr_native_unit_of_measurement = None` + `SensorStateClass.MEASUREMENT` is valid HA pattern for dimensionless integer counters.
- `BinarySensorDeviceClass.PROBLEM` is appropriate for boolean problem/fault states.
- mypy `call-arg` error on `ConfigFlow(domain=DOMAIN)` is a known false positive — ignore.
- ARG rules (unused method arguments) are NOT in ruff's default ruleset.

**How to apply**: Check for these patterns on every review of this integration.
