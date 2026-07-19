# Adding another vehicle

For a small garage, use one package and one dashboard file per vehicle. This is
more transparent than a custom integration and keeps every entity editable from
Home Assistant.

## Checklist

1. Copy `packages/vehicle_outback.yaml` to `packages/vehicle_<slug>.yaml`.
2. Replace the `outback` entity prefix with a short, stable vehicle slug.
3. Replace `Outback` and `2024 Outback Wilderness` with the display names.
4. Set the real odometer entity in the effective-odometer sensor and sync script.
5. Give every automation a new `id`.
6. Confirm the maintenance intervals for the new vehicle's manufacturer schedule.
7. Copy the dashboard file and replace its entity prefix.
8. Reload template entities/scripts/automations or restart Home Assistant.
9. Use the setup workflow to initialize each service independently.

## Stable naming

Do not add version suffixes to production entity IDs. Keep entity IDs stable and
track package revisions in Git. A useful convention is:

```text
input_number.<vehicle>_last_<service>
input_number.<vehicle>_<service>_extension
input_boolean.<vehicle>_track_<service>
sensor.<vehicle>_<service>_miles_remaining
sensor.<vehicle>_maintenance_summary
script.<vehicle>_log_maintenance
```

## Scaling beyond a few vehicles

Copying a package is reasonable for two to five vehicles. If the service catalog
changes frequently or the garage grows beyond that, generate these packages from
a small vehicle definition file rather than editing copies by hand. A custom
integration is only worthwhile if configuration through the UI, a persistent
service-history database, or public distribution is required.

