"""Config flow for Arte Forecast."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
import homeassistant.helpers.config_validation as cv

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
    DEFAULT_ILLUMINANCE_IMPACT,
    DEFAULT_LOOKBACK_HOURS,
    DEFAULT_NAME,
    DEFAULT_RESET_THRESHOLD,
    DEFAULT_TEMPERATURE_IMPACT,
    DEFAULT_UPDATE_INTERVAL_MINUTES,
    DOMAIN,
)
from .plant_helpers import PlantCandidate, build_plant_candidate

STEP_SELECT_PLANT = "select_plant"


def _build_schema(defaults: dict[str, Any] | None = None) -> vol.Schema:
    defaults = defaults or {}
    return vol.Schema(
        {
            vol.Required(CONF_NAME, default=defaults.get(CONF_NAME, DEFAULT_NAME)): cv.string,
            vol.Optional(
                CONF_PLANT_ENTITY,
                default=defaults.get(CONF_PLANT_ENTITY),
            ): vol.Any(None, cv.entity_id),
            vol.Optional(
                CONF_SOIL_MOISTURE_ENTITY,
                default=defaults.get(CONF_SOIL_MOISTURE_ENTITY),
            ): vol.Any(None, cv.entity_id),
            vol.Optional(
                CONF_MIN_THRESHOLD,
                default=defaults.get(CONF_MIN_THRESHOLD),
            ): vol.Coerce(float),
            vol.Optional(
                CONF_MAX_THRESHOLD,
                default=defaults.get(CONF_MAX_THRESHOLD),
            ): vol.Coerce(float),
            vol.Optional(
                CONF_HUMIDITY_ENTITY,
                default=defaults.get(CONF_HUMIDITY_ENTITY),
            ): vol.Any(None, cv.entity_id),
            vol.Optional(
                CONF_TEMPERATURE_ENTITY,
                default=defaults.get(CONF_TEMPERATURE_ENTITY),
            ): vol.Any(None, cv.entity_id),
            vol.Optional(
                CONF_ILLUMINANCE_ENTITY,
                default=defaults.get(CONF_ILLUMINANCE_ENTITY),
            ): vol.Any(None, cv.entity_id),
            vol.Optional(
                CONF_LOOKBACK_HOURS,
                default=defaults.get(CONF_LOOKBACK_HOURS, DEFAULT_LOOKBACK_HOURS),
            ): vol.All(vol.Coerce(int), vol.Range(min=6, max=24 * 30)),
            vol.Optional(
                CONF_UPDATE_INTERVAL_MINUTES,
                default=defaults.get(
                    CONF_UPDATE_INTERVAL_MINUTES,
                    DEFAULT_UPDATE_INTERVAL_MINUTES,
                ),
            ): vol.All(vol.Coerce(int), vol.Range(min=5, max=24 * 60)),
            vol.Optional(
                CONF_RESET_THRESHOLD,
                default=defaults.get(CONF_RESET_THRESHOLD, DEFAULT_RESET_THRESHOLD),
            ): vol.All(vol.Coerce(float), vol.Range(min=0.1)),
            vol.Optional(
                CONF_HUMIDITY_IMPACT,
                default=defaults.get(CONF_HUMIDITY_IMPACT, DEFAULT_HUMIDITY_IMPACT),
            ): vol.All(vol.Coerce(float), vol.Range(min=0.0, max=1.0)),
            vol.Optional(
                CONF_TEMPERATURE_IMPACT,
                default=defaults.get(
                    CONF_TEMPERATURE_IMPACT,
                    DEFAULT_TEMPERATURE_IMPACT,
                ),
            ): vol.All(vol.Coerce(float), vol.Range(min=0.0, max=1.0)),
            vol.Optional(
                CONF_ILLUMINANCE_IMPACT,
                default=defaults.get(
                    CONF_ILLUMINANCE_IMPACT,
                    DEFAULT_ILLUMINANCE_IMPACT,
                ),
            ): vol.All(vol.Coerce(float), vol.Range(min=0.0, max=1.0)),
        }
    )


def _validate_input(user_input: dict[str, Any]) -> dict[str, str]:
    errors: dict[str, str] = {}
    min_threshold = user_input.get(CONF_MIN_THRESHOLD)
    max_threshold = user_input.get(CONF_MAX_THRESHOLD)
    plant_entity = user_input.get(CONF_PLANT_ENTITY)
    soil_entity = user_input.get(CONF_SOIL_MOISTURE_ENTITY)

    if max_threshold is not None and min_threshold is not None and max_threshold <= min_threshold:
        errors["base"] = "invalid_thresholds"
    elif not plant_entity and not soil_entity:
        errors["base"] = "missing_source"
    elif not plant_entity and (min_threshold is None or max_threshold is None):
        errors["base"] = "missing_thresholds"
    return errors


def _build_select_schema(candidates: dict[str, str]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_PLANT_ENTITY): vol.In(candidates),
        }
    )


class ArteForecastConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Arte Forecast."""

    VERSION = 1

    def __init__(self) -> None:
        self._candidate_defaults: dict[str, dict[str, Any]] = {}
        self._selected_plant_entity: str | None = None

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        return await self.async_step_select_plant(user_input)

    async def async_step_select_plant(self, user_input: dict[str, Any] | None = None):
        candidates = self._get_discovered_candidates()
        if not candidates:
            return self.async_abort(reason="no_compatible_plants")

        candidate_map = {candidate.entity_id: candidate.title for candidate in candidates}
        self._candidate_defaults = {
            candidate.entity_id: candidate.defaults for candidate in candidates
        }

        errors: dict[str, str] = {}
        if user_input is not None:
            selected_plant = user_input[CONF_PLANT_ENTITY]
            await self.async_set_unique_id(selected_plant)
            self._abort_if_unique_id_configured()
            self._selected_plant_entity = selected_plant
            return await self.async_step_configure_plant()

        return self.async_show_form(
            step_id=STEP_SELECT_PLANT,
            data_schema=_build_select_schema(candidate_map),
            errors=errors,
        )

    async def async_step_configure_plant(self, user_input: dict[str, Any] | None = None):
        if self._selected_plant_entity is None:
            return await self.async_step_select_plant()

        defaults = self._candidate_defaults.get(self._selected_plant_entity, {})
        errors: dict[str, str] = {}

        if user_input is not None:
            user_input[CONF_PLANT_ENTITY] = self._selected_plant_entity
            errors = _validate_input(user_input)
            if not errors:
                return self.async_create_entry(
                    title=user_input[CONF_NAME],
                    data=user_input,
                )

        form_defaults = defaults if user_input is None else {**defaults, **user_input}
        return self.async_show_form(
            step_id="configure_plant",
            data_schema=_build_schema(form_defaults),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return ArteForecastOptionsFlow(config_entry)

    def _get_discovered_candidates(self) -> list[PlantCandidate]:
        configured_ids = {
            entry.unique_id
            for entry in self._async_current_entries()
            if entry.unique_id is not None
        }
        candidates: list[PlantCandidate] = []

        for state in self.hass.states.async_all("plant"):
            if state.entity_id in configured_ids:
                continue
            candidate = build_plant_candidate(state.entity_id, state.attributes)
            if candidate is not None:
                candidates.append(candidate)

        return sorted(candidates, key=lambda item: item.title.lower())


class ArteForecastOptionsFlow(config_entries.OptionsFlow):
    """Handle options for Arte Forecast."""

    def __init__(self, config_entry) -> None:
        self.config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        defaults = {**self.config_entry.data, **self.config_entry.options}
        errors: dict[str, str] = {}

        if user_input is not None:
            errors = _validate_input(user_input)
            if not errors:
                return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=_build_schema(defaults if user_input is None else user_input),
            errors=errors,
        )
