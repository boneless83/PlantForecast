"""Forecast helpers for soil moisture depletion."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from statistics import fmean

from .const import (
    DEFAULT_HUMIDITY_IMPACT,
    DEFAULT_ILLUMINANCE_IMPACT,
    DEFAULT_TEMPERATURE_IMPACT,
    MIN_RATE_PER_HOUR,
)


@dataclass
class Sample:
    """A time/value pair from Home Assistant history."""

    observed_at: datetime
    value: float


@dataclass
class ForecastResult:
    """Computed watering forecast."""

    predicted_at: datetime | None
    hours_until_min: float | None
    current_moisture: float | None
    depletion_rate_per_hour: float | None
    average_segment_rate_per_hour: float | None
    samples_used: int
    segments_used: int
    min_threshold: float
    max_threshold: float
    humidity: float | None
    temperature: float | None
    illuminance: float | None
    status: str


def calculate_forecast(
    *,
    now: datetime,
    samples: list[Sample],
    current_moisture: float | None,
    min_threshold: float,
    max_threshold: float,
    humidity: float | None,
    reset_threshold: float,
    humidity_impact: float = DEFAULT_HUMIDITY_IMPACT,
    temperature: float | None = None,
    temperature_impact: float = DEFAULT_TEMPERATURE_IMPACT,
    illuminance: float | None = None,
    illuminance_impact: float = DEFAULT_ILLUMINANCE_IMPACT,
) -> ForecastResult:
    """Estimate when soil moisture will reach the configured minimum threshold."""

    cleaned = sorted(samples, key=lambda item: item.observed_at)
    if current_moisture is None and cleaned:
        current_moisture = cleaned[-1].value

    if current_moisture is None:
        return ForecastResult(
            predicted_at=None,
            hours_until_min=None,
            current_moisture=None,
            depletion_rate_per_hour=None,
            average_segment_rate_per_hour=None,
            samples_used=0,
            segments_used=0,
            min_threshold=min_threshold,
            max_threshold=max_threshold,
            humidity=humidity,
            temperature=temperature,
            illuminance=illuminance,
            status="missing_current_moisture",
        )

    if current_moisture <= min_threshold:
        return ForecastResult(
            predicted_at=now,
            hours_until_min=0.0,
            current_moisture=current_moisture,
            depletion_rate_per_hour=0.0,
            average_segment_rate_per_hour=0.0,
            samples_used=len(cleaned),
            segments_used=0,
            min_threshold=min_threshold,
            max_threshold=max_threshold,
            humidity=humidity,
            temperature=temperature,
            illuminance=illuminance,
            status="watering_due",
        )

    segment_rates = _extract_segment_rates(cleaned, reset_threshold)
    if cleaned and len(cleaned) > 1:
        fallback_rate = _series_rate(cleaned)
    else:
        fallback_rate = None

    average_rate = fmean(segment_rates) if segment_rates else fallback_rate
    if average_rate is None or average_rate <= 0:
        return ForecastResult(
            predicted_at=None,
            hours_until_min=None,
            current_moisture=current_moisture,
            depletion_rate_per_hour=None,
            average_segment_rate_per_hour=average_rate,
            samples_used=len(cleaned),
            segments_used=len(segment_rates),
            min_threshold=min_threshold,
            max_threshold=max_threshold,
            humidity=humidity,
            temperature=temperature,
            illuminance=illuminance,
            status="insufficient_history",
        )

    adjusted_rate = _apply_environment_adjustment(
        average_rate,
        humidity=humidity,
        humidity_impact=humidity_impact,
        temperature=temperature,
        temperature_impact=temperature_impact,
        illuminance=illuminance,
        illuminance_impact=illuminance_impact,
    )
    adjusted_rate = max(adjusted_rate, MIN_RATE_PER_HOUR)

    hours_until_min = max((current_moisture - min_threshold) / adjusted_rate, 0.0)
    predicted_at = now + timedelta(hours=hours_until_min)

    return ForecastResult(
        predicted_at=predicted_at,
        hours_until_min=hours_until_min,
        current_moisture=current_moisture,
        depletion_rate_per_hour=adjusted_rate,
        average_segment_rate_per_hour=average_rate,
        samples_used=len(cleaned),
        segments_used=len(segment_rates),
        min_threshold=min_threshold,
        max_threshold=max_threshold,
        humidity=humidity,
        temperature=temperature,
        illuminance=illuminance,
        status="ok",
    )


def _extract_segment_rates(samples: list[Sample], reset_threshold: float) -> list[float]:
    """Split the history into drying segments and derive hourly depletion rates."""

    if len(samples) < 2:
        return []

    segments: list[list[Sample]] = []
    current_segment = [samples[0]]

    for previous, current in zip(samples, samples[1:]):
        delta = current.value - previous.value
        if delta >= reset_threshold:
            if len(current_segment) > 1:
                segments.append(current_segment)
            current_segment = [current]
            continue
        current_segment.append(current)

    if len(current_segment) > 1:
        segments.append(current_segment)

    rates = []
    for segment in segments:
        rate = _series_rate(segment)
        if rate is not None and rate > 0:
            rates.append(rate)
    return rates


def _series_rate(samples: list[Sample]) -> float | None:
    """Calculate the average hourly drop across a monotonic drying period."""

    start = samples[0]
    end = samples[-1]
    hours = (end.observed_at - start.observed_at).total_seconds() / 3600
    if hours <= 0:
        return None

    drop = start.value - end.value
    if drop <= 0:
        return None

    return drop / hours


def _apply_environment_adjustment(
    rate_per_hour: float,
    *,
    humidity: float | None,
    humidity_impact: float,
    temperature: float | None,
    temperature_impact: float,
    illuminance: float | None,
    illuminance_impact: float,
) -> float:
    """Adjust the drying rate using simple environmental heuristics."""

    rate = rate_per_hour

    if humidity is not None:
        normalized_humidity = (humidity - 50.0) / 50.0
        humidity_factor = 1.0 - (normalized_humidity * humidity_impact)
        humidity_factor = min(max(humidity_factor, 0.65), 1.35)
        rate *= humidity_factor

    if temperature is not None:
        normalized_temperature = (temperature - 21.0) / 10.0
        temperature_factor = 1.0 + (normalized_temperature * temperature_impact)
        temperature_factor = min(max(temperature_factor, 0.7), 1.5)
        rate *= temperature_factor

    if illuminance is not None:
        normalized_illuminance = min(max(illuminance, 0.0), 50000.0) / 20000.0
        illuminance_factor = 1.0 + ((normalized_illuminance - 0.5) * illuminance_impact)
        illuminance_factor = min(max(illuminance_factor, 0.85), 1.35)
        rate *= illuminance_factor

    return rate
