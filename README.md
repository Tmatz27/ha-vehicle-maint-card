# Vehicle Maintenance Card for Home Assistant

A vehicle-neutral Lovelace card for displaying mileage-based maintenance sensors.
The repository contains no maintenance package and no owner, location, device,
registration, manufacturer, model, or notification-target information.

## Install with HACS

1. Open **HACS → Frontend**.
2. Open the menu and choose **Custom repositories**.
3. Enter the repository root URL—not a `/tree/...` or `/packages` URL:

   ```text
   https://github.com/OWNER/REPOSITORY
   ```

4. Select **Dashboard** as the category and add the repository.
5. Install **Vehicle Maintenance Card** and restart or refresh Home Assistant when
   HACS requests it.

The `hacs.json` manifest and root `vehicle-maint-card.js` file provide the
repository structure HACS expects. The previous `packages` path is intentionally
absent because this project does not distribute a Home Assistant package.

## Add the card

Use this minimal manual-card configuration:

```yaml
type: custom:vehicle-maint-card
vehicle_name: My Vehicle
entity_prefix: vehicle
```

`entity_prefix` discovers numeric sensors matching:

```text
sensor.<entity_prefix>_*_miles_remaining
```

For a package with differently named sensors, provide an explicit list instead:

```yaml
type: custom:vehicle-maint-card
vehicle_name: My Vehicle
entities:
  - sensor.vehicle_oil_change_miles_remaining
  - sensor.vehicle_tire_rotation_miles_remaining
```

## Configuration

| Option | Required | Default | Description |
| --- | --- | --- | --- |
| `entity_prefix` | One of prefix/list | — | Discovers matching miles-remaining sensors. |
| `entities` | One of prefix/list | — | Explicit entity list for packages without a common prefix. |
| `vehicle_name` | No | `Vehicle Maintenance` | Non-sensitive heading displayed by the card. |
| `odometer_entity` | No | — | Numeric odometer sensor shown in the header. |
| `sync_script` | No | — | Script called by an optional Sync button. |
| `due_miles` | No | `500` | Upper boundary for due status. |
| `soon_miles` | No | `1500` | Upper boundary for soon status. |
| `upcoming_miles` | No | `6000` | Maximum distance shown unless `show_all` is enabled. |
| `show_all` | No | `false` | Shows services beyond the upcoming boundary. |
| `icon` | No | `mdi:car` | Header icon. |

Each maintenance sensor must have a numeric miles-remaining state. Negative values
are displayed as overdue. These optional attributes improve presentation:

```yaml
attributes:
  service_name: Oil Change
  next_due_mileage: 36000
```

Selecting a maintenance row opens Home Assistant's standard entity details dialog.

## Manual installation

1. Copy `vehicle-maint-card.js` to `config/www/vehicle-maint-card.js`.
2. Add `/local/vehicle-maint-card.js` as a JavaScript module under dashboard
   resources.
3. Add the card using the YAML examples above.
