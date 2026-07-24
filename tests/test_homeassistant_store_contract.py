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

import custom_components.vehicle_maintenance as integration
from custom_components.vehicle_maintenance import (
    BATCH_LOG_SCHEMA,
    _async_log_maintenance_batch,
    _async_send_notification,
    async_migrate_entry,
)
from custom_components.vehicle_maintenance.config_flow import (
    SERVICE_GROUPS,
    _notification_errors,
    _notification_schema,
    _service_selector,
    _services_schema,
    _vehicle_schema,
)
from custom_components.vehicle_maintenance.const import (
    ATTR_ENTRY_ID,
    CONF_INITIAL_INTERVALS,
    CONF_INTERVALS,
    CONF_NOTIFY_ENABLED,
    CONF_NOTIFY_SERVICE,
    CONF_NOTIFY_THRESHOLD,
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


def test_vehicle_and_notification_pickers_filter_expected_entities() -> None:
    vehicle_schema = _vehicle_schema({}, include_name=False)
    odometer_selector = next(iter(vehicle_schema.schema.values()))
    assert odometer_selector.config["domain"] == ["sensor"]
    assert odometer_selector.config["device_class"] == ["distance"]

    notification_schema = _notification_schema({})
    notify_selector = next(
        value
        for key, value in notification_schema.schema.items()
        if key.schema == CONF_NOTIFY_SERVICE
    )
    assert notify_selector.config["domain"] == ["notify"]


def test_notification_validation_accepts_entity_and_legacy_action() -> None:
    hass = MagicMock()
    hass.states.get.return_value = SimpleNamespace(state="unknown")
    hass.services.has_service.return_value = False

    assert (
        _notification_errors(
            hass,
            {
                CONF_NOTIFY_ENABLED: True,
                CONF_NOTIFY_SERVICE: "notify.sm_s926u",
            },
        )
        == {}
    )

    hass.states.get.return_value = None
    hass.services.has_service.return_value = True
    assert (
        _notification_errors(
            hass,
            {
                CONF_NOTIFY_ENABLED: True,
                CONF_NOTIFY_SERVICE: "notify.mobile_app_old_phone",
            },
        )
        == {}
    )


def test_notification_entity_uses_send_message_target(monkeypatch) -> None:
    hass = MagicMock()
    hass.services.has_service.return_value = False
    hass.services.async_call = AsyncMock()
    manager = SimpleNamespace(
        config={
            CONF_NOTIFY_ENABLED: True,
            CONF_NOTIFY_SERVICE: "notify.sm_s926u",
            CONF_NOTIFY_THRESHOLD: 1500,
            CONF_SERVICES: ["oil_change"],
        },
        effective_odometer=45000,
        records={},
        entry=SimpleNamespace(title="Outback", entry_id="vehicle-test"),
    )
    monkeypatch.setattr(integration, "notification_items", lambda *args: [(0, "Oil")])
    monkeypatch.setattr(
        integration, "format_notification_item", lambda item: "- Oil due"
    )

    asyncio.run(_async_send_notification(hass, manager))

    hass.services.async_call.assert_awaited_once_with(
        "notify",
        "send_message",
        {"title": "Outback maintenance", "message": "- Oil due"},
        target={"entity_id": "notify.sm_s926u"},
        blocking=False,
    )


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
