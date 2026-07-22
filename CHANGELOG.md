# Changelog

## 0.1.1 - next release candidate

- Restored each vehicle to Devices & Services as a standard device integration with Configure and Delete controls.
- Selected the complete built-in maintenance catalog by default for new vehicles.
- Replaced Not set records with a consistent Never performed starting state.
- Centered the maintenance action dialog on desktop and mobile screens.
- Added an optional card accent color with a visual color picker and Home Assistant theme fallback.
- Removed persisted vehicle maintenance data when its integration entry is deleted.

## 0.1.0 - 2026-07-21

- Fixed startup on supported Home Assistant versions by using a `Store` subclass migration hook.
- Preserved version-1 completion, extension, milestone, and cached-odometer data.
- Added accurate per-service records and odometer-relative maintenance extensions.
- Added one cached effective-odometer coordinator per vehicle and non-polling entities.
- Restricted notifications to currently selected, logged, unextended services.
- Hardened the card against unavailable odometers and blank or invalid inputs.
- Replaced the card's record editor with simple Log Maintenance and Extend Maintenance workflows.
- Added exact earlier-mileage logging with a live next-due preview.
- Added Due Soon and All Maintenance views with a 2,000-mile default window.
- Added package-v4 migration guidance, regression tests, and CI validation.
