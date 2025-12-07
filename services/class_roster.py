from __future__ import annotations

import json
import random
from dataclasses import dataclass
from datetime import date
from pathlib import Path


@dataclass
class ClassMember:
    name: str
    status: str  # "Present", "Absent", "Excused"


@dataclass
class ClassSession:
    day: str  # Monday, Tuesday, etc.
    class_name: str
    time: str
    roster: list[ClassMember]
    location: str | None = None


class ClassRosterService:
    """Service to fetch and manage class rosters organized by day.

    Roster and class configs are loaded from `configs/classes.json` by default. The
    actual attendees are provided by an external attendance service; a simple
    `DummyAttendanceService` is provided which draws from `configs/students.json`.
    """

    ALLOWED_LOCATIONS = {
        "Huntington Beach",
        "Irvine",
        "Long Beach",
        "San Diego",
        "Santa Monica",
    }

    def __init__(
        self, config_path: str | None = None, attendance_service: object | None = None
    ) -> None:
        # Attendance service that will provide dynamic rosters
        self.attendance_service = attendance_service or DummyAttendanceService()

        # Load class configs either from provided JSON or defaults
        classes = {}
        # If no config_path provided, try default location 'configs/classes.json'
        cfg_path = config_path or "configs/classes.json"
        path = Path(cfg_path)
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                for entry in data:
                    day = entry.get("day")
                    if not day:
                        continue
                    classes[day] = entry
            except Exception:
                classes = {}

        # Build ROSTERS by asking attendance service for attendees (roster contains attendees only)
        rosters: dict[str, ClassSession] = {}
        for day, info in classes.items():
            class_name = info.get("class_name", "Unnamed Class")
            time = info.get("time", "00:00")
            location = info.get("location")
            # enforce allowed locations
            if location not in self.ALLOWED_LOCATIONS:
                location = None

            attendees = self.attendance_service.get_attendees(
                class_name=class_name, day=day, location=location
            )
            rosters[day] = ClassSession(
                day=day,
                class_name=class_name,
                time=time,
                roster=attendees,
                location=location,
            )

        self.ROSTERS = rosters

    def get_roster_for_day(self, day_name: str) -> ClassSession | None:
        """Get the class roster for a specific day.

        Args:
            day_name: Day of the week (e.g., "Monday", "Tuesday")

        Returns:
            ClassSession or None if day not found
        """
        return self.ROSTERS.get(day_name)

    def get_roster_for_date(self, target_date: date) -> ClassSession | None:
        """Get the class roster for a specific date.

        Args:
            target_date: A date object

        Returns:
            ClassSession or None if day not found
        """
        day_name = target_date.strftime("%A")
        return self.get_roster_for_day(day_name)

    def get_all_rosters(self) -> dict[str, ClassSession]:
        """Get all class rosters."""
        return self.ROSTERS.copy()

    def get_present_members(self, day_name: str) -> list[ClassMember]:
        """Get members present on a specific day."""
        session = self.get_roster_for_day(day_name)
        if not session:
            return []
        return [m for m in session.roster if m.status == "Present"]


class DummyStudentDirectory:
    """Simple directory of possible students loaded from `configs/students.json` if available."""

    @classmethod
    def load_students(cls, path: str | None = None) -> list[str]:
        cfg = Path(path or "configs/students.json")
        if cfg.exists():
            try:
                data = json.loads(cfg.read_text(encoding="utf-8"))
                if isinstance(data, list) and all(isinstance(x, str) for x in data):
                    return data
            except Exception:
                return []
        # No hardcoded defaults; return empty list if file missing or invalid
        return []


class DummyAttendanceService:
    """Dummy external attendance service that returns a random list of attendees.

    The roster returned contains between 2 and 16 ClassMember entries with status 'Present'.
    Uses a deterministic random generator to make tests reproducible.
    """

    def __init__(self, seed: int = 42, students_path: str | None = None) -> None:
        self.rand = random.Random(seed)
        self.pool = DummyStudentDirectory.load_students(students_path)

    def get_attendees(
        self, *, class_name: str, day: str | None = None, location: str | None = None
    ) -> list[ClassMember]:
        pool = self.pool.copy()
        # handle small pools gracefully
        if len(pool) == 0:
            return []
        if len(pool) == 1:
            return [ClassMember(name=pool[0], status="Present")]

        max_n = min(16, len(pool))
        n = self.rand.randint(2, max_n)
        self.rand.shuffle(pool)
        selected = pool[:n]
        return [ClassMember(name=name, status="Present") for name in selected]
