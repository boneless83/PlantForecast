"""Sensor platform for Plant Watering Forecast."""

from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_HUMIDITY_ENTITY,
    CONF_PLANT_NAME,
    CONF_SOIL_MOISTURE_ENTITY,
    CONF_TEMPERATURE_ENTITY,
)
from .entity import get_coordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Plant Watering Forecast sensors."""

    coordinator = get_coordinator(hass, entry)
    async_add_entities(
        [
            NextWateringSensor(coordinator, entry),
            DaysUntilWateringSensor(coordinator, entry),
            DailyLossSensor(coordinator, entry),
        ]
    )


class BaseForecastSensor(CoordinatorEntity, SensorEntity):
    """Base class for forecast sensors."""

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self.entry = entry

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        result = self.coordinator.data
        config = {**self.entry.data, **self.entry.options}
        if result is None:
            return {}
        return {
            "plant_name": config[CONF_PLANT_NAME],
            "soil_moisture_entity": config[CONF_SOIL_MOISTURE_ENTITY],
            "temperature_entity": config.get(CONF_TEMPERATURE_ENTITY),
            "humidity_entity": config.get(CONF_HUMIDITY_ENTITY),
            "current_moisture": result.current_moisture,
            "base_daily_loss": result.base_daily_loss,
            "adjusted_daily_loss": result.adjusted_daily_loss,
            "last_watering_at": result.last_watering_at,
            "status": result.status,
            "samples_used": result.samples_used,
        }


class NextWateringSensor(BaseForecastSensor):
    """Timestamp for the predicted next watering time."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_name = f"{entry.title} next watering"
        self._attr_unique_id = f"{entry.entry_id}_next_watering"

    @property
    def native_value(self):
        return self.coordinator.data.predicted_watering_at if self.coordinator.data else None


class DaysUntilWateringSensor(BaseForecastSensor):
    """Days left until watering is needed."""

    _attr_native_unit_of_measurement = UnitOfTime.DAYS

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_name = f"{entry.title} days until watering"
        self._attr_unique_id = f"{entry.entry_id}_days_until_watering"

    @property
    def native_value(self):
        return self.coordinator.data.days_until_watering if self.coordinator.data else None


class DailyLossSensor(BaseForecastSensor):
    """Adjusted daily moisture loss."""

    _attr_native_unit_of_measurement = "%/d"

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_name = f"{entry.title} daily moisture loss"
        self._attr_unique_id = f"{entry.entry_id}_daily_moisture_loss"

    @property
    def native_value(self):
        return self.coordinator.data.adjusted_daily_loss if self.coordinator.data else None
