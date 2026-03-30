"""Shared entity helpers."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import PlantWateringCoordinator


def get_coordinator(hass: HomeAssistant, entry: ConfigEntry) -> PlantWateringCoordinator:
    """Return the shared coordinator for a config entry."""

    return hass.data[DOMAIN][entry.entry_id]
