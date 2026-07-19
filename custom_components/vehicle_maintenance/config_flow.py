"""Config flow for Vehicle Maintenance."""

from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers import selector

from .const import (
    CONF_ODOMETER_ENTITY,
    CONF_NOTIFY_SERVICE,
    CONF_NOTIFY_THRESHOLD,
    CONF_SERVICES,
    CONF_VEHICLE_NAME,
    DOMAIN,
    SERVICE_CATALOG,
)


class VehicleMaintenanceConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Configure a vehicle and its tracked services."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Collect the vehicle, odometer, and service list."""
        if user_input is not None:
            return self.async_create_entry(
                title=user_input[CONF_VEHICLE_NAME], data=user_input
            )

        service_options = [
            selector.SelectOptionDict(value=key, label=value["name"])
            for key, value in SERVICE_CATALOG.items()
        ]
        schema = vol.Schema(
            {
                vol.Required(CONF_VEHICLE_NAME): selector.TextSelector(),
                vol.Required(CONF_ODOMETER_ENTITY): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
                vol.Required(
                    CONF_SERVICES, default=list(SERVICE_CATALOG)
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=service_options,
                        multiple=True,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Optional(CONF_NOTIFY_SERVICE, default=""): selector.TextSelector(),
                vol.Optional(
                    CONF_NOTIFY_THRESHOLD, default=1500
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0, max=10000, step=100, mode=selector.NumberSelectorMode.BOX
                    )
                ),
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema)

    @staticmethod
    def async_get_options_flow(config_entry):
        """Allow the vehicle settings to be changed later."""
        return VehicleMaintenanceOptionsFlow(config_entry)


class VehicleMaintenanceOptionsFlow(config_entries.OptionsFlow):
    """Edit an existing vehicle."""

    def __init__(self, config_entry):
        self._entry = config_entry

    async def async_step_init(self, user_input=None):
        """Edit odometer and tracked services."""
        current = {**self._entry.data, **self._entry.options}
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        service_options = [
            selector.SelectOptionDict(value=key, label=value["name"])
            for key, value in SERVICE_CATALOG.items()
        ]
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_ODOMETER_ENTITY,
                    default=current[CONF_ODOMETER_ENTITY],
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
                vol.Required(
                    CONF_SERVICES,
                    default=current[CONF_SERVICES],
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=service_options,
                        multiple=True,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Optional(
                    CONF_NOTIFY_SERVICE,
                    default=current.get(CONF_NOTIFY_SERVICE, ""),
                ): selector.TextSelector(),
                vol.Optional(
                    CONF_NOTIFY_THRESHOLD,
                    default=current.get(CONF_NOTIFY_THRESHOLD, 1500),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0, max=10000, step=100, mode=selector.NumberSelectorMode.BOX
                    )
                ),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
