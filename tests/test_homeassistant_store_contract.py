"""Runtime contract test against the installed Home Assistant Store API."""

import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

pytest.importorskip("homeassistant")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from homeassistant.helpers.storage import Store  # noqa: E402

from custom_components.vehicle_maintenance.manager import (  # noqa: E402
    VehicleMaintenanceStore,
    VehicleManager,
)
from custom_components.vehicle_maintenance.config_flow import (  # noqa: E402
    _service_selector,
)
from custom_components.vehicle_maintenance.const import (  # noqa: E402
    CONF_INITIAL_INTERVALS,
    CONF_INTERVALS,
    CONF_SERVICES,
)
from custom_components.vehicle_maintenance import async_migrate_entry  # noqa: E402


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
