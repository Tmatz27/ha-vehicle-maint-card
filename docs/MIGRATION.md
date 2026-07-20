# Migrating from a package

Migration is intentionally explicit: package helpers remain the source of truth until every value is compared. No vehicle or entity ID is built into the integration.

## Safe workflow

1. Add one Vehicle Maintenance integration entry for the vehicle and select the authoritative odometer.
2. Leave the new built-in notification disabled.
3. Import every recurring service with **Developer Tools → Actions → Vehicle Maintenance: Set maintenance record**. Use `last_completed` and the value of `input_number.<vehicle>_last_<service>`. If the old package only knows a next due mileage, use `due_at` instead.
4. For an old schedule adjustment, calculate the old effective due mileage (`last completed + old interval + adjustment`) and import that value with `due_at`. Do not import it as a snooze.
5. Compare every old remaining-mile sensor with the new sensor. Confirm custom per-vehicle intervals under **Configure**.
6. Verify milestone booleans. For a completed milestone, call `log_maintenance` with its completion mileage; leave incomplete milestones active.
7. Compare the effective-odometer entity with the package's cached odometer. If necessary, call `set_effective_odometer` once with the cached value. Verify that making the source unavailable changes the source attribute to `cached` without losing mileage.
8. Enable and test the integration notification settings.
9. Disable the old package notification automation to prevent duplicates.
10. Move the old package outside the active packages directory as a temporary backup. Remove it only after several successful odometer updates, service actions, and notifications.

The package's current service dropdown is transient UI state rather than maintenance history. Open the matching row in the new card after import; no global service selector is carried forward.

## Generic action examples

```yaml
action: vehicle_maintenance.set_maintenance
data:
  entry_id: REPLACE_WITH_CONFIG_ENTRY_ID
  service: oil_change
  mode: last_completed
  mileage: "{{ states('input_number.REPLACE_last_oil_change') | int }}"
```

```yaml
action: vehicle_maintenance.set_maintenance
data:
  entry_id: REPLACE_WITH_CONFIG_ENTRY_ID
  service: differential_service
  mode: due_at
  mileage: 30000
```

```yaml
action: vehicle_maintenance.set_effective_odometer
data:
  entry_id: REPLACE_WITH_CONFIG_ENTRY_ID
  mileage: "{{ states('input_number.REPLACE_cached_odometer') | int }}"
```

Keep a copy of the old package and helper values until testing is complete. The integration stores current service records and last-completed mileage; it does not claim to be a complete maintenance event log.
