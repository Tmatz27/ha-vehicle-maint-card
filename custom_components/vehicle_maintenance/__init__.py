"""Vehicle Maintenance integration."""

from __future__ import annotations

from datetime import time
from pathlib import Path

import voluptuous as vol

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.event import async_track_time_change

from .const import (
    ATTR_ENTRY_ID,
    CONF_NOTIFY_ENABLED,
    CONF_NOTIFY_SERVICE,
    CONF_NOTIFY_THRESHOLD,
    CONF_NOTIFY_TIME,
    CONF_NOTIFY_WEEKDAY,
    CONF_INTERVALS,
    CONF_ODOMETER_ENTITY,
    CONF_SERVICES,
    CONF_VEHICLE_NAME,
    DEFAULT_NOTIFICATION_THRESHOLD,
    DEFAULT_NOTIFICATION_TIME,
    DEFAULT_NOTIFICATION_WEEKDAY,
    DOMAIN,
    PLATFORMS,
    SERVICE_CATALOG,
)
from .manager import VehicleManager
from .model import (
    complete_service,
    format_notification_item,
    initialize_service,
    notification_items,
    snooze_service,
)

CARD_URL = "/vehicle-maintenance/vehicle-maint-card.js"
CARD_RESOURCE_URL = f"{CARD_URL}?v=0.1.0"
WEEKDAYS = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Register frontend and actions exactly once for the integration."""
    card_path = Path(__file__).parent / "www" / "vehicle-maint-card.js"
    await hass.http.async_register_static_paths(
        [StaticPathConfig(CARD_URL, str(card_path), False)]
    )
    add_extra_js_url(hass, CARD_RESOURCE_URL)
    hass.data.setdefault(DOMAIN, {})

    def manager_for(call: ServiceCall) -> VehicleManager:
        manager = hass.data[DOMAIN].get(call.data[ATTR_ENTRY_ID])
        if manager is None:
            raise vol.Invalid("Unknown vehicle entry")
        return manager

    def record_for(manager: VehicleManager, service: str):
        record = manager.records.get(service)
        if record is None or service not in manager.config["services"]:
            raise vol.Invalid("Service is not tracked by this vehicle")
        return record

    async def log_maintenance(call: ServiceCall) -> None:
        manager = manager_for(call)
        key = call.data["service"]
        mileage = call.data.get("mileage", manager.effective_odometer)
        if mileage is None:
            raise vol.Invalid("No effective odometer is available")
        complete_service(
            record_for(manager, key),
            mileage,
            milestone=bool(SERVICE_CATALOG[key].get("milestone")),
        )
        await manager.async_save()

    async def snooze_maintenance(call: ServiceCall) -> None:
        manager = manager_for(call)
        if manager.effective_odometer is None:
            raise vol.Invalid("No effective odometer is available")
        snooze_service(
            record_for(manager, call.data["service"]),
            manager.effective_odometer,
            miles=call.data.get("miles"),
            until_mileage=call.data.get("until_mileage"),
        )
        await manager.async_save()

    async def clear_snooze(call: ServiceCall) -> None:
        manager = manager_for(call)
        record_for(manager, call.data["service"]).snoozed_until_mileage = None
        await manager.async_save()

    async def set_maintenance(call: ServiceCall) -> None:
        manager = manager_for(call)
        initialize_service(
            record_for(manager, call.data["service"]),
            call.data["mode"],
            call.data.get("mileage"),
        )
        await manager.async_save()

    async def reset_service(call: ServiceCall) -> None:
        manager = manager_for(call)
        initialize_service(record_for(manager, call.data["service"]), "not_set")
        await manager.async_save()

    async def set_effective_odometer(call: ServiceCall) -> None:
        manager = manager_for(call)
        await manager.async_set_odometer(
            call.data["mileage"], allow_decrease=call.data["allow_decrease"]
        )

    common = {
        vol.Required(ATTR_ENTRY_ID): cv.string,
        vol.Required("service"): vol.In(SERVICE_CATALOG),
    }
    hass.services.async_register(
        DOMAIN,
        "log_maintenance",
        log_maintenance,
        schema=vol.Schema(
            {
                **common,
                vol.Optional("mileage"): vol.All(vol.Coerce(int), vol.Range(min=0)),
            }
        ),
    )
    hass.services.async_register(
        DOMAIN,
        "snooze_maintenance",
        snooze_maintenance,
        schema=vol.Schema(
            {
                **common,
                vol.Exclusive("miles", "target"): vol.All(
                    vol.Coerce(int), vol.Range(min=1)
                ),
                vol.Exclusive("until_mileage", "target"): vol.All(
                    vol.Coerce(int), vol.Range(min=1)
                ),
            }
        ),
    )
    hass.services.async_register(
        DOMAIN, "clear_snooze", clear_snooze, schema=vol.Schema(common)
    )
    hass.services.async_register(
        DOMAIN,
        "set_maintenance",
        set_maintenance,
        schema=vol.Schema(
            {
                **common,
                vol.Required("mode"): vol.In(
                    ["not_set", "never_performed", "last_completed", "due_at"]
                ),
                vol.Optional("mileage"): vol.All(vol.Coerce(int), vol.Range(min=0)),
            }
        ),
    )
    hass.services.async_register(
        DOMAIN, "reset_service", reset_service, schema=vol.Schema(common)
    )
    hass.services.async_register(
        DOMAIN,
        "set_effective_odometer",
        set_effective_odometer,
        schema=vol.Schema(
            {
                vol.Required(ATTR_ENTRY_ID): cv.string,
                vol.Required("mileage"): vol.All(vol.Coerce(int), vol.Range(min=0)),
                vol.Optional("allow_decrease", default=False): cv.boolean,
            }
        ),
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up one isolated vehicle manager and schedule."""
    manager = VehicleManager(hass, entry)
    await manager.async_load()
    await manager.async_start()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = manager
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    entry.async_on_unload(lambda: hass.async_create_task(manager.async_stop()))

    schedule = _parse_time(manager.config.get(CONF_NOTIFY_TIME, "17:00:00"))

    @callback
    def scheduled_notification(now) -> None:
        weekday = WEEKDAYS.get(manager.config.get(CONF_NOTIFY_WEEKDAY, "sun"), 6)
        if now.weekday() == weekday:
            hass.async_create_task(_async_send_notification(hass, manager))

    entry.async_on_unload(
        async_track_time_change(
            hass,
            scheduled_notification,
            hour=schedule.hour,
            minute=schedule.minute,
            second=schedule.second,
        )
    )
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate config-entry settings separately from per-vehicle stored records."""
    if entry.version > 2:
        return False
    if entry.version == 1:
        data = dict(entry.data)
        selected = data.get(CONF_SERVICES, [])
        data.setdefault(
            CONF_INTERVALS,
            {key: SERVICE_CATALOG[key]["interval"] for key in selected},
        )
        data.setdefault(CONF_NOTIFY_ENABLED, bool(data.get(CONF_NOTIFY_SERVICE)))
        data.setdefault(CONF_NOTIFY_THRESHOLD, DEFAULT_NOTIFICATION_THRESHOLD)
        data.setdefault(CONF_NOTIFY_WEEKDAY, DEFAULT_NOTIFICATION_WEEKDAY)
        data.setdefault(CONF_NOTIFY_TIME, DEFAULT_NOTIFICATION_TIME)
        data.setdefault(CONF_VEHICLE_NAME, entry.title)
        if CONF_ODOMETER_ENTITY not in data:
            return False
        hass.config_entries.async_update_entry(entry, data=data, version=2)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unloaded


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


def _parse_time(value: str | time) -> time:
    if isinstance(value, time):
        return value
    parts = [int(part) for part in value.split(":")]
    return time(parts[0], parts[1], parts[2] if len(parts) > 2 else 0)


async def _async_send_notification(
    hass: HomeAssistant, manager: VehicleManager
) -> None:
    config = manager.config
    if not config.get(CONF_NOTIFY_ENABLED, False) or manager.effective_odometer is None:
        return
    target = str(config.get(CONF_NOTIFY_SERVICE, "")).strip()
    if "." not in target:
        return
    items = notification_items(
        manager.records,
        SERVICE_CATALOG,
        manager.effective_odometer,
        int(config.get(CONF_NOTIFY_THRESHOLD, 1500)),
    )
    if not items:
        return
    domain, service = target.split(".", 1)
    await hass.services.async_call(
        domain,
        service,
        {
            "title": f"{manager.entry.title} maintenance",
            "message": "\n".join(format_notification_item(item) for item in items),
            "data": {"tag": f"vehicle_maintenance_{manager.entry.entry_id}"},
        },
        blocking=False,
    )
