"""Shared entity helpers for Arte Forecast."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
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
    DOMAIN,
)
from .coordinator import ArteForecastCoordinator


def build_coordinator(hass: HomeAssistant, entry: ConfigEntry) -> ArteForecastCoordinator:
    """Create a coordinator from config-entry data."""

    config = {**entry.data, **entry.options}
    return ArteForecastCoordinator(
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
        update_interval=_minutes_to_timedelta(config[CONF_UPDATE_INTERVAL_MINUTES]),
    )


def _minutes_to_timedelta(minutes: int):
    from datetime import timedelta

    return timedelta(minutes=minutes)


def get_coordinator(hass: HomeAssistant, entry: ConfigEntry) -> ArteForecastCoordinator:
    """Return the shared coordinator for a config entry."""

    return hass.data[DOMAIN][entry.entry_id]
