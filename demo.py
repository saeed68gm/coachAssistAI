"""Demo script showing the workout planner in action."""

import json
import random
from datetime import date
from pathlib import Path

from services.class_roster import ClassRosterService, DummyAttendanceService
from services.weather import OpenMeteoWeatherService
from services.workout_planner import WorkoutPlannerService
from services.workout_routine import WorkoutRoutineService


def main():
    """Run demonstration of the workout planning service."""
    print("🏋️ Workout Planning Service Demo\n")
    print("=" * 60)

    # Initialize services
    # Use Open-Meteo for real data (no API key required)
    weather_service = OpenMeteoWeatherService()
    routine_service = WorkoutRoutineService()
    # Provide class config and students.json to ClassRosterService
    roster_service = ClassRosterService(
        config_path="configs/classes.json",
        attendance_service=DummyAttendanceService(
            students_path="configs/students.json"
        ),
    )

    # Create the planner
    planner = WorkoutPlannerService(weather_service, routine_service, roster_service)

    # New demo behavior requested:
    # 1) Pick a random class from the class configs
    # 2) Pick a number of random students to join that class
    # 3) Pick a random workout routine from configs/routines.json
    # 4) Print class info + weekly overview

    # Load class configs directly so we preserve multiple entries per day
    classes_cfg = []
    cfgp = Path("configs/classes.json")
    if cfgp.exists():
        try:
            classes_cfg = json.loads(cfgp.read_text(encoding="utf-8"))
        except Exception:
            classes_cfg = []

    if not classes_cfg:
        print("No class configurations found in configs/classes.json")
        return

    rng = random.Random()
    chosen = rng.choice(classes_cfg)

    # Load students pool
    students_pool = []
    sp = Path("configs/students.json")
    if sp.exists():
        try:
            students_pool = json.loads(sp.read_text(encoding="utf-8"))
        except Exception:
            students_pool = []

    # pick number of students
    attendees = []
    if len(students_pool) == 0:
        attendees = []
    elif len(students_pool) == 1:
        attendees = [students_pool[0]]
    else:
        max_n = min(16, len(students_pool))
        n = rng.randint(2, max_n)
        rng.shuffle(students_pool)
        attendees = students_pool[:n]

    # pick a random routine
    routines = {}
    rpath = Path("configs/routines.json")
    if rpath.exists():
        try:
            routines = json.loads(rpath.read_text(encoding="utf-8"))
        except Exception:
            routines = {}

    routine_key = None
    routine = None
    if routines:
        routine_key = rng.choice(list(routines.keys()))
        routine = routines.get(routine_key)

    # Build a ClassSession-like summary for chosen class
    chosen_day = chosen.get("day")
    chosen_name = chosen.get("class_name")
    chosen_time = chosen.get("time")
    chosen_location = chosen.get("location")

    print(f"\n📍 Selected Class: {chosen_name} ({chosen_day} {chosen_time})")
    print(f"Location: {chosen_location}")
    print(
        f"Attendees ({len(attendees)}): {', '.join(attendees) if attendees else 'None'}"
    )
    # Show weather for the chosen class location
    forecast = weather_service.get_wind_forecast(chosen_location or "Huntington Beach")
    print(f"\n🌍 Weather ({forecast.location}):")
    print(f"   Wind Speed: {forecast.wind_speed_mps} m/s")
    if forecast.wind_gust_mps is not None:
        print(f"   Wind Gust: {forecast.wind_gust_mps} m/s")
    print(f"   Description: {forecast.description}")
    if forecast.temperature_celsius is not None:
        print(f"   Temperature: {forecast.temperature_celsius} °C")
    if routine_key and routine:
        print(
            f"Selected Routine: {routine_key} - Duration: {routine.get('duration_minutes')} min - Intensity: {routine.get('intensity')}"
        )
        print(f"Exercises: {', '.join(routine.get('exercises', []))}")

    # Overview of the week using planner (planner will use roster_service for daily rosters)
    print("\nWeekly Overview (Dec 1-7, 2025):\n")
    base_date = date(2025, 12, 1)
    for i in range(7):
        current_date = date(base_date.year, base_date.month, base_date.day + i)
        plan = planner.generate_plan(
            current_date, chosen_location or "Huntington Beach"
        )
        day_name = current_date.strftime("%A")
        routine_name = plan.routine.name
        present_members = (
            sum(1 for m in plan.class_session.roster if m.status == "Present")
            if plan.class_session
            else 0
        )
        print(
            f"{day_name:10} | {routine_name:25} | Attendance: {present_members:2} | Duration: {plan.routine.duration_minutes:3} min | Intensity: {plan.routine.intensity:6}"
        )

    print("\n" + "=" * 60)
    print("✅ Demo completed successfully!\n")


if __name__ == "__main__":
    main()
