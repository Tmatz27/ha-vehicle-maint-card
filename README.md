# Vehicle Maintenance for Home Assistant

A vehicle-neutral, mileage-only Home Assistant integration with a bundled mobile-first card. Each vehicle is an independent config entry and device; adding another vehicle requires no YAML, helpers, copied packages, or hand-built automations.

## Features

- One authoritative odometer source with a persisted last-valid cache and live/cached status.
- Explicit service records: Not set, Never performed, last completed, or due at a known mileage.
- Per-vehicle service selection and editable intervals.
- Recurring and mileage-milestone services.
- Exact-mileage completion, factual due overrides, and independent **Remind me later** snoozes.
- Configurable weekly summaries that ignore setup-required and actively snoozed services.
- Effective odometer, summary, per-service, and aggregate due entities.
- Standalone visual card; no Mushroom, Auto Entities, card-mod, or other HACS card is required.
- Multiple vehicles and cards on the same dashboard.

## Review version

This work is prepared as `v0.1.0`. Do not publish a release or remove legacy package material until migration and live Home Assistant testing are complete. The manifest, card, frontend cache URL, and changelog use the same version.

## Installation for testing

1. Add the repository root to **HACS → Integrations → Custom repositories** as **Integration**.
2. Install Vehicle Maintenance and restart Home Assistant.
3. Add **Vehicle Maintenance** under **Settings → Devices & services**.
4. Enter a vehicle display name, select its authoritative odometer, choose services, and configure notifications.
5. Review the interval for every selected service in the second setup step.
6. Add **Vehicle Maintenance Card** from the dashboard card picker and select the integration-created vehicle.

The integration serves and loads `/vehicle-maintenance/vehicle-maint-card.js?v=0.1.0`. After an update, restart Home Assistant and clear the frontend cache if the console does not show `VEHICLE-MAINT-CARD v0.1.0`.

## Card behavior

The default **Due soon** view displays setup-required services plus unsnoozed overdue services and services due within 2,000 miles. **All maintenance** displays every selected service sorted by factual scheduled due mileage, including deferred and completed milestones.

Tap a service row—not a disconnected global selector—to open its action panel:

- **Completed now at _odometer_ mi**
- **Mileage when completed** for delayed entry
- **Remind me later** for 500, 1,000, 2,000, or custom miles from the effective odometer
- **Clear reminder**
- Advanced explicit record initialization/correction
- A separate information icon opens Home Assistant More Info

Snoozing never changes last completion, interval, or scheduled due mileage. Completion clears both snooze and due override.

Minimal advanced YAML:

```yaml
type: custom:vehicle-maint-card
main_entity: sensor.REPLACE_maintenance
upcoming_miles: 2000
```

The visual editor is recommended and does not require manually finding entity IDs.

## Entities

Each vehicle device contains:

- Effective odometer sensor, including `source: live`, `cached`, or `manual`
- Maintenance summary with `setup_required`, `overdue`, `due_soon`, `okay`, or `unavailable`
- One miles-remaining sensor per selected service with factual record and snooze attributes
- Maintenance-due binary sensor for normal automations

## Actions

- `vehicle_maintenance.log_maintenance`
- `vehicle_maintenance.snooze_maintenance`
- `vehicle_maintenance.clear_snooze`
- `vehicle_maintenance.set_maintenance`
- `vehicle_maintenance.reset_service`
- `vehicle_maintenance.set_effective_odometer`

See **Developer Tools → Actions** for fields and selectors.

## Notifications

Notifications are optional and configured per vehicle: enabled state, target action, threshold (default 1,500 miles), weekday (default Sunday), and time (default 17:00). Summaries use the effective cached odometer, sort by urgency, skip uninitialized and actively snoozed services, never send empty messages, and use a stable per-entry tag.

## Package migration

Follow the non-destructive checklist in [`docs/MIGRATION.md`](docs/MIGRATION.md). Keep the old package outside the active packages directory until values, milestones, cached odometer behavior, and notifications have been verified.

## Data scope

The integration preserves accurate current service records and last-completed mileage. It does not currently maintain or claim to maintain a complete maintenance event log.
