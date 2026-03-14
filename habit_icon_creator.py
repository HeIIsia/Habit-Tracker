import base64
import io
import os
import re
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox

from dotenv import load_dotenv
from openai import OpenAI
from PIL import Image, ImageTk

load_dotenv("keys.env")


# =========================
# MODELS / FILES
# =========================
IMAGE_MODEL = "gpt-image-1"
ANALYSIS_MODEL = "gpt-4.1-mini"
ICON_SIZE = 100
PREVIEW_SIZE = 180
ICONS_DIR = Path("habit_icons")


# =========================
# COLORS
# =========================
WINDOW_BG = "#FFFFFF"
PANEL_BG = "#E3A6FF"
PREVIEW_BG = "#C559FF"
PREVIEW_BORDER = "#8B1BCB"

TEXT_MAIN = "#B41DDA"
TEXT_MUTED = "#9954AE"
TEXT_STATUS = "#E9DDFF"

ENTRY_BG = "#E3A6FF"
ENTRY_FG = "#000000"

BUTTON_BG = "#F5E0FF"
BUTTON_ACTIVE_BG = "#454545"
BUTTON_FG = "#8B1BCB"

SYSTEM_PROMPT = """You are a professional icon designer who specializes in elegant, cute, minimalistic habit icons.

Create a single high-quality icon based on the user's habit prompt.

Hard requirements:
- High resolution, clean digital illustration style
- No pixelation
- Light background
- Cute, minimalistic shapes
- Simple composition that is easy to recognize instantly
- Soft, beautiful pastel color palette
- Clean edges and smooth shapes
- Centered composition
- Polished, friendly, aesthetically pleasing look
- The main object should fill most of the icon area while still leaving comfortable breathing room
- Avoid clutter, unnecessary detail, harsh contrast, dark backgrounds, or realistic rendering
- Make the icon feel charming, modern, and visually soft

Style requirements:
- minimalistic app icon
- cute and elegant
- pastel colors
- smooth clean shapes
- easy to recognize at small size
- bright, gentle, friendly design

Subject interpretation examples:
- reading -> a cute minimal book
- walking -> a simple pastel sneaker
- getting up early -> a soft pastel sunrise

Create exactly one icon that clearly represents the habit."""

SYSTEM_PROMPT_2 = """You are a professional game designer who specializes in high-quality pixel art UI icons for games.

Your job is to create a single pixel-art icon based on the user's habit prompt.

Hard requirements:
- Final design must read clearly as a tiny game icon.
- Avoid ambiguous and blocky silhouettes, inconsistent outlines, low contrast in key elements, flat color without shading.
- The icon must be composed as true pixel art with crisp, hard-edged pixels.
- No blur, no soft shading, no painterly texture, no glow, no feathering, no semi-transparent edges.
- Use clean pixel clusters and strong silhouette readability.
- Black background only.
- The border must be exactly 3 pixels thick.
- The border must be the outermost frame of the image on all 4 sides.
- There must be no black padding or empty margin outside the border.
- The main subject should fill most of the interior space while remaining centered and readable.
- Keep the icon tightly framed, like a polished game inventory icon.
- Use a limited pixel-art palette, about 4 to 8 colors plus black background.
- Choose a color palette that best fits the subject.
- Do not default to yellow-orange unless the subject naturally calls for it.
- Vary the palette between subjects when appropriate.
- Prefer strong contrast and visually distinct colors.
- The border color should match the icon’s palette and feel intentional.

Style requirements:
- retro game UI icon
- clean silhouette
- compact composition
- readable at very small size
- professional, polished, appealing pixel art

Subject interpretation examples:
- reading -> book
- walking -> sneaker
- getting up early -> sunrise

Create exactly one icon that is easy to recognize at very small size.
"""


def open_habit_icon_creator(
    parent,
    existing_habits,
    on_accept,
    *,
    mode="create",
    original_name="",
    initial_name="",
    initial_icon_path="",
):
    """
    Opens the icon creator dialog.

    on_accept callback receives:
        on_accept(original_name, new_name, icon_path)
    """
    return HabitIconCreatorDialog(
        parent=parent,
        existing_habits=existing_habits,
        on_accept=on_accept,
        mode=mode,
        original_name=original_name,
        initial_name=initial_name,
        initial_icon_path=initial_icon_path,
    )


class HabitIconCreatorDialog(tk.Toplevel):
    def __init__(
        self,
        parent,
        existing_habits,
        on_accept,
        *,
        mode="create",
        original_name="",
        initial_name="",
        initial_icon_path="",
    ):
        super().__init__(parent)

        self.parent = parent
        self.on_accept = on_accept
        self.mode = mode
        self.original_name = original_name.strip()
        self.initial_icon_path = initial_icon_path.strip()

        self.existing_habits = {h.strip().lower() for h in existing_habits}
        self.client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

        self.habit_var = tk.StringVar(value=initial_name.strip())
        self.habit_var.trace_add("write", self._on_name_change)

        self.current_icon_image = None
        self.current_preview_photo = None
        self.is_busy = False
        self.negative_feedback_notes = []

        self.title("Create Habit" if mode == "create" else "Edit Habit")
        self.configure(bg=WINDOW_BG)
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self._build_ui()
        self._load_initial_icon()
        self._update_action_buttons()
        self._center_on_parent()
        self.name_entry.focus_set()

    def _build_ui(self):
        outer = tk.Frame(self, bg=WINDOW_BG)
        outer.pack(padx=18, pady=18)

        tk.Label(
            outer,
            text="Enter the habit name:",
            bg=WINDOW_BG,
            fg=TEXT_MAIN,
            font=("Segoe UI", 11),
        ).pack(anchor="w")

        self.name_entry = tk.Entry(
            outer,
            textvariable=self.habit_var,
            width=30,
            font=("Segoe UI", 11),
            bg=ENTRY_BG,
            fg=ENTRY_FG,
            insertbackground=ENTRY_FG,
        )
        self.name_entry.pack(pady=(8, 10), fill="x")

        self.generate_button = tk.Button(
            outer,
            text="Generate Icon",
            width=18,
            command=self.generate_icon,
            bg=BUTTON_BG,
            fg=BUTTON_FG,
            activebackground=BUTTON_ACTIVE_BG,
            activeforeground=BUTTON_FG,
            relief="raised",
        )
        self.generate_button.pack(pady=(0, 14))

        middle = tk.Frame(outer, bg=WINDOW_BG)
        middle.pack()

        self.dislike_button = tk.Button(
            middle,
            text="👎",
            width=5,
            command=self.start_dislike_flow,
            font=("Segoe UI Emoji", 13),
            bg=BUTTON_BG,
            fg=BUTTON_FG,
            activebackground=BUTTON_ACTIVE_BG,
            activeforeground=BUTTON_FG,
            relief="raised",
        )
        self.dislike_button.pack(side="left", padx=(0, 12))

        self.preview_frame = tk.Frame(
            middle,
            width=PREVIEW_SIZE + 20,
            height=PREVIEW_SIZE + 20,
            bg=PREVIEW_BG,
            highlightbackground=PREVIEW_BORDER,
            highlightthickness=1,
        )
        self.preview_frame.pack(side="left")
        self.preview_frame.pack_propagate(False)

        self.preview_label = tk.Label(
            self.preview_frame,
            text="Generated icon\nwill appear here",
            bg=PREVIEW_BG,
            fg=TEXT_MUTED,
            font=("Segoe UI", 11),
            justify="center",
        )
        self.preview_label.pack(expand=True)

        self.like_button = tk.Button(
            middle,
            text="👍",
            width=5,
            command=self.accept_changes,
            font=("Segoe UI Emoji", 13),
            bg=BUTTON_BG,
            fg=BUTTON_FG,
            activebackground=BUTTON_ACTIVE_BG,
            activeforeground=BUTTON_FG,
            relief="raised",
        )
        self.like_button.pack(side="left", padx=(12, 0))

        self.status_label = tk.Label(
            outer,
            text="Type a habit name to begin.",
            bg=WINDOW_BG,
            fg=TEXT_STATUS,
            font=("Segoe UI", 10),
        )
        self.status_label.pack(pady=(14, 0))

    def _center_on_parent(self):
        self.update_idletasks()
        self.parent.update_idletasks()

        pw = self.parent.winfo_width()
        ph = self.parent.winfo_height()
        px = self.parent.winfo_rootx()
        py = self.parent.winfo_rooty()

        ww = self.winfo_width()
        wh = self.winfo_height()

        x = px + (pw - ww) // 2
        y = py + (ph - wh) // 2
        self.geometry(f"+{x}+{y}")

    def _load_initial_icon(self):
        if not self.initial_icon_path or not os.path.exists(self.initial_icon_path):
            return

        try:
            image = Image.open(self.initial_icon_path).convert("RGBA")
            self.current_icon_image = image.resize((ICON_SIZE, ICON_SIZE), Image.Resampling.NEAREST)
            self.display_generated_icon(self.current_icon_image, from_startup=True)
        except Exception:
            self.current_icon_image = None

    def _on_name_change(self, *_):
        self._update_action_buttons()

    def _update_action_buttons(self):
        has_name = bool(self.habit_var.get().strip())
        has_icon = self.current_icon_image is not None

        self.generate_button.config(
            state="disabled" if self.is_busy or not has_name else "normal"
        )
        self.dislike_button.config(
            state="disabled" if self.is_busy or not has_icon else "normal"
        )
        self.like_button.config(
            state="disabled" if self.is_busy or not has_name or not has_icon else "normal"
        )
        self.name_entry.config(state="disabled" if self.is_busy else "normal")

    def _set_busy(self, busy: bool, status_text: str):
        self.is_busy = busy
        self.status_label.config(text=status_text)
        self._update_action_buttons()

    def build_image_prompt(self, habit: str) -> str:
        disliked_block = ""
        if self.negative_feedback_notes:
            disliked_block = (
                "\n\nAvoid these qualities because the user disliked them:\n- "
                + "\n- ".join(self.negative_feedback_notes[-5:])
            )

        return f"""SYSTEM:
{SYSTEM_PROMPT}{disliked_block}

USER:
Habit: {habit}

Create one high-quality minimalistic icon that represents this habit.
Make the subject easy to recognize immediately, even at small size.
Use a light background, beautiful pastel colors, and cute clean shapes with smooth edges.
Keep the composition simple, centered, polished, and uncluttered, with no pixelation or harsh details.
"""
    User_prompt_pixel = """Create one pixel-art game icon that represents this habit.
Make the subject obvious immediately at tiny size.
Use a palette that fits the subject naturally and avoid repeating the same palette as previous icons unless it is clearly the best choice.
Keep the composition tightly framed so the 3-pixel border sits at the very edge of the icon image."""

    def generate_icon(self):
        if not os.environ.get("OPENAI_API_KEY"):
            messagebox.showerror(
                "Missing API key",
                "Set your OPENAI_API_KEY environment variable before running the app.",
                parent=self,
            )
            return

        habit_name = self.habit_var.get().strip()
        if not habit_name:
            return

        self._set_busy(True, f"Generating icon for: {habit_name}...")
        self.preview_label.config(image="", text="Generating...")

        threading.Thread(
            target=self._generate_icon_worker,
            args=(habit_name,),
            daemon=True,
        ).start()

    def _generate_icon_worker(self, habit_name: str):
        try:
            prompt = self.build_image_prompt(habit_name)

            response = self.client.images.generate(
                model=IMAGE_MODEL,
                prompt=prompt,
                size="1024x1024",
                quality="high",
                output_format="png",
                background="opaque",
            )

            if not response.data or not response.data[0].b64_json:
                raise RuntimeError("No image data was returned by the API.")

            image_bytes = base64.b64decode(response.data[0].b64_json)
            image = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
            final_icon = image.resize((ICON_SIZE, ICON_SIZE), Image.Resampling.NEAREST)

            self.after(0, lambda: self.display_generated_icon(final_icon))

        except Exception as exc:
            self.after(0, lambda: self.handle_generation_error(exc))

    def display_generated_icon(self, pil_image: Image.Image, from_startup=False):
        self.current_icon_image = pil_image

        preview_image = pil_image.resize((PREVIEW_SIZE, PREVIEW_SIZE), Image.Resampling.NEAREST)
        self.current_preview_photo = ImageTk.PhotoImage(preview_image)
        self.preview_label.config(image=self.current_preview_photo, text="")

        if from_startup:
            self.status_label.config(text="You can rename the habit or generate a new icon.")
            self._update_action_buttons()
        else:
            self._set_busy(False, "Icon ready.")

    def handle_generation_error(self, error: Exception):
        self._set_busy(False, "Icon generation failed.")
        self.preview_label.config(image="", text="Generated icon\nwill appear here")
        messagebox.showerror(
            "Generation failed",
            f"Could not generate icon:\n{error}",
            parent=self,
        )

    def start_dislike_flow(self):
        if self.current_icon_image is None or self.is_busy:
            return

        self._set_busy(True, "Analyzing feedback and improving icon...")
        threading.Thread(
            target=self._analyze_feedback_worker,
            daemon=True,
        ).start()

    def _analyze_feedback_worker(self):
        try:
            image_data_url = self.pil_image_to_data_url(self.current_icon_image)
            habit_name = self.habit_var.get().strip()

            developer_text = (
                "You analyze small pixel-art game icons that the user disliked. "
                "Identify the concrete visual details that likely made the icon less successful "
                "so future icons can avoid them. Focus on readability, silhouette, pixel crispness, "
                "palette, contrast, framing, border treatment, and subject clarity. "
                "Return 4 to 8 concise bullet points followed by one final line that starts exactly "
                "with 'Preference summary:' and contains a short reusable avoid-list summary."
            )
            user_text = (
                f"The user dislikes this icon for the habit '{habit_name}'. "
                f"Analyze what likely made it weak."
            )

            response = self.client.responses.create(
                model=ANALYSIS_MODEL,
                input=[
                    {
                        "role": "developer",
                        "content": [{"type": "input_text", "text": developer_text}],
                    },
                    {
                        "role": "user",
                        "content": [
                            {"type": "input_text", "text": user_text},
                            {"type": "input_image", "image_url": image_data_url, "detail": "high"},
                        ],
                    },
                ],
            )

            analysis_text = self.extract_response_text(response).strip()
            print("\n" + "=" * 70)
            print("ICON FEEDBACK ANALYSIS (DISLIKED)")
            print(f"Habit: {habit_name}")
            print("-" * 70)
            print(analysis_text)
            print("=" * 70 + "\n")

            preference_summary = self.extract_preference_summary(analysis_text)
            if preference_summary:
                self.negative_feedback_notes.append(preference_summary)

            self.after(0, self._regenerate_after_dislike)

        except Exception as exc:
            self.after(0, lambda: self.handle_feedback_error(exc))

    def _regenerate_after_dislike(self):
        self._set_busy(False, "Regenerating icon with feedback...")
        self.generate_icon()

    def handle_feedback_error(self, error: Exception):
        self._set_busy(False, "Feedback analysis failed.")
        messagebox.showerror(
            "Analysis failed",
            f"Could not analyze icon feedback:\n{error}",
            parent=self,
        )

    def accept_changes(self):
        new_name = self.habit_var.get().strip()
        if not new_name or self.current_icon_image is None:
            return

        old_key = self.original_name.lower()
        new_key = new_name.lower()

        if new_key in self.existing_habits and new_key != old_key:
            messagebox.showwarning(
                "Habit already exists",
                "A habit with this name already exists.",
                parent=self,
            )
            return

        try:
            icon_path = self.save_icon_for_habit(new_name, old_name=self.original_name)
            self.on_accept(self.original_name, new_name, icon_path)
            self.destroy()
        except Exception as exc:
            messagebox.showerror(
                "Save failed",
                f"Could not save the icon:\n{exc}",
                parent=self,
            )

    def save_icon_for_habit(self, habit_name: str, old_name: str = "") -> str:
        ICONS_DIR.mkdir(exist_ok=True)

        def safe_filename(name: str) -> str:
            cleaned = re.sub(r"[^a-zA-Z0-9_-]+", "_", name.strip()).strip("_")
            return cleaned or "habit"

        new_path = ICONS_DIR / f"{safe_filename(habit_name)}.png"
        self.current_icon_image.save(new_path, format="PNG")

        if old_name and old_name.strip().lower() != habit_name.strip().lower():
            old_path = ICONS_DIR / f"{safe_filename(old_name)}.png"
            try:
                if old_path.exists() and old_path != new_path:
                    old_path.unlink()
            except Exception:
                pass

        return str(new_path)

    def pil_image_to_data_url(self, image: Image.Image) -> str:
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")
        return f"data:image/png;base64,{encoded}"

    def extract_preference_summary(self, analysis_text: str) -> str:
        match = re.search(r"Preference summary:\s*(.+)", analysis_text, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip()

        lines = [line.strip("-• \t") for line in analysis_text.splitlines() if line.strip()]
        return lines[-1] if lines else ""

    def extract_response_text(self, response) -> str:
        direct_text = getattr(response, "output_text", None)
        if direct_text:
            return direct_text

        collected = []
        for item in getattr(response, "output", []) or []:
            for content in getattr(item, "content", []) or []:
                if getattr(content, "type", None) in {"output_text", "text"}:
                    text_value = getattr(content, "text", None)
                    if text_value:
                        collected.append(text_value)

        return "\n".join(collected).strip()
