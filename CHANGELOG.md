# Changelog

## 0.1.3 - 2026-07-22

- Split maintenance selection into four grouped, persistent checklists so multiple services can be added or removed in one pass.
- Added a card workflow for logging several maintenance items from one service visit at the same odometer reading.
- Added an atomic batch logging action that validates every selected item and saves the vehicle once.
- Added a short Why it matters explanation to every maintenance action popup.

## 0.1.2 - 2026-07-22

- Added local integration artwork for Home Assistant 2026.3 and newer.
- Replaced unsupported Spark Plugs and Wheel Alignment icons with reliable Material Design icons.
- Reworked vehicle setup and options into focused screens with a persistent multi-select service checklist.
- Updated normal-use starting intervals to match recent U.S.-market Subaru guidance while labeling inspection and condition reminders honestly.
- Added separate first and repeat coolant intervals: first due at 137,500 miles, then every 75,000 miles.
- Migrated untouched older defaults while preserving customized per-vehicle intervals.

## 0.1.1 - 2026-07-21

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
