"""Streamlit user interface for PawPal+."""
from datetime import date, datetime

import streamlit as st

from pawpal_system import Owner, Pet, Scheduler, Task

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="wide")
st.title("🐾 PawPal+")
st.caption("A simple multi-pet care planner with recurring tasks and conflict checks.")

if "owner" not in st.session_state:
    owner = Owner("Jordan")
    owner.add_pet(Pet("Mochi", "dog"))
    owner.add_pet(Pet("Pepper", "cat"))
    today = date.today()
    owner.find_pet("Mochi").add_task(Task("Morning walk", "08:00", 30, "high", "daily", today))
    owner.find_pet("Mochi").add_task(Task("Dinner", "18:00", 10, "high", "daily", today))
    owner.find_pet("Pepper").add_task(Task("Breakfast", "08:15", 10, "high", "daily", today))
    st.session_state.owner = owner

owner = st.session_state.owner
scheduler = Scheduler(owner)

with st.sidebar:
    st.header("Owner")
    owner.name = st.text_input("Owner name", value=owner.name)
    st.subheader("Add a pet")
    with st.form("add_pet_form", clear_on_submit=True):
        new_pet_name = st.text_input("Pet name")
        new_species = st.selectbox("Species", ["dog", "cat", "bird", "other"])
        pet_submitted = st.form_submit_button("Add pet")
    if pet_submitted:
        try:
            owner.add_pet(Pet(new_pet_name.strip(), new_species))
            st.success(f"Added {new_pet_name}.")
        except ValueError as exc:
            st.error(str(exc))

st.subheader("Add a care task")
pet_names = [pet.name for pet in owner.pets]
if not pet_names:
    st.info("Add a pet before creating tasks.")
else:
    with st.form("add_task_form", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            task_pet = st.selectbox("Pet", pet_names)
            task_title = st.text_input("Task", placeholder="e.g. Evening walk")
            task_date = st.date_input("Date", value=date.today())
        with col2:
            task_time = st.time_input("Start time", value=datetime.strptime("08:00", "%H:%M").time())
            duration = st.number_input("Duration (minutes)", min_value=1, max_value=240, value=20)
        with col3:
            priority = st.selectbox("Priority", ["high", "medium", "low"], index=1)
            recurrence = st.selectbox("Recurrence", ["none", "daily", "weekly"])
            notes = st.text_input("Notes (optional)")
        submitted = st.form_submit_button("Add task")
    if submitted:
        try:
            task = Task(task_title.strip(), task_time.strftime("%H:%M"), int(duration),
                        priority, recurrence, task_date, notes=notes.strip())
            owner.find_pet(task_pet).add_task(task)
            st.success(f"Added {task.title} for {task.pet_name}.")
        except ValueError as exc:
            st.error(str(exc))

st.divider()
st.subheader("Daily schedule")
schedule_date = st.date_input("Show date", value=date.today(), key="schedule_date")
filter_col1, filter_col2 = st.columns(2)
with filter_col1:
    pet_filter = st.selectbox("Filter by pet", ["All pets"] + [p.name for p in owner.pets])
with filter_col2:
    status_filter = st.selectbox("Task status", ["Incomplete", "Completed", "All"])
pet_arg = None if pet_filter == "All pets" else pet_filter
completed_arg = {"Incomplete": False, "Completed": True, "All": None}[status_filter]
tasks = scheduler.get_schedule(schedule_date, pet_name=pet_arg, completed=completed_arg)

if tasks:
    for index, task in enumerate(tasks):
        cols = st.columns([0.7, 2.2, 1.2, 1, 1, 1.2])
        cols[0].write(task.time)
        cols[1].write(f"**{task.title}**")
        cols[1].caption(f"{task.pet_name} · {task.duration_minutes} min")
        cols[2].write(task.priority.title())
        cols[3].write(task.recurrence.title())
        cols[4].write("Done" if task.completed else "Pending")
        if not task.completed and cols[5].button("Complete", key=f"complete-{id(task)}-{index}"):
            next_task = scheduler.complete_task(task)
            if next_task:
                st.toast(f"Completed. Next occurrence: {next_task.due_date.isoformat()}")
            else:
                st.toast("Task completed.")
            st.rerun()
else:
    st.info("No tasks match these filters for this date.")

conflicts = scheduler.find_conflicts(schedule_date)
if conflicts:
    st.warning("Schedule conflicts detected: overlapping tasks are listed below.")
    for first, second in conflicts:
        st.write(
            f"- **{first.title}** ({first.pet_name}, {first.time}–"
            f"{first.end_minutes // 60:02d}:{first.end_minutes % 60:02d}) overlaps "
            f"**{second.title}** ({second.pet_name}, {second.time}–"
            f"{second.end_minutes // 60:02d}:{second.end_minutes % 60:02d})."
        )
else:
    st.success("No overlapping tasks detected for this date.")

with st.expander("All registered pets and tasks"):
    for pet in owner.pets:
        st.markdown(f"**{pet.name}** ({pet.species}) — {len(pet.tasks)} task(s)")
        if pet.tasks:
            st.dataframe(
                [{"Task": t.title, "Date": t.due_date.isoformat(), "Time": t.time,
                  "Duration": t.duration_minutes, "Priority": t.priority,
                  "Recurrence": t.recurrence, "Completed": t.completed}
                 for t in pet.tasks],
                use_container_width=True, hide_index=True
            )
