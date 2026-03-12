# habit_timer.py
import tkinter as tk
from tkinter import ttk
import sqlite3
from datetime import datetime, timedelta

# --------------------
# Pastel lavender theme (edit these in one place)
# --------------------
BACKGROUND = "#F3EEFF"
PANEL_BG = "#E9DDFF"
TEXT = "#2E2545"
MUTED_TEXT = "#5B5077"
ACCENT = "#BFA2FF"
BUTTON_BG = "#D9CBFF"
BUTTON_TEXT = "#2E2545"
BORDER = "#C9B7FF"

TIMER_FONT = ("Segoe UI", 44, "bold")
UI_FONT = ("Segoe UI", 11)
BTN_FONT = ("Segoe UI", 11, "bold")

DEFAULT_DB_PATH = "habit_time.db"


def _center_on_parent(win: tk.Toplevel, parent: tk.Misc):
    win.update_idletasks()
    pw, ph = parent.winfo_width(), parent.winfo_height()
    px, py = parent.winfo_rootx(), parent.winfo_rooty()
    ww, wh = win.winfo_width(), win.winfo_height()
    x = px + (pw - ww) // 2
    y = py + (ph - wh) // 2
    win.geometry(f"+{x}+{y}")


def _fmt_mmss(seconds: int) -> str:
    seconds = max(0, int(seconds))
    m = seconds // 60
    s = seconds % 60
    return f"{m:02d}:{s:02d}"


def _gentle_beep(widget: tk.Misc, times: int = 2):
    """
    Cross-platform-ish gentle beep:
    - Windows: uses winsound.Beep (if available)
    - Otherwise: tkinter bell()
    """
    try:
        import winsound  # Windows only
        for _ in range(times):
            winsound.Beep(880, 120)   # frequency, duration ms
            winsound.Beep(660, 120)
    except Exception:
        for _ in range(times):
            try:
                widget.bell()
            except Exception:
                pass


def _init_db(db_path: str):
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS habit_work_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                habit_name TEXT NOT NULL,
                start_ts TEXT NOT NULL,
                end_ts TEXT NOT NULL,
                work_seconds INTEGER NOT NULL
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def _log_work_time(db_path: str, habit_name: str, start_ts: str, work_seconds: int):
    _init_db(db_path)
    end_ts = datetime.now().isoformat(timespec="seconds")
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO habit_work_log (habit_name, start_ts, end_ts, work_seconds) VALUES (?, ?, ?, ?)",
            (habit_name, start_ts, end_ts, int(work_seconds)),
        )
        conn.commit()
    finally:
        conn.close()


class HabitTimerWindow(tk.Toplevel):
    def __init__(self, parent: tk.Misc, habit_name: str, db_path: str = DEFAULT_DB_PATH):
        super().__init__(parent)
        self.parent = parent
        self.habit_name = habit_name
        self.db_path = db_path

        self.title(f"Timer — {habit_name}")
        self.configure(bg=BACKGROUND)
        self.resizable(False, False)

        # State
        self.running = False
        self.paused = False
        self.mode = "idle"  # idle | work | prep | break | done
        self.remaining = 0
        self.work_total = 0
        self.break_total = 0
        self.work_elapsed = 0
        self.session_start_ts = ""

        # ttk styling (best effort; ttk varies by OS)
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("Lav.TLabel", background=BACKGROUND, foreground=TEXT, font=UI_FONT)
        style.configure("Lav.TFrame", background=BACKGROUND)
        style.configure("Lav.TCombobox", fieldbackground=PANEL_BG)
        style.configure("Lav.TButton", font=BTN_FONT)

        # Layout
        outer = tk.Frame(self, bg=BACKGROUND)
        outer.pack(padx=16, pady=16)

        top = tk.Frame(outer, bg=BACKGROUND)
        top.pack(fill="x")

        ttk.Label(top, text="Work", style="Lav.TLabel").grid(row=0, column=0, padx=(0, 6), pady=(0, 6), sticky="w")
        ttk.Label(top, text="Break", style="Lav.TLabel").grid(row=0, column=1, padx=(12, 6), pady=(0, 6), sticky="w")

        self.work_var = tk.StringVar(value="25 min")
        self.break_var = tk.StringVar(value="5 min")

        self.work_combo = ttk.Combobox(
            top,
            textvariable=self.work_var,
            values=["5 min", "10 min", "15 min", "25 min", "30 min", "45 min", "60 min", "90 min"],
            state="readonly",
            width=10,
        )
        self.break_combo = ttk.Combobox(
            top,
            textvariable=self.break_var,
            values=["0 min", "3 min", "5 min", "10 min", "15 min", "20 min"],
            state="readonly",
            width=10,
        )
        self.work_combo.grid(row=1, column=0, sticky="w")
        self.break_combo.grid(row=1, column=1, sticky="w", padx=(12, 0))

        # Big timer
        self.timer_label = tk.Label(
            outer, text="00:00", font=TIMER_FONT, fg=TEXT, bg=BACKGROUND
        )
        self.timer_label.pack(pady=(14, 6))

        self.status_label = tk.Label(
            outer, text="Ready", font=UI_FONT, fg=MUTED_TEXT, bg=BACKGROUND
        )
        self.status_label.pack(pady=(0, 10))

        # Buttons row: pause, START, checkmark
        btn_row = tk.Frame(outer, bg=BACKGROUND)
        btn_row.pack()

        self.pause_btn = tk.Button(
            btn_row, text="⏸", font=BTN_FONT, fg=BUTTON_TEXT, bg=BUTTON_BG,
            activebackground=ACCENT, bd=0, width=4, command=self.toggle_pause
        )
        self.pause_btn.grid(row=0, column=0, padx=6)

        self.start_btn = tk.Button(
            btn_row, text="START", font=BTN_FONT, fg=BUTTON_TEXT, bg=BUTTON_BG,
            activebackground=ACCENT, bd=0, width=10, command=self.start_session
        )
        self.start_btn.grid(row=0, column=1, padx=6)

        self.done_btn = tk.Button(
            btn_row, text="✓", font=BTN_FONT, fg=BUTTON_TEXT, bg=BUTTON_BG,
            activebackground=ACCENT, bd=0, width=4, command=self.finish_early
        )
        self.done_btn.grid(row=0, column=2, padx=6)

        _center_on_parent(self, parent)
        self.grab_set()

    def _parse_minutes(self, s: str) -> int:
        # "25 min" -> 25
        try:
            return int(s.split()[0])
        except Exception:
            return 0

    def start_session(self):
        if self.running:
            return  # ignore if already running

        work_min = self._parse_minutes(self.work_var.get())
        break_min = self._parse_minutes(self.break_var.get())

        self.work_total = max(0, work_min) * 60
        self.break_total = max(0, break_min) * 60
        self.work_elapsed = 0
        self.session_start_ts = datetime.now().isoformat(timespec="seconds")

        if self.work_total <= 0:
            self.status_label.config(text="Choose a work duration.")
            return

        self.mode = "work"
        self.remaining = self.work_total
        self.running = True
        self.paused = False
        self.status_label.config(text="Work time")
        self._tick()

    def toggle_pause(self):
        if not self.running:
            return
        self.paused = not self.paused
        self.status_label.config(text=("Paused" if self.paused else self._mode_text()))
        if not self.paused:
            self._tick()

    def _mode_text(self) -> str:
        if self.mode == "work":
            return "Work time"
        if self.mode == "prep":
            return "Break starts soon"
        if self.mode == "break":
            return "Break time"
        if self.mode == "done":
            return "Complete"
        return "Ready"

    def _tick(self):
        if not self.running or self.paused:
            return

        self.timer_label.config(text=_fmt_mmss(self.remaining))

        if self.remaining <= 0:
            if self.mode == "work":
                _gentle_beep(self, times=2)
                self.mode = "prep"
                self.remaining = 60  # 1-minute prep countdown
                self.status_label.config(text="Break starts in 01:00")
                self.after(1000, self._tick)
                return

            if self.mode == "prep":
                # start break
                if self.break_total > 0:
                    self.mode = "break"
                    self.remaining = self.break_total
                    self.status_label.config(text="Break time")
                    self.after(1000, self._tick)
                    return
                else:
                    # no break selected → treat as complete
                    self._complete_session()
                    return

            if self.mode == "break":
                _gentle_beep(self, times=2)
                self._complete_session()
                return

        # Normal countdown step
        self.remaining -= 1
        if self.mode == "work":
            self.work_elapsed += 1
        elif self.mode == "prep":
            # update label like "Break starts in mm:ss"
            self.status_label.config(text=f"Break starts in {_fmt_mmss(self.remaining)}")

        self.after(1000, self._tick)

    def _complete_session(self):
        self.running = False
        self.mode = "done"
        self.status_label.config(text="Complete ✓")

        # Log FULL planned work time if session completed naturally,
        # not the break or prep time.
        work_to_log = self.work_total

        if work_to_log > 0 and self.session_start_ts:
            _log_work_time(self.db_path, self.habit_name, self.session_start_ts, work_to_log)

    def finish_early(self):
        """
        Checkmark button: end the session immediately and log the work time actually spent so far.
        """
        if self.running:
            self.running = False

        # If user did some work, log elapsed work seconds.
        if self.work_elapsed > 0 and self.session_start_ts:
            _log_work_time(self.db_path, self.habit_name, self.session_start_ts, self.work_elapsed)

        self.destroy()


def open_habit_timer(parent: tk.Misc, habit_name: str, db_path: str = DEFAULT_DB_PATH):
    """
    Call this from your main app when the clock button is pressed.
    """
    HabitTimerWindow(parent, habit_name, db_path=db_path)
