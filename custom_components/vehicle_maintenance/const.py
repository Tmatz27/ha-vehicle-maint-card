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
        "why": "Fresh oil protects moving engine parts and helps prevent wear, sludge, and overheating.",
    },
    "tire_rotation": {
        "name": "Tire Rotation",
        "interval": 6000,
        "icon": "mdi:rotate-right",
        "kind": "perform",
        "why": "Rotation evens tire wear, helping tires last longer and maintain predictable handling.",
    },
    "engine_air_filter": {
        "name": "Engine Air Filter",
        "interval": 30000,
        "icon": "mdi:air-filter",
        "kind": "replace",
        "why": "A clean filter maintains engine airflow and helps keep dirt out of the engine.",
    },
    "cabin_air_filter": {
        "name": "Cabin Air Filter",
        "interval": 12000,
        "icon": "mdi:air-filter",
        "kind": "replace",
        "why": "A clean filter improves heating and cooling airflow while reducing dust and pollen in the cabin.",
    },
    "brake_fluid": {
        "name": "Brake Fluid",
        "interval": 30000,
        "icon": "mdi:car-brake-fluid-level",
        "kind": "replace",
        "why": "Fresh brake fluid resists moisture buildup and helps maintain consistent braking performance.",
    },
    "coolant": {
        "name": "Coolant",
        "interval": 75000,
        "initial_interval": 137500,
        "icon": "mdi:coolant-temperature",
        "kind": "replace",
        "why": "Coolant controls engine temperature and protects the cooling system from corrosion and freezing.",
    },
    "transmission_fluid": {
        "name": "CVT Fluid Inspection",
        "interval": 30000,
        "icon": "mdi:car-shift-pattern",
        "kind": "inspect",
        "why": "Checking fluid condition and leaks can catch problems before they cause costly transmission damage.",
    },
    "differential_service": {
        "name": "Differential Fluid Inspection",
        "interval": 30000,
        "icon": "mdi:car-cog",
        "kind": "inspect",
        "why": "Correct fluid condition and level protect differential gears and bearings from excess wear.",
    },
    "wiper_blades": {
        "name": "Wiper Blades",
        "interval": 12000,
        "icon": "mdi:wiper",
        "kind": "condition",
        "why": "Effective blades preserve visibility in rain, snow, and road spray.",
    },
    "battery_check": {
        "name": "Battery Check",
        "interval": 12000,
        "icon": "mdi:car-battery",
        "kind": "condition",
        "why": "Testing can reveal a weak battery before it leaves the vehicle unable to start.",
    },
    "tire_replacement": {
        "name": "Tire Replacement",
        "interval": 50000,
        "icon": "mdi:tire",
        "kind": "condition",
        "why": "Adequate tread supports grip, braking, and resistance to hydroplaning.",
    },
    "spark_plugs": {
        "name": "Spark Plugs",
        "interval": 60000,
        "icon": "mdi:flash",
        "kind": "replace",
        "why": "Healthy spark plugs support reliable starts, smooth running, and efficient combustion.",
    },
    "brake_pads": {
        "name": "Brake Pad Inspection",
        "interval": 12000,
        "icon": "mdi:car-brake-alert",
        "kind": "inspect",
        "why": "Checking pad thickness helps preserve braking performance and can prevent rotor damage.",
    },
    "wheel_alignment": {
        "name": "Wheel Alignment Check",
        "interval": 12000,
        "icon": "mdi:steering",
        "kind": "condition",
        "why": "Correct alignment improves straight tracking and helps prevent uneven tire wear.",
    },
    "pcv_valve": {
        "name": "PCV Valve Inspection",
        "interval": 60000,
        "icon": "mdi:engine-outline",
        "kind": "inspect",
        "why": "Proper crankcase ventilation helps control pressure, oil leaks, and sludge buildup.",
    },
    "fuel_filter": {
        "name": "Fuel Filter",
        "interval": 72000,
        "icon": "mdi:fuel",
        "kind": "replace",
        "why": "Clean fuel flow helps protect injectors and maintain reliable engine performance.",
    },
    "timing_inspection": {
        "name": "Timing Belt or Chain Inspection",
        "interval": 100000,
        "icon": "mdi:engine",
        "kind": "inspect",
        "why": "Finding wear or damage early can help prevent severe engine damage.",
    },
    "service_30k": {
        "name": "30,000 mi Service",
        "interval": 30000,
        "icon": "mdi:clipboard-check-outline",
        "milestone": True,
        "kind": "milestone",
        "why": "This mileage checkpoint helps ensure the inspections and service due around 30,000 miles are reviewed together.",
    },
    "service_60k": {
        "name": "60,000 mi Service",
        "interval": 60000,
        "icon": "mdi:clipboard-check-outline",
        "milestone": True,
        "kind": "milestone",
        "why": "This mileage checkpoint helps ensure the inspections and service due around 60,000 miles are reviewed together.",
    },
    "service_90k": {
        "name": "90,000 mi Service",
        "interval": 90000,
        "icon": "mdi:clipboard-check-outline",
        "milestone": True,
        "kind": "milestone",
        "why": "This mileage checkpoint helps ensure the inspections and service due around 90,000 miles are reviewed together.",
    },
    "service_120k": {
        "name": "120,000 mi Service",
        "interval": 120000,
        "icon": "mdi:clipboard-check-outline",
        "milestone": True,
        "kind": "milestone",
        "why": "This mileage checkpoint helps ensure the inspections and service due around 120,000 miles are reviewed together.",
    },
    "service_125k": {
        "name": "125,000 mi Service",
        "interval": 125000,
        "icon": "mdi:clipboard-check-outline",
        "milestone": True,
        "kind": "milestone",
        "why": "This mileage checkpoint helps ensure the inspections and service due around 125,000 miles are reviewed together.",
    },
    "service_180k": {
        "name": "180,000 mi Service",
        "interval": 180000,
        "icon": "mdi:clipboard-check-outline",
        "milestone": True,
        "kind": "milestone",
        "why": "This mileage checkpoint helps ensure the inspections and service due around 180,000 miles are reviewed together.",
    },
    "service_200k": {
        "name": "200,000 mi Service",
        "interval": 200000,
        "icon": "mdi:clipboard-check-outline",
        "milestone": True,
        "kind": "milestone",
        "why": "This mileage checkpoint helps ensure the inspections and service due around 200,000 miles are reviewed together.",
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
