# Legacy v4 package migration

This is legacy migration guidance for the previously used v4 YAML package. The integration's built-in defaults target modern U.S.-market Subarus, but every interval remains editable per vehicle. Keep the package active while comparing values; the integration stores the current record and last completion, **not** a lifetime event history.

## Meaning of old values

- A helper value of `0` with unknown history stays **Never performed**. Zero is not imported as a factual completion.
- Choose **Last completed at mileage** only for a factual completion.
- If the old Extend action changed a last-completed helper, it is no longer factual. Calculate the known effective next-due mileage and choose **Due at known mileage**.
- Never invent a completion mileage to obtain a desired due mileage.

## Safe sequence

1. Add the vehicle integration entry and temporarily disable its built-in notification.
2. Record every old helper, remaining sensor, interval, milestone, and cached odometer in the worksheet below.
3. Import only factual records with **Developer Tools > Actions > Vehicle Maintenance: Set maintenance record**. This recovery action is intentionally not exposed in the normal card.
4. Compare all old and new due/remaining values.
5. Verify every milestone.
6. Verify the cached odometer by temporarily making the live source unavailable.
7. Enable the integration notification.
8. Disable the package notification to prevent duplicates.
9. Keep the old package outside the active packages directory as a temporary backup.
10. Remove it only after live verification.

## Outback v4 recurring worksheet

| Service key | Old helper |
|---|---|
| `oil_change` | `input_number.outback_last_oil_change_v4` |
| `tire_rotation` | `input_number.outback_last_tire_rotation_v4` |
| `engine_air_filter` | `input_number.outback_last_engine_air_filter_v4` |
| `cabin_air_filter` | `input_number.outback_last_cabin_air_filter_v4` |
| `brake_fluid` | `input_number.outback_last_brake_fluid_v4` |
| `coolant` | `input_number.outback_last_coolant_flush_v4` |
| `transmission_fluid` | `input_number.outback_last_transmission_fluid_v4` |
| `differential_service` | `input_number.outback_last_differential_service_v4` |
| `wiper_blades` | `input_number.outback_last_wiper_blades_v4` |
| `battery_check` | `input_number.outback_last_battery_check_v4` |
| `tire_replacement` | `input_number.outback_last_tire_replacement_v4` |
| `spark_plugs` | `input_number.outback_last_spark_plug_replacement_v4` |

**Important:** v4 used a 60,000-mile Battery Check interval; the integration catalog default is 12,000. Set this vehicle's `battery_check` interval to **60,000 miles** to preserve that schedule.

## Milestone worksheet

| Service key | Old helper |
|---|---|
| `service_30k` | `input_boolean.outback_service_30k_done_v4` |
| `service_60k` | `input_boolean.outback_service_60k_done_v4` |
| `service_90k` | `input_boolean.outback_service_90k_done_v4` |
| `service_120k` | `input_boolean.outback_service_120k_done_v4` |
| `service_125k` | `input_boolean.outback_service_125k_done_v4` |
| `service_180k` | `input_boolean.outback_service_180k_done_v4` |
| `service_200k` | `input_boolean.outback_service_200k_done_v4` |

For another vehicle, replace only the `outback` entity prefix with that package's prefix; do not add vehicle-specific IDs to integration runtime files.

## Action examples

Known factual completion:

```yaml
action: vehicle_maintenance.set_maintenance
data:
  entry_id: REPLACE_CONFIG_ENTRY_ID
  service: oil_change
  mode: last_completed
  mileage: 44500
```

Known next due after an old Extend adjustment:

```yaml
action: vehicle_maintenance.set_maintenance
data:
  entry_id: REPLACE_CONFIG_ENTRY_ID
  service: differential_service
  mode: due_at
  mileage: 46000
```

Unknown history (no mileage field):

```yaml
action: vehicle_maintenance.set_maintenance
data:
  entry_id: REPLACE_CONFIG_ENTRY_ID
  service: wiper_blades
  mode: never_performed
```

## Retiring the package after verification

Keep the external odometer integration/entity, any required miles-normalization template sensor, unrelated vehicle automations, and optionally a custom notification automation when advanced presentation is needed.

After verification, remove maintenance `input_number`, `input_select`, and `input_boolean` helpers; miles-remaining and summary templates; odometer cache/sync automation; package weekly notification; log/extend/setup scripts; and the old maintenance dashboard YAML.
