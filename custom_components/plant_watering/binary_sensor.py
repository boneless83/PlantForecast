"""Binary sensor platform for Plant Watering Forecast."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_WARNING_DAYS
from .entity import get_coordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up watering due binary sensor."""

    coordinator = get_coordinator(hass, entry)
    async_add_entities([WateringDueBinarySensor(coordinator, entry)])


class WateringDueBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Binary sensor that indicates whether watering is due soon."""

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self.entry = entry
        self._attr_name = f"{entry.title} watering due"
        self._attr_unique_id = f"{entry.entry_id}_watering_due"

    @property
    def is_on(self) -> bool:
        result = self.coordinator.data
        config = {**self.entry.data, **self.entry.options}
        if result is None:
            return False
        if result.status == "watering_due":
            return True
        if result.days_until_watering is None:
            return False
        return result.days_until_watering <= config[CONF_WARNING_DAYS]

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        result = self.coordinator.data
        if result is None:
            return {}
        return {
            "days_until_watering": result.days_until_watering,
            "predicted_watering_at": result.predicted_watering_at,
            "status": result.status,
        }
