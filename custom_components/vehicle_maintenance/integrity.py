"""Data-integrity checks for maintenance completion actions."""

from __future__ import annotations

from .model import ServiceRecord, complete_filter_service, complete_service


def validate_completion(
    record: ServiceRecord,
    mileage: int,
    current_odometer: int | None,
    *,
    milestone: bool = False,
) -> None:
    """Validate a factual maintenance completion before mutating its record."""
    if mileage <= 0:
        raise ValueError("Completion mileage must be positive")

    if current_odometer is not None and mileage > current_odometer:
        raise ValueError(
            "Completion mileage cannot be greater than the current odometer"
        )

    if milestone:
        if record.milestone_completed:
            raise ValueError(
                "This mileage milestone is already complete; reset it before logging it again"
            )
        return

    previous = record.last_completed_mileage
    if previous is not None and previous > 0 and mileage < previous:
        raise ValueError(
            "Completion mileage cannot be earlier than the last recorded completion"
        )


def complete_service_checked(
    record: ServiceRecord,
    mileage: int,
    current_odometer: int | None,
    *,
    milestone: bool = False,
    filter_action: str | None = None,
) -> None:
    """Validate and complete one maintenance record."""
    validate_completion(
        record,
        mileage,
        current_odometer,
        milestone=milestone,
    )
    if filter_action is not None:
        complete_filter_service(record, mileage, action=filter_action)
    else:
        complete_service(record, mileage, milestone=milestone)


def complete_service_batch_checked(
    records: list[tuple[ServiceRecord, bool, str | None]],
    mileage: int,
    current_odometer: int | None,
) -> None:
    """Validate an entire service visit before changing any maintenance record."""
    for record, milestone, _filter_action in records:
        validate_completion(
            record,
            mileage,
            current_odometer,
            milestone=milestone,
        )

    for record, milestone, filter_action in records:
        if filter_action is not None:
            complete_filter_service(record, mileage, action=filter_action)
        else:
            complete_service(record, mileage, milestone=milestone)
