"""Runtime contract test against the installed Home Assistant Store API."""

import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

pytest.importorskip("homeassistant")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import voluptuous as vol
from homeassistant.helpers.storage import Store

from custom_components.vehicle_maintenance import (
    BATCH_LOG_SCHEMA,
    _async_log_maintenance_batch,
    async_migrate_entry,
)
from custom_components.vehicle_maintenance.config_flow import (
    SERVICE_GROUPS,
    _service_selector,
    _services_schema,
)
from custom_components.vehicle_maintenance.const import (
    ATTR_ENTRY_ID,
    CONF_INITIAL_INTERVALS,
    CONF_INTERVALS,
    CONF_SERVICES,
    DEFAULT_SERVICES,
)
from custom_components.vehicle_maintenance.manager import (
    VehicleMaintenanceStore,
    VehicleManager,
)
from custom_components.vehicle_maintenance.model import ServiceRecord


def test_manager_constructs_supported_home_assistant_store() -> None:
    hass = MagicMock()
    hass.config.path.return_value = "/tmp/vehicle-maintenance-store"
    entry = SimpleNamespace(entry_id="vehicle-test", data={}, options={})

    manager = VehicleManager(hass, entry)

    assert isinstance(manager.store, VehicleMaintenanceStore)
    assert isinstance(manager.store, Store)


def test_service_selector_is_a_persistent_multi_select_list() -> None:
    config = _service_selector().config

    assert config["multiple"] is True
    assert config["mode"] == "list"
    assert len(config["options"]) > 1


def test_service_schema_groups_every_default_exactly_once() -> None:
    schema = _services_schema({CONF_SERVICES: DEFAULT_SERVICES})
    defaults = schema({})
    flattened = [service for group in defaults.values() for service in group]

    assert set(defaults) == set(SERVICE_GROUPS)
    assert set(flattened) == set(DEFAULT_SERVICES)
    assert len(flattened) == len(DEFAULT_SERVICES)


def test_batch_log_schema_accepts_multiple_services_and_rejects_empty_list() -> None:
    validated = BATCH_LOG_SCHEMA(
        {
            ATTR_ENTRY_ID: "vehicle-test",
            "services": ["oil_change", "tire_rotation"],
            "mileage": "44973",
        }
    )
    assert validated["services"] == ["oil_change", "tire_rotation"]
    assert validated["mileage"] == 44973

    with pytest.raises(vol.Invalid):
        BATCH_LOG_SCHEMA({ATTR_ENTRY_ID: "vehicle-test", "services": []})
    with pytest.raises(vol.Invalid):
        BATCH_LOG_SCHEMA(
            {
                ATTR_ENTRY_ID: "vehicle-test",
                "services": ["oil_change"],
                "mileage": 0,
            }
        )


def test_batch_log_prevalidates_and_saves_the_vehicle_once() -> None:
    oil = ServiceRecord(interval_miles=6000)
    rotation = ServiceRecord(interval_miles=6000)
    manager = SimpleNamespace(
        records={"oil_change": oil, "tire_rotation": rotation},
        config={CONF_SERVICES: ["oil_change", "tire_rotation"]},
        effective_odometer=44973,
        async_save=AsyncMock(),
    )

    asyncio.run(
        _async_log_maintenance_batch(
            manager,
            ["oil_change", "tire_rotation", "oil_change"],
        )
    )

    assert oil.last_completed_mileage == 44973
    assert rotation.last_completed_mileage == 44973
    manager.async_save.assert_awaited_once()

    unchanged = ServiceRecord(interval_miles=6000)
    invalid_manager = SimpleNamespace(
        records={"oil_change": unchanged},
        config={CONF_SERVICES: ["oil_change"]},
        effective_odometer=44973,
        async_save=AsyncMock(),
    )
    with pytest.raises(vol.Invalid):
        asyncio.run(
            _async_log_maintenance_batch(
                invalid_manager,
                ["oil_change", "tire_rotation"],
            )
        )
    assert unchanged.last_completed_mileage == 0
    invalid_manager.async_save.assert_not_awaited()


def test_config_entry_migration_updates_only_untouched_defaults() -> None:
    entry = SimpleNamespace(
        version=2,
        title="Outback",
        data={
            CONF_SERVICES: [
                "coolant",
                "transmission_fluid",
                "brake_pads",
                "fuel_filter",
            ],
            CONF_INTERVALS: {
                "coolant": 120000,
                "transmission_fluid": 60000,
                "brake_pads": 42000,
                "fuel_filter": 60000,
            },
        },
        options={},
    )

    class ConfigEntries:
        @staticmethod
        def async_update_entry(target, **changes):
            for key, value in changes.items():
                setattr(target, key, value)

    hass = SimpleNamespace(config_entries=ConfigEntries())

    assert asyncio.run(async_migrate_entry(hass, entry))
    assert entry.version == 3
    assert entry.data[CONF_INTERVALS] == {
        "coolant": 75000,
        "transmission_fluid": 30000,
        "brake_pads": 42000,
        "fuel_filter": 72000,
    }
    assert entry.data[CONF_INITIAL_INTERVALS] == {"coolant": 137500}
