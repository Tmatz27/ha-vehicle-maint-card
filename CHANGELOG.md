# Changelog

## 0.2.1 - 2026-07-25

- Fixed visual-editor dropdowns and selectors closing during unrelated Home Assistant state updates.
- Registered the included dashboard card as a persistent Lovelace module in storage-mode dashboards so desktop and Companion App clients load the same card resource.
- Added automatic migration from the previous card resource URL without requiring dashboard YAML changes.
- Kept frontend module injection as a compatibility fallback for YAML resource mode.
- Added Lovelace resource registration compatibility for supported Home Assistant generations, including 2024.x dictionary data, 2025.x `mode`, and newer `resource_mode` layouts.
- Rejected completion mileage above the current odometer and prevented routine maintenance history from being moved backward accidentally.
- Made service-visit logging validate every selected item before changing any maintenance record.
- Prevented completed one-time mileage milestones from being logged or extended again until explicitly reset.
- Removed completed one-time mileage milestones from the dashboard card while retaining their Home Assistant entities and stored completion data.
- Excluded actively extended maintenance from the summary sensor's `next_service` result.
- Scoped card/editor CSS and namespaced dialog/input IDs so multiple cards cannot interfere with each other's controls or surrounding dashboard elements.
- Cached per-vehicle maintenance entity discovery so one card render no longer repeatedly scans every Home Assistant entity.
- Added regression checks for editor stability, frontend resource registration, completion integrity, atomic batch validation, deferred summary behavior, CSS isolation, and release/cache version alignment.

## 0.2.0 - 2026-07-24

- Added separate washable settings for engine and cabin air filters.
- Added explicit Wash and Replace actions with wash count, installed mileage, and total miles on each reusable filter.
- Sorted the service-visit checklist by miles remaining instead of maintenance type.
- Added a direct options menu for vehicle details, tracked services and intervals, and notifications.
- Added multiple notification recipients, including modern notify entities and legacy YAML notify groups.
- Preserved existing notification targets and maintenance records through an automatic version-4 migration.

## 0.1.4 - 2026-07-23

- Replaced the notification action text field with a notify-entity picker.
- Fixed weekly summaries for phone targets such as `notify.sm_s926u` by using Home Assistant's `notify.send_message` action.
- Preserved delivery through previously configured legacy notification actions.
- Renamed the odometer field and limited its picker to distance sensors.

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
