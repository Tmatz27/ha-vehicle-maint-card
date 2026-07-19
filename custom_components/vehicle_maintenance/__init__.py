"""Vehicle Maintenance integration."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.storage import Store
from homeassistant.components.http import StaticPathConfig

from .const import ATTR_ENTRY_ID, DOMAIN, PLATFORMS, SIGNAL_UPDATE

STORAGE_VERSION = 1
CARD_URL = "/vehicle-maintenance/vehicle-maint-card.js"


@dataclass
class VehicleData:
    """Persistent maintenance values for one vehicle."""

    hass: HomeAssistant
    entry: ConfigEntry
    last_completed: dict[str, int] = field(default_factory=dict)
    extensions: dict[str, int] = field(default_factory=dict)

    def __post_init__(self):
        self.store = Store(
            self.hass, STORAGE_VERSION, f"{DOMAIN}.{self.entry.entry_id}"
        )

    async def async_load(self):
        stored = await self.store.async_load() or {}
        self.last_completed = stored.get("last_completed", {})
        self.extensions = stored.get("extensions", {})

    async def async_save(self):
        await self.store.async_save(
            {
                "last_completed": self.last_completed,
                "extensions": self.extensions,
            }
        )
        async_dispatcher_send(self.hass, SIGNAL_UPDATE, self.entry.entry_id)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Register frontend path and integration services."""
    card_path = Path(__file__).parent / "www" / "vehicle-maint-card.js"
    await hass.http.async_register_static_paths(
        [StaticPathConfig(CARD_URL, str(card_path), True)]
    )

    async def find_vehicle(call: ServiceCall) -> VehicleData:
        entry_id = call.data[ATTR_ENTRY_ID]
        vehicle = hass.data[DOMAIN].get(entry_id)
        if vehicle is None:
            raise vol.Invalid(f"Unknown vehicle entry: {entry_id}")
        return vehicle

    async def log_service(call: ServiceCall):
        vehicle = await find_vehicle(call)
        odometer_entity = {**vehicle.entry.data, **vehicle.entry.options}["odometer_entity"]
        odometer_state = hass.states.get(odometer_entity)
        if odometer_state is None:
            raise vol.Invalid("The configured odometer is unavailable")
        vehicle.last_completed[call.data["service"]] = int(float(odometer_state.state))
        vehicle.extensions[call.data["service"]] = 0
        await vehicle.async_save()

    async def extend_service(call: ServiceCall):
        vehicle = await find_vehicle(call)
        key = call.data["service"]
        vehicle.extensions[key] = vehicle.extensions.get(key, 0) + call.data["miles"]
        await vehicle.async_save()

    common = {vol.Required(ATTR_ENTRY_ID): cv.string, vol.Required("service"): cv.string}
    hass.services.async_register(
        DOMAIN, "log_maintenance", log_service, schema=vol.Schema(common)
    )
    hass.services.async_register(
        DOMAIN,
        "extend_maintenance",
        extend_service,
        schema=vol.Schema({**common, vol.Required("miles"): vol.Coerce(int)}),
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Create a configured vehicle."""
    hass.data.setdefault(DOMAIN, {})
    vehicle = VehicleData(hass, entry)
    await vehicle.async_load()
    hass.data[DOMAIN][entry.entry_id] = vehicle
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a vehicle."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unloaded


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Reload after options change."""
    await hass.config_entries.async_reload(entry.entry_id)
