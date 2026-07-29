"""UI configuration for Vehicle Maintenance."""

from __future__ import annotations

from datetime import time

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN, UnitOfLength
from homeassistant.helpers import selector

from .const import (
    CONF_CAR_WASH_ENABLED,
    CONF_CAR_WASH_INTERVAL_DAYS,
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
    DEFAULT_CAR_WASH_INTERVAL_DAYS,
    DEFAULT_NOTIFICATION_THRESHOLD,
    DEFAULT_NOTIFICATION_TIME,
    DEFAULT_NOTIFICATION_WEEKDAY,
    DEFAULT_SERVICES,
    DOMAIN,
    FILTER_SERVICE_KEYS,
    SERVICE_CATALOG,
    WEEKDAY_OPTIONS,
)

SERVICE_GROUPS = {
    "scheduled_services": {"perform", "replace"},
    "inspection_services": {"inspect"},
    "condition_services": {"condition"},
    "milestone_services": {"milestone"},
}


def _service_label(definition: dict) -> str:
    name = definition["name"]
    interval = int(definition["interval"])
    initial = definition.get("initial_interval")
    if definition.get("milestone"):
        return f"{name} (one-time milestone)"
    if initial is not None:
        return f"{name} (first at {initial:,} mi; then every {interval:,} mi)"
    action = {
        "condition": "condition reminder",
        "inspect": "inspect",
        "perform": "perform",
        "replace": "replace",
    }.get(definition.get("kind"), "service")
    return f"{name} ({action} every {interval:,} mi)"


def _service_selector(service_keys=None) -> selector.SelectSelector:
    allowed = set(SERVICE_CATALOG if service_keys is None else service_keys)
    options = [
        selector.SelectOptionDict(value=key, label=_service_label(value))
        for key, value in SERVICE_CATALOG.items()
        if key in allowed
    ]
    return selector.SelectSelector(
        selector.SelectSelectorConfig(
            options=options,
            multiple=True,
            mode=selector.SelectSelectorMode.LIST,
        )
    )


def _selected_services(values: dict) -> list[str]:
    if CONF_SERVICES in values:
        selected = set(values.get(CONF_SERVICES, []))
    else:
        selected = {
            service for field in SERVICE_GROUPS for service in values.get(field, [])
        }
    return [key for key in SERVICE_CATALOG if key in selected]


def _vehicle_schema(defaults: dict, *, include_name: bool) -> vol.Schema:
    fields = {}
    if include_name:
        fields[
            vol.Required(CONF_VEHICLE_NAME, default=defaults.get(CONF_VEHICLE_NAME, ""))
        ] = selector.TextSelector()
    odometer_marker = (
        vol.Required(CONF_ODOMETER_ENTITY, default=defaults[CONF_ODOMETER_ENTITY])
        if defaults.get(CONF_ODOMETER_ENTITY)
        else vol.Required(CONF_ODOMETER_ENTITY)
    )
    fields[odometer_marker] = selector.EntitySelector(
        selector.EntitySelectorConfig(domain="sensor", device_class="distance")
    )
    return vol.Schema(fields)


def _services_schema(defaults: dict) -> vol.Schema:
    selected = set(
        _selected_services(defaults)
        if CONF_SERVICES in defaults or any(key in defaults for key in SERVICE_GROUPS)
        else DEFAULT_SERVICES
    )
    fields = {}
    for field, kinds in SERVICE_GROUPS.items():
        keys = [
            key
            for key, definition in SERVICE_CATALOG.items()
            if definition.get("kind") in kinds
        ]
        fields[
            vol.Required(field, default=[key for key in keys if key in selected])
        ] = _service_selector(keys)
    return vol.Schema(fields)


def _configured_notification_targets(values: dict) -> list[str]:
    targets = values.get(CONF_NOTIFY_TARGETS)
    if targets is None:
        targets = values.get(CONF_NOTIFY_SERVICE, "")
    if isinstance(targets, str):
        targets = [targets] if targets.strip() else []
    return list(
        dict.fromkeys(
            str(target).strip() for target in targets or [] if str(target).strip()
        )
    )


def _notification_options(hass, defaults: dict) -> list[selector.SelectOptionDict]:
    labels: dict[str, str] = {}
    for entity_id in hass.states.async_entity_ids("notify"):
        state = hass.states.get(entity_id)
        friendly_name = (
            state.attributes.get("friendly_name") if state is not None else None
        )
        label = friendly_name or entity_id
        labels[entity_id] = f"{label} ({entity_id})"

    for service in hass.services.async_services().get("notify", {}):
        if service == "send_message":
            continue
        target = f"notify.{service}"
        labels.setdefault(
            target,
            f"{service.replace('_', ' ').title()} group or action ({target})",
        )

    for target in _configured_notification_targets(defaults):
        labels.setdefault(target, f"Configured target ({target})")

    return [
        selector.SelectOptionDict(value=target, label=label)
        for target, label in sorted(labels.items(), key=lambda item: item[1].lower())
    ]


def _notification_schema(
    hass, defaults: dict, selected_services: list[str] | None = None
) -> vol.Schema:
    fields = {
        vol.Required(
            CONF_NOTIFY_ENABLED,
            default=defaults.get(CONF_NOTIFY_ENABLED, False),
        ): selector.BooleanSelector(),
        vol.Optional(
            CONF_NOTIFY_TARGETS,
            default=_configured_notification_targets(defaults),
        ): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=_notification_options(hass, defaults),
                multiple=True,
                mode=selector.SelectSelectorMode.LIST,
            )
        ),
        vol.Optional(
            CONF_NOTIFY_THRESHOLD,
            default=defaults.get(CONF_NOTIFY_THRESHOLD, DEFAULT_NOTIFICATION_THRESHOLD),
        ): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=0,
                max=10000,
                step=100,
                mode=selector.NumberSelectorMode.BOX,
            )
        ),
        vol.Required(
            CONF_NOTIFY_WEEKDAY,
            default=defaults.get(CONF_NOTIFY_WEEKDAY, DEFAULT_NOTIFICATION_WEEKDAY),
        ): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=[
                    selector.SelectOptionDict(value=value, label=label)
                    for value, label in WEEKDAY_OPTIONS
                ]
            )
        ),
        vol.Required(
            CONF_NOTIFY_TIME,
            default=defaults.get(CONF_NOTIFY_TIME, DEFAULT_NOTIFICATION_TIME),
        ): selector.TimeSelector(),
    }

    # Muting is per service and never changes the maintenance record itself, so
    # an item stays visible on the card while staying out of the weekly summary.
    tracked = [key for key in (selected_services or []) if key in SERVICE_CATALOG]
    if tracked:
        muted = [
            key
            for key in defaults.get(CONF_NOTIFY_MUTED_SERVICES, []) or []
            if key in tracked
        ]
        fields[
            vol.Optional(CONF_NOTIFY_MUTED_SERVICES, default=muted)
        ] = selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=[
                    selector.SelectOptionDict(
                        value=key, label=SERVICE_CATALOG[key]["name"]
                    )
                    for key in tracked
                ],
                multiple=True,
                mode=selector.SelectSelectorMode.LIST,
            )
        )
    return vol.Schema(fields)


def _car_wash_schema(defaults: dict) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(
                CONF_CAR_WASH_ENABLED,
                default=bool(defaults.get(CONF_CAR_WASH_ENABLED, False)),
            ): selector.BooleanSelector(),
            vol.Required(
                CONF_CAR_WASH_INTERVAL_DAYS,
                default=int(
                    defaults.get(
                        CONF_CAR_WASH_INTERVAL_DAYS, DEFAULT_CAR_WASH_INTERVAL_DAYS
                    )
                ),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1,
                    max=365,
                    step=1,
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
        }
    )


def _interval_schema(
    services: list[str],
    current: dict,
    current_initial: dict,
    current_washable: list[str] | None = None,
) -> vol.Schema:
    fields = {}
    number_selector = selector.NumberSelector(
        selector.NumberSelectorConfig(
            min=1,
            max=500000,
            step=1,
            mode=selector.NumberSelectorMode.BOX,
        )
    )
    for key in services:
        definition = SERVICE_CATALOG[key]
        if initial := definition.get("initial_interval"):
            fields[
                vol.Required(
                    f"initial_interval_{key}",
                    default=int(current_initial.get(key, initial)),
                )
            ] = number_selector
        fields[
            vol.Required(
                f"interval_{key}",
                default=int(current.get(key, definition.get("interval") or 1)),
            )
        ] = number_selector
        if key in FILTER_SERVICE_KEYS:
            fields[
                vol.Required(
                    f"washable_{key}",
                    default=key in set(current_washable or []),
                )
            ] = selector.BooleanSelector()
    return vol.Schema(fields)


def _selected_initial_intervals(
    services: list[str], user_input: dict
) -> dict[str, int]:
    return {
        key: int(user_input[f"initial_interval_{key}"])
        for key in services
        if SERVICE_CATALOG[key].get("initial_interval") is not None
    }


def _selected_washable_filters(
    services: list[str], user_input: dict
) -> list[str]:
    return [
        key
        for key in FILTER_SERVICE_KEYS
        if key in services and user_input.get(f"washable_{key}", False)
    ]


def _normalize_time(value) -> str:
    if isinstance(value, time):
        return value.strftime("%H:%M:%S")
    value = str(value)
    return value if value.count(":") == 2 else f"{value}:00"


def _vehicle_errors(hass, user_input: dict, entries, current_entry_id=None) -> dict:
    errors = {}
    source = user_input[CONF_ODOMETER_ENTITY]
    if any(
        entry.entry_id != current_entry_id
        and {**entry.data, **entry.options}.get(CONF_ODOMETER_ENTITY) == source
        for entry in entries
    ):
        errors[CONF_ODOMETER_ENTITY] = "odometer_already_configured"
    state = hass.states.get(source)
    if state is None:
        errors[CONF_ODOMETER_ENTITY] = "odometer_not_numeric"
    else:
        unit = state.attributes.get("unit_of_measurement")
        if unit not in (UnitOfLength.MILES, "mile", "miles"):
            errors[CONF_ODOMETER_ENTITY] = "odometer_not_miles"
        elif state.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            errors[CONF_ODOMETER_ENTITY] = "odometer_not_numeric"
        else:
            try:
                float(state.state)
            except (TypeError, ValueError):
                errors[CONF_ODOMETER_ENTITY] = "odometer_not_numeric"
    return errors


def _notification_errors(hass, user_input: dict) -> dict:
    errors = {}
    if user_input.get(CONF_NOTIFY_ENABLED):
        targets = _configured_notification_targets(user_input)
        if not targets:
            errors[CONF_NOTIFY_TARGETS] = "invalid_notify_action"
        for target in targets:
            if "." not in target:
                errors[CONF_NOTIFY_TARGETS] = "invalid_notify_action"
                break
            domain, service = target.split(".", 1)
            is_notify_entity = domain == "notify" and hass.states.get(target) is not None
            is_legacy_action = hass.services.has_service(domain, service)
            if not is_notify_entity and not is_legacy_action:
                errors[CONF_NOTIFY_TARGETS] = "invalid_notify_action"
                break
    return errors


class VehicleMaintenanceConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 4

    def __init__(self) -> None:
        self._pending: dict = {}

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            errors = _vehicle_errors(
                self.hass, user_input, self._async_current_entries()
            )
            if errors:
                return self.async_show_form(
                    step_id="user",
                    data_schema=_vehicle_schema(user_input, include_name=True),
                    errors=errors,
                )
            self._pending = dict(user_input)
            return await self.async_step_services()
        return self.async_show_form(
            step_id="user",
            data_schema=_vehicle_schema({}, include_name=True),
        )

    async def async_step_services(self, user_input=None):
        if user_input is not None:
            selected = _selected_services(user_input)
            if not selected:
                return self.async_show_form(
                    step_id="services",
                    data_schema=_services_schema(user_input),
                    errors={"base": "select_at_least_one_service"},
                    description_placeholders={
                        "vehicle": self._pending[CONF_VEHICLE_NAME]
                    },
                )
            self._pending[CONF_SERVICES] = selected
            return await self.async_step_intervals()
        return self.async_show_form(
            step_id="services",
            data_schema=_services_schema(self._pending),
            description_placeholders={"vehicle": self._pending[CONF_VEHICLE_NAME]},
        )

    async def async_step_intervals(self, user_input=None):
        if user_input is not None:
            self._pending[CONF_INTERVALS] = {
                key: int(user_input[f"interval_{key}"])
                for key in self._pending[CONF_SERVICES]
            }
            self._pending[CONF_INITIAL_INTERVALS] = _selected_initial_intervals(
                self._pending[CONF_SERVICES], user_input
            )
            self._pending[CONF_WASHABLE_FILTERS] = _selected_washable_filters(
                self._pending[CONF_SERVICES], user_input
            )
            return await self.async_step_notifications()
        return self.async_show_form(
            step_id="intervals",
            data_schema=_interval_schema(self._pending[CONF_SERVICES], {}, {}, []),
            description_placeholders={"vehicle": self._pending[CONF_VEHICLE_NAME]},
        )

    async def async_step_notifications(self, user_input=None):
        selected = self._pending.get(CONF_SERVICES, [])
        if user_input is not None:
            errors = _notification_errors(self.hass, user_input)
            if errors:
                return self.async_show_form(
                    step_id="notifications",
                    data_schema=_notification_schema(self.hass, user_input, selected),
                    errors=errors,
                    description_placeholders={
                        "vehicle": self._pending[CONF_VEHICLE_NAME]
                    },
                )
            self._pending.update(user_input)
            self._pending[CONF_NOTIFY_TIME] = _normalize_time(
                self._pending[CONF_NOTIFY_TIME]
            )
            title = self._pending[CONF_VEHICLE_NAME]
            return self.async_create_entry(title=title, data=self._pending)
        return self.async_show_form(
            step_id="notifications",
            data_schema=_notification_schema(self.hass, {}, selected),
            description_placeholders={"vehicle": self._pending[CONF_VEHICLE_NAME]},
        )

    @staticmethod
    def async_get_options_flow(config_entry):
        return VehicleMaintenanceOptionsFlow(config_entry)


class VehicleMaintenanceOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self._entry = config_entry
        self._pending: dict = {}
        self._current: dict = {}

    async def async_step_init(self, user_input=None):
        self._current = {**self._entry.data, **self._entry.options}
        return self.async_show_menu(
            step_id="init",
            menu_options=["vehicle", "services", "notifications", "car_wash"],
        )

    def _save_options(self, changes: dict):
        options = {**self._current, **changes}
        options.pop(CONF_VEHICLE_NAME, None)
        options.pop(CONF_NOTIFY_SERVICE, None)
        return self.async_create_entry(title="", data=options)

    async def async_step_vehicle(self, user_input=None):
        defaults = {**self._current, CONF_VEHICLE_NAME: self._entry.title}
        if user_input is not None:
            errors = _vehicle_errors(
                self.hass,
                user_input,
                self.hass.config_entries.async_entries(DOMAIN),
                self._entry.entry_id,
            )
            if errors:
                return self.async_show_form(
                    step_id="vehicle",
                    data_schema=_vehicle_schema(user_input, include_name=True),
                    errors=errors,
                )
            values = dict(user_input)
            name = values.pop(CONF_VEHICLE_NAME)
            self.hass.config_entries.async_update_entry(self._entry, title=name)
            return self._save_options(values)
        return self.async_show_form(
            step_id="vehicle",
            data_schema=_vehicle_schema(defaults, include_name=True),
        )

    async def async_step_services(self, user_input=None):
        if user_input is not None:
            selected = _selected_services(user_input)
            if not selected:
                return self.async_show_form(
                    step_id="services",
                    data_schema=_services_schema(user_input),
                    errors={"base": "select_at_least_one_service"},
                    description_placeholders={"vehicle": self._entry.title},
                )
            self._pending[CONF_SERVICES] = selected
            return await self.async_step_intervals()
        return self.async_show_form(
            step_id="services",
            data_schema=_services_schema(self._current),
            description_placeholders={"vehicle": self._entry.title},
        )

    async def async_step_intervals(self, user_input=None):
        if user_input is not None:
            intervals = dict(self._current.get(CONF_INTERVALS, {}))
            intervals.update(
                {
                    key: int(user_input[f"interval_{key}"])
                    for key in self._pending[CONF_SERVICES]
                }
            )
            initial_intervals = dict(self._current.get(CONF_INITIAL_INTERVALS, {}))
            initial_intervals.update(
                _selected_initial_intervals(self._pending[CONF_SERVICES], user_input)
            )
            washable = {
                key
                for key in self._current.get(CONF_WASHABLE_FILTERS, [])
                if key in self._pending[CONF_SERVICES]
            }
            for key in FILTER_SERVICE_KEYS:
                if key not in self._pending[CONF_SERVICES]:
                    continue
                if user_input.get(f"washable_{key}", False):
                    washable.add(key)
                else:
                    washable.discard(key)
            return self._save_options(
                {
                    CONF_SERVICES: self._pending[CONF_SERVICES],
                    CONF_INTERVALS: intervals,
                    CONF_INITIAL_INTERVALS: initial_intervals,
                    CONF_WASHABLE_FILTERS: [
                        key for key in FILTER_SERVICE_KEYS if key in washable
                    ],
                    # Drop mutes for services the user just stopped tracking so a
                    # later re-enable does not silently stay out of notifications.
                    CONF_NOTIFY_MUTED_SERVICES: [
                        key
                        for key in self._current.get(CONF_NOTIFY_MUTED_SERVICES, [])
                        if key in self._pending[CONF_SERVICES]
                    ],
                }
            )
        return self.async_show_form(
            step_id="intervals",
            data_schema=_interval_schema(
                self._pending[CONF_SERVICES],
                self._current.get(CONF_INTERVALS, {}),
                self._current.get(CONF_INITIAL_INTERVALS, {}),
                self._current.get(CONF_WASHABLE_FILTERS, []),
            ),
            description_placeholders={"vehicle": self._entry.title},
        )

    async def async_step_notifications(self, user_input=None):
        selected = self._current.get(CONF_SERVICES, [])
        if user_input is not None:
            errors = _notification_errors(self.hass, user_input)
            if errors:
                return self.async_show_form(
                    step_id="notifications",
                    data_schema=_notification_schema(self.hass, user_input, selected),
                    errors=errors,
                    description_placeholders={"vehicle": self._entry.title},
                )
            values = dict(user_input)
            values[CONF_NOTIFY_TIME] = _normalize_time(values[CONF_NOTIFY_TIME])
            values.setdefault(CONF_NOTIFY_MUTED_SERVICES, [])
            return self._save_options(values)
        return self.async_show_form(
            step_id="notifications",
            data_schema=_notification_schema(self.hass, self._current, selected),
            description_placeholders={"vehicle": self._entry.title},
        )

    async def async_step_car_wash(self, user_input=None):
        if user_input is not None:
            values = dict(user_input)
            values[CONF_CAR_WASH_INTERVAL_DAYS] = int(
                values[CONF_CAR_WASH_INTERVAL_DAYS]
            )
            return self._save_options(values)
        return self.async_show_form(
            step_id="car_wash",
            data_schema=_car_wash_schema(self._current),
            description_placeholders={"vehicle": self._entry.title},
        )
