"""Sensor platform for the Arte Forecast integration."""

from __future__ import annotations

from datetime import timedelta

import voluptuous as vol

from homeassistant.components.sensor import PLATFORM_SCHEMA, SensorDeviceClass, SensorEntity
from homeassistant.const import CONF_NAME
from homeassistant.config_entries import ConfigEntry
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.core import HomeAssistant

from .const import (
    CONF_HUMIDITY_ENTITY,
    CONF_HUMIDITY_IMPACT,
    CONF_ILLUMINANCE_ENTITY,
    CONF_ILLUMINANCE_IMPACT,
    CONF_LOOKBACK_HOURS,
    CONF_MAX_THRESHOLD,
    CONF_MIN_THRESHOLD,
    CONF_PLANT_ENTITY,
    CONF_RESET_THRESHOLD,
    CONF_SOIL_MOISTURE_ENTITY,
    CONF_TEMPERATURE_ENTITY,
    CONF_TEMPERATURE_IMPACT,
    CONF_UPDATE_INTERVAL_MINUTES,
    DEFAULT_HUMIDITY_IMPACT,
    DEFAULT_LOOKBACK_HOURS,
    DEFAULT_NAME,
    DEFAULT_RESET_THRESHOLD,
    DEFAULT_TEMPERATURE_IMPACT,
    DEFAULT_ILLUMINANCE_IMPACT,
    DEFAULT_UPDATE_INTERVAL_MINUTES,
)
from .coordinator import ArteForecastCoordinator
from .entity import get_coordinator

def _validate_thresholds(config: ConfigType) -> ConfigType:
    has_explicit_thresholds = (
        config.get(CONF_MIN_THRESHOLD) is not None
        and config.get(CONF_MAX_THRESHOLD) is not None
    )
    if has_explicit_thresholds and config[CONF_MAX_THRESHOLD] <= config[CONF_MIN_THRESHOLD]:
        raise vol.Invalid("max_moisture must be greater than min_moisture")
    if not config.get(CONF_PLANT_ENTITY) and not config.get(CONF_SOIL_MOISTURE_ENTITY):
        raise vol.Invalid("soil_moisture_entity or plant_entity is required")
    if not config.get(CONF_PLANT_ENTITY) and not has_explicit_thresholds:
        raise vol.Invalid("min_moisture and max_moisture are required without plant_entity")
    return config


PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_PLANT_ENTITY): cv.entity_id,
        vol.Optional(CONF_SOIL_MOISTURE_ENTITY): cv.entity_id,
        vol.Optional(CONF_MIN_THRESHOLD): vol.Coerce(float),
        vol.Optional(CONF_MAX_THRESHOLD): vol.Coerce(float),
        vol.Optional(CONF_HUMIDITY_ENTITY): cv.entity_id,
        vol.Optional(CONF_TEMPERATURE_ENTITY): cv.entity_id,
        vol.Optional(CONF_ILLUMINANCE_ENTITY): cv.entity_id,
        vol.Optional(CONF_LOOKBACK_HOURS, default=DEFAULT_LOOKBACK_HOURS): vol.All(
            vol.Coerce(int), vol.Range(min=6, max=24 * 30)
        ),
        vol.Optional(
            CONF_UPDATE_INTERVAL_MINUTES,
            default=DEFAULT_UPDATE_INTERVAL_MINUTES,
        ): vol.All(vol.Coerce(int), vol.Range(min=5, max=24 * 60)),
        vol.Optional(CONF_RESET_THRESHOLD, default=DEFAULT_RESET_THRESHOLD): vol.All(
            vol.Coerce(float), vol.Range(min=0.1)
        ),
        vol.Optional(CONF_HUMIDITY_IMPACT, default=DEFAULT_HUMIDITY_IMPACT): vol.All(
            vol.Coerce(float), vol.Range(min=0.0, max=1.0)
        ),
        vol.Optional(
            CONF_TEMPERATURE_IMPACT,
            default=DEFAULT_TEMPERATURE_IMPACT,
        ): vol.All(vol.Coerce(float), vol.Range(min=0.0, max=1.0)),
        vol.Optional(
            CONF_ILLUMINANCE_IMPACT,
            default=DEFAULT_ILLUMINANCE_IMPACT,
        ): vol.All(vol.Coerce(float), vol.Range(min=0.0, max=1.0)),
    }
)
PLATFORM_SCHEMA = vol.All(PLATFORM_SCHEMA, _validate_thresholds)


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the forecast sensor from YAML."""

    coordinator = ArteForecastCoordinator(
        hass,
        name=config[CONF_NAME],
        plant_entity_id=config.get(CONF_PLANT_ENTITY),
        soil_moisture_entity_id=config.get(CONF_SOIL_MOISTURE_ENTITY),
        min_threshold=config.get(CONF_MIN_THRESHOLD),
        max_threshold=config.get(CONF_MAX_THRESHOLD),
        humidity_entity_id=config.get(CONF_HUMIDITY_ENTITY),
        temperature_entity_id=config.get(CONF_TEMPERATURE_ENTITY),
        illuminance_entity_id=config.get(CONF_ILLUMINANCE_ENTITY),
        lookback_hours=config[CONF_LOOKBACK_HOURS],
        reset_threshold=config[CONF_RESET_THRESHOLD],
        humidity_impact=config[CONF_HUMIDITY_IMPACT],
        temperature_impact=config[CONF_TEMPERATURE_IMPACT],
        illuminance_impact=config[CONF_ILLUMINANCE_IMPACT],
        update_interval=timedelta(minutes=config[CONF_UPDATE_INTERVAL_MINUTES]),
    )
    await coordinator.async_refresh()

    async_add_entities([ArteForecastSensor(coordinator, config[CONF_NAME])])


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the forecast timestamp sensor from a config entry."""

    coordinator = get_coordinator(hass, entry)
    async_add_entities([ArteForecastSensor(coordinator, entry.title)])


class ArteForecastSensor(CoordinatorEntity[ArteForecastCoordinator], SensorEntity):
    """Sensor that exposes the predicted next watering time."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_should_poll = False

    def __init__(self, coordinator: ArteForecastCoordinator, name: str) -> None:
        super().__init__(coordinator)
        self.coordinator = coordinator
        self._attr_name = name
        unique_source = (
            coordinator.soil_moisture_entity_id
            or coordinator.plant_entity_id
            or coordinator.name
        )
        self._attr_unique_id = f"arte_forecast_{unique_source.replace('.', '_').replace(' ', '_')}"

    @property
    def native_value(self):
        result = self.coordinator.data
        return result.predicted_at if result else None

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success and self.coordinator.data is not None

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        result = self.coordinator.data
        if result is None:
            return {}

        return {
            "status": result.status,
            "hours_until_min_moisture": result.hours_until_min,
            "current_moisture": result.current_moisture,
            "min_moisture": result.min_threshold,
            "max_moisture": result.max_threshold,
            "depletion_rate_per_hour": result.depletion_rate_per_hour,
            "average_segment_rate_per_hour": result.average_segment_rate_per_hour,
            "ambient_humidity": result.humidity,
            "ambient_temperature": result.temperature,
            "ambient_illuminance": result.illuminance,
            "samples_used": result.samples_used,
            "segments_used": result.segments_used,
            "source_entity": self.coordinator.soil_moisture_entity_id,
            "plant_entity": self.coordinator.plant_entity_id,
            "humidity_entity": self.coordinator.humidity_entity_id,
            "temperature_entity": self.coordinator.temperature_entity_id,
            "illuminance_entity": self.coordinator.illuminance_entity_id,
            "resolved_source_entity": self.coordinator.resolved_soil_moisture_entity_id,
            "resolved_humidity_entity": self.coordinator.resolved_humidity_entity_id,
            "resolved_temperature_entity": self.coordinator.resolved_temperature_entity_id,
            "resolved_illuminance_entity": self.coordinator.resolved_illuminance_entity_id,
            "resolved_min_moisture": self.coordinator.resolved_min_threshold,
            "resolved_max_moisture": self.coordinator.resolved_max_threshold,
        }
