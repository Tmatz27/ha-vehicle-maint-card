# Vehicle Maintenance for Home Assistant

Vehicle Maintenance is a Home Assistant custom integration and dashboard card for tracking mileage-based vehicle maintenance.

Each vehicle is configured through the Home Assistant interface and receives its own maintenance entities, intervals, notifications, and dashboard card. Adding another vehicle does not require copying YAML packages, helpers, templates, scripts, or automations.

## Features

- Supports multiple vehicles
- Uses an existing Home Assistant odometer sensor
- Remembers the last valid odometer reading when the source is temporarily unavailable
- Creates standardized maintenance entities for each vehicle
- Includes common recurring maintenance services and mileage milestones
- Allows different service intervals for each vehicle
- Shows overdue and upcoming maintenance
- Logs maintenance using the current odometer or an exact earlier mileage
- Extends maintenance reminders without recording false maintenance
- Provides Due Soon and All Maintenance views
- Includes optional scheduled notifications
- Includes a mobile-friendly dashboard card
- Requires no additional custom dashboard cards

## Requirements

- Home Assistant 2024.7 or newer
- A numeric odometer sensor that reports mileage in miles
- HACS is recommended for installation

If your vehicle reports kilometers, create a Home Assistant conversion sensor that reports miles and select that sensor during setup.

## Installation

### Install with HACS

1. Open **HACS** in Home Assistant.
2. Select **Integrations**.
3. Open the three-dot menu.
4. Select **Custom repositories**.
5. Enter:

   `https://github.com/Tmatz27/ha-vehicle-maint-card`

6. Select **Integration** as the category.
7. Select **Add**.
8. Find and install **Vehicle Maintenance**.
9. Restart Home Assistant.

The integration includes the Vehicle Maintenance Card. A separate Lovelace resource normally does not need to be added.

## Add a vehicle

After restarting Home Assistant:

1. Open **Settings**.
2. Select **Devices & services**.
3. Select **Add Integration**.
4. Search for **Vehicle Maintenance**.
5. Enter a display name for the vehicle.
6. Select the vehicle's odometer sensor.
7. Select the maintenance services you want to track.
8. Configure optional maintenance notifications.
9. Review the mileage interval for each selected service.
10. Finish the setup.

Home Assistant creates a separate device for the vehicle.

Repeat these steps for every additional vehicle. Each vehicle remains independent, so logging or extending maintenance for one vehicle does not affect another.

## Supported maintenance

Available maintenance items include:

- Oil Change
- Tire Rotation
- Engine Air Filter
- Cabin Air Filter
- Brake Fluid
- Coolant
- Transmission Fluid
- Differential Service
- Wiper Blades
- Battery Check
- Tire Replacement
- Spark Plugs
- Brake Pads
- Wheel Alignment
- PCV Valve
- Fuel Filter
- Timing Belt or Chain Inspection

Available mileage milestones include:

- 30,000-mile Service
- 60,000-mile Service
- 90,000-mile Service
- 120,000-mile Service
- 125,000-mile Service
- 180,000-mile Service
- 200,000-mile Service

The default intervals are starting points. Review them against the maintenance schedule for the specific vehicle.

Intervals can be changed later under:

**Settings → Devices & services → Vehicle Maintenance → Configure**

## Add the dashboard card

### Visual editor

The visual editor is the easiest way to add the card.

1. Open the desired Home Assistant dashboard.
2. Select **Edit dashboard**.
3. Select **Add card**.
4. Search for **Vehicle Maintenance Card**.
5. Select the vehicle.
6. Set the Due Soon mileage window.
7. Set the default maintenance extension amount.
8. Save the card.

The card automatically uses the selected vehicle's maintenance entities.

### Minimal YAML card

Only the vehicle's main maintenance entity is required:

```yaml
type: custom:vehicle-maint-card
main_entity: sensor.outback_maintenance
```

With this configuration:

- Maintenance due within 2,000 miles is shown by default.
- The default extension amount is 1,000 miles.
- The card includes Due Soon and All Maintenance views.

Replace `sensor.outback_maintenance` with the maintenance summary entity created for your vehicle.

### Full YAML card

```yaml
type: custom:vehicle-maint-card
main_entity: sensor.outback_maintenance
upcoming_miles: 2000
extend_miles: 1000
```

### Card configuration

| Option | Required | Default | Description |
|---|---:|---:|---|
| `type` | Yes | None | Must be `custom:vehicle-maint-card` |
| `main_entity` | Yes | None | The vehicle's main maintenance summary sensor |
| `upcoming_miles` | No | `2000` | How many miles ahead appear in Due Soon |
| `extend_miles` | No | `1000` | Default amount offered by Extend Maintenance |

The card intentionally has very few configuration options. Vehicle name, odometer source, maintenance services, intervals, and notifications are managed through the integration rather than duplicated in dashboard YAML.

## Multiple vehicles on one dashboard

Add one card for each vehicle.

```yaml
type: vertical-stack
cards:
  - type: custom:vehicle-maint-card
    main_entity: sensor.outback_maintenance
    upcoming_miles: 2000
    extend_miles: 1000

  - type: custom:vehicle-maint-card
    main_entity: sensor.forester_maintenance
    upcoming_miles: 2000
    extend_miles: 1000
```

Each card automatically finds the maintenance entities belonging to its selected vehicle.

## Using the card

The card has two primary views.

### Due Soon

Due Soon displays maintenance that is:

- Overdue
- Due within the configured `upcoming_miles` window
- Ready for attention after a previous extension expires

Maintenance with an active extension is temporarily removed from Due Soon and excluded from notifications.

### All Maintenance

All Maintenance displays every selected maintenance item, including:

- Maintenance that is not due yet
- Overdue maintenance
- Maintenance with an active extension
- Completed mileage milestones
- Services that have not been logged yet

An extended item remains visible here and shows the mileage when it will require attention again.

## Log Maintenance

Tap a maintenance row and select **Log Maintenance**.

You can log maintenance in two ways.

### Use the current odometer

Select **Use Current Odometer** to record the maintenance at the vehicle's current effective odometer.

Example:

- Current odometer: 44,973 miles
- Service interval: 6,000 miles
- Maintenance logged at: 44,973 miles
- Next maintenance due: 50,973 miles

This is the normal option when maintenance is logged immediately after it is completed.

### Enter the completion mileage

If you forgot to log the maintenance when it was completed, enter the odometer reading from when the work was actually done.

Example:

- Current odometer: 44,973 miles
- Oil change was completed at: 43,500 miles
- Oil change interval: 6,000 miles
- Next oil change due: 49,500 miles
- Miles remaining: 4,527 miles

The entered mileage is treated as the actual completion mileage. The next due mileage is calculated from that value.

The card shows the calculated next due mileage before saving.

Logging maintenance clears any active extension for that maintenance item.

## Extend Maintenance

Use **Extend Maintenance** when maintenance has been inspected but does not need to be completed yet.

For example, tires may reach their expected replacement mileage while still having acceptable tread.

Available extension choices include:

- 500 miles
- 1,000 miles
- 2,000 miles
- Custom mileage

Extensions are calculated from the current odometer.

Example:

- Current odometer: 44,973 miles
- Selected extension: 1,000 miles
- Maintenance requires attention again at: 45,973 miles

Extending maintenance:

- Does not mark maintenance as completed
- Does not change the normal service interval
- Does not create a false completion mileage
- Temporarily removes the item from Due Soon
- Temporarily suppresses notifications for that item
- Keeps the item visible under All Maintenance
- Automatically expires when the vehicle reaches the extension mileage

An active extension can be cleared from the same Extend Maintenance section.

## Services that have not been logged

A newly configured service may display **Not logged yet**.

This means the integration does not have enough information to calculate its next due mileage. It does not assume the service was completed at zero miles.

To begin tracking it:

1. Open the service.
2. Select **Log Maintenance**.
3. Use the current odometer or enter the mileage when it was most recently completed.

If the previous completion mileage is unknown, leave the service unlogged until accurate information is available.

## Odometer behavior

The integration maintains an effective odometer for each vehicle.

The source can be:

- **Live**: The configured odometer entity currently has a valid value
- **Cached**: The live entity is temporarily unavailable, so the last valid mileage is being used
- **Unavailable**: No valid live or cached mileage exists

The integration rejects invalid odometer readings, including:

- `unknown`
- `unavailable`
- Blank values
- Nonnumeric values
- Unexpected decreases
- A temporary zero after a positive mileage has already been recorded

If no effective odometer is available:

- The card displays **Odometer unavailable**
- Logging with the current odometer is disabled
- Extending maintenance is disabled
- Logging at a manually entered completion mileage remains available

## Notifications

Notifications are optional and configured separately for each vehicle.

Available settings include:

- Enable or disable notifications
- Notification action
- Notification mileage threshold
- Notification weekday
- Notification time

Example notification action:

`notify.mobile_app_travis_phone`

Notifications include only maintenance that:

- Belongs to the selected vehicle
- Is currently enabled
- Has enough information to calculate a due mileage
- Is within the notification threshold
- Does not have an active extension
- Has not already been completed as a mileage milestone

Empty notifications are not sent.

Notification settings can be changed under:

**Settings → Devices & services → Vehicle Maintenance → Configure**

## Entities

Each vehicle receives its own Home Assistant device and entities.

Typical entities include:

### Effective odometer sensor

Example:

`sensor.outback_effective_odometer`

This entity reports the mileage currently being used by the integration.

Its attributes indicate whether the value is live or cached.

### Maintenance summary sensor

Example:

`sensor.outback_maintenance`

This is the entity selected by the dashboard card.

It contains the vehicle name, effective odometer, maintenance counts, and vehicle entry information.

### Maintenance sensors

Each selected maintenance service receives a sensor.

Examples:

- `sensor.outback_oil_change`
- `sensor.outback_tire_rotation`
- `sensor.outback_cabin_air_filter`

These sensors report miles remaining and include service information as attributes.

### Maintenance due binary sensor

Example:

`binary_sensor.outback_maintenance_due`

This entity can be used in Home Assistant automations. It turns on when tracked maintenance requires attention and does not have an active extension.

## Changing vehicle settings

To change a vehicle:

1. Open **Settings**.
2. Select **Devices & services**.
3. Find **Vehicle Maintenance**.
4. Select the vehicle.
5. Select **Configure**.

You can change:

- Vehicle name
- Odometer entity
- Tracked maintenance services
- Service intervals
- Notification settings
- Notification schedule

Deselecting a maintenance service removes it from the active card and notifications. Its saved maintenance value is retained in case the service is enabled again later.

## Migrating from a YAML package

Do not immediately delete the existing maintenance package.

For each vehicle:

1. Add the vehicle through the integration.
2. Select the same authoritative odometer entity.
3. Review every service interval.
4. Open All Maintenance on the new card.
5. Log the most recent known completion mileage for each service.
6. Compare the new remaining mileage with the old package.
7. Recreate any intentional maintenance extensions.
8. Verify milestone services.
9. Test notifications.
10. Disable the old package notification automation.
11. Keep the old package as a backup until the new integration has been verified.

A value of zero in an old helper should not automatically be imported as a completed service. If the actual completion mileage is unknown, leave the service as Not logged yet.

See [`docs/MIGRATION.md`](docs/MIGRATION.md) for the complete migration checklist.

## Updating

When an update is available:

1. Install the update through HACS.
2. Restart Home Assistant.
3. Refresh the browser or Home Assistant mobile app.
4. If the old card is still displayed, clear the frontend cache and reload the dashboard.

## Troubleshooting

### The card is not available

Confirm that:

- The integration is installed
- Home Assistant was restarted
- The browser or mobile app was refreshed
- The Vehicle Maintenance integration loaded without errors

The card is bundled with the integration and normally does not require a manually added Lovelace resource.

### No vehicle appears in the card editor

Confirm that at least one Vehicle Maintenance integration entry has been configured successfully.

### The card says the main entity is missing

Select the vehicle's maintenance summary sensor, such as:

`sensor.outback_maintenance`

Do not select an individual oil-change or tire-rotation sensor as `main_entity`.

### The odometer is unavailable

Check that the configured odometer entity:

- Exists
- Has a numeric state
- Reports miles
- Is not `unknown` or `unavailable`

### Maintenance mileage looks incorrect

Check:

- The last completion mileage
- The configured service interval
- The current effective odometer
- Whether an extension is active

The normal calculation is:

`next due mileage = completion mileage + service interval`

`miles remaining = next due mileage - current odometer`

The extension calculation is:

`extension target = current odometer + extension amount`

### Changes are not appearing after an update

Restart Home Assistant and clear the frontend cache. Confirm the browser is loading the current version of the bundled card.

## Data scope

Vehicle Maintenance tracks the current maintenance state needed to calculate the next service mileage.

It is not intended to be:

- A complete lifetime service-history database
- A receipt or document manager
- A repair-cost tracker
- A replacement for manufacturer maintenance recommendations

Keep receipts and complete service records in a dedicated document or vehicle-record system.

## Removing the integration

Before removing a vehicle entry, record any maintenance values you want to preserve.

Removing the integration entry removes that vehicle's entities from Home Assistant. Reinstalling the integration does not guarantee that deleted vehicle data can be recovered.

## License

Vehicle Maintenance is released under the MIT License.
