"""Small command-line demonstration of PawPal+."""
from datetime import date
from pawpal_system import Owner, Pet, Scheduler, Task


def build_demo() -> tuple[Owner, Scheduler]:
    """Create a reproducible demo with two pets and three care tasks."""
    owner = Owner("Jordan")
    mochi = Pet("Mochi", "dog")
    pepper = Pet("Pepper", "cat")
    today = date.today()
    mochi.add_task(Task("Morning walk", "08:00", 30, "high", "daily", today))
    mochi.add_task(Task("Dinner", "18:00", 10, "high", "daily", today))
    pepper.add_task(Task("Breakfast", "08:15", 10, "high", "daily", today))
    owner.add_pet(mochi)
    owner.add_pet(pepper)
    return owner, Scheduler(owner)


def main() -> None:
    owner, scheduler = build_demo()
    print(f"PawPal+ schedule for {owner.name}")
    print(scheduler.explain_schedule())
    conflicts = scheduler.find_conflicts()
    if conflicts:
        print("\nSchedule conflicts:")
        for first, second in conflicts:
            print(f"- {first.title} ({first.pet_name}) overlaps {second.title} ({second.pet_name})")
    else:
        print("\nNo schedule conflicts detected.")


if __name__ == "__main__":
    main()
