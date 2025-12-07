from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from services.class_roster import ClassRosterService, ClassSession
from services.weather import OpenMeteoWeatherService, WindForcast
from services.workout_routine import WorkoutRoutine, WorkoutRoutineService


@dataclass
class WorkoutPlan:
    date: str
    routine: WorkoutRoutine
    wind_forecast: WindForcast
    class_session: ClassSession | None
    recommended_adjustments: list[str]
    plan_summary: str


class WorkoutPlannerService:
    """Service that generates a daily workout plan based on weather, routine, and class roster."""

    def __init__(
        self,
        weather_service: OpenMeteoWeatherService,
        routine_service: WorkoutRoutineService,
        roster_service: ClassRosterService,
    ) -> None:
        self.weather_service = weather_service
        self.routine_service = routine_service
        self.roster_service = roster_service

    def generate_plan(self, target_date: date, location: str) -> WorkoutPlan:
        """Generate a comprehensive workout plan for a specific date.

        Args:
            target_date: The date to generate the plan for
            location: The location for weather data

        Returns:
            WorkoutPlan: A complete workout plan with adjustments
        """
        # Get day name
        day_name = target_date.strftime("%A")

        # Fetch routine and class session first
        routine = self.routine_service.get_routine_for_date(target_date)
        class_session = self.roster_service.get_roster_for_date(target_date)

        # Determine weather location: prefer class location if available
        weather_location = (
            class_session.location
            if (class_session and getattr(class_session, "location", None))
            else location
        )

        # Fetch weather for chosen location
        wind_forecast = self.weather_service.get_wind_forecast(weather_location)

        if not routine:
            raise ValueError(f"No routine found for {day_name}")

        # Generate recommended adjustments based on conditions
        adjustments = self._generate_adjustments(routine, wind_forecast, class_session)

        # Create plan summary
        plan_summary = self._create_summary(
            day_name, routine, wind_forecast, class_session, adjustments
        )

        return WorkoutPlan(
            date=target_date.isoformat(),
            routine=routine,
            wind_forecast=wind_forecast,
            class_session=class_session,
            recommended_adjustments=adjustments,
            plan_summary=plan_summary,
        )

    def _generate_adjustments(
        self,
        routine: WorkoutRoutine,
        wind_forecast: WindForcast,
        class_session: ClassSession | None,
    ) -> list[str]:
        """Generate workout adjustments based on conditions."""
        adjustments = []

        # Weather-based adjustments
        if wind_forecast.wind_speed_mps > 10:
            adjustments.append(
                f"⚠️ High wind speed ({wind_forecast.wind_speed_mps} m/s) - "
                "consider moving outdoor activities indoors"
            )
        elif wind_forecast.wind_speed_mps > 5:
            adjustments.append(
                f"⚡ Moderate wind ({wind_forecast.wind_speed_mps} m/s) - "
                "adjust form for exercises, especially standing movements"
            )

        if "rain" in wind_forecast.description.lower():
            adjustments.append("🌧️ Rainy conditions - ensure proper footwear and safety")

        if (
            "clear" in wind_forecast.description.lower()
            or "sunny" in wind_forecast.description.lower()
        ):
            adjustments.append("☀️ Great weather - consider outdoor cardio session")

        # Temperature-based adjustments
        temp = getattr(wind_forecast, "temperature_celsius", None)
        if temp is not None:
            if temp >= 30:
                adjustments.append(
                    f"🔥 High temperature ({temp}°C) - shorten outdoor cardio and hydrate"
                )
            elif temp <= 5:
                adjustments.append(
                    f"❄️ Low temperature ({temp}°C) - layer up and consider indoor warm-up"
                )

        # Routine intensity adjustments
        if routine.intensity == "High":
            adjustments.append(
                "💪 High intensity workout - ensure adequate hydration and recovery"
            )

        # Class roster adjustments
        if class_session:
            present_count = sum(
                1 for m in class_session.roster if m.status == "Present"
            )
            total_count = len(class_session.roster)
            if present_count < total_count * 0.5:
                adjustments.append(
                    f"📊 Low class attendance ({present_count}/{total_count}) - "
                    "consider additional motivation or adjustments"
                )
            else:
                adjustments.append(
                    f"✅ Strong class attendance ({present_count}/{total_count})"
                )

        if not adjustments:
            adjustments.append("✨ Optimal conditions - proceed with standard routine")

        return adjustments

    def _create_summary(
        self,
        day_name: str,
        routine: WorkoutRoutine,
        wind_forecast: WindForcast,
        class_session: ClassSession | None,
        adjustments: list[str],
    ) -> str:
        """Create a formatted summary of the workout plan."""
        summary_lines = [
            f"📅 Daily Workout Plan - {day_name}",
            "=" * 50,
            f"\n🏋️ Routine: {routine.name}",
            f"   Duration: {routine.duration_minutes} minutes",
            f"   Intensity: {routine.intensity}",
            f"   Exercises: {', '.join(routine.exercises)}",
            f"\n🌍 Weather ({wind_forecast.location}):",
            f"   Wind Speed: {wind_forecast.wind_speed_mps} m/s",
            f"   Description: {wind_forecast.description}",
            f"   Temperature: {getattr(wind_forecast, 'temperature_celsius', 'N/A')} °C",
        ]

        if wind_forecast.wind_gust_mps:
            summary_lines.append(f"   Wind Gust: {wind_forecast.wind_gust_mps} m/s")

        if class_session:
            present_count = sum(
                1 for m in class_session.roster if m.status == "Present"
            )
            summary_lines.extend(
                [
                    f"\n👥 Class Session: {class_session.class_name}",
                    f"   Time: {class_session.time}",
                    f"   Attendance: {present_count}/{len(class_session.roster)} members present",
                ]
            )

        summary_lines.extend(
            [
                "\n💡 Recommendations:",
            ]
        )
        for adj in adjustments:
            summary_lines.append(f"   • {adj}")

        return "\n".join(summary_lines)
