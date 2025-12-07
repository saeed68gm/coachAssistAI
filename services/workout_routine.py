from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any


@dataclass
class WorkoutRoutine:
    day: str  # Monday, Tuesday, etc.
    name: str
    exercises: list[str]
    duration_minutes: int
    intensity: str  # Low, Medium, High


class WorkoutRoutineService:
    """Service to fetch and manage workout routines.

    Routines are loaded from `configs/routines.json` which contains template
    entries keyed by numeric strings ("1", "2", ...). We map weekdays to
    those templates in order: Monday->first key, Tuesday->second, ..., Saturday->6th,
    Sunday->last key.
    """

    def __init__(self, config_path: str = "configs/routines.json") -> None:
        self.config_path = Path(config_path)
        self.templates: dict[str, dict[str, Any]] = {}
        self.weekday_map: dict[str, str] = {}
        self._load_templates()

    def _load_templates(self) -> None:
        if not self.config_path.exists():
            # Leave templates empty; callers should handle None returns.
            return

        try:
            raw = json.loads(self.config_path.read_text(encoding="utf-8"))
        except Exception:
            raw = {}

        # Expect raw to be a dict of numeric-string keys to template dicts
        # e.g., {"1": {...}, "2": {...}}
        self.templates = {k: v for k, v in raw.items() if isinstance(v, dict)}

        # Build weekday -> template key mapping
        keys = sorted(self.templates.keys(), key=lambda x: int(x) if x.isdigit() else x)
        weekdays = [
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday",
        ]
        for i, day in enumerate(weekdays):
            if i < len(keys):
                self.weekday_map[day] = keys[i]
            else:
                # If templates < 7, map remaining days to last template
                self.weekday_map[day] = keys[-1] if keys else ""

    def _build_routine_from_template(
        self, day: str, template: dict[str, Any]
    ) -> WorkoutRoutine:
        name = template.get("name") or f"{day} Routine"
        exercises = template.get("exercises", [])
        duration = int(template.get("duration_minutes", 0))
        intensity = template.get("intensity", "Medium")
        return WorkoutRoutine(
            day=day,
            name=name,
            exercises=exercises,
            duration_minutes=duration,
            intensity=intensity,
        )

    def get_routine_for_day(self, day_name: str) -> WorkoutRoutine | None:
        """Get the workout routine for a specific weekday name.

        Args:
            day_name: Day of the week (e.g., "Monday")

        Returns:
            WorkoutRoutine or None if templates not available
        """
        key = self.weekday_map.get(day_name)
        if not key:
            return None
        template = self.templates.get(key)
        if not template:
            return None
        return self._build_routine_from_template(day_name, template)

    def get_routine_for_date(self, target_date: date) -> WorkoutRoutine | None:
        day_name = target_date.strftime("%A")
        return self.get_routine_for_day(day_name)

    def get_all_routines(self) -> dict[str, WorkoutRoutine]:
        """Return a mapping of weekday -> WorkoutRoutine (for available templates)."""
        result: dict[str, WorkoutRoutine] = {}
        for day, key in self.weekday_map.items():
            tpl = self.templates.get(key)
            if tpl:
                result[day] = self._build_routine_from_template(day, tpl)
        return result
