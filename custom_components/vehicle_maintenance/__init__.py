"""Vehicle Maintenance integration."""

from __future__ import annotations

from datetime import time
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.typing import ConfigType
from homeassistant.util import dt as dt_util

from .const import (
    ATTR_ENTRY_ID,
    CONF_INITIAL_INTERVALS,
    CONF_INTERVALS,
    CONF_NOTIFY_ENABLED,
    CONF_NOTIFY_MUTED_SERVICES,
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
    WEEKDAY_INDEX,
)
from .frontend import async_register_card_frontend
from .integrity import complete_service_batch_checked, complete_service_checked
from .manager import VehicleManager
from .model import (
    format_notification_item,
    initialize_service,
    notification_items,
    parse_clock_time,
    snooze_service,
    validate_setup_arguments,
    validate_snooze_arguments,
)

WEEKDAYS = WEEKDAY_INDEX
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


def _validate_last_completed_not_future(
    manager: VehicleManager, mode: str, mileage: int | None
) -> None:
    """Keep explicit history corrections from creating future completions."""
    if mode != "last_completed" or mileage is None:
        return
    odometer = manager.effective_odometer
    if odometer is not None and mileage > odometer:
        raise vol.Invalid(
            "Completion mileage cannot be greater than the current odometer"
        )


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
    try:
        complete_service_batch_checked(
            records,
            completion_mileage,
            manager.effective_odometer,
        )
    except ValueError as error:
        raise vol.Invalid(str(error)) from error
    await manager.async_save()


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register frontend and actions exactly once for the integration."""
    await async_register_card_frontend(hass)
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
        record = _record_for(manager, key)
        milestone = bool(SERVICE_CATALOG[key].get("milestone"))
        filter_action = call.data.get("filter_action")
        if key in manager.config.get(CONF_WASHABLE_FILTERS, []):
            filter_action = filter_action or FILTER_ACTION_REPLACE
        elif filter_action is not None:
            raise vol.Invalid("Filter actions require a washable filter")
        try:
            complete_service_checked(
                record,
                mileage,
                manager.effective_odometer,
                milestone=milestone,
                filter_action=filter_action,
            )
        except ValueError as error:
            raise vol.Invalid(str(error)) from error
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
        key = call.data["service"]
        record = _record_for(manager, key)
        if SERVICE_CATALOG[key].get("milestone") and record.milestone_completed:
            raise vol.Invalid("Completed mileage milestones cannot be extended")
        snooze_service(
            record,
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
        _validate_last_completed_not_future(
            manager, call.data["mode"], call.data.get("mileage")
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

    async def send_test_notification(call: ServiceCall) -> None:
        manager = manager_for(call)
        result = await _async_run_notification(hass, manager, test=True)
        if result["status"] == "error":
            raise vol.Invalid(f"Test notification failed: {result['error']}")
        if result["status"] == "skipped_no_targets":
            raise vol.Invalid(
                "No notification recipients are configured for this vehicle"
            )
        if result["status"] == "skipped_no_odometer":
            raise vol.Invalid("No effective odometer is available")

    async def log_car_wash(call: ServiceCall) -> None:
        manager = manager_for(call)
        when = call.data.get("date") or dt_util.now().date()
        if when > dt_util.now().date():
            raise vol.Invalid("Wash date cannot be in the future")
        try:
            await manager.async_log_car_wash(when)
        except ValueError as error:
            raise vol.Invalid(str(error)) from error

    async def reset_car_wash(call: ServiceCall) -> None:
        await manager_for(call).async_reset_car_wash()

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
    hass.services.async_register(
        DOMAIN,
        "send_test_notification",
        send_test_notification,
        schema=vol.Schema({vol.Required(ATTR_ENTRY_ID): cv.string}),
    )
    hass.services.async_register(
        DOMAIN,
        "log_car_wash",
        log_car_wash,
        schema=vol.Schema(
            {
                vol.Required(ATTR_ENTRY_ID): cv.string,
                vol.Optional("date"): cv.date,
            }
        ),
    )
    hass.services.async_register(
        DOMAIN,
        "reset_car_wash",
        reset_car_wash,
        schema=vol.Schema({vol.Required(ATTR_ENTRY_ID): cv.string}),
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
            hass.async_create_task(_async_run_notification(hass, manager))

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
    return parse_clock_time(value)


def _configured_targets(config: dict) -> list[str]:
    """Return de-duplicated notification targets across modern and legacy keys."""
    targets = config.get(CONF_NOTIFY_TARGETS)
    if targets is None:
        legacy_target = str(config.get(CONF_NOTIFY_SERVICE, "")).strip()
        targets = [legacy_target] if legacy_target else []
    elif isinstance(targets, str):
        targets = [targets]
    return list(
        dict.fromkeys(str(target).strip() for target in targets if str(target).strip())
    )


async def _async_send_notification(
    hass: HomeAssistant, manager: VehicleManager, *, test: bool = False
) -> dict[str, Any]:
    """Deliver a maintenance summary and report exactly what happened.

    A test send deliberately bypasses the enabled switch and the empty-summary
    skip so the user can confirm routing even when nothing is currently due.
    """
    config = manager.config
    result: dict[str, Any] = {
        "timestamp": dt_util.now().isoformat(),
        "test": test,
        "status": "skipped",
        "targets": [],
        "item_count": 0,
        "error": None,
    }

    if not test and not config.get(CONF_NOTIFY_ENABLED, False):
        result["status"] = "skipped_disabled"
        return result
    if manager.effective_odometer is None:
        result["status"] = "skipped_no_odometer"
        return result

    targets = _configured_targets(config)
    if not targets:
        result["status"] = "skipped_no_targets"
        return result

    threshold = int(config.get(CONF_NOTIFY_THRESHOLD, DEFAULT_NOTIFICATION_THRESHOLD))
    items = notification_items(
        manager.records,
        SERVICE_CATALOG,
        manager.effective_odometer,
        threshold,
        set(config[CONF_SERVICES]),
        set(config.get(CONF_NOTIFY_MUTED_SERVICES, [])),
    )
    result["item_count"] = len(items)
    if not items and not test:
        result["status"] = "skipped_no_items"
        return result

    title = f"{manager.entry.title} maintenance"
    if items:
        message = "\n".join(format_notification_item(item) for item in items)
    else:
        message = (
            f"Nothing is due within {threshold:,} mi. "
            "This is a test of your Vehicle Maintenance notification settings."
        )
    if test:
        title = f"{title} (test)"

    entity_targets = [
        target
        for target in targets
        if target.startswith("notify.") and hass.states.get(target) is not None
    ]
    delivered: list[str] = []
    try:
        if entity_targets:
            await hass.services.async_call(
                "notify",
                "send_message",
                {"title": title, "message": message},
                target={"entity_id": entity_targets},
                blocking=False,
            )
            delivered.extend(entity_targets)
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
            delivered.append(target)
    except Exception as error:  # noqa: BLE001 - reported back as a diagnostic
        result["status"] = "error"
        result["error"] = str(error)
        result["targets"] = delivered
        return result

    result["targets"] = delivered
    result["status"] = "sent" if delivered else "skipped_no_targets"
    return result


async def _async_run_notification(
    hass: HomeAssistant, manager: VehicleManager, *, test: bool = False
) -> dict[str, Any]:
    """Send a summary and persist the delivery diagnostic for the dashboard."""
    result = await _async_send_notification(hass, manager, test=test)
    await manager.async_record_notification(result)
    return result
