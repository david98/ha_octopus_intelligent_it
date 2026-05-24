---
name: project-octopus-integration
description: Architecture and key facts about the ha-octopus-intelligent-it HA custom integration for Octopus Energy Italia
metadata:
  type: project
---

Home Assistant custom integration for Octopus Energy Italia (SmartFlex devices).

**Why:** Italian Kraken API (`api.oeit-kraken.energy`) uses a different GraphQL schema from the UK API — `devices` query with `SmartFlexDevicePreferences`, not legacy `vehicleChargingPreferences`.

**How to apply:** When extending the integration, always verify GraphQL field names against the Proxyman captures in `requests/` (zip archives, base64-encoded JSON bodies).

Key facts:
- Auth: JWT without "Bearer " prefix in Authorization header (confirmed from API captures)
- Long-lived refresh token (~6 months) obtained via `obtainLongLivedRefreshToken` mutation
- Error codes: KT-CT-1135/KT-CT-1134 = auth error; KT-CT-1124 = token expired (retry)
- `SetSmartFlexDevicePreferences` input requires full 7-day schedule even when updating one day
- `minConstraint` in scheduleSettings indicates whether min charge entities should be created
- Proxyman .proxymanlogv2 files are zip archives; inner files are JSON with `bodyData` field (base64)

Related: [[project-ha-integration-patterns]]
