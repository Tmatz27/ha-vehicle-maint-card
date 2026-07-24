"""Pure maintenance calculations and storage migration."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

STATUS_SETUP_REQUIRED = "setup_required"
STATUS_OVERDUE = "overdue"
STATUS_DUE_SOON = "due_soon"
STATUS_OKAY = "okay"
STATUS_COMPLETED = "completed"


def validate_snooze_arguments(*, miles: int | None, until_mileage: int | None) -> None:
    """Require exactly one reminder input."""
    if (miles is None) == (until_mileage is None):
        raise ValueError("Provide exactly one of miles or until_mileage")


def validate_setup_arguments(mode: str, mileage: int | None) -> None:
    """Require mileage only for record modes that need a value."""
    if mode in ("last_completed", "due_at") and mileage is None:
        raise ValueError(f"Mileage is required for {mode}")


def accepted_odometer(
    cached: int | None, candidate: int | None, *, allow_decrease: bool = False
) -> int | None:
    """Accept only explicit, plausible odometer changes."""
    if candidate is None or candidate <= 0:
        return cached
    if cached is not None and candidate < cached and not allow_decrease:
        return cached
    return candidate


@dataclass(slots=True)
class ServiceRecord:
    """Current factual state for one maintenance service."""

    initialized: bool = True
    last_completed_mileage: int | None = 0
    interval_miles: int | None = None
    due_mileage_override: int | None = None
    snoozed_until_mileage: int | None = None
    milestone_completed: bool = False
    milestone_completed_mileage: int | None = None
    initial_due_mileage_applied: bool = False

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> ServiceRecord:
        fields = cls.__dataclass_fields__
        return cls(**{key: value[key] for key in fields if key in value})

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def scheduled_due_mileage(
    record: ServiceRecord, *, milestone: bool = False
) -> int | None:
    """Return the factual scheduled due mileage without considering snooze."""
    if not record.initialized or (milestone and record.milestone_completed):
        return None
    if record.due_mileage_override is not None:
        return record.due_mileage_override
    if milestone:
        return record.interval_miles
    if record.last_completed_mileage is None or record.interval_miles is None:
        return None
    return record.last_completed_mileage + record.interval_miles


def miles_remaining(
    record: ServiceRecord, odometer: int, *, milestone: bool = False
) -> int | None:
    due = scheduled_due_mileage(record, milestone=milestone)
    return None if due is None else due - odometer


def snooze_miles_remaining(record: ServiceRecord, odometer: int) -> int | None:
    target = record.snoozed_until_mileage
    return None if target is None else target - odometer


def snooze_active(record: ServiceRecord, odometer: int) -> bool:
    remaining = snooze_miles_remaining(record, odometer)
    return remaining is not None and remaining > 0


def service_status(
    record: ServiceRecord,
    odometer: int | None,
    *,
    milestone: bool = False,
    due_soon_miles: int = 2000,
) -> str:
    if not record.initialized:
        return STATUS_SETUP_REQUIRED
    if milestone and record.milestone_completed:
        return STATUS_COMPLETED
    if odometer is None:
        return "unavailable"
    remaining = miles_remaining(record, odometer, milestone=milestone)
    if remaining is None:
        return STATUS_SETUP_REQUIRED
    if remaining < 0:
        return STATUS_OVERDUE
    if remaining <= due_soon_miles:
        return STATUS_DUE_SOON
    return STATUS_OKAY


def complete_service(
    record: ServiceRecord, mileage: int, *, milestone: bool = False
) -> None:
    record.initialized = True
    record.due_mileage_override = None
    record.initial_due_mileage_applied = False
    record.snoozed_until_mileage = None
    if milestone:
        record.milestone_completed = True
        record.milestone_completed_mileage = mileage
    else:
        record.last_completed_mileage = mileage


def complete_service_batch(
    records: list[tuple[ServiceRecord, bool]], mileage: int
) -> None:
    """Complete several prevalidated records at one factual odometer reading."""
    for record, milestone in records:
        complete_service(record, mileage, milestone=milestone)


def initialize_service(
    record: ServiceRecord,
    mode: str,
    mileage: int | None = None,
    *,
    initial_due_mileage: int | None = None,
) -> None:
    """Apply an explicit setup state without fabricating service history."""
    record.snoozed_until_mileage = None
    record.milestone_completed = False
    record.milestone_completed_mileage = None
    if mode in ("not_set", "never_performed"):
        # ``not_set`` remains accepted for backward-compatible action calls, but
        # every user-visible record now resolves to Never performed.
        record.initialized = True
        record.last_completed_mileage = 0
        record.due_mileage_override = initial_due_mileage
        record.initial_due_mileage_applied = initial_due_mileage is not None
    elif mode == "last_completed":
        if mileage is None:
            raise ValueError("Mileage is required")
        record.initialized = True
        record.last_completed_mileage = mileage
        record.due_mileage_override = None
        record.initial_due_mileage_applied = False
    elif mode == "due_at":
        if mileage is None:
            raise ValueError("Mileage is required")
        record.initialized = True
        record.last_completed_mileage = None
        record.due_mileage_override = mileage
        record.initial_due_mileage_applied = False
    else:
        raise ValueError(f"Unsupported setup mode: {mode}")


def normalize_selected_records(
    records: dict[str, ServiceRecord],
    selected_services: list[str],
    intervals: dict[str, Any],
    service_catalog: dict[str, dict[str, Any]],
    initial_intervals: dict[str, Any] | None = None,
) -> bool:
    """Ensure selected services are calculable and never appear as Not set."""
    changed = False
    for key in selected_services:
        definition = service_catalog[key]
        interval = int(intervals.get(key, definition.get("interval", 0)))
        initial_interval = (initial_intervals or {}).get(
            key, definition.get("initial_interval")
        )
        record = records.get(key)
        if record is None:
            records[key] = ServiceRecord(
                interval_miles=interval,
                due_mileage_override=initial_interval,
                initial_due_mileage_applied=initial_interval is not None,
            )
            changed = True
            continue

        if not record.initialized:
            record.initialized = True
            changed = True
        if (
            record.last_completed_mileage is None
            and record.due_mileage_override is None
        ):
            record.last_completed_mileage = 0
            changed = True
        if record.initial_due_mileage_applied:
            configured_initial = (
                int(initial_interval) if initial_interval is not None else None
            )
            if record.due_mileage_override != configured_initial:
                record.due_mileage_override = configured_initial
                changed = True
        elif (
            initial_interval is not None
            and record.last_completed_mileage == 0
            and record.due_mileage_override is None
        ):
            record.due_mileage_override = int(initial_interval)
            record.initial_due_mileage_applied = True
            changed = True
        if record.interval_miles != interval:
            record.interval_miles = interval
            changed = True
    return changed


def snooze_service(
    record: ServiceRecord,
    odometer: int,
    *,
    miles: int | None = None,
    until_mileage: int | None = None,
) -> int:
    validate_snooze_arguments(miles=miles, until_mileage=until_mileage)
    if not record.initialized:
        raise ValueError("Maintenance must be logged before it can be extended")
    if until_mileage is None:
        if miles is None or miles <= 0:
            raise ValueError("A positive mileage interval or target is required")
        until_mileage = odometer + miles
    if until_mileage <= odometer:
        raise ValueError("Extension target must be greater than the current odometer")
    record.snoozed_until_mileage = until_mileage
    return until_mileage


def migrate_v1_data(
    old: dict[str, Any], service_catalog: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    """Migrate version-1 dictionaries without reinterpreting extensions as snoozes."""
    last_completed = old.get("last_completed", {})
    extensions = old.get("extensions", {})
    completed = set(old.get("completed_milestones", []))
    records: dict[str, dict[str, Any]] = {}
    keys = set(service_catalog) | set(last_completed) | set(extensions) | completed
    for key in keys:
        definition = service_catalog.get(key, {})
        interval = definition.get("interval")
        last = last_completed.get(key)
        extension = extensions.get(key, 0)
        due_override = (
            int(definition["initial_interval"])
            if last is None and definition.get("initial_interval") is not None
            else None
        )
        if extension and interval is not None:
            due_override = (last if last is not None else 0) + interval + extension
        record = ServiceRecord(
            initialized=True,
            last_completed_mileage=last if last is not None else 0,
            interval_miles=interval,
            due_mileage_override=due_override,
            milestone_completed=key in completed,
            milestone_completed_mileage=None,
            initial_due_mileage_applied=(
                due_override is not None
                and not extension
                and definition.get("initial_interval") is not None
            ),
        )
        records[key] = record.as_dict()
    return {
        "cached_odometer": old.get("cached_odometer"),
        "services": records,
    }


def migrate_storage_data(
    old_major_version: int,
    old_data: dict[str, Any] | None,
    service_catalog: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Migrate a stored payload, preserving current-version data verbatim."""
    data = old_data or {}
    if old_major_version == 1:
        return migrate_v1_data(data, service_catalog)
    if old_major_version == 2:
        return data
    raise ValueError(f"Unsupported storage version: {old_major_version}")


def notification_items(
    records: dict[str, ServiceRecord],
    catalog: dict[str, dict[str, Any]],
    odometer: int,
    threshold: int,
    selected_services: set[str] | None = None,
) -> list[tuple[int, str]]:
    """Return unsnoozed, initialized notification items sorted by urgency."""
    result: list[tuple[int, str]] = []
    for key, record in records.items():
        if selected_services is not None and key not in selected_services:
            continue
        definition = catalog.get(key, {})
        milestone = bool(definition.get("milestone"))
        if not record.initialized or (milestone and record.milestone_completed):
            continue
        if snooze_active(record, odometer):
            continue
        remaining = miles_remaining(record, odometer, milestone=milestone)
        if remaining is not None and remaining <= threshold:
            result.append((remaining, definition.get("name", key)))
    return sorted(result)


def format_notification_item(item: tuple[int, str]) -> str:
    miles, name = item
    if miles < 0:
        return f"- {name}: {abs(miles):,} mi overdue"
    return f"- {name}: {miles:,} mi remaining"
