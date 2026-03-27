"""Coordinator for reading Home Assistant history and computing a forecast."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timedelta
import logging
from typing import Any

from homeassistant.components.recorder import get_instance, history
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .forecast import ForecastResult, Sample, calculate_forecast
from .plant_helpers import (
    PLANT_HUMIDITY_ENTITY_KEYS,
    PLANT_ILLUMINANCE_ENTITY_KEYS,
    PLANT_MAX_KEYS,
    PLANT_MIN_KEYS,
    PLANT_SOIL_ENTITY_KEYS,
    PLANT_TEMPERATURE_ENTITY_KEYS,
    resolve_entity_reference,
    resolve_float_value,
)

_LOGGER = logging.getLogger(__name__)


class ArteForecastCoordinator(DataUpdateCoordinator[ForecastResult]):
    """Periodically compute the next watering forecast for one plant."""

    def __init__(
        self,
        hass: HomeAssistant,
        *,
        name: str,
        plant_entity_id: str | None,
        soil_moisture_entity_id: str | None,
        min_threshold: float | None,
        max_threshold: float | None,
        humidity_entity_id: str | None,
        temperature_entity_id: str | None,
        illuminance_entity_id: str | None,
        lookback_hours: int,
        reset_threshold: float,
        humidity_impact: float,
        temperature_impact: float,
        illuminance_impact: float,
        update_interval: timedelta,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=name,
            update_interval=update_interval,
        )
        self.plant_entity_id = plant_entity_id
        self.soil_moisture_entity_id = soil_moisture_entity_id
        self.humidity_entity_id = humidity_entity_id
        self.temperature_entity_id = temperature_entity_id
        self.illuminance_entity_id = illuminance_entity_id
        self.min_threshold = min_threshold
        self.max_threshold = max_threshold
        self.lookback_hours = lookback_hours
        self.reset_threshold = reset_threshold
        self.humidity_impact = humidity_impact
        self.temperature_impact = temperature_impact
        self.illuminance_impact = illuminance_impact
        self.resolved_soil_moisture_entity_id: str | None = soil_moisture_entity_id
        self.resolved_humidity_entity_id: str | None = humidity_entity_id
        self.resolved_temperature_entity_id: str | None = temperature_entity_id
        self.resolved_illuminance_entity_id: str | None = illuminance_entity_id
        self.resolved_min_threshold: float | None = min_threshold
        self.resolved_max_threshold: float | None = max_threshold

    async def _async_update_data(self) -> ForecastResult:
        now = dt_util.utcnow()
        plant_attributes = _read_attributes(self.hass, self.plant_entity_id)
        soil_moisture_entity_id = resolve_entity_reference(
            self.soil_moisture_entity_id,
            plant_attributes,
            PLANT_SOIL_ENTITY_KEYS,
        )
        min_threshold = resolve_float_value(
            self.min_threshold,
            plant_attributes,
            PLANT_MIN_KEYS,
        )
        max_threshold = resolve_float_value(
            self.max_threshold,
            plant_attributes,
            PLANT_MAX_KEYS,
        )
        humidity_entity_id = resolve_entity_reference(
            self.humidity_entity_id,
            plant_attributes,
            PLANT_HUMIDITY_ENTITY_KEYS,
        )
        temperature_entity_id = resolve_entity_reference(
            self.temperature_entity_id,
            plant_attributes,
            PLANT_TEMPERATURE_ENTITY_KEYS,
        )
        illuminance_entity_id = resolve_entity_reference(
            self.illuminance_entity_id,
            plant_attributes,
            PLANT_ILLUMINANCE_ENTITY_KEYS,
        )

        self.resolved_soil_moisture_entity_id = soil_moisture_entity_id
        self.resolved_humidity_entity_id = humidity_entity_id
        self.resolved_temperature_entity_id = temperature_entity_id
        self.resolved_illuminance_entity_id = illuminance_entity_id
        self.resolved_min_threshold = min_threshold
        self.resolved_max_threshold = max_threshold

        if soil_moisture_entity_id is None:
            raise UpdateFailed("No soil moisture entity configured or resolvable from plant entity")
        if min_threshold is None or max_threshold is None:
            raise UpdateFailed("No moisture thresholds configured or resolvable from plant entity")
        if max_threshold <= min_threshold:
            raise UpdateFailed("Resolved max moisture must be greater than min moisture")

        start = now - timedelta(hours=self.lookback_hours)

        try:
            samples = await self._async_load_history(start, now, soil_moisture_entity_id)
        except Exception as err:
            raise UpdateFailed(f"Unable to load soil moisture history: {err}") from err

        current_moisture = _read_float_state(self.hass, soil_moisture_entity_id)
        humidity = (
            _read_float_state(self.hass, humidity_entity_id)
            if humidity_entity_id
            else None
        )
        temperature = (
            _read_float_state(self.hass, temperature_entity_id)
            if temperature_entity_id
            else None
        )
        illuminance = (
            _read_float_state(self.hass, illuminance_entity_id)
            if illuminance_entity_id
            else None
        )

        return calculate_forecast(
            now=now,
            samples=samples,
            current_moisture=current_moisture,
            min_threshold=min_threshold,
            max_threshold=max_threshold,
            humidity=humidity,
            temperature=temperature,
            illuminance=illuminance,
            reset_threshold=self.reset_threshold,
            humidity_impact=self.humidity_impact,
            temperature_impact=self.temperature_impact,
            illuminance_impact=self.illuminance_impact,
        )

    async def _async_load_history(
        self,
        start: datetime,
        end: datetime,
        soil_moisture_entity_id: str,
    ) -> list[Sample]:
        """Load historical sensor states from the recorder database."""

        def _fetch() -> list[Sample]:
            history_map = history.state_changes_during_period(
                self.hass,
                start_time=start,
                end_time=end,
                entity_id=soil_moisture_entity_id,
                include_start_time_state=True,
                no_attributes=True,
            )
            states = history_map.get(soil_moisture_entity_id, [])
            samples: list[Sample] = []

            for state in states:
                value = _parse_float(state.state)
                if value is None:
                    continue
                samples.append(
                    Sample(
                        observed_at=state.last_updated or state.last_changed or start,
                        value=value,
                    )
                )
            return samples

        return await get_instance(self.hass).async_add_executor_job(_fetch)

    @property
    def extra_diagnostics(self) -> dict[str, Any]:
        """Expose debug-friendly details for troubleshooting."""

        return asdict(self.data) if self.data else {}


def _read_float_state(hass: HomeAssistant, entity_id: str | None) -> float | None:
    if not entity_id:
        return None
    state = hass.states.get(entity_id)
    if state is None:
        return None
    return _parse_float(state.state)


def _read_attributes(hass: HomeAssistant, entity_id: str | None) -> dict[str, Any] | None:
    if not entity_id:
        return None
    state = hass.states.get(entity_id)
    if state is None:
        return None
    return dict(state.attributes)


def _parse_float(value: str | None) -> float | None:
    if value in (None, "unknown", "unavailable"):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
