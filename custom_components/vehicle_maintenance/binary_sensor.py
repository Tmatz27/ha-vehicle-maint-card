"""Automation-friendly maintenance due binary sensor."""

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_SERVICES,
    DEFAULT_UPCOMING_MILES,
    DOMAIN,
    SERVICE_CATALOG,
    SIGNAL_UPDATE,
)
from .manager import VehicleManager
from .model import miles_remaining, snooze_active


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities([MaintenanceDueBinarySensor(hass.data[DOMAIN][entry.entry_id])])


class MaintenanceDueBinarySensor(BinarySensorEntity):
    _attr_has_entity_name = True
    _attr_name = "Maintenance due"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_icon = "mdi:car-wrench"

    def __init__(self, manager: VehicleManager) -> None:
        self.manager = manager
        self._attr_unique_id = f"{manager.entry.entry_id}_maintenance_due"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, manager.entry.entry_id)},
            name=manager.entry.title,
            manufacturer="Vehicle Maintenance",
        )

    @property
    def is_on(self) -> bool:
        odometer = self.manager.effective_odometer
        if odometer is None:
            return False
        for key in self.manager.config[CONF_SERVICES]:
            record = self.manager.records[key]
            if not record.initialized or snooze_active(record, odometer):
                continue
            remaining = miles_remaining(
                record, odometer, milestone=bool(SERVICE_CATALOG[key].get("milestone"))
            )
            if remaining is not None and remaining <= DEFAULT_UPCOMING_MILES:
                return True
        return False

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_dispatcher_connect(self.hass, SIGNAL_UPDATE, self._handle_update)
        )

    @callback
    def _handle_update(self, entry_id: str) -> None:
        if entry_id == self.manager.entry.entry_id:
            self.async_write_ha_state()
