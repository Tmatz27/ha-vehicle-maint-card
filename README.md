# Vehicle Maintenance for Home Assistant

A vehicle-neutral custom integration and Lovelace card for standardized,
mileage-based vehicle maintenance. The repository contains no owner, location,
device, registration, manufacturer, model, or notification-target information.

## What changed

The project is now a Home Assistant **integration**, rather than a YAML package or
a dashboard-only repository. The integration owns the standardized entities and
persistent maintenance state. The bundled card selects one integration-created
vehicle entity and discovers the rest automatically.

Each configured vehicle is independent, so a dashboard can contain multiple
Vehicle Maintenance cards—one card per vehicle.

## Install with HACS

1. Remove any earlier custom-repository entry that points to `/tree/...` or
   `/packages`.
2. Open **HACS → Integrations → Custom repositories**.
3. Add the repository root URL:

   ```text
   https://github.com/OWNER/REPOSITORY
   ```

4. Select **Integration** as the category and install **Vehicle Maintenance**.
5. Restart Home Assistant.

On startup, the integration loads its bundled card through Home Assistant's
frontend component. It does not depend on a storage-mode Lovelace resource. After
upgrading from an earlier release, restart Home Assistant and perform a full
browser refresh. The card will then appear in the dashboard card picker as
**Vehicle Maintenance Card**.

## Add a vehicle

1. Open **Settings → Devices & services**.
2. Select **Add integration** and search for **Vehicle Maintenance**.
3. Enter a non-sensitive vehicle display name.
4. Select the vehicle's existing odometer sensor.
5. Select every maintenance service that should be tracked.
6. Optionally enter a notify service such as `notify.notify` and choose the mileage
   threshold for the Sunday 17:00 maintenance summary.
7. Submit the form.

The integration creates:

- One main maintenance entity for card selection.
- One miles-remaining sensor for every selected service.
- A device that groups all entities belonging to that vehicle.
- Persistent last-completed and extension values for each service.

Open the integration's **Configure** dialog later to change the odometer or tracked
services.

## Card troubleshooting

The integration automatically loads the bundled card and serves it at:

```text
/vehicle-maintenance/vehicle-maint-card.js
```

You should not need to add a dashboard resource manually. If an earlier version
created a manual resource entry for this URL, remove that entry to prevent the
card from being loaded twice. Then restart Home Assistant and clear the browser or
companion-app frontend cache.

If the URL above returns JavaScript when opened directly but the card is absent,
check the browser console for `VEHICLE-MAINT-CARD`. Its version should match the
installed integration version.

## One repository or two?

Only one repository is required. HACS installs this project as an **Integration**.
The Python integration contains and serves the frontend JavaScript, and Home
Assistant's frontend loader imports it globally. A separate HACS Dashboard
repository would only be necessary if the card were intended to work without the
integration.

## Add and visually configure a card

1. Edit a dashboard and select **Add card**.
2. Choose **Vehicle Maintenance Card**.
3. Select a vehicle from the visual editor.
4. Optionally adjust the upcoming-mile boundary and default extension amount.
5. Save the card.

No entity IDs need to be entered in YAML. The card stores only the selected main
entity and uses its integration entry ID to find that vehicle's service sensors.

Minimal YAML remains available for advanced users:

```yaml
type: custom:vehicle-maint-card
main_entity: sensor.my_vehicle_maintenance
upcoming_miles: 6000
extend_miles: 1000
```

## Card workflow

The card provides a service selector and two actions:

- **Log maintenance** records the current odometer as the service's completion
  mileage and clears any prior extension.
- **Extend maintenance** moves the next due mileage by 500, 1,000, or 2,000 miles
  without changing completion history.

Both actions ask for confirmation. Selecting a maintenance row opens Home
Assistant's standard entity details dialog.

An expandable **Set maintenance history** section also supports the package-era
setup workflows:

- Last completed at a known mileage.
- Due at a known mileage.
- Never performed, with mileage zero retained as a valid baseline.

Milestone services from 30,000 through 200,000 miles can be selected during
integration setup. Logging a milestone completes and hides it; resetting it to
Never performed makes it active again. The optional weekly notification includes
all selected recurring and incomplete milestone services within the configured
threshold.

## Package functionality mapping

| Previous package behavior | Integration behavior |
| --- | --- |
| Effective odometer template | User selects the authoritative odometer sensor. |
| Miles-remaining templates | Integration creates standardized sensors. |
| Selected service helper | Service selector is built into the card. |
| Log script | **Log maintenance** card action and integration service. |
| Extend script | **Extend maintenance** preserves completion history. |
| Initial history setup | Expandable history workflow in the card. |
| Milestone booleans | Persistent milestone completion state. |
| Weekly mobile notification | Optional configurable notify service and threshold. |
| Multiple copied packages | One config entry and one card per vehicle. |

## Default service intervals

Intervals are initial generic defaults and should be reviewed against the service
schedule appropriate for the configured vehicle. They are centralized in
`custom_components/vehicle_maintenance/const.py` so future versions can expose
per-vehicle interval editing without changing the entity contract.
