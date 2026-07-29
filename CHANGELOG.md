# Changelog

## 0.3.0 - 2026-07-29

### Fixed

- Fixed the card's accent-color header tint (the `.hero` background gradient) failing to render on themes that only define `--card-background-color`, which is the default for nearly every Home Assistant theme. `color-mix()` now falls back correctly instead of silently dropping the whole background declaration.
- Corrected the bundled card's internal version banner, which still logged `v0.2.0` in the browser console after the 0.2.1 and 0.2.2 releases.
- Wired the Home Assistant Store/runtime-contract CI job to run the full test suite instead of a single file, so `tests/test_integrity_runtime.py` (batch-logging atomicity and summary-sensor regression checks) actually executes in CI.

### Added

- Added a confirmation recap to service visits. Both the current-odometer and exact-mileage paths now list every selected item and the mileage that will be applied before any record is written.
- Added a non-blocking warning when a custom extension is longer than 20,000 miles, so a mistyped extension is caught without preventing a deliberate long deferral.
- Added optional car wash tracking, disabled by default and configured under **Configure > Car wash tracking**. Washes are tracked by date rather than mileage and are deliberately kept out of the mechanical service catalog, Due Soon, and maintenance notifications. Adds a `car_wash` sensor, a `Log car wash` button, a **Car Care** card section, and the `log_car_wash` and `reset_car_wash` actions.
- Added per-service notification muting. A muted service stays fully visible on the card but is left out of the weekly summary, and its mute clears automatically if the service is deselected.
- Added a `Send test notification` button and matching `send_test_notification` action that deliver immediately even when nothing is due, so notification routing can be confirmed without waiting for the weekly summary.
- Added notification delivery diagnostics to the maintenance summary sensor, including the next scheduled summary and the status, time, recipients, item count, and any error from the most recent attempt.
- Added a CSV export of the vehicle's current maintenance state for resale, warranty, or personal records. This remains a current-state snapshot, not a lifetime repair-history database.

### Changed

- Clarified in setup and options that the odometer sensor must report miles, and that a miles conversion template sensor is needed first if the vehicle reports kilometres.
- Bumped the Lovelace resource version so browsers and Companion App clients load the new card instead of a cached 0.2.2 bundle.

### Notes

- Stored maintenance records, vehicle entries, intervals, extensions, and dashboard configurations are unchanged. The new wash and notification-diagnostic keys are optional additions to existing storage, so no data migration is required and no config-entry version bump was needed.

## 0.2.2 - 2026-07-26

- Fixed the visual editor losing focus when Home Assistant repeats `setConfig()` while the card configuration dialog is open.
- Prevented unchanged config echoes from rebuilding the editor DOM.
- Deferred genuinely necessary editor rebuilds until the active dropdown, number field, or color control loses focus.
- Bumped the Lovelace resource version so browsers and Companion App clients do not reuse the cached 0.2.1 bootstrap.
- Added regression checks for both repeated config updates and focus-safe editor rendering.

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
