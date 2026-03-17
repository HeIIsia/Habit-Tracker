# Habit Tracker

A desktop habit tracker built around *doing the habit* (via a focused work timer) and seeing your streak at a glance.


<img width="975" height="719" alt="screen_001" src="https://github.com/user-attachments/assets/e279486a-4032-4681-99d1-c7c5eb07f6f2" />

<img width="971" height="719" alt="screen_003" src="https://github.com/user-attachments/assets/a373120e-d6d9-4d70-8e61-297b81dca479" />


## What you can do
- **Create habits** and give each one a matching **icon**.
- **Start a work/break timer** for any habit (🕒). When a full session completes, the app records today for that habit and logs the work time.
- **Edit habit settings** with **…** (rename the habit and/or change its icon).
- **Remove habits** you no longer want to track.

## Main screen
Each habit row shows:
- **Icon** (left)
- **Habit name + streak + total days recorded**
- A **30-segment progress bar** that visualizes your current streak
- Two action buttons on the right:
  - **🕒 Timer** — open the focus timer for this habit
  - **…** — open habit settings (rename / icon)

## How streaks work
- Each habit stores only a **list of completed dates**.
- Your **streak is calculated automatically from those dates**:
  - If today is already recorded, the streak counts consecutive days ending **today**
  - Otherwise, the streak counts consecutive days ending **yesterday**
- If your streak is **0**, the bar shows **no green segments**.

## Focus timer (work/break)
Open the timer with **🕒** next to a habit.
- Choose **Work** and **Break** durations from the dropdowns.
- Press **START** to begin the work countdown.
- When work finishes:
  - gentle beeps signal the transition
  - a **1-minute prep countdown** runs
  - then the break countdown starts
- When the break finishes, gentle beeps signal the session is complete.
- On completion, the app:
  1) logs the **work time** to the database
  2) records **today** for that habit (so it counts toward your streak)

## Habit creation & icon settings
- Click **Create** to add a new habit.
- Use **Generate Icon** to create a matching icon, then confirm when you like it.
- Use **…** to edit a habit later (rename and/or update the icon).

## Data files
The app stores your data locally in the same folder as the scripts.

### `habits.jsonl`
Stores one record per habit (the app keeps this file “compacted” so it doesn’t grow with duplicates).

Example:
```json
{"habit_name": "Reading", "dates": ["2026-02-25", "2026-02-26"], "icon_path": "icons/reading.png"}

