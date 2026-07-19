# Home Assistant Vehicle Maintenance

This repository contains a reusable Home Assistant package and Lovelace cards for
mileage-based vehicle maintenance. The included example is configured for a
2024 Subaru Outback Wilderness, but the naming and file layout are designed to
make adding another vehicle predictable.

## What is included

- `packages/vehicle_outback.yaml` — helpers, maintenance sensors, notifications,
  setup/log/defer scripts, and a vehicle summary sensor.
- `dashboards/outback_maintenance.yaml` — a mobile-friendly dashboard stack using
  Mushroom, Auto Entities, Template Entity Row, and card-mod.
- `docs/ADDING_A_VEHICLE.md` — a repeatable checklist for cloning the package for
  another vehicle.

## Required frontend cards

Install these through HACS before using the dashboard:

- Mushroom
- Auto Entities
- Template Entity Row
- card-mod

No popup or Browser Mod dependency is required.

## Installation

1. Copy `packages/vehicle_outback.yaml` into the Home Assistant `packages`
   directory.
2. Ensure packages are enabled in `configuration.yaml`:

   ```yaml
   homeassistant:
     packages: !include_dir_named packages
   ```

3. Change `notify.vehicle_maintenance` in the package to an existing notify
   service, or create a notify group with that name.
4. Restart Home Assistant and verify the configuration.
5. Paste `dashboards/outback_maintenance.yaml` into a manual dashboard card.

## First-time setup

The package deliberately treats mileage `0` as valid. Tracking is controlled by
a separate boolean for each service, so an untracked item is never confused with
a vehicle whose service history genuinely starts at zero.

Open **Maintenance setup** on the dashboard, select a service, then choose one of
these modes:

- **Last completed at mileage** — stores the entered mileage as service history.
- **Due at mileage** — derives the last-completed baseline from the normal interval.
- **Never performed** — stores a zero-mile baseline and tracks the item normally.
- **Not tracked** — hides the item from cards, summaries, and notifications.

## Design notes

Deferring a service no longer changes its last-completed mileage. Each recurring
service has an independent extension helper; logging the service clears that
extension. This preserves maintenance history while still allowing a due date to
be moved temporarily.

