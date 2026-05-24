---
name: project-schedule-entity-model
description: time and number entities are 1 per device (not one per day); values are broadcast uniformly to all 7 schedule days; min-charge is absent from the API payload
metadata:
  type: project
---

The `time` and `number` HA entity platforms each expose exactly 1 entity per SmartFlex device (`target_time` and `max_charge` respectively). When a value is written, the coordinator broadcasts it to all 7 days in the mutation's schedules array — every entry gets the same `{dayOfWeek, time, max}` tuple.

**Why:** The Octopus Italia API accepts a 7-entry schedule but the UX intent is a single uniform target; per-day entities were removed to avoid misleading complexity. The `DAYS_OF_WEEK` constant in `const.py` is still used internally to build the mutation payload.

**How to apply:** Do not add per-day entities. Any future schedule-related entity should follow the same broadcast pattern through `async_set_device_preferences()`. The `min` field must never appear in the mutation payload (not supported by the API).
