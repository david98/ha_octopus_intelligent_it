# Octopus Intelligent (Italia) — Home Assistant Integration

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz)

A Home Assistant custom integration for **Octopus Energy Italia** (SmartFlex devices).
It exposes your SmartFlex vehicle or charger as native HA entities — schedule times,
charge targets, device status, and alerts — and lets you modify charging preferences
directly from HA or automations.

---

## Features

- **Config flow**: email/password login → only a long-lived refresh token (~6 months) is persisted; credentials are discarded immediately after setup.
- **Multi-account support**: if your user has more than one account number, a second step lets you pick the right one.
- **Per-device entities** for every SmartFlex device on the account:
  - **Sensors**: status, provider, grid export mode, target type, alert count, latest alert message/time.
  - **Binary sensors**: suspended flag, charging duration capped, has-alerts.
  - **Select**: operating mode (`CHARGE`, etc.), charge unit (`PERCENTAGE` / `KILOWATT_HOURS`).
  - **Time** (7 × per day): target readiness time per day of the week.
  - **Number** (7 × per day): max charge target; min charge target (when supported by the device).
- **Configurable polling interval** (default 5 min, range 1–60 min) via the options flow.
- **Automatic token rotation**: when the API rotates the refresh token the new value is persisted without requiring re-authentication.
- **Re-auth flow**: if the refresh token expires HA will raise a re-auth notification allowing you to log in again without removing the integration.

---

## Requirements

- Octopus Energy Italia account with at least one SmartFlex device configured.
- Home Assistant 2024.1.0 or newer.
- Internet access to `api.oeit-kraken.energy`.

---

## Installation via HACS

1. Open HACS in your Home Assistant instance.
2. Click the three-dot menu (top right) and choose **Custom repositories**.
3. Paste the repository URL: `https://github.com/david98/ha-octopus-intelligent-it`
4. Select **Integration** as the category, then click **Add**.
5. Search for **"Octopus Intelligent (Italia)"** in HACS and click **Download**.
6. Restart Home Assistant.
7. Go to **Settings → Devices & Services → Add Integration** and search for **"Octopus Intelligent (Italia)"**.

---

## Manual installation

```bash
# From your HA config directory
ln -s /path/to/ha-octopus-intelligent-it/custom_components/octopus_intelligent_it \
      custom_components/octopus_intelligent_it
```

Then restart Home Assistant and follow step 7 above.

---

## Auth notes

- **Long-lived refresh token**: stored in the config entry, valid for approximately 6 months. The integration automatically persists rotated tokens so you should rarely need to re-authenticate.
- **Re-auth**: if the token expires (e.g. you revoked it from the Octopus app), Home Assistant will show a re-auth notification. Click it, enter your credentials, and the integration resumes without any data loss.

---

## Release process

To publish a new version:

1. Bump `version` in `custom_components/octopus_intelligent_it/manifest.json`.
2. Commit the change: `git commit -am "chore: bump version to X.Y.Z"`.
3. Create a git tag: `git tag vX.Y.Z`.
4. Push tag: `git push origin vX.Y.Z`.
5. Create a **GitHub Release** from the tag with a changelog describing the changes.

HACS users will see the new version available after the release is published.

---

## Development

Requirements: Python 3.12+, `brew install lefthook convco`.

```bash
make setup        # Create .venv, install Ruff, install git hooks
make lint         # Run ruff check on custom_components/
make format       # Check formatting (ruff format --check)
make format-fix   # Auto-fix formatting and lint issues
make check        # Full pre-push gate: lint + format check
```

Pre-commit hooks auto-fix staged Python files via Ruff (format + lint with `--fix`) and re-stage the result.
Pre-push runs the full `make lint` + `make format` gate.
Commit messages must follow [Conventional Commits](https://www.conventionalcommits.org/) (enforced by `convco`).

---

## Credits / Inspired by

This integration was inspired by [`megakid/ha_octopus_intelligent`](https://github.com/megakid/ha_octopus_intelligent), which provided the HA scaffolding patterns used here (config flow, coordinator, entity platform structure).

The GraphQL client was written from scratch because the Italian API (`api.oeit-kraken.energy`) uses a different schema from the UK API: it exposes devices via the `devices` query and uses `SmartFlexDevicePreferences` / `setDevicePreferences` — rather than the legacy `vehicleChargingPreferences` / `registeredKrakenflexDevice` fields used in the UK integration.
