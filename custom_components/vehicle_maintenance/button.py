"""One-tap Vehicle Maintenance buttons."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import CONF_CAR_WASH_ENABLED, DOMAIN, SIGNAL_UPDATE
from .manager import VehicleManager


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    manager: VehicleManager = hass.data[DOMAIN][entry.entry_id]
    entities: list[ButtonEntity] = [SendTestNotificationButton(manager)]
    if manager.config.get(CONF_CAR_WASH_ENABLED, False):
        entities.append(LogCarWashButton(manager))
    async_add_entities(entities)


class VehicleButton(ButtonEntity):
    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, manager: VehicleManager) -> None:
        self.manager = manager
        self.entry = manager.entry
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self.entry.entry_id)},
            name=self.entry.title,
            manufacturer="Vehicle Maintenance",
        )

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_dispatcher_connect(self.hass, SIGNAL_UPDATE, self._handle_update)
        )

    @callback
    def _handle_update(self, entry_id: str) -> None:
        if entry_id == self.entry.entry_id:
            self.async_write_ha_state()


class SendTestNotificationButton(VehicleButton):
    """Confirm notification routing without waiting for the weekly summary."""

    _attr_name = "Send test notification"
    _attr_icon = "mdi:message-alert-outline"
    _attr_entity_category = None

    def __init__(self, manager: VehicleManager) -> None:
        super().__init__(manager)
        self._attr_unique_id = f"{self.entry.entry_id}_send_test_notification"

    async def async_press(self) -> None:
        # Imported here so the platform never depends on package import order.
        from . import _async_run_notification

        await _async_run_notification(self.hass, self.manager, test=True)

    @property
    def extra_state_attributes(self) -> dict:
        last = self.manager.last_notification or {}
        return {
            "last_notification_status": last.get("status"),
            "last_notification_time": last.get("timestamp"),
            "last_notification_targets": last.get("targets"),
            "last_notification_error": last.get("error"),
        }


class LogCarWashButton(VehicleButton):
    """Record a wash today without opening the dashboard card."""

    _attr_name = "Log car wash"
    _attr_icon = "mdi:car-wash"

    def __init__(self, manager: VehicleManager) -> None:
        super().__init__(manager)
        self._attr_unique_id = f"{self.entry.entry_id}_log_car_wash"

    async def async_press(self) -> None:
        await self.manager.async_log_car_wash(dt_util.now().date())
