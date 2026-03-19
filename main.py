import tkinter as tk
from tkinter import ttk
import os
import json
import math
import sqlite3
from datetime import datetime, timedelta, date

from PIL import Image, ImageTk

import habit_timer
import freeze_store
print("freeze_store loaded from:", freeze_store.__file__)
print("freeze_store has get_global:", hasattr(freeze_store, "get_global"))

from datetime import timedelta

def work_streak_only(dates_set, today):
    """
    dates_set: set[date] of *work* days only (no freezes)
    today: datetime.date
    Counts consecutive work days ending on today if present, otherwise yesterday if present.
    """
    if not dates_set:
        return 0

    end = today if today in dates_set else (today - timedelta(days=1) if (today - timedelta(days=1)) in dates_set else None)
    if end is None:
        return 0

    streak = 0
    cursor = end
    while cursor in dates_set:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


import debug_settings
from habit_icon_creator import open_habit_icon_creator

# -----------------------------
# Files / Config
# -----------------------------
HABITS_FILE = "habits.jsonl"
THEME_FILE = "theme.json"
MAX_DAYS_BAR = 30

ICON_BOX_SIZE = 100
ICON_PREVIEW_SIZE = 64

TIME_DB_PATH = getattr(habit_timer, "DEFAULT_DB_PATH", "habit_time.db")

# -----------------------------
# Default palette (overridden by theme.json)
# -----------------------------
BACKGROUND = "#F3EEFF"
PANEL_BG = "#E9DDFF"
TEXT = "#B41DDA"
MUTED_TEXT = "#9954AE"
ACCENT = "#FFDBF5"
BUTTON_BG = "#BFA2FF"

BAR_BG = "#E3A6FF"
BAR_EMPTY = "#B41DDA"
BAR_FILLED = "#9DFF00"
FREEZE_TILE_BG = "#BDEBFF"  # frozen tile (yesterday protected)

# Today intensity colors
TODAY_30M = "#D3FFBD"
TODAY_1H = "#A3FF8F"
TODAY_2H = "#5AFF52"
TODAY_2H_PLUS_BG = "#00DA04"

STAR_FILL = "#FFE45E"
STAR_OUTLINE = TEXT

BTN_ACTIVE_BG = ACCENT

TEXT_SOFT = MUTED_TEXT
TEXT_BRIGHT = TEXT


def _load_theme_overrides():
    global BACKGROUND, PANEL_BG, TEXT, MUTED_TEXT, ACCENT, BUTTON_BG
    global BAR_BG, BAR_EMPTY, BAR_FILLED, FREEZE_TILE_BG

    if not os.path.exists(THEME_FILE):
        return
    try:
        with open(THEME_FILE, "r", encoding="utf-8") as f:
            t = json.load(f)
        if not isinstance(t, dict):
            return

        BACKGROUND = t.get("BACKGROUND", BACKGROUND)
        PANEL_BG = t.get("PANEL_BG", PANEL_BG)
        TEXT = t.get("TEXT", TEXT)
        MUTED_TEXT = t.get("MUTED_TEXT", MUTED_TEXT)
        ACCENT = t.get("ACCENT", ACCENT)
        BUTTON_BG = t.get("BUTTON_BG", BUTTON_BG)
        BAR_BG = t.get("BAR_BG", BAR_BG)
        BAR_EMPTY = t.get("BAR_EMPTY", BAR_EMPTY)
        BAR_FILLED = t.get("BAR_FILLED", BAR_FILLED)
        FREEZE_TILE_BG = t.get("FREEZE_TILE_BG", FREEZE_TILE_BG)
    except Exception:
        pass


_load_theme_overrides()
TEXT_SOFT = MUTED_TEXT
TEXT_BRIGHT = TEXT
STAR_OUTLINE = TEXT


# -----------------------------
# Utilities
# -----------------------------
def center_on_parent(win: tk.Toplevel, parent: tk.Misc):
    win.update_idletasks()
    parent.update_idletasks()
    pw, ph = parent.winfo_width(), parent.winfo_height()
    px, py = parent.winfo_rootx(), parent.winfo_rooty()
    ww, wh = win.winfo_width(), win.winfo_height()
    x = px + (pw - ww) // 2
    y = py + (ph - wh) // 2
    win.geometry(f"+{x}+{y}")


def today_date():
    return datetime.now().date()


def today_str():
    return today_date().strftime("%Y-%m-%d")


def parse_ymd(s: str):
    return datetime.strptime(s, "%Y-%m-%d").date()


def ymd(d: date):
    return d.strftime("%Y-%m-%d")


def time_left_today_hhmm():
    now = datetime.now()
    end = now.replace(hour=23, minute=59, second=59, microsecond=0)
    secs = max(0, int((end - now).total_seconds()))
    return secs // 3600, (secs % 3600) // 60


def format_list_nice(items):
    items = list(items)
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return ", ".join(items[:-1]) + f", and {items[-1]}"


# -----------------------------
# DB: total seconds worked today
# -----------------------------
def get_work_seconds_today(habit_name: str, db_path: str = TIME_DB_PATH) -> int:
    if not os.path.exists(db_path):
        return 0

    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute(
            "SELECT COALESCE(SUM(work_seconds), 0) "
            "FROM habit_work_log "
            "WHERE habit_name = ? AND substr(start_ts, 1, 10) = ?",
            (habit_name, today_str()),
        )
        (total,) = cur.fetchone()
        return int(total or 0)
    except Exception:
        return 0
    finally:
        try:
            if conn:
                conn.close()
        except Exception:
            pass


def today_tile_style(work_seconds: int):
    # returns ("color", hex) or ("star", hex) or None
    if work_seconds > 2 * 3600:
        return ("star", TODAY_2H_PLUS_BG)
    if work_seconds >= 2 * 3600:
        return ("color", TODAY_2H)
    if work_seconds >= 1 * 3600:
        return ("color", TODAY_1H)
    if work_seconds >= 30 * 60:
        return ("color", TODAY_30M)
    return None


def draw_star(canvas: tk.Canvas, x0, y0, x1, y1):
    cx = (x0 + x1) / 2
    cy = (y0 + y1) / 2
    r_outer = min(x1 - x0, y1 - y0) * 0.45
    r_inner = r_outer * 0.5
    points = []
    for i in range(10):
        ang = math.pi / 2 + i * (math.pi / 5)
        r = r_outer if i % 2 == 0 else r_inner
        points.extend([cx + r * math.cos(ang), cy - r * math.sin(ang)])
    canvas.create_polygon(points, fill=STAR_FILL, outline=STAR_OUTLINE, width=1)


# -----------------------------
# Habits JSONL
# -----------------------------
def _sanitize_record(rec: dict) -> dict:
    name = rec.get("habit_name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("Invalid habit_name")

    dates = rec.get("dates", [])
    if not isinstance(dates, list):
        dates = []
    clean_dates = set()
    for s in dates:
        if isinstance(s, str):
            try:
                parse_ymd(s)
                clean_dates.add(s)
            except Exception:
                pass

    protected = rec.get("protected_dates", [])
    if not isinstance(protected, list):
        protected = []
    clean_protected = set()
    for s in protected:
        if isinstance(s, str):
            try:
                parse_ymd(s)
                clean_protected.add(s)
            except Exception:
                pass

    icon_path = rec.get("icon_path", "")
    if not isinstance(icon_path, str):
        icon_path = ""

    work_award_blocks = rec.get("work_award_blocks", 0)
    if not isinstance(work_award_blocks, int) or work_award_blocks < 0:
        work_award_blocks = 0

    star_days = rec.get("star_days", [])
    if not isinstance(star_days, list):
        star_days = []
    clean_star_days = set()
    for s in star_days:
        if isinstance(s, str):
            try:
                parse_ymd(s)
                clean_star_days.add(s)
            except Exception:
                pass

    return {
        "habit_name": name.strip(),
        "dates": sorted(clean_dates),
        "protected_dates": sorted(clean_protected),
        "icon_path": icon_path.strip(),
        "work_award_blocks": work_award_blocks,
        "star_days": sorted(clean_star_days),
    }


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


# -----------------------------
# Streak helpers
# -----------------------------
def get_streak_days(dates_set, protected_set):
    effective = set(dates_set) | set(protected_set)
    if not effective:
        return []

    td = today_date()
    yd = td - timedelta(days=1)

    if td in effective:
        end = td
    elif yd in effective:
        end = yd
    else:
        return []

    days = []
    cursor = end
    while cursor in effective:
        days.append(cursor)
        cursor -= timedelta(days=1)
    days.reverse()
    return days


def work_streak_only(dates_set):
    if not dates_set:
        return 0
    td = today_date()
    yd = td - timedelta(days=1)
    end = td if td in dates_set else (yd if yd in dates_set else None)
    if end is None:
        return 0

    streak = 0
    cursor = end
    while cursor in dates_set:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


# -----------------------------
# Progress bar
# -----------------------------
def make_progress_bar(parent, streak_days, dates_set, protected_set, today_style):
    width, height = 540, 22
    bar = tk.Canvas(parent, width=width, height=height, bg=BAR_BG, highlightthickness=0)

    pad = 2
    seg_w = (width - pad * (MAX_DAYS_BAR + 1)) / MAX_DAYS_BAR

    if not streak_days:
        for i in range(MAX_DAYS_BAR):
            x0 = pad + i * (seg_w + pad)
            x1 = x0 + seg_w
            bar.create_rectangle(x0, 4, x1, 18, fill=BAR_EMPTY, outline="")
        return bar

    streak_days = streak_days[-MAX_DAYS_BAR:]
    filled = len(streak_days)

    for i in range(MAX_DAYS_BAR):
        x0 = pad + i * (seg_w + pad)
        x1 = x0 + seg_w

        if i >= filled:
            bar.create_rectangle(x0, 4, x1, 18, fill=BAR_EMPTY, outline="")
            continue

        day = streak_days[i]
        base = FREEZE_TILE_BG if day in protected_set else BAR_FILLED

        is_today = (day == today_date() and day in dates_set)
        if is_today and today_style:
            base = today_style[1]

        bar.create_rectangle(x0, 4, x1, 18, fill=base, outline="")
        if is_today and today_style and today_style[0] == "star":
            draw_star(bar, x0, 4, x1, 18)

    return bar


# -----------------------------
# App
# -----------------------------
class HabitApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Habit Tracker")
        self.geometry("1000x620")
        self.configure(bg=BACKGROUND)

        compact_habits_file(HABITS_FILE)


        top = tk.Frame(self, bg=BACKGROUND)
        top.pack(fill="x", padx=12, pady=12)

        top.grid_columnconfigure(0, weight=0)
        top.grid_columnconfigure(1, weight=1)
        top.grid_columnconfigure(2, weight=0)

        left = tk.Frame(top, bg=BACKGROUND)
        left.grid(row=0, column=0, sticky="w")

        ttk.Button(left, text="Create", command=self.open_create_dialog).pack(side="left")
        self.remove_btn = ttk.Button(left, text="Remove", command=self.open_remove_dropdown)
        self.remove_btn.pack(side="left", padx=(8, 0))
        ttk.Button(left, text="Settings", command=self.open_settings).pack(side="left", padx=(8, 0))

        self.global_freeze_label = tk.Label(
            top, text="", fg=TEXT_BRIGHT, bg=BACKGROUND, font=("Segoe UI", 14, "bold")
        )
        self.global_freeze_label.grid(row=0, column=1)

        self.time_left_label = tk.Label(
            top, text="", fg=TEXT_BRIGHT, bg=BACKGROUND, font=("Segoe UI", 16, "bold")
        )
        self.time_left_label.grid(row=0, column=2, sticky="e")

        self.list_frame = tk.Frame(self, bg=BACKGROUND)
        self.list_frame.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        self.icon_refs = []
        self.habits = load_habits_jsonl(HABITS_FILE)

        self._update_top_loop()
        self.refresh_view()

        self.after(1000, self.check_missed_yesterday)

    def open_settings(self):
        def habits_provider():
            self.habits = load_habits_jsonl(HABITS_FILE)
            return sorted(list(self.habits.keys()), key=str.lower)

        def apply_strike_callback(habit_name: str, strike_days: int):
            self.habits = load_habits_jsonl(HABITS_FILE)
            rec = self.habits.get(habit_name)
            if not rec:
                return
            end_day = today_date() - timedelta(days=1)
            new_dates = [ymd(end_day - timedelta(days=(strike_days - 1 - i))) for i in range(strike_days)] if strike_days > 0 else []
            blocks = (strike_days // 5) if strike_days > 0 else 0
            upsert_habit({**rec, "habit_name": habit_name, "dates": new_dates, "protected_dates": [], "work_award_blocks": blocks}, HABITS_FILE)
            self.refresh_view()

        debug_settings.open_settings_window(self, habits_provider, apply_strike_callback)

    def _update_top_loop(self):
        gf = freeze_store.get_global()
        self.global_freeze_label.config(text=f"★ Freezes: {gf}")
        hh, mm = time_left_today_hhmm()
        self.time_left_label.config(text=f"Time left today: {hh:02d}:{mm:02d}")
        self.after(1000, self._update_top_loop)

    def load_icon_photo(self, icon_path: str):
        if not icon_path or not os.path.exists(icon_path):
            return None
        try:
            img = Image.open(icon_path).convert("RGBA")
            try:
                resample = Image.Resampling.NEAREST
            except AttributeError:
                resample = Image.NEAREST
            img = img.resize((ICON_PREVIEW_SIZE, ICON_PREVIEW_SIZE), resample)
            return ImageTk.PhotoImage(img)
        except Exception:
            return None

    """def mark_habit_done_from_timer(self, habit_name: str):
        self.habits = load_habits_jsonl(HABITS_FILE)
        rec = self.habits.get(habit_name)
        if not rec:
            return

        dates = set(rec.get("dates", []))
        protected = set(rec.get("protected_dates", []))

        t = today_str()
        dates.add(t)"""

    def mark_habit_done_from_timer(self, habit_name: str):
        self.habits = load_habits_jsonl(HABITS_FILE)
        rec = self.habits.get(habit_name)
        if not rec:
            return

        # --- add today's date (work day) ---
        t_str = today_str()
        dates_strs = set(rec.get("dates", []))
        dates_strs.add(t_str)

        # Parse to date objects for streak math
        dates_set = set(parse_ymd(s) for s in dates_strs)
        today = today_date()

        # --- compute work streak + blocks ---
        streak = work_streak_only(dates_set, today)  # work days only
        blocks = streak // 5  # 5-day blocks earned

        prev_blocks = rec.get("work_award_blocks", 0)
        if not isinstance(prev_blocks, int) or prev_blocks < 0:
            prev_blocks = 0

        # If streak broke and restarted, allow earning again
        if blocks < prev_blocks:
            prev_blocks = blocks

        # Award any newly reached 5-day blocks
        if blocks > prev_blocks:
            freeze_store.add_habit(habit_name, blocks - prev_blocks)
            prev_blocks = blocks

        # --- persist habit record ---
        upsert_habit(
            {
                **rec,
                "habit_name": habit_name,
                "dates": sorted(dates_strs),
                "work_award_blocks": prev_blocks,
            },
            HABITS_FILE,
        )

        self.refresh_view()

        # Star -> global freeze once per day
        seconds_today = get_work_seconds_today(habit_name)
        style = today_tile_style(seconds_today)
        star_earned = bool(style and style[0] == "star")

        star_days = set(rec.get("star_days", []))
        if star_earned and t not in star_days:
            star_days.add(t)
            freeze_store.add_global(1)

        # 5-day work streak -> habit freeze(s)
        work_streak = work_streak_only(set(parse_ymd(d) for d in dates))
        blocks = work_streak // 5
        prev_blocks = int(rec.get("work_award_blocks", 0))
        if blocks > prev_blocks:
            freeze_store.add_habit(habit_name, blocks - prev_blocks)
            prev_blocks = blocks
        if work_streak == 0:
            prev_blocks = 0

        upsert_habit(
            {
                **rec,
                "habit_name": habit_name,
                "dates": sorted(dates),
                "protected_dates": sorted(protected),
                "work_award_blocks": prev_blocks,
                "star_days": sorted(star_days),
            },
            HABITS_FILE,
        )
        self.refresh_view()

    def finish_create_or_edit_habit(self, old_name: str, new_name: str, icon_path: str):
        old_name = (old_name or "").strip()
        new_name = (new_name or "").strip()
        icon_path = (icon_path or "").strip()
        if not new_name:
            return

        self.habits = load_habits_jsonl(HABITS_FILE)

        if old_name and old_name in self.habits:
            old_record = self.habits[old_name]
            dates = list(old_record.get("dates", []))
            protected = list(old_record.get("protected_dates", []))
            work_award_blocks = int(old_record.get("work_award_blocks", 0))
            star_days = list(old_record.get("star_days", []))

            if old_name != new_name:
                delete_habit(old_name, HABITS_FILE)
                hf = freeze_store.get_habit(old_name)
                if hf:
                    freeze_store.set_habit(new_name, hf)
                    freeze_store.set_habit(old_name, 0)
        else:
            dates, protected, work_award_blocks, star_days = [], [], 0, []

        upsert_habit(
            {
                "habit_name": new_name,
                "dates": dates,
                "protected_dates": protected,
                "icon_path": icon_path,
                "work_award_blocks": work_award_blocks,
                "star_days": star_days,
            },
            HABITS_FILE,
        )
        self.refresh_view()

    def open_edit_dialog(self, habit_name: str):
        rec = self.habits.get(habit_name, {})
        open_habit_icon_creator(
            parent=self,
            existing_habits=self.habits.keys(),
            on_accept=self.finish_create_or_edit_habit,
            mode="edit",
            original_name=habit_name,
            initial_name=habit_name,
            initial_icon_path=rec.get("icon_path", ""),
        )

    def open_create_dialog(self):
        open_habit_icon_creator(
            parent=self,
            existing_habits=self.habits.keys(),
            on_accept=self.finish_create_or_edit_habit,
            mode="create",
            original_name="",
            initial_name="",
            initial_icon_path="",
        )

    def open_remove_dropdown(self):
        self.habits = load_habits_jsonl(HABITS_FILE)
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

        tk.Label(
            dialog,
            text=f"Are you sure you want to remove {habit_name}?",
            fg=TEXT_BRIGHT,
            bg=BACKGROUND,
            font=("Segoe UI", 11),
            wraplength=420,
            justify="left",
        ).pack(padx=12, pady=(12, 10))

        btns = tk.Frame(dialog, bg=BACKGROUND)
        btns.pack(padx=12, pady=(0, 12), fill="x")

        def ok():
            delete_habit(habit_name, HABITS_FILE)
            freeze_store.set_habit(habit_name, 0)
            dialog.destroy()
            self.refresh_view()

        ttk.Button(btns, text="OK", command=ok).pack(side="left")
        ttk.Button(btns, text="Cancel", command=dialog.destroy).pack(side="left", padx=(8, 0))
        center_on_parent(dialog, self)

    def check_missed_yesterday(self):
        self.habits = load_habits_jsonl(HABITS_FILE)
        misses = []

        y = today_date() - timedelta(days=1)
        y_s = ymd(y)
        prev = y - timedelta(days=1)

        for name, rec in self.habits.items():
            dates = set(parse_ymd(d) for d in rec.get("dates", []))
            protected = set(parse_ymd(d) for d in rec.get("protected_dates", []))
            effective = dates | protected

            if y in effective:
                continue
            if prev not in effective:
                continue

            hf = freeze_store.get_habit(name)
            if hf > 0:
                hf -= 1
                protected.add(y)
                freeze_store.set_habit(name, hf)
                upsert_habit({**rec, "habit_name": name, "protected_dates": sorted(ymd(d) for d in protected)}, HABITS_FILE)
            else:
                misses.append(name)

        self.habits = load_habits_jsonl(HABITS_FILE)
        self.refresh_view()

        if not misses:
            return

        missed_list_text = format_list_nice(misses)
        gf = freeze_store.get_global()

        if gf <= 0:
            self._popup_info(f"Oh-oh, looks like you missed a day on {missed_list_text}.")
            return

        if len(misses) == 1:
            self._prompt_single_freeze(misses[0], y_s, missed_list_text)
        else:
            self._prompt_multi_freeze(misses, y_s, missed_list_text)

    def _popup_info(self, text):
        dialog = tk.Toplevel(self)
        dialog.title("Oh-oh")
        dialog.configure(bg=BACKGROUND)
        dialog.resizable(False, False)
        dialog.grab_set()

        tk.Label(dialog, text=text, fg=TEXT_BRIGHT, bg=BACKGROUND,
                 font=("Segoe UI", 11), wraplength=460, justify="left").pack(padx=12, pady=(12, 10))
        ttk.Button(dialog, text="OK", command=dialog.destroy).pack(padx=12, pady=(0, 12))
        center_on_parent(dialog, self)

    def _apply_global_freeze(self, habit_name: str, y_s: str) -> bool:
        if freeze_store.get_global() <= 0:
            return False
        rec = load_habits_jsonl(HABITS_FILE).get(habit_name)
        if not rec:
            return False

        protected = set(rec.get("protected_dates", []))
        protected.add(y_s)

        freeze_store.add_global(-1)
        upsert_habit({**rec, "habit_name": habit_name, "protected_dates": sorted(protected)}, HABITS_FILE)
        return True

    def _prompt_single_freeze(self, habit_name: str, y_s: str, missed_list_text: str):
        dialog = tk.Toplevel(self)
        dialog.title("Oh-oh")
        dialog.configure(bg=BACKGROUND)
        dialog.resizable(False, False)
        dialog.grab_set()

        tk.Label(
            dialog,
            text=f"Oh-oh, looks like you missed a day on {missed_list_text}.\n\nUse 1 Freeze on {habit_name}?",
            fg=TEXT_BRIGHT,
            bg=BACKGROUND,
            font=("Segoe UI", 11),
            wraplength=460,
            justify="left",
        ).pack(padx=12, pady=(12, 10))

        btns = tk.Frame(dialog, bg=BACKGROUND)
        btns.pack(padx=12, pady=(0, 12), fill="x")

        def ok():
            self._apply_global_freeze(habit_name, y_s)
            dialog.destroy()
            self.refresh_view()

        ttk.Button(btns, text="OK", command=ok).pack(side="left")
        ttk.Button(btns, text="Cancel", command=dialog.destroy).pack(side="left", padx=(8, 0))
        center_on_parent(dialog, self)

    def _prompt_multi_freeze(self, habits: list, y_s: str, missed_list_text: str):
        dialog = tk.Toplevel(self)
        dialog.title("Oh-oh")
        dialog.configure(bg=BACKGROUND)
        dialog.resizable(False, False)
        dialog.grab_set()

        tk.Label(
            dialog,
            text=f"Oh-oh, looks like you missed a day on {missed_list_text}.\n\nWhich of these habits would you like to protect with your Freeze?",
            fg=TEXT_BRIGHT,
            bg=BACKGROUND,
            font=("Segoe UI", 11),
            wraplength=480,
            justify="left",
        ).pack(padx=12, pady=(12, 8))

        choice = tk.StringVar(value=habits[0])
        cb = ttk.Combobox(dialog, textvariable=choice, values=habits, state="readonly", width=28)
        cb.pack(padx=12, pady=(0, 12))

        btns = tk.Frame(dialog, bg=BACKGROUND)
        btns.pack(padx=12, pady=(0, 12), fill="x")

        def proceed():
            picked = choice.get()
            dialog.destroy()
            self._confirm_choice(picked, y_s)

        ttk.Button(btns, text="OK", command=proceed).pack(side="left")
        ttk.Button(btns, text="Cancel", command=dialog.destroy).pack(side="left", padx=(8, 0))
        center_on_parent(dialog, self)

    def _confirm_choice(self, habit_name: str, y_s: str):
        dialog = tk.Toplevel(self)
        dialog.title("Confirm")
        dialog.configure(bg=BACKGROUND)
        dialog.resizable(False, False)
        dialog.grab_set()

        tk.Label(
            dialog,
            text=f"You chose to protect {habit_name}. Is that correct?",
            fg=TEXT_BRIGHT,
            bg=BACKGROUND,
            font=("Segoe UI", 11),
            wraplength=420,
            justify="left",
        ).pack(padx=12, pady=(12, 10))

        btns = tk.Frame(dialog, bg=BACKGROUND)
        btns.pack(padx=12, pady=(0, 12), fill="x")

        def ok():
            self._apply_global_freeze(habit_name, y_s)
            dialog.destroy()
            self.refresh_view()

        ttk.Button(btns, text="OK", command=ok).pack(side="left")
        ttk.Button(btns, text="Cancel", command=dialog.destroy).pack(side="left", padx=(8, 0))
        center_on_parent(dialog, self)

    def refresh_view(self):
        self.habits = load_habits_jsonl(HABITS_FILE)
        self.icon_refs = []

        for w in self.list_frame.winfo_children():
            w.destroy()

        if not self.habits:
            tk.Label(self.list_frame, text="No habits yet. Click Create.",
                     fg=TEXT_SOFT, bg=BACKGROUND, font=("Segoe UI", 12)).pack(anchor="w", pady=10)
            return

        for habit_name in sorted(self.habits.keys(), key=str.lower):
            rec = self.habits[habit_name]
            dates_set = set(parse_ymd(d) for d in rec.get("dates", []))
            protected_set = set(parse_ymd(d) for d in rec.get("protected_dates", []))

            streak_days = get_streak_days(dates_set, protected_set)
            strike = len(streak_days)
            habit_freezes = freeze_store.get_habit(habit_name)

            row = tk.Frame(self.list_frame, bg=BACKGROUND)
            row.pack(fill="x", anchor="n", pady=10)

            icon_holder = tk.Frame(row, bg=BACKGROUND, width=ICON_BOX_SIZE, height=ICON_BOX_SIZE)
            icon_holder.pack(side="left", padx=(0, 10))
            icon_holder.pack_propagate(False)

            photo = self.load_icon_photo(rec.get("icon_path", ""))
            if photo is not None:
                self.icon_refs.append(photo)
                tk.Label(icon_holder, image=photo, bg=BACKGROUND).pack(expand=True)
            else:
                tk.Label(icon_holder, text="■", fg=TEXT_SOFT, bg=BACKGROUND, font=("Segoe UI", 12)).pack(expand=True)

            mid = tk.Frame(row, bg=BACKGROUND)
            mid.pack(side="left", fill="x", expand=True)

            tk.Label(
                mid,
                text=f"{habit_name}   (Strike: {strike} | Freeze: {habit_freezes})",
                fg=TEXT_BRIGHT,
                bg=BACKGROUND,
                font=("Segoe UI", 11, "bold"),
            ).pack(anchor="w")

            line = tk.Frame(mid, bg=BACKGROUND)
            line.pack(fill="x", anchor="w", pady=(6, 0))

            style = None
            if today_date() in dates_set:
                style = today_tile_style(get_work_seconds_today(habit_name))

            bar = make_progress_bar(line, streak_days, dates_set, protected_set, style)
            bar.pack(side="left", anchor="w")

            btns = tk.Frame(line, bg=BACKGROUND)
            btns.pack(side="left", padx=(12, 0), anchor="center")

            tk.Button(
                btns,
                text="🕒",
                font=("Segoe UI", 12),
                fg=TEXT_BRIGHT,
                bg=BACKGROUND,
                activebackground=BTN_ACTIVE_BG,
                bd=0,
                command=lambda h=habit_name: habit_timer.open_habit_timer(
                    self,
                    h,
                    #db_path=TIME_DB_PATH,
                    #on_complete=(lambda habit=h: self.mark_habit_done_from_timer(habit)),
                    on_complete=lambda habit=h: self.mark_habit_done_from_timer(habit)
                ),
            ).pack(side="left", padx=6)

            tk.Button(
                btns,
                text="...",
                font=("Segoe UI", 12, "bold"),
                fg=TEXT_BRIGHT,
                bg=BACKGROUND,
                activebackground=BTN_ACTIVE_BG,
                bd=0,
                command=lambda h=habit_name: self.open_edit_dialog(h),
            ).pack(side="left", padx=6)


if __name__ == "__main__":
    app = HabitApp()
    app.mainloop()
