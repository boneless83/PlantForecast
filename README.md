# Plant Watering Forecast

Custom Home Assistant integration for predicting when a plant will likely need water next.

## Installation

Copy `custom_components/plant_watering` into your Home Assistant `custom_components` directory, restart Home Assistant, then add the integration through `Settings -> Devices & Services -> Add Integration`.

For HACS as a custom repository:

1. Add this GitHub repository in HACS as type `Integration`
2. Install `Plant Watering Forecast`
3. Restart Home Assistant
4. Add the integration through the UI

## What it does

For each configured plant, the integration:

- reads historical soil moisture from the selected sensor
- detects probable watering events from sharp upward jumps
- estimates daily moisture loss from the recent drying phase
- adjusts that loss using optional room temperature and humidity sensors
- creates forecast entities automatically

Created entities per plant:

- timestamp sensor: next watering
- numeric sensor: days until watering
- numeric sensor: adjusted daily moisture loss
- binary sensor: watering due

## Current scope

The integration is configured through the Home Assistant UI.

You select:

- plant name
- soil moisture sensor
- optional temperature sensor
- optional humidity sensor
- minimum and maximum moisture

The forecast logic and derived entities are then created automatically.

## Notes

- Recorder must be enabled in Home Assistant because the integration reads historical sensor states.
- The first forecast is only as good as the available history window.
- A watering event is currently inferred from a moisture jump, not from a dedicated "watered" button.
