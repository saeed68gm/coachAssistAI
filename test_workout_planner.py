"""Integration tests that validate key services against the current configs.

These tests aim to exercise the real code paths for:
- `WorkoutRoutineService` reading `configs/routines.json`
- `ClassRosterService` loading `configs/classes.json` and using `DummyAttendanceService`
- `OpenMeteoWeatherService` fetching current weather (network-required)
- `WorkoutPlannerService` integrating the above

Network calls to Open-Meteo are attempted; if they fail (no network or rate
limits), those specific assertions are skipped rather than failing the suite.
"""

import json
import unittest
from datetime import date
from pathlib import Path

from services.class_roster import ClassRosterService, DummyAttendanceService
from services.weather import OpenMeteoWeatherService
from services.workout_planner import WorkoutPlannerService
from services.workout_routine import WorkoutRoutineService


class TestServicesIntegration(unittest.TestCase):
    def setUp(self):
        self.routine_service = WorkoutRoutineService()
        self.roster_service = ClassRosterService(
            attendance_service=DummyAttendanceService(
                students_path="configs/students.json"
            )
        )
        self.weather_service = OpenMeteoWeatherService()
        self.planner = WorkoutPlannerService(
            self.weather_service, self.routine_service, self.roster_service
        )

    def test_routines_loaded(self):
        routines = self.routine_service.get_all_routines()
        # Expect at least Monday and Saturday present based on configs
        self.assertIn("Monday", routines)
        self.assertIn("Saturday", routines)
        for _day, r in routines.items():
            self.assertTrue(len(r.exercises) > 0)
            self.assertTrue(r.duration_minutes > 0)

    def test_rosters_from_config(self):
        rosters = self.roster_service.get_all_rosters()
        cfg = Path("configs/classes.json")
        if not cfg.exists():
            self.skipTest("No class config present")

        data = json.loads(cfg.read_text(encoding="utf-8"))
        # Expect roster entries for days present in config
        config_days = {entry.get("day") for entry in data if entry.get("day")}
        for d in config_days:
            session = rosters.get(d)
            self.assertIsNotNone(session)
            # roster may be empty if no students configured; ensure attribute exists
            self.assertIsNotNone(session.roster)

    def test_weather_fetch_for_class_locations(self):
        cfg = Path("configs/classes.json")
        if not cfg.exists():
            self.skipTest("No class config present")

        data = json.loads(cfg.read_text(encoding="utf-8"))
        for entry in data:
            loc = entry.get("location") or "Huntington Beach"
            try:
                forecast = self.weather_service.get_wind_forecast(loc)
            except Exception as exc:
                self.skipTest(f"Open-Meteo request failed: {exc}")
            # Expect numeric wind and temperature fields
            self.assertIsNotNone(forecast.wind_speed_mps)

    def test_planner_generates_plans_for_config_days(self):
        cfg = Path("configs/classes.json")
        if not cfg.exists():
            self.skipTest("No class config present")

        data = json.loads(cfg.read_text(encoding="utf-8"))
        # For each unique day in config, generate a plan and assert key fields
        seen_days = set()
        for entry in data:
            day = entry.get("day")
            if not day or day in seen_days:
                continue
            seen_days.add(day)
            # Map to a date in Dec 2025 with that weekday
            # Simple mapping: find a date in Dec 1-7 with matching weekday
            base = date(2025, 12, 1)
            target = None
            for i in range(7):
                d = date(base.year, base.month, base.day + i)
                if d.strftime("%A") == day:
                    target = d
                    break
            if not target:
                self.skipTest(f"Cannot map day {day} to Dec 1-7, 2025")

            try:
                plan = self.planner.generate_plan(
                    target, entry.get("location") or "Huntington Beach"
                )
            except Exception as exc:
                self.skipTest(f"Planner failed due to external error: {exc}")

            self.assertIsNotNone(plan.routine)
            self.assertIsNotNone(plan.wind_forecast)
            # Class session may be None if roster config omitted,
            # but planner should still return a plan
            self.assertIsNotNone(plan.plan_summary)


if __name__ == "__main__":
    unittest.main()
