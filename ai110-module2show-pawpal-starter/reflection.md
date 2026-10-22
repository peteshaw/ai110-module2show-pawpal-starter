# PawPal+ Project Reflection

> **Personalize before submitting:** This is a draft based on the implementation and the development work in this project. Edit any statements that do not match your own design decisions or experience.

## 1. System Design

**a. Initial design**

The implementation uses four core classes. `Task` stores the care activity, time, duration, priority, recurrence, date, and completion state. `Pet` stores basic pet information and its tasks. `Owner` manages multiple pets and provides one method to retrieve tasks across all pets. `Scheduler` gets tasks through the owner-level method and handles sorting, filtering, conflict checks, and completion behavior. Keeping these responsibilities separate makes the code easier to test.

**b. Design changes**

The implementation makes recurrence part of task completion: `Task.mark_completed()` returns the next occurrence when the task repeats, and `Scheduler.complete_task()` attaches that occurrence to the same pet. This keeps the recurrence rule close to the task data while letting the scheduler coordinate the owner/pet update. The final UML diagram was updated to match these classes and methods.

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

The schedule filters tasks by date, pet, and completion state, then sorts by start time. Priority breaks ties when two tasks start at the same time. Conflict detection compares time intervals, so a 30-minute task beginning at 08:00 conflicts with another task beginning at 08:15. Daily and weekly recurrence produce a new incomplete task one day or seven days after the completed task.

**b. Tradeoffs**

The scheduler detects overlaps but does not automatically move tasks. Automatically rescheduling could be convenient, but it would require assumptions about owner availability, acceptable time windows, task flexibility, and which task should move. Reporting the conflict is predictable and lets the owner decide what to change. Priority also does not move a task away from its entered time.

## 3. AI Collaboration

**a. How you used AI**

AI assistance was used to help organize the implementation into classes, develop the scheduler behavior, build tests, and improve the documentation. The most useful prompts are specific about expected behavior—for example, asking for tests that verify recurrence dates or overlapping task intervals—because the result can be checked against a clear requirement.

**b. Judgment and verification**

One important verification step was running the automated tests rather than assuming the code was correct from inspection. An initial test run exposed a mismatch between the intended default schedule (incomplete tasks) and the implementation's filtering behavior. The default was corrected and the suite was rerun. The current test suite passes, but it does not cover every possible input or UI interaction.

## 4. Testing and Verification

**a. What you tested**

The tests cover task completion, adding a task to a pet and retrieving it through the owner, sorting and filtering, daily and weekly recurrence, overlap detection across pets, validation of invalid time/duration values, and duplicate pet names. These tests focus on core behaviors that could otherwise produce incorrect schedules or inconsistent task data.

**b. Confidence**

Confidence is moderate to high for the tested behaviors because the suite passes. Further tests should cover tasks that end near midnight, two tasks with the exact same start time and different priorities, invalid recurrence/priority values, and UI behavior across reruns. A persistent database and daylight-saving/time-zone behavior are outside the current implementation.

## 5. Reflection

**a. What went well**

The separation between models and scheduling logic makes it possible to test most behavior without launching Streamlit. The CLI demo also provides a quick way to inspect the schedule and conflict messages.

**b. What you would improve**

I would add persistence so tasks survive a new app session, plus task editing/deletion and a guided conflict-resolution feature. I would also add more tests around boundary cases and potentially use dedicated date/time types throughout the UI.

**c. Key takeaway**

A useful lesson from this project is that a working UI is not a substitute for a clearly defined backend contract. Having `Owner.get_all_tasks()` as the scheduler's entry point and testing scheduler behavior independently makes the design easier to understand and change.
