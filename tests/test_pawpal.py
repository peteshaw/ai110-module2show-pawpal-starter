import pytest

from pawpal_system import Owner, Pet, Scheduler, Task


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


def test_complete_task_with_missing_pet_leaves_task_unchanged():
    task = Task(title="Orphan task", start_time="09:00", duration_minutes=15, recurrence="daily")
    scheduler = Scheduler(Owner(name="Jordan"))
    with pytest.raises(ValueError):
        scheduler.complete_task(task)
    assert task.completed is False


def test_complete_recurring_task_adds_next_occurrence_to_pet():
    owner = Owner(name="Jordan")
    pet = Pet(name="Mochi")
    owner.add_pet(pet)
    task = Task(title="Walk", start_time="08:00", duration_minutes=30, recurrence="daily")
    pet.add_task(task)
    next_task = Scheduler(owner).complete_task(task)
    assert task.completed is True
    assert next_task in pet.tasks
    assert next_task.start_time == "08:00"
