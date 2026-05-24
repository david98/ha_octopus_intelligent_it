# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

A **Home Assistant custom integration** for [Octopus Energy Italia](https://octopusenergy.it/) (SmartFlex devices). It communicates directly with the Italian Kraken GraphQL API (`api.oeit-kraken.energy`) and exposes SmartFlex device data as native HA entities (sensors, binary sensors, select, time, number). Supports multiple devices on a single account.

This integration is distributed as a HACS custom repository and can also be installed manually via symlink.

## File Layout

```
custom_components/
└── octopus_intelligent_it/
    ├── __init__.py              # Entry setup / teardown
    ├── manifest.json            # Integration metadata + PyJWT requirement
    ├── const.py                 # Domain, config keys, defaults, platform list
    ├── queries.py               # GraphQL query/mutation strings (verbatim from API captures)
    ├── kraken_client.py         # Async GraphQL client with token refresh logic
    ├── config_flow.py           # Config flow (email/pwd → long-lived token) + options flow
    ├── coordinator.py           # DataUpdateCoordinator: polls all device data
    ├── entity.py                # Base entity class (DeviceInfo, availability, helpers)
    ├── sensor.py                # Read-only sensors (status, provider, alerts, …)
    ├── binary_sensor.py         # Boolean sensors (suspended, capped, has_alerts)
    ├── select.py                # Writable selects (mode, unit)
    ├── time.py                  # Writable time entities (target time × 7 days)
    ├── number.py                # Writable number entities (max/min charge × 7 days)
    ├── strings.json             # EN translation source of truth
    └── translations/
        ├── en.json
        └── it.json
requests/                        # Proxyman network captures (zip archives, read-only reference)
hacs.json                        # HACS metadata
README.md
```

## Architecture

### Auth flow

1. Config flow: email + password → `Login` mutation → short-lived access token.
2. Exchange for a long-lived refresh token (~6 months) via `obtainLongLivedRefreshToken`.
3. Only the refresh token is stored in the config entry; credentials are discarded.
4. `KrakenClient._ensure_token()` silently refreshes the access token (1-hour TTL) before each GraphQL call.
5. If the API rotates the refresh token, `on_refresh_token_change` callback persists the new value to the config entry immediately.

### KrakenClient

Wraps `aiohttp.ClientSession`. Key points:
- Auth header is the raw JWT string (no `Bearer ` prefix — confirmed from API captures).
- On HTTP 401 or error code `KT-CT-1124` (token expired): clears `_access_token`, refreshes once, retries.
- On `KT-CT-1135` / `KT-CT-1134`: raises `KrakenAuthError` → triggers HA re-auth flow.

### Coordinator

`OctopusDataUpdateCoordinator` fetches in parallel per poll cycle:
- `GetSmartFlexDevices` (all devices)
- `GetSmartFlexDevicePreferences` (all devices)
- `GetSmartFlexDeviceAlerts` (all devices)
- `GetSmartFlexDevicePreferenceSettings` (one call per device — requires `deviceId`)

Merges results into `dict[device_id, DeviceData]`.

`async_set_device_preferences()` builds the full 7-day schedule payload from current data + overrides, calls `SetSmartFlexDevicePreferences`, then triggers a refresh.

### Entity platforms

| Platform | Entities per device |
|---|---|
| `sensor` | 7 (status, provider, gridExport, targetType, alertsCount, latestAlertMsg, latestAlertTime) |
| `binary_sensor` | 3 (suspended, chargingDurationCapped, hasAlerts) |
| `select` | 2 (mode, unit) |
| `time` | 7 (one per day of week) |
| `number` | 7–14 (max × 7; min × 7 only when minConstraint is present) |

## Dev workflow

### Local hot-reload in HA

```bash
# Symlink the custom component into your HA config directory
ln -s /path/to/ha-octopus-intelligent-it/custom_components/octopus_intelligent_it \
      <HA_CONFIG>/custom_components/octopus_intelligent_it

# Restart HA (or reload the integration from Settings → Integrations)
```

### Reading logs

In HA's developer tools → Logs, filter by `octopus_intelligent_it`. For verbose output, add to `configuration.yaml`:

```yaml
logger:
  default: warning
  logs:
    custom_components.octopus_intelligent_it: debug
```

### Reproducing API calls from captures

The `requests/` directory contains Proxyman network captures (`.proxymanlogv2` files — zip archives). To extract and inspect:

```bash
mkdir -p /tmp/proxyman_logs
for f in requests/*.proxymanlogv2; do
  unzip -o "$f" -d /tmp/proxyman_logs/
done

# Each extracted file is a JSON object with base64-encoded request/response body:
python3 -c "
import json, base64
with open('/tmp/proxyman_logs/<request_file>') as f:
    d = json.load(f)
# Decode request body
body = json.loads(base64.b64decode(d['request']['bodyData']))
print(json.dumps(body, indent=2))
# Decode response body
resp = json.loads(base64.b64decode(d['response']['bodyData']))
print(json.dumps(resp, indent=2))
"
```

### Dev tooling

The project uses **Ruff** (lint + format) gated by **lefthook** and **convco** for commit message validation.

```bash
make setup        # Create .venv, install ruff, run lefthook install
make check        # Full pre-push gate: ruff check + ruff format --check
make format-fix   # Auto-fix formatting and lint issues in custom_components/
make lint         # ruff check custom_components (read-only)
make format       # ruff format --check custom_components (read-only)
```

- **pre-commit**: `ruff check --fix` runs first, then `ruff format`, on staged `.py` files; fixes are re-staged automatically (`stage_fixed: true`).
- **pre-push**: `make lint` + `make format` run on the full project.
- **commit-msg**: `convco check` validates Conventional Commits format.

To bootstrap a fresh checkout: `brew install lefthook convco && make setup`.

## Key dependencies

| Dependency | Role |
|---|---|
| `aiohttp` | HTTP client (provided by HA, not declared in manifest) |
| `PyJWT>=2.10.0` | Decode JWT access token expiry without signature verification |
