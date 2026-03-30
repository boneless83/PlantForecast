"""Forecast calculation helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from .const import MIN_DAILY_LOSS, REFERENCE_HUMIDITY, REFERENCE_TEMPERATURE


@dataclass
class MoistureSample:
    """A recorded soil moisture sample."""

    observed_at: datetime
    value: float


@dataclass
class ForecastResult:
    """Computed watering forecast for one plant."""

    current_moisture: float | None
    base_daily_loss: float | None
    adjusted_daily_loss: float | None
    hours_until_watering: float | None
    days_until_watering: float | None
    predicted_watering_at: datetime | None
    last_watering_at: datetime | None
    status: str
    samples_used: int
    humidity: float | None
    temperature: float | None


def calculate_forecast(
    *,
    now: datetime,
    samples: list[MoistureSample],
    current_moisture: float | None,
    min_moisture: float,
    max_moisture: float,
    humidity: float | None,
    temperature: float | None,
    lookback_hours: int,
    watering_jump: float,
    temperature_factor: float,
    humidity_factor: float,
) -> ForecastResult:
    """Calculate next watering time from moisture history and room climate."""

    ordered = sorted(samples, key=lambda item: item.observed_at)
    if current_moisture is None and ordered:
        current_moisture = ordered[-1].value

    if current_moisture is None:
        return ForecastResult(
            current_moisture=None,
            base_daily_loss=None,
            adjusted_daily_loss=None,
            hours_until_watering=None,
            days_until_watering=None,
            predicted_watering_at=None,
            last_watering_at=None,
            status="missing_current_moisture",
            samples_used=0,
            humidity=humidity,
            temperature=temperature,
        )

    if current_moisture <= min_moisture:
        return ForecastResult(
            current_moisture=current_moisture,
            base_daily_loss=0.0,
            adjusted_daily_loss=0.0,
            hours_until_watering=0.0,
            days_until_watering=0.0,
            predicted_watering_at=now,
            last_watering_at=_detect_last_watering(ordered, watering_jump),
            status="watering_due",
            samples_used=len(ordered),
            humidity=humidity,
            temperature=temperature,
        )

    last_watering_at = _detect_last_watering(ordered, watering_jump)
    if last_watering_at is not None:
        window_start = last_watering_at
    else:
        window_start = now - timedelta(hours=lookback_hours)

    active_samples = [sample for sample in ordered if sample.observed_at >= window_start]
    base_daily_loss = _calculate_daily_loss(active_samples, now, current_moisture)

    if base_daily_loss is None or base_daily_loss <= 0:
        return ForecastResult(
            current_moisture=current_moisture,
            base_daily_loss=None,
            adjusted_daily_loss=None,
            hours_until_watering=None,
            days_until_watering=None,
            predicted_watering_at=None,
            last_watering_at=last_watering_at,
            status="insufficient_history",
            samples_used=len(active_samples),
            humidity=humidity,
            temperature=temperature,
        )

    adjusted_daily_loss = _apply_climate_adjustment(
        base_daily_loss=base_daily_loss,
        temperature=temperature,
        humidity=humidity,
        temperature_factor=temperature_factor,
        humidity_factor=humidity_factor,
    )
    adjusted_daily_loss = max(adjusted_daily_loss, MIN_DAILY_LOSS)

    days_until_watering = max((current_moisture - min_moisture) / adjusted_daily_loss, 0.0)
    hours_until_watering = days_until_watering * 24

    return ForecastResult(
        current_moisture=current_moisture,
        base_daily_loss=round(base_daily_loss, 2),
        adjusted_daily_loss=round(adjusted_daily_loss, 2),
        hours_until_watering=round(hours_until_watering, 1),
        days_until_watering=round(days_until_watering, 1),
        predicted_watering_at=now + timedelta(days=days_until_watering),
        last_watering_at=last_watering_at,
        status="ok",
        samples_used=len(active_samples),
        humidity=humidity,
        temperature=temperature,
    )


def _detect_last_watering(samples: list[MoistureSample], watering_jump: float) -> datetime | None:
    last_watering_at: datetime | None = None
    for previous, current in zip(samples, samples[1:]):
        if current.value - previous.value >= watering_jump:
            last_watering_at = current.observed_at
    return last_watering_at


def _calculate_daily_loss(
    samples: list[MoistureSample],
    now: datetime,
    current_moisture: float,
) -> float | None:
    if len(samples) < 2:
        return None

    start = samples[0]
    hours = (now - start.observed_at).total_seconds() / 3600
    if hours <= 0:
        return None

    drop = start.value - current_moisture
    if drop <= 0:
        return None

    return drop / (hours / 24)


def _apply_climate_adjustment(
    *,
    base_daily_loss: float,
    temperature: float | None,
    humidity: float | None,
    temperature_factor: float,
    humidity_factor: float,
) -> float:
    result = base_daily_loss

    if temperature is not None:
        delta = temperature - REFERENCE_TEMPERATURE
        result *= min(max(1 + (delta * temperature_factor), 0.85), 1.25)

    if humidity is not None:
        delta = REFERENCE_HUMIDITY - humidity
        result *= min(max(1 + (delta * humidity_factor), 0.80), 1.30)

    return result
