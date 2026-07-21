# Changelog

## 0.1.0 - next release candidate

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
