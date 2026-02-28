import tkinter as tk
from tkinter import ttk
import os, json
from datetime import datetime, timedelta

HABITS_FILE = "habits.jsonl"
MAX_DAYS_BAR = 30

# Theme
BACKGROUND = "#000000"
FONT_COLOR = "#E3A6FF"
#bg="#1f1f1f"


#base_color = "#2ecc71" \
#             "#2b2b2b"


# ---------- popup centering ----------
def center_on_parent(win: tk.Toplevel, parent: tk.Tk):
    win.update_idletasks()
    pw, ph = parent.winfo_width(), parent.winfo_height()
    px, py = parent.winfo_rootx(), parent.winfo_rooty()
    ww, wh = win.winfo_width(), win.winfo_height()
    x = px + (pw - ww) // 2
    y = py + (ph - wh) // 2
    win.geometry(f"+{x}+{y}")

# ---------- date helpers ----------
def today_str():
    return datetime.now().date().strftime("%Y-%m-%d")

def parse_ymd(s: str):
    return datetime.strptime(s, "%Y-%m-%d").date()

def time_remaining_to_end_of_day():
    now = datetime.now()
    end = now.replace(hour=23, minute=59, second=59, microsecond=0)
    delta = end - now
    secs = max(0, int(delta.total_seconds()))
    return secs // 3600, (secs % 3600) // 60

# ---------- strike computed from dates ----------
def strike_from_dates(dates_list, today=None) -> int:
    """
    If today is recorded, streak ends today.
    Otherwise, streak ends yesterday.
    """
    if today is None:
        today = datetime.now().date()

    dset = set()
    for s in dates_list:
        if isinstance(s, str):
            try:
                dset.add(parse_ymd(s))
            except Exception:
                pass
    if not dset:
        return 0

    cursor = today if today in dset else (today - timedelta(days=1))
    streak = 0
    while cursor in dset:
        streak += 1
        cursor -= timedelta(days=1)
    return streak

# ---------- JSONL helpers (one line per habit; no 'strike' stored) ----------
def _sanitize_record(rec: dict) -> dict:
    name = rec.get("habit_name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("Invalid habit_name")

    dates = rec.get("dates", [])
    if not isinstance(dates, list):
        dates = []

    clean = set()
    for s in dates:
        if isinstance(s, str):
            try:
                parse_ymd(s)          # validate format
                clean.add(s)
            except Exception:
                pass

    return {"habit_name": name.strip(), "dates": sorted(clean)}

def load_habits_jsonl(filename=HABITS_FILE):
    habits = {}
    if not os.path.exists(filename):
        return habits

    with open(filename, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue

            name = rec.get("habit_name")
            if not isinstance(name, str) or not name.strip():
                continue

            # support any old tombstones; removes habit if present
            if rec.get("deleted") is True:
                habits.pop(name.strip(), None)
                continue

            try:
                habits[name.strip()] = _sanitize_record(rec)
            except ValueError:
                continue

    return habits

def save_habits_jsonl(habits: dict, filename=HABITS_FILE):
    with open(filename, "w", encoding="utf-8") as f:
        for name in sorted(habits.keys(), key=str.lower):
            rec = _sanitize_record(habits[name])
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

def upsert_habit(record: dict, filename=HABITS_FILE):
    habits = load_habits_jsonl(filename)
    rec = _sanitize_record(record)
    habits[rec["habit_name"]] = rec
    save_habits_jsonl(habits, filename)

def delete_habit(habit_name: str, filename=HABITS_FILE):
    habits = load_habits_jsonl(filename)
    habits.pop(habit_name, None)
    save_habits_jsonl(habits, filename)

def compact_habits_file(filename=HABITS_FILE):
    if not os.path.exists(filename):
        return
    habits = load_habits_jsonl(filename)
    save_habits_jsonl(habits, filename)

# ---------- progress bar ----------
def make_progress_bar(parent, filled_days: int, highlight_today: bool):
    width, height = 540, 22
    bar = tk.Canvas(parent, width=width, height=height, bg="#1f1f1f", highlightthickness=0)

    filled = max(0, min(MAX_DAYS_BAR, filled_days))
    pad = 2
    seg_w = (width - pad*(MAX_DAYS_BAR+1)) / MAX_DAYS_BAR

    for i in range(MAX_DAYS_BAR):
        x0 = pad + i*(seg_w+pad)
        x1 = x0 + seg_w
        base_color = "#2ecc71" if i < filled else "#2b2b2b"
        bar.create_rectangle(x0, 4, x1, 18, fill=base_color, outline="")

    if highlight_today and filled > 0:
        i = filled - 1
        x0 = pad + i*(seg_w+pad)
        x1 = x0 + seg_w
        bar.create_rectangle(x0, 1, x1, 4, fill="#36f18a", outline="")

    return bar

# ---------- GUI ----------
class HabitApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Habit Tracker")
        self.geometry("780x520")
        self.configure(bg=BACKGROUND)

        # Cleanup once: removes duplicates + strips old stored 'strike'
        compact_habits_file(HABITS_FILE)

        top = tk.Frame(self, bg=BACKGROUND)
        top.pack(fill="x", padx=12, pady=12)

        ttk.Button(top, text="Create", command=self.open_create_dialog).pack(side="left")

        self.remove_btn = ttk.Button(top, text="Remove", command=self.open_remove_dropdown)
        self.remove_btn.pack(side="left", padx=(8, 0))

        self.list_frame = tk.Frame(self, bg=BACKGROUND)
        self.list_frame.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        self.habits = {}
        self.refresh_view()

    def refresh_view(self):
        self.habits = load_habits_jsonl(HABITS_FILE)

        for w in self.list_frame.winfo_children():
            w.destroy()

        if not self.habits:
            tk.Label(self.list_frame, text="No habits yet. Click Create.",
                     fg="#cccccc", bg=BACKGROUND, font=("Segoe UI", 12)).pack(anchor="w", pady=10)
            return

        for habit_name in sorted(self.habits.keys(), key=str.lower):
            rec = self.habits[habit_name]
            dates = sorted(set(rec.get("dates", [])))

            strike = strike_from_dates(dates)  # computed live

            row = tk.Frame(self.list_frame, bg=BACKGROUND)
            row.pack(fill="x", anchor="n", pady=10)

            mid = tk.Frame(row, bg=BACKGROUND)
            mid.pack(side="left", fill="x", expand=True)

            tk.Label(
                mid,
                text=f"{habit_name}   (strike: {strike}, days: {len(dates)})",
                fg="#e6e6e6", bg=BACKGROUND,
                font=("Segoe UI", 11, "bold")
            ).pack(anchor="w")

            line = tk.Frame(mid, bg=BACKGROUND)
            line.pack(fill="x", anchor="w", pady=(6, 0))

            #highlight = (today_str() in set(dates))
            #bar = make_progress_bar(line, filled_days=len(dates), highlight_today=highlight)
            strike = strike_from_dates(dates)  # already computed above

            filled_days = strike if strike > 0 else 0
            highlight = (today_str() in set(dates)) and (strike > 0)

            bar = make_progress_bar(line, filled_days=filled_days, highlight_today=highlight)
            bar.pack(side="left", anchor="w")

            btns = tk.Frame(line, bg=BACKGROUND)
            btns.pack(side="left", padx=(12, 0), anchor="center")

            tk.Button(btns, text="✓", font=("Segoe UI", 12, "bold"),
                      fg="#2ecc71", bg=BACKGROUND, activebackground="#111111",
                      bd=0, command=lambda h=habit_name: self.on_check(h)).pack(side="left", padx=6)

            tk.Button(btns, text="🕒", font=("Segoe UI", 12),
                      fg="#e6e6e6", bg=BACKGROUND, activebackground="#111111",
                      bd=0, command=lambda h=habit_name: self.on_clock(h)).pack(side="left", padx=6)

            tk.Button(btns, text="✗", font=("Segoe UI", 12, "bold"),
                      fg="#ff4d4d", bg=BACKGROUND, activebackground="#111111",
                      bd=0, command=lambda h=habit_name: self.on_reset_prompt(h)).pack(side="left", padx=6)

    # ---------- Remove dropdown + confirm ----------
    def open_remove_dropdown(self):
        habits = sorted(self.habits.keys(), key=str.lower)
        menu = tk.Menu(self, tearoff=0)

        if not habits:
            menu.add_command(label="(no habits)", state="disabled")
        else:
            for h in habits:
                menu.add_command(label=h, command=lambda name=h: self.confirm_remove(name))

        x = self.remove_btn.winfo_rootx()
        y = self.remove_btn.winfo_rooty() + self.remove_btn.winfo_height()
        menu.tk_popup(x, y)

    def confirm_remove(self, habit_name: str):
        dialog = tk.Toplevel(self)
        dialog.title("Remove habit")
        dialog.configure(bg=BACKGROUND)
        dialog.resizable(False, False)
        dialog.grab_set()

        tk.Label(dialog,
                 text=f"Are you sure you want to remove {habit_name}?",
                 fg="#e6e6e6", bg=BACKGROUND,
                 font=("Segoe UI", 11), wraplength=420, justify="left"
        ).pack(padx=12, pady=(12, 10))

        btns = tk.Frame(dialog, bg=BACKGROUND)
        btns.pack(padx=12, pady=(0, 12), fill="x")

        def ok():
            delete_habit(habit_name, HABITS_FILE)
            dialog.destroy()
            self.refresh_view()

        ttk.Button(btns, text="OK", command=ok).pack(side="bottom")
        #ttk.Button(btns, text="Cancel", command=dialog.destroy).pack(side="left", padx=(8, 0))

        center_on_parent(dialog, self)

    # ---------- buttons ----------
    def on_check(self, habit_name: str):
        rec = self.habits.get(habit_name, {"habit_name": habit_name, "dates": []})
        dates = sorted(set(rec.get("dates", [])))

        t = today_str()
        if t in dates:
            pop = tk.Toplevel(self)
            pop.title("Already recorded")
            pop.configure(bg=BACKGROUND)
            pop.resizable(False, False)
            pop.grab_set()
            tk.Label(pop, text=f"'{habit_name}' is already recorded for today.",
                     fg="#e6e6e6", bg=BACKGROUND, font=("Segoe UI", 11)
            ).pack(padx=12, pady=(12, 10))
            ttk.Button(pop, text="OK", command=pop.destroy).pack(padx=12, pady=(0, 12))
            center_on_parent(pop, self)
            return

        # Confirm: today counts only after OK
        dialog = tk.Toplevel(self)
        dialog.title("Confirm")
        dialog.configure(bg=BACKGROUND)
        dialog.resizable(False, False)
        dialog.grab_set()

        tk.Label(dialog, text=f"Mark '{habit_name}' as done today?",
                 fg="#e6e6e6", bg=BACKGROUND, font=("Segoe UI", 11)
        ).pack(padx=12, pady=(12, 10))

        btns = tk.Frame(dialog, bg=BACKGROUND)
        btns.pack(padx=12, pady=(0, 12), fill="x")

        def ok():
            dates.append(t)
            upsert_habit({"habit_name": habit_name, "dates": dates}, HABITS_FILE)
            dialog.destroy()
            self.refresh_view()

        ttk.Button(btns, text="OK", command=ok).pack(side="bottom")
        #ttk.Button(btns, text="Cancel", command=dialog.destroy).pack(side="left", padx=(8, 0))

        center_on_parent(dialog, self)

    def on_clock(self, habit_name: str):
        rec = self.habits.get(habit_name, {"habit_name": habit_name, "dates": []})
        dates = sorted(set(rec.get("dates", [])))

        strike = strike_from_dates(dates)
        h, m = time_remaining_to_end_of_day()

        msg = (f"You still have {h:02d}:{m:02d} remaining before the strike resets."
               if strike >= 1 else
               f"Your strike has been reset, but you still have {h:02d}:{m:02d} to make today count!")

        pop = tk.Toplevel(self)
        pop.title("Time Remaining")
        pop.configure(bg=BACKGROUND)
        pop.resizable(False, False)
        pop.grab_set()

        tk.Label(pop, text=msg, fg="#e6e6e6", bg=BACKGROUND,
                 font=("Segoe UI", 11), wraplength=420, justify="left"
        ).pack(padx=12, pady=(12, 10))
        ttk.Button(pop, text="OK", command=pop.destroy).pack(padx=12, pady=(0, 12))

        center_on_parent(pop, self)

    def on_reset_prompt(self, habit_name: str):
        dialog = tk.Toplevel(self)
        dialog.title("Reset progress")
        dialog.configure(bg=BACKGROUND)
        dialog.resizable(False, False)
        dialog.grab_set()

        tk.Label(dialog, text="This will reset the progress. Continue?",
                 fg="#e6e6e6", bg=BACKGROUND, font=("Segoe UI", 11)
        ).pack(padx=12, pady=(12, 10))

        btns = tk.Frame(dialog, bg=BACKGROUND)
        btns.pack(padx=12, pady=(0, 12), fill="x")

        def ok():
            upsert_habit({"habit_name": habit_name, "dates": []}, HABITS_FILE)
            dialog.destroy()
            self.refresh_view()

        ttk.Button(btns, text="OK", command=ok).pack(side="bottom")
        #ttk.Button(btns, text="Cancel", command=dialog.destroy).pack(side="left", padx=(8, 0))

        center_on_parent(dialog, self)

    def open_create_dialog(self):
        dialog = tk.Toplevel(self)
        dialog.title("Create a new habit")
        dialog.configure(bg=BACKGROUND)
        dialog.resizable(False, False)
        dialog.grab_set()

        tk.Label(dialog, text="What new habit would you like to track?",
                 fg="#e6e6e6", bg=BACKGROUND, font=("Segoe UI", 11)
        ).pack(padx=12, pady=(12, 6))

        entry = ttk.Entry(dialog, width=34)
        entry.pack(padx=12, pady=(0, 10))
        entry.focus_set()

        btns = tk.Frame(dialog, bg=BACKGROUND)
        btns.pack(padx=12, pady=(0, 12), fill="x")

        def show_exists_popup():
            pop = tk.Toplevel(dialog)
            pop.title("Already exists")
            pop.configure(bg=BACKGROUND)
            pop.resizable(False, False)
            pop.grab_set()

            tk.Label(pop, text="This habit already exists.",
                     fg="#e6e6e6", bg=BACKGROUND, font=("Segoe UI", 11)
            ).pack(padx=12, pady=(12, 8))

            ttk.Button(pop, text="OK", command=pop.destroy).pack(padx=12, pady=(0, 12))
            center_on_parent(pop, self)

        def on_ok():
            name = entry.get().strip()
            if not name:
                return
            exists = any(h.lower() == name.lower() for h in self.habits.keys())
            if exists:
                show_exists_popup()
                return

            upsert_habit({"habit_name": name, "dates": []}, HABITS_FILE)
            dialog.destroy()
            self.refresh_view()

        ttk.Button(btns, text="OK", command=on_ok).pack(side="bottom")
        #ttk.Button(btns, text="Close", command=dialog.destroy).pack(side="left", padx=(8, 0))

        center_on_parent(dialog, self)

if __name__ == "__main__":
    app = HabitApp()
    app.mainloop()
