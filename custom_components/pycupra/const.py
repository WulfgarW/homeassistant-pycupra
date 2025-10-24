from datetime import timedelta

DOMAIN = "pycupra"
DATA_KEY = DOMAIN

# Configuration definitions
DEFAULT_DEBUG = False
CONF_MUTABLE = "mutable"
CONF_BRAND = "brand"
CONF_SPIN = "spin"
CONF_SCANDINAVIAN_MILES = "scandinavian_miles"
CONF_IMPERIAL_UNITS = "imperial_units"
CONF_NO_CONVERSION = "no_conversion"
CONF_CONVERT = "convert"
CONF_VEHICLE = "vehicle"
CONF_INSTRUMENTS = "instruments"
CONF_DEBUG = "debug"
CONF_NIGHTLY_UPDATE_REDUCTION = "nightly_update_reduction"
CONF_FIREBASE = "use_push_notifications"

# Service definitions
SERVICE_SET_SCHEDULE = "set_departure_schedule"
SERVICE_SET_DEPARTURE_PROFILE_SCHEDULE = "set_departure_profile_schedule"
SERVICE_SET_MAX_CURRENT = "set_charger_max_current"
SERVICE_SET_TARGET_SOC = "set_charger_target_soc"
SERVICE_SEND_DESTINATION = "send_destination"
SERVICE_SET_CHARGE_LIMIT = "set_charge_limit"
SERVICE_SET_CLIMATER = "set_climater"
SERVICE_SET_PHEATER_DURATION = "set_pheater_duration"

UPDATE_CALLBACK = "update_callback"
DATA = "data"
UNDO_UPDATE_LISTENER = "undo_update_listener"

SIGNAL_STATE_UPDATED = f"{DOMAIN}.updated"

MIN_SCAN_INTERVAL = 120
DEFAULT_SCAN_INTERVAL = 600

CONVERT_DICT = {
    CONF_NO_CONVERSION: "No conversion",
    CONF_IMPERIAL_UNITS: "Imperial units",
    CONF_SCANDINAVIAN_MILES: "km to mil",
}

PLATFORMS = {
    "sensor": "sensor",
    "binary_sensor": "binary_sensor",
    "lock": "lock",
    "device_tracker": "device_tracker",
    "switch": "switch",
    "climate": "climate",
    "button": "button",
    "event": "event",
}

BUTTON_INSTRUMENTS = {"refresh_data", "update_data"}

SIGNAL_FIREBASE_EVENT = f"{DOMAIN}.firebase_event"

FIREBASE_KNOWN_TYPES = {
    "vehicle-access-locked-successful",
    "vehicle-access-unlocked-successful",
    "departure-times-updated",
    "departure-profiles-updated",
    "charging-status-changed",
    "charging-started",
    "charging-stopped",
    "charging-settings-updated",
    "climatisation-status-changed",
    "climatisation-started",
    "climatisation-stopped",
    "climatisation-settings-updated",
    "climatisation-error-fail",
    "vehicle-area-alarm-vehicle-exits-zone-triggered",
    "vehicle-area-alarm-vehicle-enters-zone-triggered",
    "vehicle-wake-up-succeeded",
    "vehicle-wakeup-succeeded",
    "vehicle-honk-and-flash-started",
    "vehicle-area-alert-added",
    "vehicle-area-alert-updated",
}

