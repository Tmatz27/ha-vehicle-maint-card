# Vehicle Maintenance for Home Assistant

Vehicle Maintenance is a Home Assistant custom integration and dashboard card for tracking mileage-based vehicle maintenance.

Each vehicle is configured through the Home Assistant interface and receives its own maintenance entities, intervals, notifications, and dashboard card. Adding another vehicle does not require copying YAML packages, helpers, templates, scripts, or automations.

## Features

- Supports multiple vehicles
- Uses an existing Home Assistant odometer sensor
- Remembers the last valid odometer reading when the source is temporarily unavailable
- Creates standardized maintenance entities for each vehicle
- Selects the complete built-in service and milestone catalog for new vehicles
- Uses four grouped, persistent checklists so multiple services can be added or removed in one pass
- Starts every selected item as Never performed instead of Not set
- Allows different service intervals for each vehicle
- Includes modern Subaru normal-use starting intervals with inspection and condition reminders clearly identified
- Shows overdue and upcoming maintenance
- Logs maintenance using the current odometer or an exact earlier mileage
- Logs several items from one service visit at a shared odometer reading
- Extends maintenance reminders without recording false maintenance
- Provides Due Soon and All Maintenance views
- Includes optional scheduled notifications
- Includes a mobile-friendly dashboard card
- Supports a per-card accent color or the active Home Assistant theme color
- Requires no additional custom dashboard cards

## Requirements

- Home Assistant 2024.7 or newer
- A numeric odometer sensor that reports mileage in miles
- HACS is recommended for installation

If your vehicle reports kilometers, create a Home Assistant conversion sensor that reports miles and select that sensor during setup.

Home Assistant 2026.3 or newer displays the integration's bundled icon. Older supported Home Assistant releases use the generic integration placeholder but retain all maintenance functionality.

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
7. Review the four maintenance checklists: Scheduled Service and Replacements, Inspections, Condition-Based Reminders, and Mileage Milestones. All built-in items are selected by default. Check or uncheck as many items as needed, then submit once.
8. Review the mileage interval for each selected service.
9. Configure optional maintenance notifications.
10. Finish the setup.

Home Assistant creates a separate device for the vehicle.

Every selected service starts as **Never performed**. The integration immediately calculates its first due mileage from the configured interval. Log the most recent factual completion mileage when one is known.

Repeat these steps for every additional vehicle. Each vehicle remains independent, so logging or extending maintenance for one vehicle does not affect another.

## Supported maintenance

Available maintenance items include:

- Oil Change
- Tire Rotation
- Engine Air Filter
- Cabin Air Filter
- Brake Fluid
- Coolant
- CVT Fluid Inspection
- Differential Fluid Inspection
- Wiper Blades
- Battery Check
- Tire Replacement
- Spark Plugs
- Brake Pad Inspection
- Wheel Alignment Check
- PCV Valve Inspection
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

### Built-in Subaru schedule defaults

The starting intervals follow the normal-use schedule in Subaru of America's [2024 Warranty and Maintenance Booklet](https://techinfo.subaru.com/stis/doc/warrantyBooklet/2024_war_and_maint_041723.pdf) where Subaru publishes a fixed mileage. The same booklet distinguishes replacement, inspection, and performed items. The integration keeps that distinction instead of presenting every reminder as a required replacement.

| Maintenance item | Default | Meaning |
|---|---:|---|
| Oil Change | 6,000 mi | Replace |
| Tire Rotation | 6,000 mi | Perform and inspect |
| Engine Air Filter | 30,000 mi | Replace |
| Cabin Air Filter | 12,000 mi | Replace |
| Brake Fluid | 30,000 mi | Replace |
| Coolant | First at 137,500 mi; then 75,000 mi | Replace |
| CVT Fluid | 30,000 mi | Inspect under normal use |
| Differential Fluid | 30,000 mi | Inspect under normal use |
| Spark Plugs | 60,000 mi | Replace |
| Brake Pads | 12,000 mi | Inspect and replace by wear |
| Fuel Filter | 72,000 mi | Replace |
| Wheel Alignment | 12,000 mi | Condition reminder; align when needed |
| Wiper Blades | 12,000 mi | Condition reminder |
| Battery | 12,000 mi | Condition reminder |
| Tire Replacement | 50,000 mi | Planning reminder; replace by tread, age, and condition |
| PCV Valve | 60,000 mi | Inspection reminder |
| Timing Belt or Chain | 100,000 mi | Inspection reminder; model dependent |

Subaru specifies shorter intervals for some severe driving conditions. For example, the booklet calls for 3,000-mile oil changes under severe use and approximately 24,855-mile CVT fluid replacement when applicable. Always review the booklet for the exact model, year, engine, location, and driving conditions.

The named mileage milestones are convenience reminders. They do not replace the itemized factory schedule.

Every interval can be changed for each vehicle under:

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
8. Optionally choose a custom card accent color. Leave it on the Home Assistant theme setting to follow your dashboard theme.
9. Save the card.

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
accent_color: "#43a047"
```

### Card configuration

| Option | Required | Default | Description |
|---|---:|---:|---|
| `type` | Yes | None | Must be `custom:vehicle-maint-card` |
| `main_entity` | Yes | None | The vehicle's main maintenance summary sensor |
| `upcoming_miles` | No | `2000` | How many miles ahead appear in Due Soon |
| `extend_miles` | No | `1000` | Default amount offered by Extend Maintenance |
| `accent_color` | No | Home Assistant theme | Six-digit hex color used for the card accent, such as `"#43a047"` for green |

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
    accent_color: "#1976d2"

  - type: custom:vehicle-maint-card
    main_entity: sensor.forester_maintenance
    upcoming_miles: 2000
    extend_miles: 1000
    accent_color: "#43a047"
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
- Services marked Never performed

An extended item remains visible here and shows the mileage when it will require attention again.

## Log Maintenance

Tap a maintenance row and select **Log Maintenance**.

The popup begins with a short **Why it matters** summary explaining the purpose of that maintenance item. This is informational guidance; use the schedule appropriate for the vehicle and its operating conditions.

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

## Log a Service Visit

Use **Log a Service Visit** when several maintenance items were completed together, such as an oil change, tire rotation, and cabin air filter replacement.

1. Select **Log a Service Visit** on the card.
2. Check every maintenance item completed during the visit. Use **Select Due Items** as a shortcut when appropriate.
3. Log the visit using the current odometer, or enter the exact mileage if the visit happened earlier.

The integration applies one factual mileage to every selected item, calculates each recurring item's next due mileage from its own interval, clears active extensions for those items, and saves the vehicle once. One-time mileage milestones retain their milestone behavior.

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

## Never performed services

A newly configured service displays **Never performed** until maintenance is logged.

This is a starting state, not a fabricated completion. Its first due mileage is the configured interval. For example, a new oil-change record with a 6,000-mile interval is first due at 6,000 miles. If the vehicle is already beyond that mileage, the card correctly shows the item as overdue and still identifies it as Never performed.

To begin tracking it:

1. Open the service.
2. Select **Log Maintenance**.
3. Use the current odometer or enter the mileage when it was most recently completed.

If the previous completion mileage is unknown, leave the item as Never performed. When a factual mileage becomes available, log it using the current odometer or enter the exact earlier mileage.

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

The integration schedules these notifications internally for each vehicle. It does not create a separate Home Assistant automation entity, so nothing new appears under **Settings > Automations & scenes**.

Available settings include:

- Enable or disable notifications
- Notification target
- Notification mileage threshold
- Notification weekday
- Notification time

Select the phone or other notify entity that should receive the summary. For
example:

`notify.sm_s926u`

The integration sends modern notify entities through Home Assistant's
`notify.send_message` action. Existing configurations that use a legacy
phone-specific action such as `notify.mobile_app_travis_phone` remain supported.

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

Choose the vehicle and continue through its configuration screens to **Maintenance notifications**. Changes reload that vehicle's internal schedule automatically. Disable the built-in notification before creating a separate Home Assistant notification automation, or both may send alerts.

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

### Delete a vehicle

Each vehicle appears as its own entry under **Settings > Devices & services > Vehicle Maintenance**. Open the vehicle's menu and select **Delete** to remove that vehicle, its entities, and its stored maintenance records. Deleting one vehicle does not affect any other vehicle.

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

A value of zero in an old helper should not automatically be imported as a completed service. If the actual completion mileage is unknown, leave the service as Never performed.

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

Removing the integration entry removes that vehicle's entities and persisted maintenance records from Home Assistant. Deletion is permanent, so record any values you want to preserve first.

## License

Vehicle Maintenance is released under the MIT License.
