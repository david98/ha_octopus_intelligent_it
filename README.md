# Octopus Intelligent (Italia) — Home Assistant Integration

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz)
[![Built with Claude Code](https://img.shields.io/badge/Built%20with-Claude%20Code-blueviolet?logo=anthropic)](https://claude.ai/code)

> **Note:** This project was developed with the assistance of [Claude Code](https://claude.ai/code) (Anthropic's AI coding assistant). All code has been reviewed and validated by a human developer.

> **Disclaimer:** This project is an independent, community-developed integration and is **not affiliated with, endorsed by, or associated with Octopus Energy Ltd, Octopus Energy Italia S.r.l., or any of their subsidiaries**. "Octopus Energy" and related names and logos are trademarks of their respective owners. Use of these names is purely for descriptive identification purposes.

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
  - **Time**: single target readiness time, broadcast to all 7 schedule days.
  - **Number**: single max charge target, broadcast to all 7 schedule days.
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

Releases are fully automated via [release-please](https://github.com/googleapis/release-please).
When ready to release, find and merge the open Release PR on GitHub (titled
`chore(main): release X.Y.Z`). No manual version bumping or tagging is required.

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full release flow description.

---

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md) for setup instructions, code style, commit conventions, and the release flow.

Quick reference:

```bash
make setup        # Auto-detect OS, install system tools, create .venv, install git hooks
make check        # Full pre-push gate: lint + format check
make format-fix   # Auto-fix formatting and lint issues
```

---

## Disclaimer

This is an **independent, community project** and is in no way affiliated with, endorsed by, or associated with **Octopus Energy Ltd**, **Octopus Energy Italia S.r.l.**, or any of their subsidiaries or affiliates.

"Octopus Energy", "Kraken", "SmartFlex", and related names, logos, and trademarks are the property of their respective owners. Their use in this project is solely for descriptive and identification purposes, to indicate compatibility with the Octopus Energy Italia platform.

This integration accesses the Octopus Energy Italia GraphQL API on the user's behalf, using only the credentials provided by the user. The project authors assume no responsibility for changes to the API, service interruptions, or any consequences arising from use of this software.

---

## Credits / Inspired by

This integration was inspired by [`megakid/ha_octopus_intelligent`](https://github.com/megakid/ha_octopus_intelligent), which provided the HA scaffolding patterns used here (config flow, coordinator, entity platform structure).

The GraphQL client was written from scratch because the Italian API (`api.oeit-kraken.energy`) uses a different schema from the UK API: it exposes devices via the `devices` query and uses `SmartFlexDevicePreferences` / `setDevicePreferences` — rather than the legacy `vehicleChargingPreferences` / `registeredKrakenflexDevice` fields used in the UK integration.
