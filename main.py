"""Main entry point for the workout planning service.

This script generates today's workout plan using the same services
used by the demo, but focused on producing a single, clean plan output.
"""

import os
import random
from datetime import date

from services.class_roster import ClassRosterService, DummyAttendanceService
from services.weather import WeatherService, WindForcast
from services.workout_planner import WorkoutPlannerService
from services.workout_routine import WorkoutRoutineService


class WeatherClient:
    """Use the real WeatherService when API key is present, otherwise produce
    a lightweight random forecast (no hard-coded PRESET table).
    """

    def __init__(self, seed: int | None = None):
        api_key = os.environ.get("OPENWEATHER_API_KEY")
        if api_key:
            self.client = WeatherService(api_key)
            self.use_api = True
        else:
            self.client = random.Random(seed)
            self.use_api = False

    def get_wind_forecast(self, location: str) -> WindForcast:
        if self.use_api:
            return self.client.get_wind_forecast(location)

        rng: random.Random = self.client
        base_wind = round(rng.uniform(1.0, 7.0), 1)
        gust = round(base_wind + rng.uniform(0.0, 4.0), 1)
        temps = rng.uniform(14.0, 24.0)
        desc_opts = ["Clear", "Partly cloudy", "Breezy", "Sunny"]
        desc = rng.choice(desc_opts)
        return WindForcast(
            location=location,
            wind_speed_mps=base_wind,
            wind_gust_mps=gust,
            description=desc,
            temperature_celsius=round(temps, 1),
        )


def main():
    """Generate and print today's workout plan using config-driven services."""
    # Initialize services
    weather_service = WeatherClient()
    routine_service = WorkoutRoutineService()
    roster_service = ClassRosterService(
        config_path="configs/classes.json",
        attendance_service=DummyAttendanceService(
            students_path="configs/students.json"
        ),
    )

    planner = WorkoutPlannerService(weather_service, routine_service, roster_service)

    today = date.today()

    # Try to use the class location for today if available
    class_session = roster_service.get_roster_for_date(today)
    preferred_location = (
        class_session.location
        if class_session and class_session.location
        else "Huntington Beach"
    )

    plan = planner.generate_plan(today, preferred_location)

    print(plan.plan_summary)


if __name__ == "__main__":
    main()
