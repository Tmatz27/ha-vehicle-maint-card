"""UI configuration for Vehicle Maintenance."""

from __future__ import annotations

from datetime import time

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers import selector

from .const import (
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


def _service_selector(default: list[str]):
    options = [
        selector.SelectOptionDict(value=key, label=value["name"])
        for key, value in SERVICE_CATALOG.items()
    ]
    return selector.SelectSelector(
        selector.SelectSelectorConfig(
            options=options, multiple=True, mode=selector.SelectSelectorMode.DROPDOWN
        )
    )


def _base_schema(defaults: dict, *, include_name: bool) -> vol.Schema:
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
    fields[
        vol.Required(
            CONF_SERVICES, default=defaults.get(CONF_SERVICES, DEFAULT_SERVICES)
        )
    ] = _service_selector(defaults.get(CONF_SERVICES, DEFAULT_SERVICES))
    fields[
        vol.Required(
            CONF_NOTIFY_ENABLED, default=defaults.get(CONF_NOTIFY_ENABLED, False)
        )
    ] = selector.BooleanSelector()
    fields[
        vol.Optional(CONF_NOTIFY_SERVICE, default=defaults.get(CONF_NOTIFY_SERVICE, ""))
    ] = selector.TextSelector()
    fields[
        vol.Optional(
            CONF_NOTIFY_THRESHOLD,
            default=defaults.get(CONF_NOTIFY_THRESHOLD, DEFAULT_NOTIFICATION_THRESHOLD),
        )
    ] = selector.NumberSelector(
        selector.NumberSelectorConfig(
            min=0, max=10000, step=100, mode=selector.NumberSelectorMode.BOX
        )
    )
    weekdays = [
        ("mon", "Monday"),
        ("tue", "Tuesday"),
        ("wed", "Wednesday"),
        ("thu", "Thursday"),
        ("fri", "Friday"),
        ("sat", "Saturday"),
        ("sun", "Sunday"),
    ]
    fields[
        vol.Required(
            CONF_NOTIFY_WEEKDAY,
            default=defaults.get(CONF_NOTIFY_WEEKDAY, DEFAULT_NOTIFICATION_WEEKDAY),
        )
    ] = selector.SelectSelector(
        selector.SelectSelectorConfig(
            options=[
                selector.SelectOptionDict(value=value, label=label)
                for value, label in weekdays
            ]
        )
    )
    fields[
        vol.Required(
            CONF_NOTIFY_TIME,
            default=defaults.get(CONF_NOTIFY_TIME, DEFAULT_NOTIFICATION_TIME),
        )
    ] = selector.TimeSelector()
    return vol.Schema(fields)


def _interval_schema(services: list[str], current: dict) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(
                f"interval_{key}",
                default=int(
                    current.get(key, SERVICE_CATALOG[key].get("interval") or 1)
                ),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1, max=500000, step=1, mode=selector.NumberSelectorMode.BOX
                )
            )
            for key in services
        }
    )


def _normalize_time(value) -> str:
    if isinstance(value, time):
        return value.strftime("%H:%M:%S")
    value = str(value)
    return value if value.count(":") == 2 else f"{value}:00"


class VehicleMaintenanceConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 2

    def __init__(self) -> None:
        self._pending: dict = {}

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            self._pending = dict(user_input)
            return await self.async_step_intervals()
        return self.async_show_form(
            step_id="user", data_schema=_base_schema({}, include_name=True)
        )

    async def async_step_intervals(self, user_input=None):
        if user_input is not None:
            self._pending[CONF_INTERVALS] = {
                key: int(user_input[f"interval_{key}"])
                for key in self._pending[CONF_SERVICES]
            }
            self._pending[CONF_NOTIFY_TIME] = _normalize_time(
                self._pending[CONF_NOTIFY_TIME]
            )
            title = self._pending[CONF_VEHICLE_NAME]
            return self.async_create_entry(title=title, data=self._pending)
        return self.async_show_form(
            step_id="intervals",
            data_schema=_interval_schema(self._pending[CONF_SERVICES], {}),
            description_placeholders={"vehicle": self._pending[CONF_VEHICLE_NAME]},
        )

    @staticmethod
    def async_get_options_flow(config_entry):
        return VehicleMaintenanceOptionsFlow(config_entry)


class VehicleMaintenanceOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self._entry = config_entry
        self._pending: dict = {}

    async def async_step_init(self, user_input=None):
        current = {**self._entry.data, **self._entry.options}
        defaults = {**current, CONF_VEHICLE_NAME: self._entry.title}
        if user_input is not None:
            self._pending = dict(user_input)
            return await self.async_step_intervals()
        return self.async_show_form(
            step_id="init", data_schema=_base_schema(defaults, include_name=True)
        )

    async def async_step_intervals(self, user_input=None):
        current = {**self._entry.data, **self._entry.options}
        if user_input is not None:
            self._pending[CONF_INTERVALS] = {
                key: int(user_input[f"interval_{key}"])
                for key in self._pending[CONF_SERVICES]
            }
            self._pending[CONF_NOTIFY_TIME] = _normalize_time(
                self._pending[CONF_NOTIFY_TIME]
            )
            name = self._pending.pop(CONF_VEHICLE_NAME)
            self.hass.config_entries.async_update_entry(self._entry, title=name)
            return self.async_create_entry(title="", data=self._pending)
        return self.async_show_form(
            step_id="intervals",
            data_schema=_interval_schema(
                self._pending[CONF_SERVICES], current.get(CONF_INTERVALS, {})
            ),
            description_placeholders={"vehicle": self._pending[CONF_VEHICLE_NAME]},
        )
