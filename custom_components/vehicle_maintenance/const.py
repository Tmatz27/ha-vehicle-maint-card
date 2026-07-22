"""Constants and built-in catalog for Vehicle Maintenance."""

DOMAIN = "vehicle_maintenance"
PLATFORMS = ["sensor", "binary_sensor"]
CONF_VEHICLE_NAME = "vehicle_name"
CONF_ODOMETER_ENTITY = "odometer_entity"
CONF_SERVICES = "services"
CONF_INTERVALS = "intervals"
CONF_INITIAL_INTERVALS = "initial_intervals"
CONF_NOTIFY_ENABLED = "notify_enabled"
CONF_NOTIFY_SERVICE = "notify_service"
CONF_NOTIFY_THRESHOLD = "notify_threshold"
CONF_NOTIFY_WEEKDAY = "notify_weekday"
CONF_NOTIFY_TIME = "notify_time"
ATTR_ENTRY_ID = "entry_id"
ATTR_SERVICE_KEY = "service_key"
SIGNAL_UPDATE = f"{DOMAIN}_update"
DEFAULT_NOTIFICATION_THRESHOLD = 1500
DEFAULT_NOTIFICATION_WEEKDAY = "sun"
DEFAULT_NOTIFICATION_TIME = "17:00:00"
DEFAULT_UPCOMING_MILES = 2000

# Defaults follow the normal-use schedule for recent U.S.-market Subaru vehicles
# where Subaru publishes a mileage interval. Condition-based reminders are marked
# separately and remain editable per vehicle in the options flow.
SERVICE_CATALOG = {
    "oil_change": {
        "name": "Oil Change",
        "interval": 6000,
        "icon": "mdi:oil",
        "kind": "replace",
    },
    "tire_rotation": {
        "name": "Tire Rotation",
        "interval": 6000,
        "icon": "mdi:rotate-right",
        "kind": "perform",
    },
    "engine_air_filter": {
        "name": "Engine Air Filter",
        "interval": 30000,
        "icon": "mdi:air-filter",
        "kind": "replace",
    },
    "cabin_air_filter": {
        "name": "Cabin Air Filter",
        "interval": 12000,
        "icon": "mdi:air-filter",
        "kind": "replace",
    },
    "brake_fluid": {
        "name": "Brake Fluid",
        "interval": 30000,
        "icon": "mdi:car-brake-fluid-level",
        "kind": "replace",
    },
    "coolant": {
        "name": "Coolant",
        "interval": 75000,
        "initial_interval": 137500,
        "icon": "mdi:coolant-temperature",
        "kind": "replace",
    },
    "transmission_fluid": {
        "name": "CVT Fluid Inspection",
        "interval": 30000,
        "icon": "mdi:car-shift-pattern",
        "kind": "inspect",
    },
    "differential_service": {
        "name": "Differential Fluid Inspection",
        "interval": 30000,
        "icon": "mdi:car-cog",
        "kind": "inspect",
    },
    "wiper_blades": {
        "name": "Wiper Blades",
        "interval": 12000,
        "icon": "mdi:wiper",
        "kind": "condition",
    },
    "battery_check": {
        "name": "Battery Check",
        "interval": 12000,
        "icon": "mdi:car-battery",
        "kind": "condition",
    },
    "tire_replacement": {
        "name": "Tire Replacement",
        "interval": 50000,
        "icon": "mdi:tire",
        "kind": "condition",
    },
    "spark_plugs": {
        "name": "Spark Plugs",
        "interval": 60000,
        "icon": "mdi:flash",
        "kind": "replace",
    },
    "brake_pads": {
        "name": "Brake Pad Inspection",
        "interval": 12000,
        "icon": "mdi:car-brake-alert",
        "kind": "inspect",
    },
    "wheel_alignment": {
        "name": "Wheel Alignment Check",
        "interval": 12000,
        "icon": "mdi:steering",
        "kind": "condition",
    },
    "pcv_valve": {
        "name": "PCV Valve Inspection",
        "interval": 60000,
        "icon": "mdi:engine-outline",
        "kind": "inspect",
    },
    "fuel_filter": {
        "name": "Fuel Filter",
        "interval": 72000,
        "icon": "mdi:fuel",
        "kind": "replace",
    },
    "timing_inspection": {
        "name": "Timing Belt or Chain Inspection",
        "interval": 100000,
        "icon": "mdi:engine",
        "kind": "inspect",
    },
    "service_30k": {
        "name": "30,000 mi Service",
        "interval": 30000,
        "icon": "mdi:clipboard-check-outline",
        "milestone": True,
        "kind": "milestone",
    },
    "service_60k": {
        "name": "60,000 mi Service",
        "interval": 60000,
        "icon": "mdi:clipboard-check-outline",
        "milestone": True,
        "kind": "milestone",
    },
    "service_90k": {
        "name": "90,000 mi Service",
        "interval": 90000,
        "icon": "mdi:clipboard-check-outline",
        "milestone": True,
        "kind": "milestone",
    },
    "service_120k": {
        "name": "120,000 mi Service",
        "interval": 120000,
        "icon": "mdi:clipboard-check-outline",
        "milestone": True,
        "kind": "milestone",
    },
    "service_125k": {
        "name": "125,000 mi Service",
        "interval": 125000,
        "icon": "mdi:clipboard-check-outline",
        "milestone": True,
        "kind": "milestone",
    },
    "service_180k": {
        "name": "180,000 mi Service",
        "interval": 180000,
        "icon": "mdi:clipboard-check-outline",
        "milestone": True,
        "kind": "milestone",
    },
    "service_200k": {
        "name": "200,000 mi Service",
        "interval": 200000,
        "icon": "mdi:clipboard-check-outline",
        "milestone": True,
        "kind": "milestone",
    },
}

# Config-entry version 2 stored these values as defaults. Version 3 updates only
# values that still match the old defaults, preserving intentional customization.
PREVIOUS_DEFAULT_INTERVALS = {
    "coolant": 120000,
    "transmission_fluid": 60000,
    "brake_pads": 50000,
    "fuel_filter": 60000,
}

# New vehicles start with the complete built-in catalog selected. Existing vehicles
# keep their explicit selections so an update never re-enables a service the user
# intentionally disabled.
DEFAULT_SERVICES = list(SERVICE_CATALOG)
