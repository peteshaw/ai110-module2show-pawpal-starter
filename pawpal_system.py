"""Core domain models and scheduling logic for PawPal+.

Times use local 24-hour ``HH:MM`` strings. A task's duration is measured in
minutes, and recurrence creates a new, incomplete task after completion.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from typing import Iterable, Optional


def _parse_time(value: str) -> time:
    """Parse a 24-hour HH:MM time and raise ValueError for invalid input."""
    try:
        return datetime.strptime(value, "%H:%M").time()
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Time must use 24-hour HH:MM format: {value!r}") from exc


@dataclass
class Task:
    """A single care activity assigned to a pet."""
    title: str
    time: str
    duration_minutes: int
    priority: str = "medium"
    recurrence: str = "none"  # none, daily, weekly
    due_date: date = field(default_factory=date.today)
    completed: bool = False
    pet_name: Optional[str] = None
    notes: str = ""

    def __post_init__(self) -> None:
        self.time = _parse_time(self.time).strftime("%H:%M")
        if not self.title.strip():
            raise ValueError("Task title cannot be empty")
        if not isinstance(self.duration_minutes, int) or self.duration_minutes < 1:
            raise ValueError("duration_minutes must be a positive integer")
        if self.priority not in {"low", "medium", "high"}:
            raise ValueError("priority must be low, medium, or high")
        if self.recurrence not in {"none", "daily", "weekly"}:
            raise ValueError("recurrence must be none, daily, or weekly")

    @property
    def start_minutes(self) -> int:
        """Return the start time as minutes after midnight."""
        t = _parse_time(self.time)
        return t.hour * 60 + t.minute

    @property
    def end_minutes(self) -> int:
        """Return the end time as minutes after midnight."""
        return self.start_minutes + self.duration_minutes

    def mark_completed(self) -> Optional["Task"]:
        """Mark complete and return the next occurrence, if recurring."""
        if self.completed:
            return None
        self.completed = True
        if self.recurrence == "none":
            return None
        next_date = self.due_date + timedelta(days=1 if self.recurrence == "daily" else 7)
        return Task(
            title=self.title, time=self.time, duration_minutes=self.duration_minutes,
            priority=self.priority, recurrence=self.recurrence, due_date=next_date,
            completed=False, pet_name=self.pet_name, notes=self.notes,
        )


@dataclass
class Pet:
    """A pet and the care tasks assigned to it."""
    name: str
    species: str = "other"
    age: Optional[int] = None
    tasks: list[Task] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Pet name cannot be empty")

    def add_task(self, task: Task) -> None:
        """Assign a task to this pet."""
        task.pet_name = self.name
        self.tasks.append(task)

    def get_tasks(self, include_completed: bool = True) -> list[Task]:
        """Return this pet's tasks, optionally excluding completed tasks."""
        return [task for task in self.tasks if include_completed or not task.completed]


@dataclass
class Owner:
    """An owner who manages one or more pets."""
    name: str
    pets: list[Pet] = field(default_factory=list)

    def add_pet(self, pet: Pet) -> None:
        """Add a pet unless a pet with the same name already exists."""
        if any(existing.name.casefold() == pet.name.casefold() for existing in self.pets):
            raise ValueError(f"A pet named {pet.name!r} is already registered")
        self.pets.append(pet)

    def get_all_tasks(self, include_completed: bool = True) -> list[Task]:
        """Return tasks for all pets; Scheduler uses this owner-level interface."""
        return [
            task for pet in self.pets
            for task in pet.get_tasks(include_completed=include_completed)
        ]

    def find_pet(self, name: str) -> Pet:
        """Find a pet by case-insensitive name."""
        for pet in self.pets:
            if pet.name.casefold() == name.casefold():
                return pet
        raise ValueError(f"No pet named {name!r}")


class Scheduler:
    """Sort, filter, and identify conflicts in an owner's care schedule."""

    PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}

    def __init__(self, owner: Owner):
        self.owner = owner

    def get_schedule(
        self,
        for_date: Optional[date] = None,
        pet_name: Optional[str] = None,
        completed: Optional[bool] = False,
    ) -> list[Task]:
        """Return tasks for a date, optionally filtered by pet/completion.

        The default view excludes completed tasks and sorts by start time,
        then descending priority for tasks starting at the same time.
        """
        target_date = for_date or date.today()
        tasks = [
            task for task in self.owner.get_all_tasks()
            if task.due_date == target_date
            and (pet_name is None or (task.pet_name or "").casefold() == pet_name.casefold())
            and (completed is None or task.completed is completed)
        ]
        return sorted(tasks, key=lambda t: (t.start_minutes, self.PRIORITY_ORDER[t.priority], t.title.casefold()))

    def find_conflicts(self, for_date: Optional[date] = None) -> list[tuple[Task, Task]]:
        """Find overlapping task intervals on a date, including cross-pet conflicts."""
        tasks = self.get_schedule(for_date=for_date, completed=None)
        conflicts: list[tuple[Task, Task]] = []
        for index, first in enumerate(tasks):
            for second in tasks[index + 1:]:
                if second.start_minutes >= first.end_minutes:
                    break
                if first.start_minutes < second.end_minutes and second.start_minutes < first.end_minutes:
                    conflicts.append((first, second))
        return conflicts

    def complete_task(self, task: Task) -> Optional[Task]:
        """Complete a task and add its next recurring occurrence to its pet."""
        next_task = task.mark_completed()
        if next_task is not None:
            self.owner.find_pet(task.pet_name or "").add_task(next_task)
        return next_task

    def explain_schedule(self, tasks: Optional[Iterable[Task]] = None) -> str:
        """Render a readable schedule with a short rationale for ordering."""
        items = list(tasks) if tasks is not None else self.get_schedule()
        if not items:
            return "No tasks scheduled for this date."
        lines = ["Today's Schedule"]
        for task in items:
            lines.append(
                f"{task.time} — {task.title} ({task.duration_minutes} min) "
                f"[{task.priority}; {task.pet_name or 'unassigned'}]"
            )
        lines.append("Tasks are ordered by start time; ties are ordered by priority.")
        return "\n".join(lines)
