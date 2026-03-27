import unittest
from datetime import datetime, timedelta, timezone

from custom_components.arte_forecast.forecast import Sample, calculate_forecast


class CalculateForecastTests(unittest.TestCase):
    def test_detects_watering_cycles(self) -> None:
        now = datetime(2026, 3, 27, 12, 0, tzinfo=timezone.utc)
        samples = [
            Sample(now - timedelta(hours=30), 55),
            Sample(now - timedelta(hours=24), 49),
            Sample(now - timedelta(hours=18), 43),
            Sample(now - timedelta(hours=12), 52),
            Sample(now - timedelta(hours=6), 46),
            Sample(now - timedelta(hours=1), 41),
        ]

        result = calculate_forecast(
            now=now,
            samples=samples,
            current_moisture=41,
            min_threshold=25,
            max_threshold=55,
            humidity=50,
            reset_threshold=4,
        )

        self.assertEqual(result.status, "ok")
        self.assertEqual(result.segments_used, 2)
        self.assertIsNotNone(result.depletion_rate_per_hour)
        self.assertEqual(round(result.depletion_rate_per_hour or 0, 2), 1.0)
        self.assertEqual(round(result.hours_until_min or 0, 2), 16.0)
        self.assertEqual(result.predicted_at, now + timedelta(hours=16))

    def test_marks_due_when_below_minimum(self) -> None:
        now = datetime(2026, 3, 27, 12, 0, tzinfo=timezone.utc)

        result = calculate_forecast(
            now=now,
            samples=[],
            current_moisture=18,
            min_threshold=20,
            max_threshold=50,
            humidity=None,
            reset_threshold=4,
        )

        self.assertEqual(result.status, "watering_due")
        self.assertEqual(result.hours_until_min, 0)
        self.assertEqual(result.predicted_at, now)

    def test_environment_can_speed_up_drying(self) -> None:
        now = datetime(2026, 3, 27, 12, 0, tzinfo=timezone.utc)
        samples = [
            Sample(now - timedelta(hours=12), 50),
            Sample(now - timedelta(hours=6), 44),
            Sample(now, 38),
        ]

        result = calculate_forecast(
            now=now,
            samples=samples,
            current_moisture=38,
            min_threshold=26,
            max_threshold=55,
            humidity=30,
            temperature=28,
            illuminance=30000,
            reset_threshold=4,
            humidity_impact=0.35,
            temperature_impact=0.30,
            illuminance_impact=0.20,
        )

        self.assertEqual(result.status, "ok")
        self.assertIsNotNone(result.depletion_rate_per_hour)
        self.assertGreater(result.depletion_rate_per_hour or 0, 1.0)
        self.assertLess(result.hours_until_min or 999, 12.0)


if __name__ == "__main__":
    unittest.main()
