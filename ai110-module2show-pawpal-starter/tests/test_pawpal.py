from datetime import date, timedelta

import pytest

from pawpal_system import Owner, Pet, Scheduler, Task


def setup_owner():
    owner = Owner("Jordan")
    owner.add_pet(Pet("Mochi", "dog"))
    owner.add_pet(Pet("Pepper", "cat"))
    return owner


def test_task_completion():
    task = Task("Feeding", "08:00", 10)
    assert task.mark_completed() is None
    assert task.completed is True


def test_add_task_to_pet_and_owner():
    owner = setup_owner()
    task = Task("Walk", "08:00", 30)
    owner.find_pet("Mochi").add_task(task)
    assert task.pet_name == "Mochi"
    assert owner.get_all_tasks() == [task]


def test_schedule_sorted_by_time_and_filters():
    owner = setup_owner()
    today = date.today()
    owner.find_pet("Mochi").add_task(Task("Later", "10:00", 10, due_date=today))
    owner.find_pet("Pepper").add_task(Task("Early", "07:00", 10, due_date=today))
    owner.find_pet("Mochi").add_task(Task("Done", "08:00", 10, due_date=today, completed=True))
    scheduler = Scheduler(owner)
    assert [t.title for t in scheduler.get_schedule()] == ["Early", "Later"]
    assert [t.title for t in scheduler.get_schedule(pet_name="Mochi")] == ["Later"]
    assert [t.title for t in scheduler.get_schedule(completed=True)] == ["Done"]


def test_daily_recurrence_creates_next_day_task():
    owner = setup_owner()
    task = Task("Medication", "09:00", 5, recurrence="daily", due_date=date.today())
    owner.find_pet("Mochi").add_task(task)
    next_task = Scheduler(owner).complete_task(task)
    assert task.completed
    assert next_task is not None
    assert next_task.due_date == task.due_date + timedelta(days=1)
    assert next_task.completed is False
    assert next_task in owner.find_pet("Mochi").tasks


def test_weekly_recurrence_creates_next_week_task():
    owner = setup_owner()
    task = Task("Grooming", "09:00", 20, recurrence="weekly", due_date=date.today())
    owner.find_pet("Mochi").add_task(task)
    next_task = Scheduler(owner).complete_task(task)
    assert next_task.due_date == task.due_date + timedelta(days=7)


def test_overlapping_tasks_are_conflicts_across_pets():
    owner = setup_owner()
    today = date.today()
    owner.find_pet("Mochi").add_task(Task("Walk", "08:00", 30, due_date=today))
    owner.find_pet("Pepper").add_task(Task("Feeding", "08:20", 10, due_date=today))
    owner.find_pet("Pepper").add_task(Task("Later", "09:00", 10, due_date=today))
    conflicts = Scheduler(owner).find_conflicts(today)
    assert len(conflicts) == 1
    assert {conflicts[0][0].title, conflicts[0][1].title} == {"Walk", "Feeding"}


def test_invalid_time_and_duration_rejected():
    with pytest.raises(ValueError):
        Task("Walk", "25:61", 10)
    with pytest.raises(ValueError):
        Task("Walk", "08:00", 0)


def test_duplicate_pet_name_rejected_case_insensitively():
    owner = setup_owner()
    with pytest.raises(ValueError):
        owner.add_pet(Pet("mochi", "dog"))
