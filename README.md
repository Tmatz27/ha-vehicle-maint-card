# Generic Home Assistant Vehicle Maintenance Dashboard

This repository contains only a reusable Lovelace dashboard. It does not include,
modify, or assume ownership of a Home Assistant maintenance package.

The dashboard is intentionally vehicle-neutral. It contains no owner, device,
location, registration, manufacturer, model, model year, notification target, or
other personally identifiable information.

## Included file

- `dashboards/vehicle_maintenance.yaml` — a manual-card YAML stack for one vehicle.

## Frontend requirements

Install these cards through HACS:

- Mushroom
- Auto Entities
- Template Entity Row
- card-mod

The dashboard does not require Browser Mod or a popup integration.

## Configure it for a vehicle

1. Copy `dashboards/vehicle_maintenance.yaml` into a manual card.
2. Search the copied YAML for `REPLACE_`. Every value with that prefix is a
   configuration placeholder, not real vehicle information.
3. Replace `REPLACE_VEHICLE_NAME` with the dashboard display name.
4. Replace `replace_vehicle` with the common entity prefix used by the existing
   maintenance package. For example, if a package exposes
   `sensor.family_car_oil_change_miles_remaining`, use `family_car`.
5. Replace the summary, odometer, helper, and script entity IDs if the existing
   package uses a different naming scheme.
6. Delete any optional action or setup section whose entities are not supplied by
   that package.

The only mandatory data for the two maintenance lists is a collection of numeric
sensor states representing miles remaining. Those sensors should share a prefix
and end in `_miles_remaining`. The dashboard filters and sorts them automatically.

## Expected optional metadata

Rows are more descriptive when each miles-remaining sensor provides:

```yaml
attributes:
  service_name: Oil Change
  next_due_mileage: 36000
```

If `service_name` is missing, the row falls back to the entity's friendly name.
If `next_due_mileage` is missing, the secondary due-mileage line is omitted.

See the comments in the dashboard file for optional summary and action entities.

