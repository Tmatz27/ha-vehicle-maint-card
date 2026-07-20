"""Vehicle Maintenance integration."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.components.frontend import add_extra_js_url
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.storage import Store
from homeassistant.helpers.event import async_track_time_change
from homeassistant.components.http import StaticPathConfig

from .const import (
    ATTR_ENTRY_ID,
    CONF_NOTIFY_SERVICE,
    CONF_NOTIFY_THRESHOLD,
    CONF_ODOMETER_ENTITY,
    CONF_SERVICES,
    DOMAIN,
    PLATFORMS,
    SERVICE_CATALOG,
    SIGNAL_UPDATE,
)

STORAGE_VERSION = 1
CARD_URL = "/vehicle-maintenance/vehicle-maint-card.js"
CARD_RESOURCE_URL = f"{CARD_URL}?v=0.0.7"


@dataclass
class VehicleData:
    """Persistent maintenance values for one vehicle."""

    hass: HomeAssistant
    entry: ConfigEntry
    last_completed: dict[str, int] = field(default_factory=dict)
    extensions: dict[str, int] = field(default_factory=dict)
    completed_milestones: set[str] = field(default_factory=set)

    def __post_init__(self):
        self.store = Store(
            self.hass, STORAGE_VERSION, f"{DOMAIN}.{self.entry.entry_id}"
        )

    async def async_load(self):
        stored = await self.store.async_load() or {}
        self.last_completed = stored.get("last_completed", {})
        self.extensions = stored.get("extensions", {})
        self.completed_milestones = set(stored.get("completed_milestones", []))

    async def async_save(self):
        await self.store.async_save(
            {
                "last_completed": self.last_completed,
                "extensions": self.extensions,
                "completed_milestones": sorted(self.completed_milestones),
            }
        )
        async_dispatcher_send(self.hass, SIGNAL_UPDATE, self.entry.entry_id)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Register frontend path and integration services."""
    card_path = Path(__file__).parent / "www" / "vehicle-maint-card.js"
    await hass.http.async_register_static_paths(
        [StaticPathConfig(CARD_URL, str(card_path), False)]
    )

    # Load the card through Home Assistant's frontend integration instead of
    # modifying Lovelace storage. This works for storage- and YAML-mode dashboards
    # and makes the visual card/editor available as soon as the frontend loads.
    add_extra_js_url(hass, CARD_RESOURCE_URL)

    async def find_vehicle(call: ServiceCall) -> VehicleData:
        entry_id = call.data[ATTR_ENTRY_ID]
        vehicle = hass.data[DOMAIN].get(entry_id)
        if vehicle is None:
            raise vol.Invalid(f"Unknown vehicle entry: {entry_id}")
        return vehicle

    async def log_service(call: ServiceCall):
        vehicle = await find_vehicle(call)
        key = call.data["service"]
        definition = SERVICE_CATALOG[key]
        odometer_entity = {**vehicle.entry.data, **vehicle.entry.options}[
            "odometer_entity"
        ]
        odometer_state = hass.states.get(odometer_entity)
        if odometer_state is None:
            raise vol.Invalid("The configured odometer is unavailable")
        if definition.get("milestone"):
            vehicle.completed_milestones.add(key)
        else:
            vehicle.last_completed[key] = int(float(odometer_state.state))
            vehicle.extensions[key] = 0
        await vehicle.async_save()

    async def extend_service(call: ServiceCall):
        vehicle = await find_vehicle(call)
        key = call.data["service"]
        if SERVICE_CATALOG[key].get("milestone"):
            raise vol.Invalid("Milestone services cannot be extended")
        vehicle.extensions[key] = vehicle.extensions.get(key, 0) + call.data["miles"]
        await vehicle.async_save()

    async def set_service(call: ServiceCall):
        vehicle = await find_vehicle(call)
        key = call.data["service"]
        mode = call.data["mode"]
        mileage = call.data.get("mileage", 0)
        definition = SERVICE_CATALOG[key]
        if definition.get("milestone"):
            if mode == "never_performed":
                vehicle.completed_milestones.discard(key)
            elif mode == "last_completed":
                vehicle.completed_milestones.add(key)
            else:
                raise vol.Invalid("A milestone can only be reset or completed")
        elif mode == "last_completed":
            vehicle.last_completed[key] = mileage
            vehicle.extensions[key] = 0
        elif mode == "due_at":
            baseline = max(0, mileage - definition["interval"])
            vehicle.last_completed[key] = baseline
            vehicle.extensions[key] = mileage - baseline - definition["interval"]
        elif mode == "never_performed":
            vehicle.last_completed[key] = 0
            vehicle.extensions[key] = 0
        await vehicle.async_save()

    common = {
        vol.Required(ATTR_ENTRY_ID): cv.string,
        vol.Required("service"): vol.In(SERVICE_CATALOG),
    }
    hass.services.async_register(
        DOMAIN, "log_maintenance", log_service, schema=vol.Schema(common)
    )
    hass.services.async_register(
        DOMAIN,
        "set_maintenance",
        set_service,
        schema=vol.Schema(
            {
                **common,
                vol.Required("mode"): vol.In(
                    ["last_completed", "due_at", "never_performed"]
                ),
                vol.Optional("mileage", default=0): vol.Coerce(int),
            }
        ),
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

    @callback
    def schedule_notification(now):
        if now.weekday() != 6:
            return
        hass.async_create_task(_async_send_maintenance_notification(hass, vehicle))

    entry.async_on_unload(
        async_track_time_change(
            hass, schedule_notification, hour=17, minute=0, second=0
        )
    )
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


async def _async_send_maintenance_notification(
    hass: HomeAssistant, vehicle: VehicleData
) -> None:
    """Send the optional weekly summary using the configured notify service."""
    data = {**vehicle.entry.data, **vehicle.entry.options}
    notify_service = data.get(CONF_NOTIFY_SERVICE, "").strip()
    if not notify_service:
        return
    threshold = int(data.get(CONF_NOTIFY_THRESHOLD, 1500))
    odometer_state = hass.states.get(data[CONF_ODOMETER_ENTITY])
    if odometer_state is None:
        return
    odometer = int(float(odometer_state.state))
    due = []
    for key in data[CONF_SERVICES]:
        definition = SERVICE_CATALOG[key]
        if definition.get("milestone") and key in vehicle.completed_milestones:
            continue
        remaining = (
            definition["interval"] - odometer
            if definition.get("milestone")
            else vehicle.last_completed.get(key, 0)
            + definition["interval"]
            + vehicle.extensions.get(key, 0)
            - odometer
        )
        if remaining <= threshold:
            due.append((remaining, definition["name"]))
    if not due:
        return
    due.sort()
    lines = [
        f"- {name}: {abs(miles):,} mi overdue"
        if miles < 0
        else f"- {name}: {miles:,} mi remaining"
        for miles, name in due
    ]
    domain, service = notify_service.split(".", 1)
    await hass.services.async_call(
        domain,
        service,
        {
            "title": f"{vehicle.entry.title} maintenance",
            "message": "\n".join(lines),
        },
        blocking=False,
    )
