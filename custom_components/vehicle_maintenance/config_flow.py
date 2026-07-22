"""UI configuration for Vehicle Maintenance."""

from __future__ import annotations

from datetime import time

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN, UnitOfLength
from homeassistant.helpers import selector

from .const import (
    CONF_INITIAL_INTERVALS,
    CONF_INTERVALS,
    CONF_NOTIFY_ENABLED,
    CONF_NOTIFY_SERVICE,
    CONF_NOTIFY_THRESHOLD,
    CONF_NOTIFY_TIME,
    CONF_NOTIFY_WEEKDAY,
    CONF_ODOMETER_ENTITY,
    CONF_SERVICES,
    CONF_VEHICLE_NAME,
    DEFAULT_NOTIFICATION_THRESHOLD,
    DEFAULT_NOTIFICATION_TIME,
    DEFAULT_NOTIFICATION_WEEKDAY,
    DEFAULT_SERVICES,
    DOMAIN,
    SERVICE_CATALOG,
)


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


def _service_selector() -> selector.SelectSelector:
    options = [
        selector.SelectOptionDict(value=key, label=_service_label(value))
        for key, value in SERVICE_CATALOG.items()
    ]
    return selector.SelectSelector(
        selector.SelectSelectorConfig(
            options=options,
            multiple=True,
            mode=selector.SelectSelectorMode.LIST,
        )
    )


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
        selector.EntitySelectorConfig(domain="sensor")
    )
    return vol.Schema(fields)


def _services_schema(defaults: dict) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(
                CONF_SERVICES,
                default=defaults.get(CONF_SERVICES, DEFAULT_SERVICES),
            ): _service_selector()
        }
    )


def _notification_schema(defaults: dict) -> vol.Schema:
    weekdays = [
        ("mon", "Monday"),
        ("tue", "Tuesday"),
        ("wed", "Wednesday"),
        ("thu", "Thursday"),
        ("fri", "Friday"),
        ("sat", "Saturday"),
        ("sun", "Sunday"),
    ]
    return vol.Schema(
        {
            vol.Required(
                CONF_NOTIFY_ENABLED,
                default=defaults.get(CONF_NOTIFY_ENABLED, False),
            ): selector.BooleanSelector(),
            vol.Optional(
                CONF_NOTIFY_SERVICE,
                default=defaults.get(CONF_NOTIFY_SERVICE, ""),
            ): selector.TextSelector(),
            vol.Optional(
                CONF_NOTIFY_THRESHOLD,
                default=defaults.get(
                    CONF_NOTIFY_THRESHOLD, DEFAULT_NOTIFICATION_THRESHOLD
                ),
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
                        for value, label in weekdays
                    ]
                )
            ),
            vol.Required(
                CONF_NOTIFY_TIME,
                default=defaults.get(CONF_NOTIFY_TIME, DEFAULT_NOTIFICATION_TIME),
            ): selector.TimeSelector(),
        }
    )


def _interval_schema(
    services: list[str], current: dict, current_initial: dict
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
    return vol.Schema(fields)


def _selected_initial_intervals(
    services: list[str], user_input: dict
) -> dict[str, int]:
    return {
        key: int(user_input[f"initial_interval_{key}"])
        for key in services
        if SERVICE_CATALOG[key].get("initial_interval") is not None
    }


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
        target = str(user_input.get(CONF_NOTIFY_SERVICE, "")).strip()
        if "." not in target:
            errors[CONF_NOTIFY_SERVICE] = "invalid_notify_action"
        else:
            domain, service = target.split(".", 1)
            if not hass.services.has_service(domain, service):
                errors[CONF_NOTIFY_SERVICE] = "invalid_notify_action"
    return errors


class VehicleMaintenanceConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 3

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
            selected = list(user_input.get(CONF_SERVICES, []))
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
            return await self.async_step_notifications()
        return self.async_show_form(
            step_id="intervals",
            data_schema=_interval_schema(self._pending[CONF_SERVICES], {}, {}),
            description_placeholders={"vehicle": self._pending[CONF_VEHICLE_NAME]},
        )

    async def async_step_notifications(self, user_input=None):
        if user_input is not None:
            errors = _notification_errors(self.hass, user_input)
            if errors:
                return self.async_show_form(
                    step_id="notifications",
                    data_schema=_notification_schema(user_input),
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
            data_schema=_notification_schema({}),
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
                    step_id="init",
                    data_schema=_vehicle_schema(user_input, include_name=True),
                    errors=errors,
                )
            self._pending = dict(user_input)
            return await self.async_step_services()
        return self.async_show_form(
            step_id="init",
            data_schema=_vehicle_schema(defaults, include_name=True),
        )

    async def async_step_services(self, user_input=None):
        if user_input is not None:
            selected = list(user_input.get(CONF_SERVICES, []))
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
            data_schema=_services_schema(self._current),
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
            return await self.async_step_notifications()
        return self.async_show_form(
            step_id="intervals",
            data_schema=_interval_schema(
                self._pending[CONF_SERVICES],
                self._current.get(CONF_INTERVALS, {}),
                self._current.get(CONF_INITIAL_INTERVALS, {}),
            ),
            description_placeholders={"vehicle": self._pending[CONF_VEHICLE_NAME]},
        )

    async def async_step_notifications(self, user_input=None):
        if user_input is not None:
            errors = _notification_errors(self.hass, user_input)
            if errors:
                return self.async_show_form(
                    step_id="notifications",
                    data_schema=_notification_schema(user_input),
                    errors=errors,
                    description_placeholders={
                        "vehicle": self._pending[CONF_VEHICLE_NAME]
                    },
                )
            self._pending.update(user_input)
            self._pending[CONF_NOTIFY_TIME] = _normalize_time(
                self._pending[CONF_NOTIFY_TIME]
            )
            name = self._pending.pop(CONF_VEHICLE_NAME)
            self.hass.config_entries.async_update_entry(self._entry, title=name)
            return self.async_create_entry(title="", data=self._pending)
        return self.async_show_form(
            step_id="notifications",
            data_schema=_notification_schema(self._current),
            description_placeholders={"vehicle": self._pending[CONF_VEHICLE_NAME]},
        )
