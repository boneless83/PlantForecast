"""Config flow for Plant Watering Forecast."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
    TextSelectorConfig,
)

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
    CONF_WARNING_DAYS,
    CONF_WATERING_JUMP,
    DEFAULT_HUMIDITY_FACTOR,
    DEFAULT_LOOKBACK_HOURS,
    DEFAULT_TEMPERATURE_FACTOR,
    DEFAULT_WARNING_DAYS,
    DEFAULT_WATERING_JUMP,
    DOMAIN,
)


def _build_schema(defaults: dict[str, Any] | None = None) -> vol.Schema:
    defaults = defaults or {}
    return vol.Schema(
        {
            vol.Required(
                CONF_PLANT_NAME,
                default=defaults.get(CONF_PLANT_NAME, "Plant"),
            ): TextSelector(TextSelectorConfig()),
            vol.Required(
                CONF_SOIL_MOISTURE_ENTITY,
                default=defaults.get(CONF_SOIL_MOISTURE_ENTITY),
            ): EntitySelector(
                EntitySelectorConfig(domain="sensor")
            ),
            vol.Optional(
                CONF_TEMPERATURE_ENTITY,
                default=defaults.get(CONF_TEMPERATURE_ENTITY),
            ): EntitySelector(
                EntitySelectorConfig(domain="sensor")
            ),
            vol.Optional(
                CONF_HUMIDITY_ENTITY,
                default=defaults.get(CONF_HUMIDITY_ENTITY),
            ): EntitySelector(
                EntitySelectorConfig(domain="sensor")
            ),
            vol.Required(
                CONF_MIN_MOISTURE,
                default=defaults.get(CONF_MIN_MOISTURE, 20),
            ): NumberSelector(
                NumberSelectorConfig(min=0, max=100, step=1, mode=NumberSelectorMode.BOX)
            ),
            vol.Required(
                CONF_MAX_MOISTURE,
                default=defaults.get(CONF_MAX_MOISTURE, 60),
            ): NumberSelector(
                NumberSelectorConfig(min=0, max=100, step=1, mode=NumberSelectorMode.BOX)
            ),
            vol.Optional(
                CONF_LOOKBACK_HOURS,
                default=defaults.get(CONF_LOOKBACK_HOURS, DEFAULT_LOOKBACK_HOURS),
            ): NumberSelector(
                NumberSelectorConfig(min=12, max=168, step=12, mode=NumberSelectorMode.BOX)
            ),
            vol.Optional(
                CONF_WATERING_JUMP,
                default=defaults.get(CONF_WATERING_JUMP, DEFAULT_WATERING_JUMP),
            ): NumberSelector(
                NumberSelectorConfig(min=1, max=30, step=0.5, mode=NumberSelectorMode.BOX)
            ),
            vol.Optional(
                CONF_TEMPERATURE_FACTOR,
                default=defaults.get(CONF_TEMPERATURE_FACTOR, DEFAULT_TEMPERATURE_FACTOR),
            ): NumberSelector(
                NumberSelectorConfig(min=0, max=0.2, step=0.01, mode=NumberSelectorMode.BOX)
            ),
            vol.Optional(
                CONF_HUMIDITY_FACTOR,
                default=defaults.get(CONF_HUMIDITY_FACTOR, DEFAULT_HUMIDITY_FACTOR),
            ): NumberSelector(
                NumberSelectorConfig(min=0, max=0.1, step=0.01, mode=NumberSelectorMode.BOX)
            ),
            vol.Optional(
                CONF_WARNING_DAYS,
                default=defaults.get(CONF_WARNING_DAYS, DEFAULT_WARNING_DAYS),
            ): NumberSelector(
                NumberSelectorConfig(min=0, max=7, step=0.1, mode=NumberSelectorMode.BOX)
            ),
        }
    )


def _validate_input(user_input: dict[str, Any]) -> dict[str, str]:
    errors: dict[str, str] = {}
    if user_input[CONF_MAX_MOISTURE] <= user_input[CONF_MIN_MOISTURE]:
        errors["base"] = "invalid_thresholds"
    return errors


class PlantWateringConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Plant Watering Forecast."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}

        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_SOIL_MOISTURE_ENTITY])
            self._abort_if_unique_id_configured()

            errors = _validate_input(user_input)
            if not errors:
                return self.async_create_entry(
                    title=user_input[CONF_PLANT_NAME],
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=_build_schema(user_input),
            errors=errors,
        )

    @staticmethod
    def async_get_options_flow(config_entry):
        return PlantWateringOptionsFlow(config_entry)


class PlantWateringOptionsFlow(config_entries.OptionsFlow):
    """Handle options for Plant Watering Forecast."""

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
