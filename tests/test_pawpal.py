from datetime import date

import pytest

from pawpal_system import Owner, Pet, Scheduler, Task

DAY = date(2026, 3, 10)


def make_scheduler(*pet_names):
    """Return a Scheduler for an owner with the given (empty) pets."""
    owner = Owner(name="Jordan")
    for name in pet_names:
        owner.add_pet(Pet(name=name))
    return Scheduler(owner)


def add(scheduler, pet_name, title, start_time, duration=30, **kwargs):
    """Create a task due on DAY, assign it to a pet, and return it."""
    kwargs.setdefault("due_date", DAY)
    task = Task(title=title, start_time=start_time, duration_minutes=duration, **kwargs)
    scheduler.owner.find_pet(pet_name).add_task(task)
    return task


def titles(tasks):
    return [task.title for task in tasks]


def conflict_titles(conflicts):
    return [(first.title, second.title) for first, second in conflicts]


# --- Basics -----------------------------------------------------------------

def test_mark_completed_changes_status():
    task = Task(title="Morning walk", start_time="08:00", duration_minutes=30)
    assert task.completed is False
    task.mark_completed()
    assert task.completed is True


def test_add_task_increases_pet_task_count():
    pet = Pet(name="Mochi", species="dog")
    assert len(pet.tasks) == 0
    pet.add_task(Task(title="Feed", start_time="07:30", duration_minutes=10))
    assert len(pet.tasks) == 1


# --- Sorting ----------------------------------------------------------------

def test_schedule_is_sorted_by_start_time():
    scheduler = make_scheduler("Mochi")
    add(scheduler, "Mochi", "Dinner", "18:00")
    add(scheduler, "Mochi", "Walk", "08:00")
    add(scheduler, "Mochi", "Lunch", "12:30")
    assert titles(scheduler.get_schedule(for_date=DAY)) == ["Walk", "Lunch", "Dinner"]


def test_single_digit_hours_sort_numerically_not_alphabetically():
    scheduler = make_scheduler("Mochi")
    add(scheduler, "Mochi", "Late", "10:00")
    early = add(scheduler, "Mochi", "Early", "9:00")
    assert early.start_time == "09:00"
    assert titles(scheduler.get_schedule(for_date=DAY)) == ["Early", "Late"]


def test_same_start_time_orders_by_priority_high_first():
    scheduler = make_scheduler("Mochi")
    add(scheduler, "Mochi", "Low", "08:00", priority="low")
    add(scheduler, "Mochi", "High", "08:00", priority="high")
    add(scheduler, "Mochi", "Medium", "08:00", priority="medium")
    assert titles(scheduler.get_schedule(for_date=DAY)) == ["High", "Medium", "Low"]


def test_same_start_time_and_priority_orders_by_title_ignoring_case():
    scheduler = make_scheduler("Mochi")
    add(scheduler, "Mochi", "brush", "08:00")
    add(scheduler, "Mochi", "Feed", "08:00")
    add(scheduler, "Mochi", "apple", "08:00")
    assert titles(scheduler.get_schedule(for_date=DAY)) == ["apple", "brush", "Feed"]


def test_schedule_merges_and_sorts_tasks_across_pets():
    scheduler = make_scheduler("Mochi", "Pepper")
    add(scheduler, "Mochi", "Mochi dinner", "18:00")
    add(scheduler, "Pepper", "Pepper breakfast", "08:15")
    add(scheduler, "Mochi", "Mochi walk", "08:00")
    assert titles(scheduler.get_schedule(for_date=DAY)) == [
        "Mochi walk", "Pepper breakfast", "Mochi dinner",
    ]


# --- Filtering --------------------------------------------------------------

def test_schedule_only_includes_tasks_for_requested_date():
    scheduler = make_scheduler("Mochi")
    add(scheduler, "Mochi", "Today", "08:00")
    add(scheduler, "Mochi", "Tomorrow", "08:00", due_date=date(2026, 3, 11))
    assert titles(scheduler.get_schedule(for_date=DAY)) == ["Today"]


def test_schedule_filters_by_pet_name_ignoring_case():
    scheduler = make_scheduler("Mochi", "Pepper")
    add(scheduler, "Mochi", "Walk", "08:00")
    add(scheduler, "Pepper", "Feed", "09:00")
    assert titles(scheduler.get_schedule(for_date=DAY, pet_name="pePPer")) == ["Feed"]


@pytest.mark.parametrize("completed, expected", [
    (False, ["Open"]),
    (True, ["Done"]),
    (None, ["Done", "Open"]),
])
def test_schedule_completed_filter(completed, expected):
    scheduler = make_scheduler("Mochi")
    add(scheduler, "Mochi", "Done", "08:00").mark_completed()
    add(scheduler, "Mochi", "Open", "09:00")
    assert titles(scheduler.get_schedule(for_date=DAY, completed=completed)) == expected


def test_explain_schedule_with_no_tasks():
    scheduler = make_scheduler("Mochi")
    assert scheduler.explain_schedule([]) == "No tasks scheduled for this date."


# --- Recurrence -------------------------------------------------------------

@pytest.mark.parametrize("recurrence, due, expected", [
    ("daily", date(2026, 3, 10), date(2026, 3, 11)),
    ("weekly", date(2026, 3, 10), date(2026, 3, 17)),
    ("daily", date(2026, 1, 31), date(2026, 2, 1)),     # month boundary
    ("daily", date(2026, 12, 31), date(2027, 1, 1)),    # year boundary
    ("daily", date(2028, 2, 28), date(2028, 2, 29)),    # leap day
    ("weekly", date(2026, 2, 25), date(2026, 3, 4)),    # weekly across February
])
def test_recurring_task_next_due_date(recurrence, due, expected):
    task = Task(title="Walk", start_time="08:00", duration_minutes=30,
                recurrence=recurrence, due_date=due)
    assert task.mark_completed().due_date == expected


def test_next_occurrence_copies_details_and_is_incomplete():
    task = Task(title="Meds", start_time="07:45", duration_minutes=5, priority="high",
                recurrence="daily", due_date=DAY, pet_name="Mochi", notes="With food")
    next_task = task.mark_completed()
    assert next_task is not task
    assert next_task.completed is False
    assert (next_task.title, next_task.start_time, next_task.duration_minutes,
            next_task.priority, next_task.recurrence, next_task.pet_name, next_task.notes) == (
            "Meds", "07:45", 5, "high", "daily", "Mochi", "With food")


def test_non_recurring_task_has_no_next_occurrence():
    scheduler = make_scheduler("Mochi")
    task = add(scheduler, "Mochi", "Vet visit", "10:00")
    assert scheduler.complete_task(task) is None
    assert task.completed is True
    assert len(scheduler.owner.find_pet("Mochi").tasks) == 1


def test_completing_twice_does_not_create_duplicate_occurrence():
    scheduler = make_scheduler("Mochi")
    task = add(scheduler, "Mochi", "Walk", "08:00", recurrence="daily")
    assert scheduler.complete_task(task) is not None
    assert scheduler.complete_task(task) is None
    assert len(scheduler.owner.find_pet("Mochi").tasks) == 2


def test_complete_recurring_task_adds_next_occurrence_to_pet():
    scheduler = make_scheduler("Mochi")
    task = add(scheduler, "Mochi", "Walk", "08:00", recurrence="daily")
    next_task = scheduler.complete_task(task)
    assert task.completed is True
    assert next_task in scheduler.owner.find_pet("Mochi").tasks
    assert next_task.start_time == "08:00"


def test_next_occurrence_appears_in_next_days_schedule():
    scheduler = make_scheduler("Mochi")
    task = add(scheduler, "Mochi", "Walk", "08:00", recurrence="daily")
    scheduler.complete_task(task)
    assert scheduler.get_schedule(for_date=DAY) == []
    assert titles(scheduler.get_schedule(for_date=date(2026, 3, 11))) == ["Walk"]


def test_complete_task_with_missing_pet_leaves_task_unchanged():
    task = Task(title="Orphan task", start_time="09:00", duration_minutes=15, recurrence="daily")
    scheduler = Scheduler(Owner(name="Jordan"))
    with pytest.raises(ValueError):
        scheduler.complete_task(task)
    assert task.completed is False


# --- Conflicts --------------------------------------------------------------

def test_no_conflicts_when_tasks_are_separate():
    scheduler = make_scheduler("Mochi")
    add(scheduler, "Mochi", "Walk", "08:00", duration=30)
    add(scheduler, "Mochi", "Feed", "09:00", duration=10)
    assert scheduler.find_conflicts(for_date=DAY) == []


def test_back_to_back_tasks_do_not_conflict():
    scheduler = make_scheduler("Mochi")
    add(scheduler, "Mochi", "Walk", "08:00", duration=30)
    add(scheduler, "Mochi", "Feed", "08:30", duration=10)
    assert scheduler.find_conflicts(for_date=DAY) == []


def test_partially_overlapping_tasks_conflict():
    scheduler = make_scheduler("Mochi")
    add(scheduler, "Mochi", "Walk", "08:00", duration=30)
    add(scheduler, "Mochi", "Feed", "08:29", duration=10)
    assert conflict_titles(scheduler.find_conflicts(for_date=DAY)) == [("Walk", "Feed")]


def test_tasks_starting_at_same_time_conflict():
    scheduler = make_scheduler("Mochi")
    add(scheduler, "Mochi", "Walk", "08:00", duration=30, priority="high")
    add(scheduler, "Mochi", "Feed", "08:00", duration=5, priority="low")
    assert conflict_titles(scheduler.find_conflicts(for_date=DAY)) == [("Walk", "Feed")]


def test_long_task_conflicts_with_every_task_inside_it():
    scheduler = make_scheduler("Mochi")
    add(scheduler, "Mochi", "Grooming", "08:00", duration=120)
    add(scheduler, "Mochi", "Feed", "08:30", duration=10)
    add(scheduler, "Mochi", "Meds", "09:00", duration=5)
    add(scheduler, "Mochi", "Walk", "10:00", duration=30)  # starts as Grooming ends
    assert conflict_titles(scheduler.find_conflicts(for_date=DAY)) == [
        ("Grooming", "Feed"), ("Grooming", "Meds"),
    ]


def test_chain_of_overlaps_only_pairs_tasks_that_actually_overlap():
    scheduler = make_scheduler("Mochi")
    add(scheduler, "Mochi", "A", "08:00", duration=30)   # 08:00-08:30
    add(scheduler, "Mochi", "B", "08:20", duration=30)   # 08:20-08:50
    add(scheduler, "Mochi", "C", "08:40", duration=30)   # 08:40-09:10
    assert conflict_titles(scheduler.find_conflicts(for_date=DAY)) == [("A", "B"), ("B", "C")]


def test_tasks_for_different_pets_can_conflict():
    scheduler = make_scheduler("Mochi", "Pepper")
    add(scheduler, "Mochi", "Walk Mochi", "08:00", duration=30)
    add(scheduler, "Pepper", "Feed Pepper", "08:15", duration=10)
    conflicts = scheduler.find_conflicts(for_date=DAY)
    assert conflict_titles(conflicts) == [("Walk Mochi", "Feed Pepper")]
    assert {conflicts[0][0].pet_name, conflicts[0][1].pet_name} == {"Mochi", "Pepper"}


def test_same_time_on_different_dates_does_not_conflict():
    scheduler = make_scheduler("Mochi")
    add(scheduler, "Mochi", "Walk", "08:00")
    add(scheduler, "Mochi", "Walk tomorrow", "08:00", due_date=date(2026, 3, 11))
    assert scheduler.find_conflicts(for_date=DAY) == []


def test_completed_tasks_are_ignored_for_conflicts():
    scheduler = make_scheduler("Mochi")
    add(scheduler, "Mochi", "Walk", "08:00", duration=30).mark_completed()
    add(scheduler, "Mochi", "Feed", "08:10", duration=10)
    assert scheduler.find_conflicts(for_date=DAY) == []
