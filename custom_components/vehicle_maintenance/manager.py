"""Per-vehicle state, odometer coordination, and persistence."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.storage import Store

from .const import (
    CONF_INTERVALS,
    CONF_ODOMETER_ENTITY,
    CONF_SERVICES,
    DOMAIN,
    SERVICE_CATALOG,
    SIGNAL_UPDATE,
)
from .model import ServiceRecord, accepted_odometer, migrate_v1_data

STORAGE_VERSION = 2


@dataclass
class VehicleManager:
    """One coordinator and one source listener for a configured vehicle."""

    hass: HomeAssistant
    entry: ConfigEntry
    records: dict[str, ServiceRecord] = field(default_factory=dict)
    cached_odometer: int | None = None
    odometer_source: str = "unavailable"

    def __post_init__(self) -> None:
        self.store = Store(
            self.hass,
            STORAGE_VERSION,
            f"{DOMAIN}.{self.entry.entry_id}",
            async_migrate_func=self._async_migrate,
        )
        self._unsub_odometer = None

    async def _async_migrate(
        self, old_major_version: int, old_minor_version: int, old_data: dict[str, Any]
    ) -> dict[str, Any]:
        if old_major_version == 1:
            return migrate_v1_data(old_data, SERVICE_CATALOG)
        return old_data

    @property
    def config(self) -> dict[str, Any]:
        return {**self.entry.data, **self.entry.options}

    @property
    def effective_odometer(self) -> int | None:
        return self.cached_odometer

    async def async_load(self) -> None:
        stored = await self.store.async_load() or {}
        self.cached_odometer = stored.get("cached_odometer")
        self.records = {
            key: ServiceRecord.from_dict(value)
            for key, value in stored.get("services", {}).items()
        }
        self._ensure_selected_records()
        await self.async_refresh_odometer(save=True)

    def _ensure_selected_records(self) -> None:
        intervals = self.config.get(CONF_INTERVALS, {})
        for key in self.config[CONF_SERVICES]:
            definition = SERVICE_CATALOG[key]
            record = self.records.setdefault(key, ServiceRecord())
            record.interval_miles = int(
                intervals.get(key, definition.get("interval", 0))
            )

    async def async_start(self) -> None:
        if self._unsub_odometer is not None:
            return
        source = self.config[CONF_ODOMETER_ENTITY]
        self._unsub_odometer = async_track_state_change_event(
            self.hass, [source], self._handle_odometer_event
        )

    async def async_stop(self) -> None:
        if self._unsub_odometer:
            self._unsub_odometer()
            self._unsub_odometer = None

    @callback
    def _handle_odometer_event(self, event) -> None:
        self.hass.async_create_task(self.async_refresh_odometer())

    async def async_refresh_odometer(self, *, save: bool = True) -> bool:
        state = self.hass.states.get(self.config[CONF_ODOMETER_ENTITY])
        try:
            value = int(float(state.state)) if state is not None else None
        except (TypeError, ValueError):
            value = None
        accepted = accepted_odometer(self.cached_odometer, value)
        if accepted is None or accepted != value:
            self.odometer_source = (
                "cached" if self.cached_odometer is not None else "unavailable"
            )
            self.async_update_listeners()
            return False
        changed = accepted != self.cached_odometer
        self.cached_odometer = accepted
        self.odometer_source = "live"
        if changed and save:
            await self.async_save()
        else:
            self.async_update_listeners()
        return True

    async def async_set_odometer(
        self, mileage: int, *, allow_decrease: bool = False
    ) -> None:
        if mileage < 0:
            raise ValueError("Mileage cannot be negative")
        if (
            self.cached_odometer is not None
            and mileage < self.cached_odometer
            and not allow_decrease
        ):
            raise ValueError("Decreasing mileage requires explicit confirmation")
        self.cached_odometer = mileage
        self.odometer_source = "manual"
        await self.async_save()

    async def async_save(self) -> None:
        await self.store.async_save(
            {
                "cached_odometer": self.cached_odometer,
                "services": {
                    key: record.as_dict() for key, record in self.records.items()
                },
            }
        )
        self.async_update_listeners()

    @callback
    def async_update_listeners(self) -> None:
        async_dispatcher_send(self.hass, SIGNAL_UPDATE, self.entry.entry_id)
