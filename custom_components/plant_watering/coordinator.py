"""Coordinator for Plant Watering Forecast."""

from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.components.recorder import get_instance, history
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import (
    CONF_HUMIDITY_ENTITY,
    CONF_HUMIDITY_FACTOR,
    CONF_LOOKBACK_HOURS,
    CONF_MAX_MOISTURE,
    CONF_MIN_MOISTURE,
    CONF_PLANT_NAME,
    CONF_SOIL_MOISTURE_ENTITY,
    CONF_TEMPERATURE_ENTITY,
    CONF_TEMPERATURE_FACTOR,
    CONF_WATERING_JUMP,
    DEFAULT_UPDATE_MINUTES,
)
from .forecast import ForecastResult, MoistureSample, calculate_forecast

_LOGGER = logging.getLogger(__name__)


class PlantWateringCoordinator(DataUpdateCoordinator[ForecastResult]):
    """Load history and compute watering forecast."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.entry = entry
        self.config = {**entry.data, **entry.options}
        super().__init__(
            hass,
            _LOGGER,
            name=self.config[CONF_PLANT_NAME],
            update_interval=timedelta(minutes=DEFAULT_UPDATE_MINUTES),
        )

    async def _async_update_data(self) -> ForecastResult:
        soil_entity = self.config[CONF_SOIL_MOISTURE_ENTITY]
        now = dt_util.utcnow()
        start = now - timedelta(hours=self.config[CONF_LOOKBACK_HOURS])

        try:
            samples = await self._async_load_history(soil_entity, start, now)
        except Exception as err:
            raise UpdateFailed(f"Unable to load soil moisture history: {err}") from err

        current_moisture = _read_float_state(self.hass, soil_entity)
        humidity = _read_float_state(self.hass, self.config.get(CONF_HUMIDITY_ENTITY))
        temperature = _read_float_state(self.hass, self.config.get(CONF_TEMPERATURE_ENTITY))

        return calculate_forecast(
            now=now,
            samples=samples,
            current_moisture=current_moisture,
            min_moisture=self.config[CONF_MIN_MOISTURE],
            max_moisture=self.config[CONF_MAX_MOISTURE],
            humidity=humidity,
            temperature=temperature,
            lookback_hours=self.config[CONF_LOOKBACK_HOURS],
            watering_jump=self.config[CONF_WATERING_JUMP],
            temperature_factor=self.config[CONF_TEMPERATURE_FACTOR],
            humidity_factor=self.config[CONF_HUMIDITY_FACTOR],
        )

    async def _async_load_history(self, entity_id: str, start, end) -> list[MoistureSample]:
        """Load moisture history from recorder."""

        def _fetch() -> list[MoistureSample]:
            history_map = history.state_changes_during_period(
                self.hass,
                start_time=start,
                end_time=end,
                entity_id=entity_id,
                include_start_time_state=True,
                no_attributes=True,
            )
            states = history_map.get(entity_id, [])
            samples: list[MoistureSample] = []
            for state in states:
                value = _parse_float(state.state)
                if value is None:
                    continue
                samples.append(
                    MoistureSample(
                        observed_at=state.last_updated or state.last_changed or start,
                        value=value,
                    )
                )
            return samples

        return await get_instance(self.hass).async_add_executor_job(_fetch)


def _read_float_state(hass: HomeAssistant, entity_id: str | None) -> float | None:
    if not entity_id:
        return None
    state = hass.states.get(entity_id)
    if state is None:
        return None
    return _parse_float(state.state)


def _parse_float(value: str | None) -> float | None:
    if value in (None, "unknown", "unavailable"):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
