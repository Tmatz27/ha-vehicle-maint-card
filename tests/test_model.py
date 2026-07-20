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


def test_missing_history_requires_setup():
    record = ServiceRecord(interval_miles=6000)
    assert model.service_status(record, 44973) == "setup_required"
    assert model.miles_remaining(record, 44973) is None


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
    assert not unset.initialized
    assert migrated["services"]["30k"]["milestone_completed"]


def test_notification_sorting_and_formatting():
    records = {
        "soon": ServiceRecord(True, 44000, 2000),
        "late": ServiceRecord(True, 30000, 10000),
        "unset": ServiceRecord(interval_miles=1000),
    }
    catalog = {
        "soon": {"name": "Soon", "interval": 2000},
        "late": {"name": "Late", "interval": 10000},
        "unset": {"name": "Unset", "interval": 1000},
    }
    items = model.notification_items(records, catalog, 45000, 1500)
    assert items == [(-5000, "Late"), (1000, "Soon")]
    assert model.format_notification_item(items[0]) == "- Late: 5,000 mi overdue"
