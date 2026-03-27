import unittest

from custom_components.arte_forecast.plant_helpers import (
    PLANT_MAX_KEYS,
    PLANT_MIN_KEYS,
    PLANT_SOIL_ENTITY_KEYS,
    build_plant_candidate,
    resolve_entity_reference,
    resolve_float_value,
)


class PlantHelperTests(unittest.TestCase):
    def test_resolves_values_from_plant_attributes(self) -> None:
        attributes = {
            "moisture_entity": "sensor.monstera_soil",
            "min_moisture": 22,
            "max_moisture": "55",
        }

        self.assertEqual(
            resolve_entity_reference(None, attributes, PLANT_SOIL_ENTITY_KEYS),
            "sensor.monstera_soil",
        )
        self.assertEqual(resolve_float_value(None, attributes, PLANT_MIN_KEYS), 22.0)
        self.assertEqual(resolve_float_value(None, attributes, PLANT_MAX_KEYS), 55.0)

    def test_explicit_values_override_plant_attributes(self) -> None:
        attributes = {
            "moisture_entity": "sensor.monstera_soil",
            "min_moisture": 22,
        }

        self.assertEqual(
            resolve_entity_reference(
                "sensor.override_soil",
                attributes,
                PLANT_SOIL_ENTITY_KEYS,
            ),
            "sensor.override_soil",
        )
        self.assertEqual(resolve_float_value(18.0, attributes, PLANT_MIN_KEYS), 18.0)

    def test_builds_candidate_from_compatible_plant(self) -> None:
        attributes = {
            "friendly_name": "Monstera",
            "moisture_entity": "sensor.monstera_soil",
            "temperature_entity": "sensor.living_room_temperature",
            "min_moisture": 22,
            "max_moisture": 55,
        }

        candidate = build_plant_candidate("plant.monstera", attributes)

        self.assertIsNotNone(candidate)
        assert candidate is not None
        self.assertEqual(candidate.entity_id, "plant.monstera")
        self.assertEqual(candidate.title, "Monstera")
        self.assertEqual(candidate.defaults["soil_moisture_entity"], "sensor.monstera_soil")
        self.assertEqual(candidate.defaults["temperature_entity"], "sensor.living_room_temperature")
        self.assertEqual(candidate.defaults["min_moisture"], 22.0)
        self.assertEqual(candidate.defaults["max_moisture"], 55.0)

    def test_rejects_incomplete_plant_candidate(self) -> None:
        attributes = {
            "friendly_name": "Dry plant",
            "moisture_entity": "sensor.dry_plant_soil",
            "min_moisture": 40,
        }

        self.assertIsNone(build_plant_candidate("plant.dry_plant", attributes))


if __name__ == "__main__":
    unittest.main()
