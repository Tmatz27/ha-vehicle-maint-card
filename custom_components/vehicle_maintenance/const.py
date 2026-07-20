"""Constants for Vehicle Maintenance."""

DOMAIN = "vehicle_maintenance"
PLATFORMS = ["sensor"]
CONF_ODOMETER_ENTITY = "odometer_entity"
CONF_SERVICES = "services"
CONF_VEHICLE_NAME = "vehicle_name"
CONF_NOTIFY_SERVICE = "notify_service"
CONF_NOTIFY_THRESHOLD = "notify_threshold"
ATTR_ENTRY_ID = "entry_id"
ATTR_SERVICE_KEY = "service_key"
SIGNAL_UPDATE = f"{DOMAIN}_update"

SERVICE_CATALOG = {
    "oil_change": {"name": "Oil Change", "interval": 6000, "icon": "mdi:oil"},
    "tire_rotation": {
        "name": "Tire Rotation",
        "interval": 6000,
        "icon": "mdi:rotate-right",
    },
    "engine_air_filter": {
        "name": "Engine Air Filter",
        "interval": 30000,
        "icon": "mdi:air-filter",
    },
    "cabin_air_filter": {
        "name": "Cabin Air Filter",
        "interval": 12000,
        "icon": "mdi:air-filter",
    },
    "brake_fluid": {
        "name": "Brake Fluid",
        "interval": 30000,
        "icon": "mdi:car-brake-fluid-level",
    },
    "coolant": {
        "name": "Coolant",
        "interval": 120000,
        "icon": "mdi:coolant-temperature",
    },
    "transmission_fluid": {
        "name": "Transmission Fluid",
        "interval": 60000,
        "icon": "mdi:car-shift-pattern",
    },
    "differential_service": {
        "name": "Differential Service",
        "interval": 30000,
        "icon": "mdi:car-cog",
    },
    "wiper_blades": {"name": "Wiper Blades", "interval": 12000, "icon": "mdi:wiper"},
    "battery_check": {
        "name": "Battery Check",
        "interval": 12000,
        "icon": "mdi:car-battery",
    },
    "tire_replacement": {
        "name": "Tire Replacement",
        "interval": 50000,
        "icon": "mdi:tire",
    },
    "spark_plugs": {"name": "Spark Plugs", "interval": 60000, "icon": "mdi:spark-plug"},
    "service_30k": {
        "name": "30,000 mi Service",
        "interval": 30000,
        "icon": "mdi:clipboard-check-outline",
        "milestone": True,
    },
    "service_60k": {
        "name": "60,000 mi Service",
        "interval": 60000,
        "icon": "mdi:clipboard-check-outline",
        "milestone": True,
    },
    "service_90k": {
        "name": "90,000 mi Service",
        "interval": 90000,
        "icon": "mdi:clipboard-check-outline",
        "milestone": True,
    },
    "service_120k": {
        "name": "120,000 mi Service",
        "interval": 120000,
        "icon": "mdi:clipboard-check-outline",
        "milestone": True,
    },
    "service_125k": {
        "name": "125,000 mi Service",
        "interval": 125000,
        "icon": "mdi:clipboard-check-outline",
        "milestone": True,
    },
    "service_180k": {
        "name": "180,000 mi Service",
        "interval": 180000,
        "icon": "mdi:clipboard-check-outline",
        "milestone": True,
    },
    "service_200k": {
        "name": "200,000 mi Service",
        "interval": 200000,
        "icon": "mdi:clipboard-check-outline",
        "milestone": True,
    },
}
