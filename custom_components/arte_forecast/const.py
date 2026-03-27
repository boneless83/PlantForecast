"""Constants for the Arte Forecast integration."""

DOMAIN = "arte_forecast"
DEFAULT_NAME = "Plant watering forecast"
DEFAULT_LOOKBACK_HOURS = 72
DEFAULT_UPDATE_INTERVAL_MINUTES = 30
DEFAULT_RESET_THRESHOLD = 3.0
DEFAULT_HUMIDITY_IMPACT = 0.35
DEFAULT_TEMPERATURE_IMPACT = 0.30
DEFAULT_ILLUMINANCE_IMPACT = 0.20
MIN_RATE_PER_HOUR = 0.01
PLATFORMS = ["sensor", "binary_sensor"]

CONF_PLANT_ENTITY = "plant_entity"
CONF_SOIL_MOISTURE_ENTITY = "soil_moisture_entity"
CONF_HUMIDITY_ENTITY = "humidity_entity"
CONF_TEMPERATURE_ENTITY = "temperature_entity"
CONF_ILLUMINANCE_ENTITY = "illuminance_entity"
CONF_MIN_THRESHOLD = "min_moisture"
CONF_MAX_THRESHOLD = "max_moisture"
CONF_LOOKBACK_HOURS = "lookback_hours"
CONF_UPDATE_INTERVAL_MINUTES = "update_interval_minutes"
CONF_RESET_THRESHOLD = "reset_threshold"
CONF_HUMIDITY_IMPACT = "humidity_impact"
CONF_TEMPERATURE_IMPACT = "temperature_impact"
CONF_ILLUMINANCE_IMPACT = "illuminance_impact"
