---
name: project-ha-integration
description: HA custom integration octopus_intelligent_it — architecture, recurring lint patterns, known issues found across six reviews (May 2026)
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

**Dev tooling added (fourth review, May 2026 — lefthook + Ruff)**:
- pyproject.toml: Ruff config (line-length 88, py312 target, select E/W/F/I/B/UP/SIM/C4/PIE/RUF/ASYNC/PTH, ignore E501 globally). Missing [build-system] table — pip falls back to setuptools default.
- E501 is both globally ignored AND in per-file-ignores for queries.py — the per-file entry is redundant.
- lefthook.yml: pre-commit parallel:true with ruff-format AND ruff-lint(check --fix) — RACE CONDITION: both write to the same staged files simultaneously.
- Makefile format-fix: runs `ruff format` before `ruff check --fix` — wrong order per Ruff docs (should be check --fix first, then format).
- time.py L57/L70: bare `list[dict]` annotation — should be `list[dict[str, Any]]` for precision.
- time.py async_set_value: validation only logs warnings on out-of-range/misaligned times, write always proceeds to API.
- .venv uses Python 3.14.5, pyproject.toml requires-python>=3.12, HA runs 3.12.x — mismatch noted.

**GitHub Actions CI workflow added (May 2026 — sixth review)**:
- `.github/workflows/validate.yml`: `on:` key is unquoted — yamllint default rules warn (truthy: `on` = boolean True in YAML 1.1). GitHub Actions runner uses go-yaml (YAML 1.2 semantics) so it works at runtime, but yamllint flags it. Best practice is `"on":` or `'on':`.
- Missing document-start `---` at top of file — yamllint default warns.
- `hacs/action@main` and `home-assistant/actions/hassfest@master` are mutable branch tags, not pinned SHAs — supply-chain risk.
- `cache: pip` in setup-python step without a `cache-dependency-path` pointing to pyproject.toml — cache key may be stale or miss.
- No `name:` on any `run:` step — reduces readability in Actions UI.
- Ruff installed via bare `pip install "ruff>=0.7.0"` without virtualenv — acceptable in CI but worth noting.

**Auth flow change (May 2026 — fifth review)**:
The `obtainLongLivedRefreshToken` step was removed from the login flow. `login_with_credentials` now returns the standard refresh token directly from the Login mutation (`refreshToken` + `refreshExpiresIn`). The variable `OBTAIN_LONG_LIVED_REFRESH_TOKEN` in queries.py is now dead code. Stale "long-lived" language remains in: `KrakenClient` class docstring (L41-46), `login_with_credentials` docstring (L288-295), `strings.json`/`en.json`/`it.json` user step description, and `CLAUDE.md` architecture section.

**HA-specific patterns confirmed valid**:
- `_attr_native_unit_of_measurement = None` + `SensorStateClass.MEASUREMENT` is valid HA pattern for dimensionless integer counters.
- `BinarySensorDeviceClass.PROBLEM` is appropriate for boolean problem/fault states.
- mypy `call-arg` error on `ConfigFlow(domain=DOMAIN)` is a known false positive — ignore.
- ARG rules (unused method arguments) are NOT in ruff's default ruleset.

**Schedule collapse refactor (seventh review, May 2026 — collapse per-day to single entity)**:
FIXED in eighth review (iteration 1 fix run, May 2026):
- coordinator.py: `from .const import DAYS_OF_WEEK` moved to module-level import (was deferred inside method). RESOLVED.
- coordinator.py: float conversion now wrapped in try/except (TypeError, ValueError). RESOLVED.
- coordinator.py: `mode` and `unit` are now conditionally added to `mutation_input` only when non-None. RESOLVED.
- time.py: `list[dict]` annotations replaced with `list[dict[str, Any]]`. RESOLVED.

REMAINING after eighth review (iteration 1 fix run, May 2026):
- coordinator.py L208: dict literal `{"deviceId": device_id, "schedules": schedule_inputs}` exceeds 88-char line length — ruff format would split it across 4 lines. MEDIUM (format violation).
- time.py L54: `.get("schedules", [])` call line exceeds 88 chars — ruff format would wrap it. MEDIUM (format violation).
- time.py L66: `.get("scheduleSettings", [])` call line exceeds 88 chars — ruff format would wrap it. MEDIUM (format violation).
- time.py async_set_value: validation only emits warnings; writes always proceed to the API regardless of range/alignment violations (carry-over — not new). LOW.
- time.py L82-83: `from_minutes` falls back to `0` when `time_from` is None, but `time_from` is derived from `_parse_time("00:00:00")` which cannot fail — inconsistency in None guard. LOW.

**Release automation added (ninth review, May 2026)**:
- `.release-please-config.json`: uses `release-type: simple` + `extra-files` with `jsonpath: $.version` to bump manifest.json. Valid syntax confirmed against release-please source.
- `.release-please-manifest.json`: version `0.1.0` matches manifest.json. Correct.
- `.github/workflows/release.yml`: Missing YAML document-start `---` (yamllint warns). `on:` is unquoted (same yamllint `truthy` warning as validate.yml). One `run:` step line exceeds 80-char yamllint default (96 chars). No explicit `token:` in release-please-action step — relies on GITHUB_TOKEN default (correct for public repos).
- `.github/workflows/release.yml`: `issues: write` permission declared but not strictly required — CLAUDE.md docs say only `contents: write` + `pull-requests: write` needed. Not harmful but unnecessary.
- `hacs.json`: `zip_release: true` + `filename: octopus_intelligent_it.zip` are valid HACS fields and correctly reference the zip asset created by the workflow.
- `CHANGELOG.md`: Only `# Changelog` header — placeholder for release-please to append to. Correct bootstrap pattern.

**How to apply**: Check for these patterns on every review of this integration.
