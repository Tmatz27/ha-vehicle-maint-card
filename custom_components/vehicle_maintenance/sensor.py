"""Vehicle Maintenance sensor entities."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfLength
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import (
    ATTR_ENTRY_ID,
    ATTR_SERVICE_KEY,
    CONF_CAR_WASH_ENABLED,
    CONF_CAR_WASH_INTERVAL_DAYS,
    CONF_INITIAL_INTERVALS,
    CONF_NOTIFY_ENABLED,
    CONF_NOTIFY_MUTED_SERVICES,
    CONF_NOTIFY_TIME,
    CONF_NOTIFY_WEEKDAY,
    CONF_SERVICES,
    CONF_WASHABLE_FILTERS,
    DEFAULT_CAR_WASH_INTERVAL_DAYS,
    DEFAULT_NOTIFICATION_TIME,
    DEFAULT_NOTIFICATION_WEEKDAY,
    DEFAULT_UPCOMING_MILES,
    DOMAIN,
    SERVICE_CATALOG,
    SIGNAL_UPDATE,
    WEEKDAY_INDEX,
)
from .manager import VehicleManager
from .model import (
    car_wash_days_remaining,
    car_wash_status,
    days_since_wash,
    miles_remaining,
    next_notification_time,
    parse_clock_time,
    scheduled_due_mileage,
    service_status,
    snooze_active,
    snooze_miles_remaining,
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    manager: VehicleManager = hass.data[DOMAIN][entry.entry_id]
    entities: list[SensorEntity] = [
        EffectiveOdometerSensor(manager),
        VehicleSummarySensor(manager),
    ]
    entities += [MaintenanceSensor(manager, key) for key in manager.config[CONF_SERVICES]]
    if manager.config.get(CONF_CAR_WASH_ENABLED, False):
        entities.append(CarWashSensor(manager))
    async_add_entities(entities)


class VehicleEntity(SensorEntity):
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


class EffectiveOdometerSensor(VehicleEntity):
    _attr_name = "Effective odometer"
    _attr_icon = "mdi:road-variant"
    _attr_native_unit_of_measurement = UnitOfLength.MILES

    def __init__(self, manager: VehicleManager) -> None:
        super().__init__(manager)
        self._attr_unique_id = f"{self.entry.entry_id}_effective_odometer"

    @property
    def native_value(self) -> int | None:
        return self.manager.effective_odometer

    @property
    def available(self) -> bool:
        return self.manager.effective_odometer is not None

    @property
    def extra_state_attributes(self) -> dict:
        return {
            ATTR_ENTRY_ID: self.entry.entry_id,
            "source": self.manager.odometer_source,
            "source_entity": self.manager.config["odometer_entity"],
        }


class VehicleSummarySensor(VehicleEntity):
    _attr_name = "Maintenance"
    _attr_icon = "mdi:car-wrench"

    def __init__(self, manager: VehicleManager) -> None:
        super().__init__(manager)
        self._attr_unique_id = f"{self.entry.entry_id}_maintenance"

    def _summary(self) -> tuple[str, dict]:
        odometer = self.manager.effective_odometer
        statuses = []
        candidates = []
        deferred = 0
        for key in self.manager.config[CONF_SERVICES]:
            record = self.manager.records[key]
            definition = SERVICE_CATALOG[key]
            milestone = bool(definition.get("milestone"))
            status = service_status(
                record,
                odometer,
                milestone=milestone,
                due_soon_miles=DEFAULT_UPCOMING_MILES,
            )
            statuses.append(status)
            remaining = (
                None
                if odometer is None
                else miles_remaining(record, odometer, milestone=milestone)
            )
            deferred_active = odometer is not None and snooze_active(record, odometer)
            if remaining is not None and not deferred_active:
                candidates.append((remaining, definition["name"]))
            if deferred_active:
                deferred += 1
                if status in ("overdue", "due_soon"):
                    statuses[-1] = "deferred"
        if odometer is None:
            state = "unavailable"
        elif "overdue" in statuses:
            state = "overdue"
        elif "due_soon" in statuses:
            state = "due_soon"
        elif "setup_required" in statuses:
            state = "setup_required"
        else:
            state = "okay"
        candidates.sort()
        return state, {
            "setup_required_count": statuses.count("setup_required"),
            "overdue_count": statuses.count("overdue"),
            "due_soon_count": statuses.count("due_soon"),
            "deferred_count": deferred,
            "next_service": candidates[0][1] if candidates else None,
            "next_service_miles": candidates[0][0] if candidates else None,
        }

    def _notification_diagnostics(self) -> dict:
        """Expose delivery diagnostics so routing problems are visible."""
        config = self.manager.config
        last = self.manager.last_notification or {}
        enabled = bool(config.get(CONF_NOTIFY_ENABLED, False))
        next_summary = None
        if enabled:
            weekday = WEEKDAY_INDEX.get(
                config.get(CONF_NOTIFY_WEEKDAY, DEFAULT_NOTIFICATION_WEEKDAY), 6
            )
            scheduled = parse_clock_time(
                config.get(CONF_NOTIFY_TIME, DEFAULT_NOTIFICATION_TIME)
            )
            next_summary = next_notification_time(
                dt_util.now(), weekday, scheduled
            ).isoformat()
        return {
            "notifications_enabled": enabled,
            "notification_muted_services": list(
                config.get(CONF_NOTIFY_MUTED_SERVICES, [])
            ),
            "next_scheduled_summary": next_summary,
            "last_notification_status": last.get("status"),
            "last_notification_time": last.get("timestamp"),
            "last_notification_targets": last.get("targets"),
            "last_notification_item_count": last.get("item_count"),
            "last_notification_error": last.get("error"),
            "last_notification_was_test": last.get("test"),
        }

    @property
    def native_value(self) -> str:
        return self._summary()[0]

    @property
    def extra_state_attributes(self) -> dict:
        state, counts = self._summary()
        config = self.manager.config
        return {
            ATTR_ENTRY_ID: self.entry.entry_id,
            "integration": DOMAIN,
            "vehicle_name": self.entry.title,
            "effective_odometer": self.manager.effective_odometer,
            "odometer_source": self.manager.odometer_source,
            "status": state,
            **counts,
            "car_wash_enabled": bool(config.get(CONF_CAR_WASH_ENABLED, False)),
            **self._notification_diagnostics(),
        }


class CarWashSensor(VehicleEntity):
    """Days since the vehicle was last washed.

    Washing is tracked by date rather than mileage because weather, road salt,
    and pollen drive it far more than distance driven.
    """

    _attr_name = "Car wash"
    _attr_icon = "mdi:car-wash"
    _attr_native_unit_of_measurement = "days"

    def __init__(self, manager: VehicleManager) -> None:
        super().__init__(manager)
        self._attr_unique_id = f"{self.entry.entry_id}_car_wash"

    def _interval_days(self) -> int:
        return int(
            self.manager.config.get(
                CONF_CAR_WASH_INTERVAL_DAYS, DEFAULT_CAR_WASH_INTERVAL_DAYS
            )
        )

    @property
    def native_value(self) -> int | None:
        return days_since_wash(self.manager.car_wash, dt_util.now().date())

    @property
    def extra_state_attributes(self) -> dict:
        today = dt_util.now().date()
        record = self.manager.car_wash
        interval = self._interval_days()
        return {
            ATTR_ENTRY_ID: self.entry.entry_id,
            "car_wash": True,
            "status": car_wash_status(record, today, interval),
            "interval_days": interval,
            "days_since_wash": days_since_wash(record, today),
            "days_remaining": car_wash_days_remaining(record, today, interval),
            "last_washed_date": record.last_washed_date,
            "wash_count": record.wash_count,
        }


class MaintenanceSensor(VehicleEntity):
    _attr_native_unit_of_measurement = UnitOfLength.MILES

    def __init__(self, manager: VehicleManager, service_key: str) -> None:
        super().__init__(manager)
        self.service_key = service_key
        definition = SERVICE_CATALOG[service_key]
        self._attr_name = definition["name"]
        self._attr_icon = definition["icon"]
        self._attr_unique_id = f"{self.entry.entry_id}_{service_key}_miles_remaining"

    @property
    def native_value(self) -> int | None:
        odometer = self.manager.effective_odometer
        if odometer is None:
            return None
        return miles_remaining(
            self.manager.records[self.service_key],
            odometer,
            milestone=bool(SERVICE_CATALOG[self.service_key].get("milestone")),
        )

    @property
    def extra_state_attributes(self) -> dict:
        record = self.manager.records[self.service_key]
        definition = SERVICE_CATALOG[self.service_key]
        odometer = self.manager.effective_odometer
        milestone = bool(definition.get("milestone"))
        remaining = (
            None
            if odometer is None
            else miles_remaining(record, odometer, milestone=milestone)
        )
        washable = self.service_key in self.manager.config.get(
            CONF_WASHABLE_FILTERS, []
        )
        filter_miles = (
            None
            if not washable
            or odometer is None
            or record.filter_installed_mileage is None
            else max(0, odometer - record.filter_installed_mileage)
        )
        return {
            ATTR_ENTRY_ID: self.entry.entry_id,
            ATTR_SERVICE_KEY: self.service_key,
            "service_name": definition["name"],
            "why_it_matters": definition["why"],
            "maintenance_type": definition.get("kind", "service"),
            "interval_miles": record.interval_miles,
            "initial_interval_miles": self.manager.config.get(
                CONF_INITIAL_INTERVALS, {}
            ).get(self.service_key, definition.get("initial_interval")),
            "initialized": record.initialized,
            "status": service_status(
                record,
                odometer,
                milestone=milestone,
                due_soon_miles=DEFAULT_UPCOMING_MILES,
            ),
            "last_completed_mileage": record.last_completed_mileage,
            "due_mileage_override": record.due_mileage_override,
            "scheduled_due_mileage": scheduled_due_mileage(record, milestone=milestone),
            "miles_remaining": remaining,
            "snoozed_until_mileage": record.snoozed_until_mileage,
            "snooze_miles_remaining": None
            if odometer is None
            else snooze_miles_remaining(record, odometer),
            "deferred": False if odometer is None else snooze_active(record, odometer),
            "milestone": milestone,
            "milestone_completed": record.milestone_completed,
            "milestone_completed_mileage": record.milestone_completed_mileage,
            "washable": washable,
            "wash_count": record.wash_count if washable else None,
            "filter_installed_mileage": (
                record.filter_installed_mileage if washable else None
            ),
            "last_washed_mileage": (
                record.last_washed_mileage if washable else None
            ),
            "last_filter_action": record.last_filter_action if washable else None,
            "filter_miles": filter_miles,
        }
