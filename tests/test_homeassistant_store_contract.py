"""Runtime contract test against the installed Home Assistant Store API."""

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


def test_manager_constructs_supported_home_assistant_store() -> None:
    hass = MagicMock()
    hass.config.path.return_value = "/tmp/vehicle-maintenance-store"
    entry = SimpleNamespace(entry_id="vehicle-test", data={}, options={})

    manager = VehicleManager(hass, entry)

    assert isinstance(manager.store, VehicleMaintenanceStore)
    assert isinstance(manager.store, Store)
