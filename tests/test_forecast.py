import unittest
from datetime import datetime, timedelta, timezone
import importlib.util
from pathlib import Path
import sys
import types


def _load_forecast_module():
    root = Path(__file__).resolve().parents[1]
    package_root = root / "custom_components" / "plant_watering"

    custom_components_pkg = types.ModuleType("custom_components")
    custom_components_pkg.__path__ = [str(root / "custom_components")]
    sys.modules.setdefault("custom_components", custom_components_pkg)

    plant_watering_pkg = types.ModuleType("custom_components.plant_watering")
    plant_watering_pkg.__path__ = [str(package_root)]
    sys.modules.setdefault("custom_components.plant_watering", plant_watering_pkg)

    for module_name in ("const", "forecast"):
        full_name = f"custom_components.plant_watering.{module_name}"
        module_path = package_root / f"{module_name}.py"
        spec = importlib.util.spec_from_file_location(full_name, module_path)
        module = importlib.util.module_from_spec(spec)
        assert spec is not None
        assert spec.loader is not None
        sys.modules[full_name] = module
        spec.loader.exec_module(module)

    return sys.modules["custom_components.plant_watering.forecast"]


forecast_module = _load_forecast_module()
MoistureSample = forecast_module.MoistureSample
calculate_forecast = forecast_module.calculate_forecast


class ForecastTests(unittest.TestCase):
    def test_detects_last_watering_and_forecasts_future(self) -> None:
        now = datetime(2026, 3, 30, 10, 0, tzinfo=timezone.utc)
        samples = [
            MoistureSample(now - timedelta(hours=48), 55),
            MoistureSample(now - timedelta(hours=36), 47),
            MoistureSample(now - timedelta(hours=24), 56),
            MoistureSample(now - timedelta(hours=12), 50),
            MoistureSample(now - timedelta(hours=1), 44),
        ]

        result = calculate_forecast(
            now=now,
            samples=samples,
            current_moisture=44,
            min_moisture=20,
            max_moisture=60,
            humidity=50,
            temperature=22,
            lookback_hours=48,
            watering_jump=8,
            temperature_factor=0.03,
            humidity_factor=0.01,
        )

        self.assertEqual(result.status, "ok")
        self.assertEqual(result.base_daily_loss, 12.0)
        self.assertEqual(result.adjusted_daily_loss, 12.0)
        self.assertEqual(result.days_until_watering, 2.0)

    def test_reports_due_when_current_is_below_minimum(self) -> None:
        now = datetime(2026, 3, 30, 10, 0, tzinfo=timezone.utc)

        result = calculate_forecast(
            now=now,
            samples=[],
            current_moisture=18,
            min_moisture=20,
            max_moisture=60,
            humidity=None,
            temperature=None,
            lookback_hours=48,
            watering_jump=8,
            temperature_factor=0.03,
            humidity_factor=0.01,
        )

        self.assertEqual(result.status, "watering_due")
        self.assertEqual(result.days_until_watering, 0.0)


if __name__ == "__main__":
    unittest.main()
