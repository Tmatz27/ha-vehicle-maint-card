"""Pure maintenance calculations and storage migration."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

STATUS_SETUP_REQUIRED = "setup_required"
STATUS_OVERDUE = "overdue"
STATUS_DUE_SOON = "due_soon"
STATUS_OKAY = "okay"
STATUS_COMPLETED = "completed"


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

    initialized: bool = False
    last_completed_mileage: int | None = None
    interval_miles: int | None = None
    due_mileage_override: int | None = None
    snoozed_until_mileage: int | None = None
    milestone_completed: bool = False
    milestone_completed_mileage: int | None = None

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
    record.snoozed_until_mileage = None
    if milestone:
        record.milestone_completed = True
        record.milestone_completed_mileage = mileage
    else:
        record.last_completed_mileage = mileage


def initialize_service(
    record: ServiceRecord, mode: str, mileage: int | None = None
) -> None:
    """Apply an explicit setup state without fabricating service history."""
    record.snoozed_until_mileage = None
    record.milestone_completed = False
    record.milestone_completed_mileage = None
    if mode == "not_set":
        record.initialized = False
        record.last_completed_mileage = None
        record.due_mileage_override = None
    elif mode == "never_performed":
        record.initialized = True
        record.last_completed_mileage = 0
        record.due_mileage_override = None
    elif mode == "last_completed":
        if mileage is None:
            raise ValueError("Mileage is required")
        record.initialized = True
        record.last_completed_mileage = mileage
        record.due_mileage_override = None
    elif mode == "due_at":
        if mileage is None:
            raise ValueError("Mileage is required")
        record.initialized = True
        record.last_completed_mileage = None
        record.due_mileage_override = mileage
    else:
        raise ValueError(f"Unsupported setup mode: {mode}")


def snooze_service(
    record: ServiceRecord,
    odometer: int,
    *,
    miles: int | None = None,
    until_mileage: int | None = None,
) -> int:
    if not record.initialized:
        raise ValueError("Service history must be initialized before snoozing")
    if until_mileage is None:
        if miles is None or miles <= 0:
            raise ValueError("A positive mileage interval or target is required")
        until_mileage = odometer + miles
    if until_mileage <= odometer:
        raise ValueError("Snooze target must be greater than the current odometer")
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
        milestone = bool(definition.get("milestone"))
        initialized = key in last_completed or key in extensions or milestone
        last = last_completed.get(key)
        extension = extensions.get(key, 0)
        due_override = None
        if extension and interval is not None:
            due_override = (last if last is not None else 0) + interval + extension
        record = ServiceRecord(
            initialized=initialized,
            last_completed_mileage=last,
            interval_miles=interval,
            due_mileage_override=due_override,
            milestone_completed=key in completed,
            milestone_completed_mileage=None,
        )
        records[key] = record.as_dict()
    return {
        "cached_odometer": old.get("cached_odometer"),
        "services": records,
    }


def notification_items(
    records: dict[str, ServiceRecord],
    catalog: dict[str, dict[str, Any]],
    odometer: int,
    threshold: int,
) -> list[tuple[int, str]]:
    """Return unsnoozed, initialized notification items sorted by urgency."""
    result: list[tuple[int, str]] = []
    for key, record in records.items():
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
