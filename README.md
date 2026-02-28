# Habit-Tracker
Track daily habits in one place: add new habits, mark them done each day, see your current streak at a glance, check how much time is left before today ends, reset progress when needed, and remove habits you no longer want to track—all with quick buttons and clear pop-ups.

## What you can do
- **Create habits** you want to build (e.g., Reading, Programming, Socializing).
- **Mark a habit as done today** with ✓ (you’ll confirm with OK).
- **See your current streak** at a glance (consecutive days).
- **Check time left today** with 🕒 so you know how long you have before the day ends.
- **Reset a habit’s progress** with ✗ (confirmation required).
- **Remove habits** you no longer want to track.

## How streaks work
- Your **streak is calculated from recorded dates**.
- **Today counts toward your streak only after you press ✓ and confirm OK.**
- If you skip a day, the streak resets automatically (based on the date history).

## Requirements
- Python 3.9+ recommended
- Tkinter (usually included with Python on Windows/macOS; Linux may require an extra package)

## Data file
The app stores habits in:

- `habits.jsonl`

Each habit is stored as one JSON object per line:

```json
{"habit_name": "Reading", "dates": ["2026-02-25", "2026-02-26"]}
```

- `dates` contains the days you marked the habit as completed (`YYYY-MM-DD`).
- The app computes the streak from these dates, so no separate “strike” field is needed.

## Buttons
For each habit row:
- **✓** Mark done today (adds today’s date after OK).
- **🕒** Show time remaining today and whether you still have time to keep the streak.
- **✗** Reset progress (clears recorded dates after OK).

Top bar:
- **Create** Add a new habit.
- **Remove** Pick an existing habit to delete from the list (confirmation required).


## Notes
- The app expects `habits.jsonl` to be in the **same folder** as the script.
- If you previously stored duplicate lines, the app’s startup “compact” step should clean it up.


