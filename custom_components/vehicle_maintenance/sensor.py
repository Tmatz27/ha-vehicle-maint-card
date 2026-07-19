"""Sensors created by Vehicle Maintenance."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfLength
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event

from .const import (
    ATTR_ENTRY_ID,
    ATTR_SERVICE_KEY,
    CONF_ODOMETER_ENTITY,
    CONF_SERVICES,
    DOMAIN,
    SERVICE_CATALOG,
    SIGNAL_UPDATE,
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    """Create the main vehicle entity and service sensors."""
    selected = {**entry.data, **entry.options}[CONF_SERVICES]
    async_add_entities(
        [VehicleSummarySensor(entry)]
        + [MaintenanceSensor(hass, entry, key) for key in selected]
    )


class VehicleEntity(SensorEntity):
    """Common vehicle entity properties."""

    _attr_has_entity_name = True

    def __init__(self, entry: ConfigEntry):
        self.entry = entry
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="Vehicle Maintenance",
        )


class VehicleSummarySensor(VehicleEntity):
    """Main entity selected by the visual card editor."""

    _attr_name = "Maintenance"
    _attr_icon = "mdi:car-wrench"

    def __init__(self, entry: ConfigEntry):
        super().__init__(entry)
        self._attr_unique_id = f"{entry.entry_id}_maintenance"

    @property
    def native_value(self):
        return "ready"

    @property
    def extra_state_attributes(self):
        data = {**self.entry.data, **self.entry.options}
        return {
            ATTR_ENTRY_ID: self.entry.entry_id,
            "integration": DOMAIN,
            "vehicle_name": self.entry.title,
            "odometer_entity": data[CONF_ODOMETER_ENTITY],
            "services": data[CONF_SERVICES],
        }


class MaintenanceSensor(VehicleEntity):
    """Miles remaining for one recurring service."""

    _attr_native_unit_of_measurement = UnitOfLength.MILES
    _attr_icon = "mdi:wrench-outline"

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, service_key: str):
        super().__init__(entry)
        self.hass = hass
        self.service_key = service_key
        definition = SERVICE_CATALOG[service_key]
        self._attr_name = definition["name"]
        self._attr_icon = definition["icon"]
        self._attr_unique_id = f"{entry.entry_id}_{service_key}_miles_remaining"

    @property
    def native_value(self):
        vehicle = self.hass.data[DOMAIN][self.entry.entry_id]
        data = {**self.entry.data, **self.entry.options}
        odometer = self.hass.states.get(data[CONF_ODOMETER_ENTITY])
        if odometer is None:
            return None
        try:
            current_mileage = int(float(odometer.state))
        except (TypeError, ValueError):
            return None
        definition = SERVICE_CATALOG[self.service_key]
        if definition.get("milestone"):
            if self.service_key in vehicle.completed_milestones:
                return None
            return definition["interval"] - current_mileage
        return (
            vehicle.last_completed.get(self.service_key, 0)
            + definition["interval"]
            + vehicle.extensions.get(self.service_key, 0)
            - current_mileage
        )

    @property
    def available(self):
        vehicle = self.hass.data[DOMAIN][self.entry.entry_id]
        definition = SERVICE_CATALOG[self.service_key]
        if (
            definition.get("milestone")
            and self.service_key in vehicle.completed_milestones
        ):
            return False
        data = {**self.entry.data, **self.entry.options}
        state = self.hass.states.get(data[CONF_ODOMETER_ENTITY])
        if state is None:
            return False
        try:
            float(state.state)
        except (TypeError, ValueError):
            return False
        return True

    @property
    def extra_state_attributes(self):
        vehicle = self.hass.data[DOMAIN][self.entry.entry_id]
        definition = SERVICE_CATALOG[self.service_key]
        last = vehicle.last_completed.get(self.service_key, 0)
        extension = vehicle.extensions.get(self.service_key, 0)
        milestone = definition.get("milestone", False)
        return {
            ATTR_ENTRY_ID: self.entry.entry_id,
            ATTR_SERVICE_KEY: self.service_key,
            "service_name": definition["name"],
            "interval_miles": definition["interval"],
            "last_completed_mileage": last,
            "extension_miles": extension,
            "next_due_mileage": (
                definition["interval"]
                if milestone
                else last + definition["interval"] + extension
            ),
            "milestone": milestone,
            "completed": self.service_key in vehicle.completed_milestones,
        }

    async def async_added_to_hass(self):
        data = {**self.entry.data, **self.entry.options}
        self.async_on_remove(
            async_dispatcher_connect(self.hass, SIGNAL_UPDATE, self._handle_update)
        )
        self.async_on_remove(
            async_track_state_change_event(
                self.hass,
                [data[CONF_ODOMETER_ENTITY]],
                self._handle_odometer_update,
            )
        )

    @callback
    def _handle_update(self, entry_id):
        if entry_id == self.entry.entry_id:
            self.async_write_ha_state()

    @callback
    def _handle_odometer_update(self, event):
        self.async_write_ha_state()
