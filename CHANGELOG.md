# Changelog

## 0.1.0 — next release candidate

- Fixed startup on supported Home Assistant versions by using a `Store` subclass migration hook.
- Preserved version-1 completion, extension, milestone, and cached-odometer data.
- Added explicit service records, factual due overrides, and odometer-relative reminder snoozes.
- Added one cached effective-odometer coordinator per vehicle and non-polling entities.
- Restricted notifications to currently selected, initialized, unsnoozed services.
- Hardened the card against unavailable odometers and blank or invalid inputs.
- Added row-specific completion, reminder, and advanced correction workflows.
- Added package-v4 migration guidance, regression tests, and CI validation.
