# PawPal+ — Pet Care Scheduler

PawPal+ is a small Python and Streamlit app for tracking care tasks for multiple pets. It demonstrates object-oriented design, date-aware scheduling, recurring tasks, filtering, overlap detection, and automated tests.

## Features

- **Task, Pet, Owner, Scheduler classes** separate task data, pet task lists, owner-level aggregation, and scheduling behavior.
- Add pets and care tasks with a date, start time, duration, priority, notes, and recurrence (`none`, `daily`, `weekly`).
- View a schedule sorted by start time. When tasks share a start time, higher priority appears first.
- Filter the schedule by pet and completion status.
- Mark tasks complete. Daily and weekly tasks create a new incomplete occurrence one day or seven days later.
- Detect overlapping task time ranges, including conflicts between different pets.
- Streamlit state keeps the owner and tasks while interacting with the app.

## Setup

Python 3.10+ is recommended.

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Run the app

Launch the interactive UI:

```bash
streamlit run app.py
```

Run the CLI demonstration:

```bash
python main.py
```

The CLI demo creates an owner with two pets and three tasks dated for the current day. It prints the schedule and flags overlapping tasks.

## Example CLI output

The following is the output from `python main.py` in the development environment (the schedule date is generated at runtime):

```text
PawPal+ schedule for Jordan
Today's Schedule
08:00 — Morning walk (30 min) [high; Mochi]
08:15 — Breakfast (10 min) [high; Pepper]
18:00 — Dinner (10 min) [high; Mochi]
Tasks are ordered by start time; ties are ordered by priority.

Schedule conflicts:
- Morning walk (Mochi) overlaps Breakfast (Pepper)
```

The conflict is intentional in the demo: Mochi's 08:00–08:30 walk overlaps Pepper's 08:15–08:25 breakfast task.

## Scheduling behavior

| Feature | Implementation | Notes |
|---|---|---|
| Task sorting | `Scheduler.get_schedule()` | Start time ascending; priority descending for equal start times; title breaks remaining ties. |
| Filtering | `Scheduler.get_schedule()` | Supports a date, pet name, and completion status. By default it shows incomplete tasks for the current date. |
| Conflict handling | `Scheduler.find_conflicts()` | Reports overlapping time intervals, including tasks assigned to different pets. Adjacent tasks whose end/start times match are not considered overlapping. |
| Recurring tasks | `Task.mark_completed()` and `Scheduler.complete_task()` | Completing daily/weekly tasks creates the next occurrence on the same pet. Non-recurring tasks do not repeat. |
| Explanation | `Scheduler.explain_schedule()` | Prints each task's time, duration, priority, and pet, then explains the ordering rule. |

Times are local 24-hour `HH:MM` strings. This is a small single-day planner, not a calendar/time-zone service. Tasks that run past midnight are not split across dates.

## Tests

Run the suite from the project root:

```bash
python -m pytest -v
```

The current test suite covers task completion, task assignment and owner aggregation, time sorting, pet/completion filters, daily and weekly recurrence, overlapping tasks across pets, invalid time/duration validation, and duplicate pet names.

Latest local test run (`python -m pytest -v`):

```text
tests/test_pawpal.py::test_task_completion PASSED
tests/test_pawpal.py::test_add_task_to_pet_and_owner PASSED
tests/test_pawpal.py::test_schedule_sorted_by_time_and_filters PASSED
tests/test_pawpal.py::test_daily_recurrence_creates_next_day_task PASSED
tests/test_pawpal.py::test_weekly_recurrence_creates_next_week_task PASSED
tests/test_pawpal.py::test_overlapping_tasks_are_conflicts_across_pets PASSED
tests/test_pawpal.py::test_invalid_time_and_duration_rejected PASSED
tests/test_pawpal.py::test_duplicate_pet_name_rejected_case_insensitively PASSED

============================== 8 passed in 0.03s ===============================
```

The tests are automated checks of the current implementation; they do not prove every edge case is covered. Confidence: **moderate to high for the tested core behaviors**. Useful next tests include tasks near midnight, simultaneous tasks with different priorities, and repeated completion attempts.

## Demo walkthrough

1. Run `streamlit run app.py`.
2. In the sidebar, edit the owner name or add another pet.
3. Add a task and choose the pet, date, time, duration, priority, and recurrence.
4. Use the daily schedule filters to show a particular pet and/or completed tasks.
5. Select **Complete** to mark a task done; recurring tasks create their next occurrence.
6. Review the conflict warning below the schedule and adjust times/durations to resolve overlaps.
7. Run `python main.py` for the same core logic in a terminal.

## Design summary

- `Task` validates task data and owns recurrence behavior.
- `Pet` owns its assigned task list.
- `Owner` manages pets and provides `get_all_tasks()`. `Scheduler` obtains tasks through that owner method instead of reaching into each pet directly.
- `Scheduler` owns schedule sorting/filtering, conflict detection, and completion orchestration.
- `diagrams/uml_final.mmd` is the final Mermaid class diagram.

## Limitations and possible improvements

The scheduler reports conflicts rather than automatically moving tasks. Priority is used only to order tasks that start at the same time; it does not override a requested start time. Persistence is in Streamlit session state, so tasks are not saved to a database or retained across a new session. Possible extensions include persistent storage, configurable owner availability, editing/deleting tasks, and suggestions for resolving conflicts.
