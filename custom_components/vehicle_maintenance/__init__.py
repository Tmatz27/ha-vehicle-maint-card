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
from homeassistant.helpers.typing import ConfigType

from .const import (
    ATTR_ENTRY_ID,
    CONF_INITIAL_INTERVALS,
    CONF_INTERVALS,
    CONF_NOTIFY_ENABLED,
    CONF_NOTIFY_SERVICE,
    CONF_NOTIFY_TARGETS,
    CONF_NOTIFY_THRESHOLD,
    CONF_NOTIFY_TIME,
    CONF_NOTIFY_WEEKDAY,
    CONF_ODOMETER_ENTITY,
    CONF_SERVICES,
    CONF_VEHICLE_NAME,
    CONF_WASHABLE_FILTERS,
    DEFAULT_NOTIFICATION_THRESHOLD,
    DEFAULT_NOTIFICATION_TIME,
    DEFAULT_NOTIFICATION_WEEKDAY,
    DOMAIN,
    FILTER_ACTION_REPLACE,
    FILTER_ACTIONS,
    FILTER_SERVICE_KEYS,
    PLATFORMS,
    PREVIOUS_DEFAULT_INTERVALS,
    SERVICE_CATALOG,
)
from .manager import VehicleManager
from .model import (
    complete_filter_service,
    complete_service,
    complete_service_batch,
    format_notification_item,
    initialize_service,
    notification_items,
    snooze_service,
    validate_setup_arguments,
    validate_snooze_arguments,
)

CARD_URL = "/vehicle-maintenance/vehicle-maint-card.js"
CARD_RESOURCE_URL = f"{CARD_URL}?v=0.2.0"
WEEKDAYS = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)
BATCH_LOG_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_ENTRY_ID): cv.string,
        vol.Required("services"): vol.All(
            cv.ensure_list,
            [vol.In(SERVICE_CATALOG)],
            vol.Length(min=1),
        ),
        vol.Optional("mileage"): vol.All(vol.Coerce(int), vol.Range(min=1)),
        vol.Optional("filter_actions", default={}): {
            vol.In(FILTER_SERVICE_KEYS): vol.In(FILTER_ACTIONS)
        },
    }
)


def _validate_snooze_data(data: dict) -> dict:
    try:
        validate_snooze_arguments(
            miles=data.get("miles"), until_mileage=data.get("until_mileage")
        )
    except ValueError as error:
        raise vol.Invalid(str(error)) from error
    return data


def _validate_set_data(data: dict) -> dict:
    try:
        validate_setup_arguments(data["mode"], data.get("mileage"))
    except ValueError as error:
        raise vol.Invalid(str(error)) from error
    return data


def _record_for(manager: VehicleManager, service: str):
    record = manager.records.get(service)
    if record is None or service not in manager.config[CONF_SERVICES]:
        raise vol.Invalid("Service is not tracked by this vehicle")
    return record


async def _async_log_maintenance_batch(
    manager: VehicleManager,
    services: list[str],
    mileage: int | None = None,
    filter_actions: dict[str, str] | None = None,
) -> None:
    keys = list(dict.fromkeys(services))
    actions = filter_actions or {}
    if any(key not in keys for key in actions):
        raise vol.Invalid("Filter actions must belong to selected maintenance")
    washable = set(manager.config.get(CONF_WASHABLE_FILTERS, []))
    records = [
        (
            _record_for(manager, key),
            bool(SERVICE_CATALOG[key].get("milestone")),
            actions.get(key, FILTER_ACTION_REPLACE) if key in washable else None,
        )
        for key in keys
    ]
    if any(key in actions and key not in washable for key in keys):
        raise vol.Invalid("Filter actions require a washable filter")
    completion_mileage = manager.effective_odometer if mileage is None else mileage
    if completion_mileage is None:
        raise vol.Invalid("No effective odometer is available")
    complete_service_batch(records, completion_mileage)
    await manager.async_save()


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
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

    async def log_maintenance(call: ServiceCall) -> None:
        manager = manager_for(call)
        key = call.data["service"]
        mileage = call.data.get("mileage", manager.effective_odometer)
        if mileage is None:
            raise vol.Invalid("No effective odometer is available")
        filter_action = call.data.get("filter_action")
        if key in manager.config.get(CONF_WASHABLE_FILTERS, []):
            complete_filter_service(
                _record_for(manager, key),
                mileage,
                action=filter_action or FILTER_ACTION_REPLACE,
            )
        else:
            if filter_action is not None:
                raise vol.Invalid("Filter actions require a washable filter")
            complete_service(
                _record_for(manager, key),
                mileage,
                milestone=bool(SERVICE_CATALOG[key].get("milestone")),
            )
        await manager.async_save()

    async def log_maintenance_batch(call: ServiceCall) -> None:
        manager = manager_for(call)
        await _async_log_maintenance_batch(
            manager,
            call.data["services"],
            call.data.get("mileage"),
            call.data.get("filter_actions"),
        )

    async def snooze_maintenance(call: ServiceCall) -> None:
        manager = manager_for(call)
        if manager.effective_odometer is None:
            raise vol.Invalid("No effective odometer is available")
        snooze_service(
            _record_for(manager, call.data["service"]),
            manager.effective_odometer,
            miles=call.data.get("miles"),
            until_mileage=call.data.get("until_mileage"),
        )
        await manager.async_save()

    async def clear_snooze(call: ServiceCall) -> None:
        manager = manager_for(call)
        _record_for(manager, call.data["service"]).snoozed_until_mileage = None
        await manager.async_save()

    async def set_maintenance(call: ServiceCall) -> None:
        manager = manager_for(call)
        key = call.data["service"]
        initial_due = manager.config.get(CONF_INITIAL_INTERVALS, {}).get(
            key, SERVICE_CATALOG[key].get("initial_interval")
        )
        initialize_service(
            _record_for(manager, key),
            call.data["mode"],
            call.data.get("mileage"),
            initial_due_mileage=initial_due,
        )
        await manager.async_save()

    async def reset_service(call: ServiceCall) -> None:
        manager = manager_for(call)
        key = call.data["service"]
        initial_due = manager.config.get(CONF_INITIAL_INTERVALS, {}).get(
            key, SERVICE_CATALOG[key].get("initial_interval")
        )
        initialize_service(
            _record_for(manager, key),
            "never_performed",
            initial_due_mileage=initial_due,
        )
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
                vol.Optional("mileage"): vol.All(vol.Coerce(int), vol.Range(min=1)),
                vol.Optional("filter_action"): vol.In(FILTER_ACTIONS),
            }
        ),
    )
    hass.services.async_register(
        DOMAIN,
        "log_maintenance_batch",
        log_maintenance_batch,
        schema=BATCH_LOG_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        "snooze_maintenance",
        snooze_maintenance,
        schema=vol.All(
            vol.Schema(
                {
                    **common,
                    vol.Optional("miles"): vol.All(vol.Coerce(int), vol.Range(min=1)),
                    vol.Optional("until_mileage"): vol.All(
                        vol.Coerce(int), vol.Range(min=1)
                    ),
                }
            ),
            _validate_snooze_data,
        ),
    )
    hass.services.async_register(
        DOMAIN, "clear_snooze", clear_snooze, schema=vol.Schema(common)
    )
    hass.services.async_register(
        DOMAIN,
        "set_maintenance",
        set_maintenance,
        schema=vol.All(
            vol.Schema(
                {
                    **common,
                    vol.Required("mode"): vol.In(
                        ["not_set", "never_performed", "last_completed", "due_at"]
                    ),
                    vol.Optional("mileage"): vol.All(vol.Coerce(int), vol.Range(min=0)),
                }
            ),
            _validate_set_data,
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
    if entry.version > 4:
        return False
    version = entry.version
    if version == 1:
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
        version = 2
    if version == 2:
        data = dict(entry.data)
        options = dict(entry.options)
        target = options if CONF_INTERVALS in options else data
        intervals = dict(target.get(CONF_INTERVALS, {}))
        for key, previous in PREVIOUS_DEFAULT_INTERVALS.items():
            if intervals.get(key) == previous:
                intervals[key] = SERVICE_CATALOG[key]["interval"]
        target[CONF_INTERVALS] = intervals
        selected = {**data, **options}.get(CONF_SERVICES, [])
        initial_intervals = dict(target.get(CONF_INITIAL_INTERVALS, {}))
        for key in selected:
            if initial := SERVICE_CATALOG[key].get("initial_interval"):
                initial_intervals.setdefault(key, initial)
        target[CONF_INITIAL_INTERVALS] = initial_intervals
        hass.config_entries.async_update_entry(
            entry,
            data=data,
            options=options,
            version=3,
        )
        version = 3
    if version == 3:
        data = dict(entry.data)
        options = dict(entry.options)
        for values in (data, options):
            if CONF_NOTIFY_TARGETS not in values and values.get(CONF_NOTIFY_SERVICE):
                values[CONF_NOTIFY_TARGETS] = [values[CONF_NOTIFY_SERVICE]]
            values.pop(CONF_NOTIFY_SERVICE, None)
            if CONF_SERVICES in values:
                values.setdefault(CONF_WASHABLE_FILTERS, [])
        hass.config_entries.async_update_entry(
            entry,
            data=data,
            options=options,
            version=4,
        )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unloaded


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Remove the persisted maintenance records for a deleted vehicle."""
    manager = VehicleManager(hass, entry)
    await manager.store.async_remove()


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
    targets = config.get(CONF_NOTIFY_TARGETS)
    if targets is None:
        legacy_target = str(config.get(CONF_NOTIFY_SERVICE, "")).strip()
        targets = [legacy_target] if legacy_target else []
    elif isinstance(targets, str):
        targets = [targets]
    targets = list(
        dict.fromkeys(str(target).strip() for target in targets if str(target).strip())
    )
    if not targets:
        return
    items = notification_items(
        manager.records,
        SERVICE_CATALOG,
        manager.effective_odometer,
        int(config.get(CONF_NOTIFY_THRESHOLD, 1500)),
        set(manager.config[CONF_SERVICES]),
    )
    if not items:
        return
    message = "\n".join(format_notification_item(item) for item in items)
    title = f"{manager.entry.title} maintenance"
    entity_targets = [
        target
        for target in targets
        if target.startswith("notify.") and hass.states.get(target) is not None
    ]
    if entity_targets:
        await hass.services.async_call(
            "notify",
            "send_message",
            {"title": title, "message": message},
            target={"entity_id": entity_targets},
            blocking=False,
        )
    for target in targets:
        if target in entity_targets or "." not in target:
            continue
        domain, service = target.split(".", 1)
        if not hass.services.has_service(domain, service):
            continue
        await hass.services.async_call(
            domain,
            service,
            {
                "title": title,
                "message": message,
                "data": {"tag": f"vehicle_maintenance_{manager.entry.entry_id}"},
            },
            blocking=False,
        )
