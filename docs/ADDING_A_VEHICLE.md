# Adding a Vehicle

Every vehicle is a separate Home Assistant config entry and device. No YAML package, helper duplication, entity-prefix replacement, or copied automation is required.

## Before setup

Confirm that the vehicle already has a Home Assistant odometer sensor with:

- A numeric state
- Mileage reported in miles
- A stable entity ID

If the source reports kilometers, create a miles conversion sensor first.

## Add the vehicle

1. Open **Settings > Devices & services**.
2. Select **Add Integration**.
3. Search for **Vehicle Maintenance**.
4. Enter the vehicle display name.
5. Select its authoritative odometer sensor.
6. Review the recurring services and mileage milestones. The full catalog is selected by default; deselect only items you do not want to track.
7. Enable notifications if desired and select the notification action.
8. Review every service interval on the next screen.
9. Finish setup.

The odometer sensor cannot be assigned to two Vehicle Maintenance entries. This prevents two vehicle records from accidentally using the same mileage.

## Add its card

Use the dashboard visual editor and select **Vehicle Maintenance Card**, or add:

```yaml
type: custom:vehicle-maint-card
main_entity: sensor.REPLACE_maintenance
upcoming_miles: 2000
extend_miles: 1000
accent_color: "#43a047"
```

Replace the example entity with the maintenance summary sensor created for the vehicle.

## Begin tracking services

Open **All Maintenance** on the card. Every new item starts as **Never performed** and receives a first due mileage from its configured interval.

For each known service:

1. Open its row.
2. Select **Log Maintenance**.
3. Use the current odometer or enter the actual earlier completion mileage.
4. Review the next due preview and save.

Do not enter zero when the previous completion mileage is unknown. Leave the item as Never performed until accurate information is available.

Mileage milestones use the same Log Maintenance workflow when completed.

## Change the vehicle later

Open **Settings > Devices & services > Vehicle Maintenance**, select the vehicle, and choose **Configure**.

The options flow can change:

- Display name
- Odometer source
- Selected maintenance services
- Per-vehicle intervals
- Notification target, threshold, weekday, and time

Disabling a service removes it from active tracking but retains its stored record in case it is enabled again.

To remove the vehicle completely, open its menu on the Vehicle Maintenance integration page and select **Delete**. This removes only that vehicle and its stored maintenance records.

## Add another vehicle

Repeat the integration setup and add another card using the new vehicle's maintenance summary sensor. State, intervals, extensions, and notifications remain isolated between vehicles.
