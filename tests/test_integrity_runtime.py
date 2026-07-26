"""Regression tests for maintenance data integrity and summary behavior."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

pytest.importorskip("homeassistant")

import voluptuous as vol  # noqa: E402

from custom_components.vehicle_maintenance import (  # noqa: E402
    _async_log_maintenance_batch,
)
from custom_components.vehicle_maintenance.const import CONF_SERVICES  # noqa: E402
from custom_components.vehicle_maintenance.integrity import (  # noqa: E402
    complete_service_batch_checked,
    complete_service_checked,
)
from custom_components.vehicle_maintenance.model import ServiceRecord  # noqa: E402
from custom_components.vehicle_maintenance.sensor import (  # noqa: E402
    VehicleSummarySensor,
)


def test_completion_rejects_future_and_backward_history() -> None:
    record = ServiceRecord(last_completed_mileage=40000, interval_miles=6000)

    with pytest.raises(ValueError, match="current odometer"):
        complete_service_checked(record, 51000, 50000)
    assert record.last_completed_mileage == 40000

    with pytest.raises(ValueError, match="earlier than the last recorded"):
        complete_service_checked(record, 39000, 50000)
    assert record.last_completed_mileage == 40000

    complete_service_checked(record, 45000, 50000)
    assert record.last_completed_mileage == 45000


def test_completed_milestone_requires_reset_before_relogging() -> None:
    milestone = ServiceRecord(
        interval_miles=60000,
        milestone_completed=True,
        milestone_completed_mileage=60248,
    )

    with pytest.raises(ValueError, match="already complete"):
        complete_service_checked(milestone, 70000, 70000, milestone=True)

    assert milestone.milestone_completed_mileage == 60248


def test_batch_validation_is_atomic() -> None:
    valid = ServiceRecord(last_completed_mileage=40000, interval_miles=6000)
    invalid = ServiceRecord(last_completed_mileage=48000, interval_miles=6000)

    with pytest.raises(ValueError, match="earlier than the last recorded"):
        complete_service_batch_checked(
            [(valid, False, None), (invalid, False, None)],
            45000,
            50000,
        )

    assert valid.last_completed_mileage == 40000
    assert invalid.last_completed_mileage == 48000


def test_batch_service_rejects_future_mileage_before_saving() -> None:
    record = ServiceRecord(last_completed_mileage=40000, interval_miles=6000)
    manager = SimpleNamespace(
        records={"oil_change": record},
        config={CONF_SERVICES: ["oil_change"]},
        effective_odometer=50000,
        async_save=AsyncMock(),
    )

    with pytest.raises(vol.Invalid, match="current odometer"):
        asyncio.run(
            _async_log_maintenance_batch(
                manager,
                ["oil_change"],
                mileage=51000,
            )
        )

    assert record.last_completed_mileage == 40000
    manager.async_save.assert_not_awaited()


def test_deferred_service_is_not_reported_as_next_service() -> None:
    manager = SimpleNamespace(
        entry=SimpleNamespace(entry_id="vehicle-test", title="Outback"),
        effective_odometer=45000,
        odometer_source="live",
        config={CONF_SERVICES: ["oil_change", "tire_rotation"]},
        records={
            "oil_change": ServiceRecord(
                last_completed_mileage=40000,
                interval_miles=6000,
                snoozed_until_mileage=50000,
            ),
            "tire_rotation": ServiceRecord(
                last_completed_mileage=42000,
                interval_miles=6000,
            ),
        },
    )

    _state, attributes = VehicleSummarySensor(manager)._summary()

    assert attributes["deferred_count"] == 1
    assert attributes["next_service"] == "Tire Rotation"
    assert attributes["next_service_miles"] == 3000
