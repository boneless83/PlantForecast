"""Binary sensor platform for Arte Forecast."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .entity import get_coordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the watering-due binary sensor from a config entry."""

    coordinator = get_coordinator(hass, entry)
    async_add_entities([ArteForecastWateringDueBinarySensor(coordinator, entry)])


class ArteForecastWateringDueBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Expose whether the plant should be watered now."""

    _attr_should_poll = False

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_name = f"{entry.title} watering due"
        self._attr_unique_id = f"{entry.entry_id}_watering_due"

    @property
    def is_on(self) -> bool:
        result = self.coordinator.data
        if result is None:
            return False
        return result.status == "watering_due"

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        result = self.coordinator.data
        if result is None:
            return {}
        return {
            "status": result.status,
            "hours_until_min_moisture": result.hours_until_min,
            "current_moisture": result.current_moisture,
            "plant_entity": self.coordinator.plant_entity_id,
            "resolved_source_entity": self.coordinator.resolved_soil_moisture_entity_id,
            "resolved_min_moisture": self.coordinator.resolved_min_threshold,
            "resolved_max_moisture": self.coordinator.resolved_max_threshold,
        }
