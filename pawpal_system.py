"""Core data models and scheduling logic for PawPal+.

An Owner has Pets, each Pet has Tasks, and a Scheduler builds a daily
schedule from all of an owner's tasks.

Conventions:
    - Times are 24-hour "HH:MM" strings in local time (e.g. "08:00", "18:30").
    - Durations are whole minutes.
    - Completing a recurring task creates a fresh, incomplete copy for the
      next day (daily) or next week (weekly).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from typing import Iterable, Optional


def _parse_time(value: str) -> time:
    """Convert an "HH:MM" string into a time object.

    Raises:
        ValueError: If the value is not a valid 24-hour "HH:MM" time.
    """
    try:
        return datetime.strptime(value, "%H:%M").time()
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Time must use 24-hour HH:MM format: {value!r}") from exc


@dataclass
class Task:
    """One care activity for a pet, such as a walk or a meal.

    Attributes:
        title: Short name shown in the schedule.
        start_time: When the task starts, as "HH:MM".
        duration_minutes: How long the task takes, in minutes.
        priority: "low", "medium", or "high".
        recurrence: "none", "daily", or "weekly".
        due_date: The day the task is scheduled for (defaults to today).
        completed: Whether the task has been done.
        pet_name: Name of the pet this task belongs to; set by Pet.add_task().
        notes: Optional free-text notes.
    """
    title: str
    start_time: str
    duration_minutes: int
    priority: str = "medium"
    recurrence: str = "none"  # none, daily, weekly
    due_date: date = field(default_factory=date.today)
    completed: bool = False
    pet_name: Optional[str] = None
    notes: str = ""

    def __post_init__(self) -> None:
        self.start_time = _parse_time(self.start_time).strftime("%H:%M")
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
        """Start time as minutes after midnight (e.g. "08:30" -> 510)."""
        t = _parse_time(self.start_time)
        return t.hour * 60 + t.minute

    @property
    def end_minutes(self) -> int:
        """End time as minutes after midnight (start + duration)."""
        return self.start_minutes + self.duration_minutes

    def mark_completed(self) -> Optional["Task"]:
        """Mark this task as done.

        Returns:
            A new, incomplete Task for the next occurrence if this task
            repeats, otherwise None. Also returns None if the task was
            already completed, so the next occurrence is never created twice.
        """
        if self.completed:
            return None
        self.completed = True
        if self.recurrence == "none":
            return None
        next_date = self.due_date + timedelta(days=1 if self.recurrence == "daily" else 7)
        return Task(
            title=self.title, start_time=self.start_time, duration_minutes=self.duration_minutes,
            priority=self.priority, recurrence=self.recurrence, due_date=next_date,
            completed=False, pet_name=self.pet_name, notes=self.notes,
        )


@dataclass
class Pet:
    """A pet and the list of care tasks assigned to it."""
    name: str
    species: str = "other"
    age: Optional[int] = None
    tasks: list[Task] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Pet name cannot be empty")

    def add_task(self, task: Task) -> None:
        """Add a task to this pet and tag the task with the pet's name."""
        task.pet_name = self.name
        self.tasks.append(task)

    def get_tasks(self, include_completed: bool = True) -> list[Task]:
        """Return this pet's tasks.

        Args:
            include_completed: If False, leave out tasks that are already done.
        """
        return [task for task in self.tasks if include_completed or not task.completed]


@dataclass
class Owner:
    """A person who looks after one or more pets."""
    name: str
    pets: list[Pet] = field(default_factory=list)

    def add_pet(self, pet: Pet) -> None:
        """Register a new pet with this owner.

        Raises:
            ValueError: If a pet with the same name (ignoring case) already exists.
        """
        if any(existing.name.casefold() == pet.name.casefold() for existing in self.pets):
            raise ValueError(f"A pet named {pet.name!r} is already registered")
        self.pets.append(pet)

    def get_all_tasks(self, include_completed: bool = True) -> list[Task]:
        """Return every task across all of this owner's pets.

        Args:
            include_completed: If False, leave out tasks that are already done.
        """
        return [
            task for pet in self.pets
            for task in pet.get_tasks(include_completed=include_completed)
        ]

    def find_pet(self, name: str) -> Pet:
        """Look up one of this owner's pets by name (ignoring case).

        Raises:
            ValueError: If no pet has that name.
        """
        for pet in self.pets:
            if pet.name.casefold() == name.casefold():
                return pet
        raise ValueError(f"No pet named {name!r}")


class Scheduler:
    """Builds, checks, and explains the daily care schedule for one owner."""

    PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}

    def __init__(self, owner: Owner):
        self.owner = owner

    def get_schedule(
        self,
        for_date: Optional[date] = None,
        pet_name: Optional[str] = None,
        completed: Optional[bool] = False,
    ) -> list[Task]:
        """Return the tasks scheduled for one day, in order.

        Tasks are sorted by start time. Tasks that start at the same time are
        ordered high -> medium -> low priority, then alphabetically by title.

        Args:
            for_date: The day to show. Defaults to today.
            pet_name: Only include this pet's tasks (ignoring case).
                Defaults to all pets.
            completed: Which tasks to include:
                False (default) -> only tasks still to do,
                True -> only finished tasks,
                None -> all tasks.
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
        """Find pairs of tasks whose time slots overlap on a given day.

        Tasks for different pets are checked too, since the owner can only
        do one thing at a time. Completed tasks are ignored, and a task that
        ends exactly when another starts is not a conflict.

        Args:
            for_date: The day to check. Defaults to today.

        Returns:
            A list of (earlier task, later task) pairs.
        """
        tasks = self.get_schedule(for_date=for_date)
        conflicts: list[tuple[Task, Task]] = []
        for index, first in enumerate(tasks):
            for second in tasks[index + 1:]:
                if second.start_minutes >= first.end_minutes:
                    break
                if first.start_minutes < second.end_minutes and second.start_minutes < first.end_minutes:
                    conflicts.append((first, second))
        return conflicts

    def complete_task(self, task: Task) -> Optional[Task]:
        """Mark a task as done and schedule its next occurrence if it repeats.

        Returns:
            The newly created next task, or None if the task does not repeat.

        Raises:
            ValueError: If the task's pet is not registered with this owner.
                The task is left unchanged in that case.
        """
        # Look up the pet before mutating the task so a missing pet leaves it unchanged.
        pet = self.owner.find_pet(task.pet_name or "")
        next_task = task.mark_completed()
        if next_task is not None:
            pet.add_task(next_task)
        return next_task

    def explain_schedule(self, tasks: Optional[Iterable[Task]] = None) -> str:
        """Format a schedule as plain text, one task per line.

        Args:
            tasks: The tasks to show. Defaults to today's to-do list from
                get_schedule().

        Returns:
            The schedule text, ending with a note on how tasks are ordered.
        """
        items = list(tasks) if tasks is not None else self.get_schedule()
        if not items:
            return "No tasks scheduled for this date."
        lines = ["Today's Schedule"]
        for task in items:
            lines.append(
                f"{task.start_time} — {task.title} ({task.duration_minutes} min) "
                f"[{task.priority}; {task.pet_name or 'unassigned'}]"
            )
        lines.append("Tasks are ordered by start time; ties are ordered by priority.")
        return "\n".join(lines)
