"""Helpers for resolving plant-entity attributes into forecast inputs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .const import (
    CONF_HUMIDITY_ENTITY,
    CONF_ILLUMINANCE_ENTITY,
    CONF_MAX_THRESHOLD,
    CONF_MIN_THRESHOLD,
    CONF_PLANT_ENTITY,
    CONF_SOIL_MOISTURE_ENTITY,
    CONF_TEMPERATURE_ENTITY,
    DEFAULT_NAME,
)

CONF_NAME = "name"

PLANT_SOIL_ENTITY_KEYS = (
    "soil_moisture_entity",
    "moisture_entity",
    "moisture_sensor",
    "soil_sensor",
)
PLANT_HUMIDITY_ENTITY_KEYS = ("humidity_entity", "humidity_sensor")
PLANT_TEMPERATURE_ENTITY_KEYS = ("temperature_entity", "temperature_sensor")
PLANT_ILLUMINANCE_ENTITY_KEYS = (
    "illuminance_entity",
    "illuminance_sensor",
    "brightness_entity",
    "brightness_sensor",
)
PLANT_MIN_KEYS = ("min_moisture", "min_soil_moisture", "minimum_moisture")
PLANT_MAX_KEYS = ("max_moisture", "max_soil_moisture", "maximum_moisture")


@dataclass
class PlantCandidate:
    """A compatible plant entity that can back one forecast entry."""

    entity_id: str
    title: str
    defaults: dict[str, Any]


def resolve_entity_reference(
    explicit_value: str | None,
    plant_attributes: Mapping[str, Any] | None,
    candidate_keys: tuple[str, ...],
) -> str | None:
    """Prefer explicit config, otherwise scan plant attributes for an entity id."""

    if explicit_value:
        return explicit_value
    if not plant_attributes:
        return None

    for key in candidate_keys:
        value = plant_attributes.get(key)
        if isinstance(value, str) and "." in value:
            return value
    return None


def resolve_float_value(
    explicit_value: float | None,
    plant_attributes: Mapping[str, Any] | None,
    candidate_keys: tuple[str, ...],
) -> float | None:
    """Prefer explicit config, otherwise scan plant attributes for a float."""

    if explicit_value is not None:
        return explicit_value
    if not plant_attributes:
        return None

    for key in candidate_keys:
        value = plant_attributes.get(key)
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return None


def build_plant_candidate(entity_id: str, attributes: Mapping[str, Any]) -> PlantCandidate | None:
    """Build a forecast candidate from a plant entity if it exposes enough data."""

    soil_entity = resolve_entity_reference(None, attributes, PLANT_SOIL_ENTITY_KEYS)
    min_threshold = resolve_float_value(None, attributes, PLANT_MIN_KEYS)
    max_threshold = resolve_float_value(None, attributes, PLANT_MAX_KEYS)

    if soil_entity is None or min_threshold is None or max_threshold is None:
        return None
    if max_threshold <= min_threshold:
        return None

    friendly_name = attributes.get("friendly_name")
    title = friendly_name if isinstance(friendly_name, str) and friendly_name else entity_id

    defaults: dict[str, Any] = {
        CONF_NAME: f"{title} forecast" if title else DEFAULT_NAME,
        CONF_PLANT_ENTITY: entity_id,
        CONF_SOIL_MOISTURE_ENTITY: soil_entity,
        CONF_MIN_THRESHOLD: min_threshold,
        CONF_MAX_THRESHOLD: max_threshold,
    }

    humidity_entity = resolve_entity_reference(None, attributes, PLANT_HUMIDITY_ENTITY_KEYS)
    temperature_entity = resolve_entity_reference(None, attributes, PLANT_TEMPERATURE_ENTITY_KEYS)
    illuminance_entity = resolve_entity_reference(None, attributes, PLANT_ILLUMINANCE_ENTITY_KEYS)

    if humidity_entity:
        defaults[CONF_HUMIDITY_ENTITY] = humidity_entity
    if temperature_entity:
        defaults[CONF_TEMPERATURE_ENTITY] = temperature_entity
    if illuminance_entity:
        defaults[CONF_ILLUMINANCE_ENTITY] = illuminance_entity

    return PlantCandidate(entity_id=entity_id, title=title, defaults=defaults)
