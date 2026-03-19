import os, json
import tkinter as tk
from tkinter import ttk, filedialog, colorchooser, messagebox
from PIL import Image

import freeze_store

THEME_FILE = "theme.json"

def load_theme() -> dict:
    if not os.path.exists(THEME_FILE):
        return {}
    try:
        with open(THEME_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}

def save_theme(theme: dict) -> None:
    with open(THEME_FILE, "w", encoding="utf-8") as f:
        json.dump(theme, f, indent=2)

def rgb_to_hex(rgb):
    return "#{:02X}{:02X}{:02X}".format(*rgb)

def extract_palette(image_path: str, k: int = 10):
    img = Image.open(image_path).convert("RGB")
    img = img.resize((96, 96))
    pixels = list(img.getdata())

    buckets = {}
    for r, g, b in pixels:
        br = r // 16
        bg = g // 16
        bb = b // 16
        key = (br, bg, bb)
        buckets[key] = buckets.get(key, 0) + 1

    top = sorted(buckets.items(), key=lambda x: x[1], reverse=True)[:k]
    colors = []
    for (br, bg, bb), _cnt in top:
        colors.append((br * 16 + 8, bg * 16 + 8, bb * 16 + 8))
    return colors

def open_settings_window(parent, habits_provider, apply_strike_callback):
    win = tk.Toplevel(parent)
    win.title("Settings / Debug")
    win.configure(bg=parent["bg"])
    win.resizable(False, False)
    win.grab_set()

    theme = load_theme()

    # --- Theme section ---
    tk.Label(win, text="Theme / Palette", bg=parent["bg"], fg="#333", font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=12, pady=(12, 6))
    palette_frame = tk.Frame(win, bg=parent["bg"])
    palette_frame.pack(fill="x", padx=12)

    def choose_theme_image():
        path = filedialog.askopenfilename(
            title="Pick an image to extract colors from",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.webp")]
        )
        if not path:
            return
        cols = extract_palette(path, k=10)
        cols_sorted = sorted(cols, key=lambda c: (c[0] + c[1] + c[2]))

        light = cols_sorted[-1]
        dark = cols_sorted[0]
        mid1 = cols_sorted[len(cols_sorted)//2]
        mid2 = cols_sorted[len(cols_sorted)//2 - 1]

        theme_update = {
            "BACKGROUND": rgb_to_hex(light),
            "PANEL_BG": rgb_to_hex(mid1),
            "ACCENT": rgb_to_hex(mid2),
            "BUTTON_BG": rgb_to_hex(mid2),
            "TEXT": rgb_to_hex(dark),
            "MUTED_TEXT": rgb_to_hex(cols_sorted[2] if len(cols_sorted) > 2 else dark),
        }
        theme.update(theme_update)
        save_theme(theme)
        messagebox.showinfo("Theme saved", "Theme saved to theme.json.\nRestart the app to apply.")

    ttk.Button(palette_frame, text="Pick Image → Extract Theme", command=choose_theme_image).pack(side="left")

    def pick_color_for(key):
        c = colorchooser.askcolor(title=f"Pick {key}")
        if not c or not c[1]:
            return
        theme[key] = c[1]
        save_theme(theme)
        messagebox.showinfo("Saved", f"{key} saved.\nRestart the app to apply.")

    ttk.Button(palette_frame, text="Pick BACKGROUND", command=lambda: pick_color_for("BACKGROUND")).pack(side="left", padx=6)
    ttk.Button(palette_frame, text="Pick TEXT", command=lambda: pick_color_for("TEXT")).pack(side="left", padx=6)

    # --- Freeze counts ---
    tk.Label(win, text="Freeze Counts", bg=parent["bg"], fg="#333", font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=12, pady=(14, 6))
    fr = tk.Frame(win, bg=parent["bg"])
    fr.pack(fill="x", padx=12)

    global_var = tk.StringVar(value=str(freeze_store.get_global()))
    tk.Label(fr, text="Global (★) Freezes:", bg=parent["bg"]).grid(row=0, column=0, sticky="w")
    ttk.Entry(fr, textvariable=global_var, width=8).grid(row=0, column=1, padx=6, sticky="w")

    habit_names = habits_provider()
    habit_var = tk.StringVar(value=(habit_names[0] if habit_names else ""))
    habit_freeze_var = tk.StringVar(value="0")

    tk.Label(fr, text="Habit:", bg=parent["bg"]).grid(row=1, column=0, sticky="w", pady=(8, 0))
    cb = ttk.Combobox(fr, textvariable=habit_var, values=habit_names, state="readonly", width=22)
    cb.grid(row=1, column=1, sticky="w", padx=6, pady=(8, 0))

    tk.Label(fr, text="Habit Freezes:", bg=parent["bg"]).grid(row=2, column=0, sticky="w")
    ttk.Entry(fr, textvariable=habit_freeze_var, width=8).grid(row=2, column=1, sticky="w", padx=6)

    def load_selected_habit_freeze(*_):
        if habit_var.get():
            habit_freeze_var.set(str(freeze_store.get_habit(habit_var.get())))
    cb.bind("<<ComboboxSelected>>", load_selected_habit_freeze)
    load_selected_habit_freeze()

    def save_freezes():
        freeze_store.set_global(int(global_var.get() or "0"))
        if habit_var.get():
            freeze_store.set_habit(habit_var.get(), int(habit_freeze_var.get() or "0"))
        messagebox.showinfo("Saved", "Freeze counts saved.")

    ttk.Button(fr, text="Save Freezes", command=save_freezes).grid(row=3, column=0, columnspan=2, pady=(10, 0), sticky="w")

    # --- Force streak ---
    tk.Label(win, text="Force Streak (testing)", bg=parent["bg"], fg="#333", font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=12, pady=(14, 6))
    st = tk.Frame(win, bg=parent["bg"])
    st.pack(fill="x", padx=12, pady=(0, 12))

    strike_var = tk.StringVar(value="5")
    tk.Label(st, text="Set streak days to:", bg=parent["bg"]).grid(row=0, column=0, sticky="w")
    ttk.Entry(st, textvariable=strike_var, width=8).grid(row=0, column=1, padx=6, sticky="w")

    def apply_strike():
        h = habit_var.get()
        if not h:
            return
        n = max(0, int(strike_var.get() or "0"))
        apply_strike_callback(h, n)
        messagebox.showinfo("Done", f"Set {h} streak to {n} (ending yesterday).")

    ttk.Button(st, text="Apply", command=apply_strike).grid(row=0, column=2, padx=6)

    return win
