"""Unit tests for maintenance arithmetic and migration."""

import importlib.util
from pathlib import Path
import sys

MODULE = Path(__file__).parents[1] / "custom_components/vehicle_maintenance/model.py"
spec = importlib.util.spec_from_file_location("vehicle_maintenance_model", MODULE)
model = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = model
spec.loader.exec_module(model)

ServiceRecord = model.ServiceRecord


def test_multiple_vehicle_records_are_isolated():
    first = ServiceRecord(True, 43000, 6000)
    second = ServiceRecord(True, 10000, 5000)
    model.complete_service(first, 44500)
    assert first.last_completed_mileage == 44500
    assert second.last_completed_mileage == 10000


def test_new_record_starts_as_never_performed():
    record = ServiceRecord(interval_miles=6000)
    assert record.initialized
    assert record.last_completed_mileage == 0
    assert model.scheduled_due_mileage(record) == 6000
    assert model.service_status(record, 44973) == "overdue"


def test_first_service_interval_can_differ_from_repeat_interval():
    catalog = {
        "coolant": {
            "name": "Coolant",
            "interval": 75000,
            "initial_interval": 137500,
        }
    }
    records = {}

    assert model.normalize_selected_records(
        records, ["coolant"], {"coolant": 75000}, catalog
    )
    coolant = records["coolant"]
    assert coolant.last_completed_mileage == 0
    assert coolant.due_mileage_override == 137500
    assert coolant.initial_due_mileage_applied
    assert model.scheduled_due_mileage(coolant) == 137500

    assert model.normalize_selected_records(
        records,
        ["coolant"],
        {"coolant": 75000},
        catalog,
        {"coolant": 140000},
    )
    assert model.scheduled_due_mileage(coolant) == 140000

    model.complete_service(coolant, 137500)
    assert coolant.due_mileage_override is None
    assert not coolant.initial_due_mileage_applied
    assert model.scheduled_due_mileage(coolant) == 212500

    model.initialize_service(coolant, "never_performed", initial_due_mileage=137500)
    assert coolant.initial_due_mileage_applied
    assert model.scheduled_due_mileage(coolant) == 137500


def test_custom_due_override_is_not_replaced_by_first_service_interval():
    catalog = {
        "coolant": {
            "name": "Coolant",
            "interval": 75000,
            "initial_interval": 137500,
        }
    }
    record = ServiceRecord(
        last_completed_mileage=None,
        interval_miles=75000,
        due_mileage_override=150000,
    )
    records = {"coolant": record}

    assert not model.normalize_selected_records(
        records,
        ["coolant"],
        {"coolant": 75000},
        catalog,
        {"coolant": 140000},
    )
    assert model.scheduled_due_mileage(record) == 150000


def test_log_current_and_historical_mileage():
    record = ServiceRecord(True, 43000, 6000)
    model.complete_service(record, 44973)
    assert model.scheduled_due_mileage(record) == 50973
    model.complete_service(record, 44500)
    assert model.scheduled_due_mileage(record) == 50500
    assert model.miles_remaining(record, 44973) == 5527


def test_completion_clears_snooze_and_override():
    record = ServiceRecord(True, 40000, 6000, 47000, 48000)
    model.complete_service(record, 44500)
    assert record.due_mileage_override is None
    assert record.snoozed_until_mileage is None


def test_odometer_rejects_zero_and_decrease():
    assert model.accepted_odometer(44973, None) == 44973
    assert model.accepted_odometer(44973, 0) == 44973
    assert model.accepted_odometer(44973, 44000) == 44973
    assert model.accepted_odometer(44973, 44000, allow_decrease=True) == 44000
    assert model.accepted_odometer(None, 1) == 1


def test_past_due_snooze_is_from_current_odometer():
    record = ServiceRecord(True, None, 30000, due_mileage_override=30000)
    target = model.snooze_service(record, 44973, miles=1000)
    assert target == 45973
    assert model.scheduled_due_mileage(record) == 30000
    assert model.miles_remaining(record, 44973) == -14973
    assert model.snooze_active(record, 45972)
    assert not model.snooze_active(record, 45973)


def test_snooze_controls_notification_eligibility():
    record = ServiceRecord(True, 40000, 6000, snoozed_until_mileage=46000)
    records = {"oil": record}
    catalog = {"oil": {"name": "Oil", "interval": 6000}}
    assert model.notification_items(records, catalog, 45000, 1500) == []
    assert model.notification_items(records, catalog, 46000, 1500) == [(0, "Oil")]


def test_milestone_completion_exact_and_snooze():
    record = ServiceRecord(True, interval_miles=30000, due_mileage_override=30000)
    model.snooze_service(record, 44973, miles=1000)
    assert model.snooze_active(record, 45000)
    model.complete_service(record, 44500, milestone=True)
    assert record.milestone_completed
    assert record.milestone_completed_mileage == 44500
    assert record.snoozed_until_mileage is None


def test_per_vehicle_interval_override():
    first = ServiceRecord(True, 10000, 6000)
    second = ServiceRecord(True, 10000, 10000)
    assert model.scheduled_due_mileage(first) == 16000
    assert model.scheduled_due_mileage(second) == 20000


def test_version_one_migration_preserves_effective_due_override():
    old = {
        "last_completed": {"oil": 40000},
        "extensions": {"oil": 1000},
        "completed_milestones": ["30k"],
        "cached_odometer": 44973,
    }
    catalog = {
        "oil": {"name": "Oil", "interval": 6000},
        "30k": {"name": "30k", "interval": 30000, "milestone": True},
        "unset": {"name": "Unset", "interval": 12000},
    }
    migrated = model.migrate_v1_data(old, catalog)
    oil = ServiceRecord.from_dict(migrated["services"]["oil"])
    unset = ServiceRecord.from_dict(migrated["services"]["unset"])
    assert migrated["cached_odometer"] == 44973
    assert oil.due_mileage_override == 47000
    assert oil.snoozed_until_mileage is None
    assert unset.initialized
    assert unset.last_completed_mileage == 0
    assert migrated["services"]["30k"]["milestone_completed"]


def test_notification_sorting_and_formatting():
    records = {
        "soon": ServiceRecord(True, 44000, 2000),
        "late": ServiceRecord(True, 30000, 10000),
        "unset": ServiceRecord(False, None, 1000),
    }
    catalog = {
        "soon": {"name": "Soon", "interval": 2000},
        "late": {"name": "Late", "interval": 10000},
        "unset": {"name": "Unset", "interval": 1000},
    }
    items = model.notification_items(records, catalog, 45000, 1500)
    assert items == [(-5000, "Late"), (1000, "Soon")]
    assert model.format_notification_item(items[0]) == "- Late: 5,000 mi overdue"


def test_deselected_service_is_excluded_from_notifications():
    records = {
        "selected": ServiceRecord(True, 40000, 6000),
        "deselected": ServiceRecord(True, 10000, 6000),
    }
    catalog = {
        "selected": {"name": "Selected", "interval": 6000},
        "deselected": {"name": "Deselected", "interval": 6000},
    }
    assert model.notification_items(records, catalog, 45000, 1500, {"selected"}) == [
        (1000, "Selected")
    ]


def test_storage_migration_versions_and_future_rejection():
    migrate_storage_data = model.migrate_storage_data
    catalog = {"oil": {"name": "Oil", "interval": 6000}}

    current = {"cached_odometer": 123, "services": {}}
    assert migrate_storage_data(2, current, catalog) is current
    assert migrate_storage_data(1, None, catalog) == {
        "cached_odometer": None,
        "services": {
            "oil": {
                "initialized": True,
                "last_completed_mileage": 0,
                "interval_miles": 6000,
                "due_mileage_override": None,
                "snoozed_until_mileage": None,
                "milestone_completed": False,
                "milestone_completed_mileage": None,
                "initial_due_mileage_applied": False,
            }
        },
    }
    import pytest

    with pytest.raises(ValueError, match="Unsupported storage version"):
        migrate_storage_data(99, current, catalog)


def test_service_argument_validation():
    import pytest

    model.validate_snooze_arguments(miles=1000, until_mileage=None)
    model.validate_snooze_arguments(miles=None, until_mileage=50000)
    for miles, target in ((None, None), (1000, 50000)):
        with pytest.raises(ValueError, match="exactly one"):
            model.validate_snooze_arguments(miles=miles, until_mileage=target)
    model.validate_setup_arguments("not_set", None)
    model.validate_setup_arguments("never_performed", None)
    with pytest.raises(ValueError, match="Mileage is required"):
        model.validate_setup_arguments("last_completed", None)


def test_selected_records_never_remain_uninitialized():
    records = {
        "legacy": ServiceRecord(False, None, 12000),
        "completed": ServiceRecord(True, 43000, 6000),
    }
    catalog = {
        "new": {"interval": 5000},
        "legacy": {"interval": 12000},
        "completed": {"interval": 6000},
    }

    changed = model.normalize_selected_records(
        records,
        ["new", "legacy", "completed"],
        {"new": 7500},
        catalog,
    )

    assert changed
    assert records["new"] == ServiceRecord(interval_miles=7500)
    assert records["legacy"].initialized
    assert records["legacy"].last_completed_mileage == 0
    assert records["completed"].last_completed_mileage == 43000


def test_legacy_not_set_action_maps_to_never_performed():
    record = ServiceRecord(True, 43000, 6000, snoozed_until_mileage=50000)

    model.initialize_service(record, "not_set")

    assert record.initialized
    assert record.last_completed_mileage == 0
    assert record.due_mileage_override is None
    assert record.snoozed_until_mileage is None
