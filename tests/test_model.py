"""Unit tests for maintenance arithmetic and migration."""

import importlib.util
import sys
from datetime import date as _date
from datetime import datetime as _datetime
from datetime import time as _time
from datetime import timezone as _timezone
from pathlib import Path

_utc = _timezone.utc

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


def test_batch_completion_logs_one_odometer_and_each_service_semantics():
    oil = ServiceRecord(True, 40000, 6000, snoozed_until_mileage=47000)
    rotation = ServiceRecord(True, 40000, 6000)
    milestone = ServiceRecord(True, interval_miles=60000)

    model.complete_service_batch(
        [(oil, False, None), (rotation, False, None), (milestone, True, None)],
        44973,
    )

    assert oil.last_completed_mileage == 44973
    assert rotation.last_completed_mileage == 44973
    assert oil.snoozed_until_mileage is None
    assert model.scheduled_due_mileage(oil) == 50973
    assert milestone.milestone_completed
    assert milestone.milestone_completed_mileage == 44973


def test_washable_filter_tracks_washes_without_resetting_filter_age():
    record = ServiceRecord(True, 30000, 12000)

    model.complete_filter_service(record, 30000, action="replace")
    model.complete_filter_service(record, 42000, action="wash")
    model.complete_filter_service(record, 54000, action="wash")

    assert record.last_completed_mileage == 54000
    assert record.filter_installed_mileage == 30000
    assert record.last_washed_mileage == 54000
    assert record.last_filter_action == "wash"
    assert record.wash_count == 2
    assert model.scheduled_due_mileage(record) == 66000


def test_replacing_washable_filter_resets_its_wash_count_and_age():
    record = ServiceRecord(
        True,
        42000,
        12000,
        wash_count=3,
        filter_installed_mileage=18000,
        last_washed_mileage=42000,
        last_filter_action="wash",
    )

    model.complete_filter_service(record, 50000, action="replace")

    assert record.filter_installed_mileage == 50000
    assert record.last_washed_mileage is None
    assert record.last_filter_action == "replace"
    assert record.wash_count == 0


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
                "wash_count": 0,
                "filter_installed_mileage": None,
                "last_washed_mileage": None,
                "last_filter_action": None,
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


def test_car_wash_is_tracked_by_date_and_never_fabricates_a_wash():
    record = model.CarWashRecord()

    assert record.last_washed_date is None
    assert record.wash_count == 0
    assert model.days_since_wash(record, _date(2026, 7, 29)) is None
    assert model.car_wash_status(record, _date(2026, 7, 29), 14) == "never_washed"

    model.log_car_wash(record, _date(2026, 7, 20))

    assert record.last_washed_date == "2026-07-20"
    assert record.wash_count == 1
    assert model.days_since_wash(record, _date(2026, 7, 29)) == 9
    assert model.car_wash_days_remaining(record, _date(2026, 7, 29), 14) == 5


def test_car_wash_status_tracks_elapsed_days_against_the_interval():
    record = model.CarWashRecord(last_washed_date="2026-07-01")

    assert model.car_wash_status(record, _date(2026, 7, 5), 14) == "okay"
    assert model.car_wash_status(record, _date(2026, 7, 12), 14) == "due_soon"
    assert model.car_wash_status(record, _date(2026, 7, 15), 14) == "due_soon"
    assert model.car_wash_status(record, _date(2026, 7, 16), 14) == "overdue"


def test_car_wash_refuses_to_backdate_before_the_last_recorded_wash():
    record = model.CarWashRecord(last_washed_date="2026-07-20", wash_count=3)

    try:
        model.log_car_wash(record, _date(2026, 7, 10))
    except ValueError as error:
        assert "earlier than the last recorded wash" in str(error)
    else:  # pragma: no cover - guards against a silently accepted backdate
        raise AssertionError("expected a backdated wash to be rejected")

    assert record.last_washed_date == "2026-07-20"
    assert record.wash_count == 3


def test_car_wash_reset_clears_history():
    record = model.CarWashRecord(last_washed_date="2026-07-20", wash_count=4)

    model.reset_car_wash(record)

    assert record.last_washed_date is None
    assert record.wash_count == 0


def test_unreadable_stored_wash_dates_never_raise():
    assert model.parse_iso_date(None) is None
    assert model.parse_iso_date("") is None
    assert model.parse_iso_date("not-a-date") is None
    assert model.parse_iso_date("2026-13-45") is None
    assert model.parse_iso_date("2026-07-20") == _date(2026, 7, 20)
    assert model.parse_iso_date(_date(2026, 7, 20)) == _date(2026, 7, 20)


def test_muted_services_are_left_out_of_notifications_but_keep_their_record():
    records = {
        "oil_change": ServiceRecord(True, 40000, 6000),
        "tire_replacement": ServiceRecord(True, 0, 50000),
    }
    catalog = {
        "oil_change": {"name": "Oil Change", "interval": 6000},
        "tire_replacement": {"name": "Tire Replacement", "interval": 50000},
    }

    # At 49,000 mi both items are inside the 2,000 mi threshold, so anything that
    # drops out of the summary dropped out because of muting and nothing else.
    unmuted = model.notification_items(records, catalog, 49000, 2000)
    assert [name for _miles, name in unmuted] == ["Oil Change", "Tire Replacement"]

    muted = model.notification_items(
        records, catalog, 49000, 2000, None, {"tire_replacement"}
    )
    assert [name for _miles, name in muted] == ["Oil Change"]

    # Muting is a notification preference only; the record is untouched.
    assert records["tire_replacement"].last_completed_mileage == 0
    assert records["tire_replacement"].interval_miles == 50000


def test_next_scheduled_summary_lands_on_the_configured_weekday_and_time():
    # Home Assistant always passes an aware datetime, so mirror that here.
    def _dt(*args):
        return _datetime(*args, tzinfo=_utc)

    # Wednesday 2026-07-29 at 09:00.
    now = _dt(2026, 7, 29, 9, 0)

    # Sunday (index 6) at 17:00 is later the same week.
    assert model.next_notification_time(now, 6, _time(17, 0)) == _dt(2026, 8, 2, 17, 0)
    # Wednesday 17:00 is still ahead of 09:00 today.
    assert model.next_notification_time(now, 2, _time(17, 0)) == _dt(2026, 7, 29, 17, 0)
    # Wednesday 08:00 already passed, so it rolls a full week forward.
    assert model.next_notification_time(now, 2, _time(8, 0)) == _dt(2026, 8, 5, 8, 0)


def test_clock_times_parse_with_and_without_seconds():
    assert model.parse_clock_time("17:00:00") == _time(17, 0, 0)
    assert model.parse_clock_time("07:30") == _time(7, 30, 0)
    assert model.parse_clock_time(_time(6, 15)) == _time(6, 15)
