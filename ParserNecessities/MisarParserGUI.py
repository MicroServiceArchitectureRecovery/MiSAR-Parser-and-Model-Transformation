"""
Parser GUI

@Author RanaFakeeh-87
@Author aljvdi
"""
from __future__ import annotations

import json
import os
import shutil
import stat
import sys
import threading
import tkinter as tk
import tkinter.font as tkfont
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Iterable, List, Optional

try:
    import yaml
except Exception:
    yaml = None

try:
    from git import Repo
except Exception:
    Repo = None

try:
    from MisarParserMain import create_psm_instance
except Exception as exc:
    create_psm_instance = None
    BACKEND_IMPORT_ERROR = exc
else:
    BACKEND_IMPORT_ERROR = None

try:
    from MisarParserConfig import describe_psm_selection
except Exception:
    def describe_psm_selection() -> str:
        return "Not available"

try:
    from MisarParserLanguage import format_module_display_path, strip_language_badge
except Exception:
    def format_module_display_path(path: str) -> str:
        return path

    def strip_language_badge(path: str) -> str:
        return path


try:
    from MisarParserValidation import (
        format_docker_compose_user_messages,
        format_docker_compose_validation_messages,
        log_docker_compose_validation_results,
        validate_docker_compose_files,
    )
except Exception:
    def validate_docker_compose_files(file_paths, log=False):
        return []

    def format_docker_compose_validation_messages(results):
        return [], []

    def format_docker_compose_user_messages(results):
        return [], []

    def log_docker_compose_validation_results(results):
        return None


APP_NAME = "MiSAR Parser"
USER_HOME_DIR = Path.home()
PARSER_UI_DIR = Path(__file__).resolve().parent
PROJECT_ROOT_DIR = PARSER_UI_DIR.parent
MISAR_DIR = USER_HOME_DIR / "MiSAR"
PARSER_DIR = MISAR_DIR / "Parser"
VERSION_FILE_PATH = PROJECT_ROOT_DIR / "MISAR.versions.json"
CONFIG_FILE_PATH = PROJECT_ROOT_DIR / "MISAR.configs.json"
SESSION_FILE_PATH = PARSER_DIR / "MisarParserGUI.last_session.json"
WINDOW_SIZE_CONFIG_KEY = "ui.window_size"
BASELINE_DPI = 96.0
BASELINE_TK_SCALING = BASELINE_DPI / 72.0
VERSION_KEYS = {"parser": ("misar.parser",)}


def _read_version_json(file_path: Path) -> dict:
    try:
        if not file_path.is_file():
            return {}
        data = json.loads(file_path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def read_misar_configs() -> dict:
    """Read shared MISAR UI options written by the AIO launcher."""
    try:
        if not CONFIG_FILE_PATH.is_file():
            return {}
        data = json.loads(CONFIG_FILE_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def normalise_window_size_choice(choice: str) -> str:
    choice = str(choice or "auto").strip().lower()
    return choice if choice in {"auto", "compact", "normal", "comfortable", "large"} else "auto"


def configured_window_size_choice() -> str:
    configs = read_misar_configs()
    return normalise_window_size_choice(configs.get(WINDOW_SIZE_CONFIG_KEY, "auto"))


def safe_float(value, default):
    """Convert platform/Tk numeric values safely."""
    try:
        return float(value)
    except Exception:
        return float(default)


def normalise_scale_factor(value):
    """Clamp invalid display-scale values to a safe cross-platform range."""
    try:
        value = float(value)
    except Exception:
        return 1.0

    if value <= 0:
        return 1.0

    return max(0.75, min(value, 3.0))


def read_tk_scaling_info(root=None, screen_width=None, screen_height=None) -> dict:
    """Read DPI/Tk scaling using Tk APIs available on Windows, macOS and Linux."""
    tk_scaling = BASELINE_TK_SCALING
    pixels_per_inch = BASELINE_DPI

    if root is not None:
        try:
            tk_scaling = safe_float(root.tk.call("tk", "scaling"), BASELINE_TK_SCALING)
        except Exception:
            tk_scaling = BASELINE_TK_SCALING

        try:
            pixels_per_inch = safe_float(root.winfo_fpixels("1i"), BASELINE_DPI)
        except Exception:
            pixels_per_inch = BASELINE_DPI

    tk_dpi_scale = normalise_scale_factor(tk_scaling / BASELINE_TK_SCALING)
    pixel_dpi_scale = normalise_scale_factor(pixels_per_inch / BASELINE_DPI)
    effective_scale = max(tk_dpi_scale, pixel_dpi_scale, 1.0)

    return {
        "tk_scaling": float(tk_scaling),
        "pixels_per_inch": float(pixels_per_inch),
        "tk_dpi_scale": float(tk_dpi_scale),
        "pixel_dpi_scale": float(pixel_dpi_scale),
        "effective_scale": float(effective_scale),
        "effective_width": int(screen_width / effective_scale) if screen_width else None,
        "effective_height": int(screen_height / effective_scale) if screen_height else None,
    }


def is_compact_layout_required(choice: str, screen_width: int, screen_height: int, scaling_info: dict | None = None) -> bool:
    """Return True when parser should use compact sizing/list rows."""
    choice = normalise_window_size_choice(choice)

    if choice == "compact":
        return True

    if choice != "auto":
        return False

    scaling_info = scaling_info or {}
    effective_width = scaling_info.get("effective_width") or screen_width
    effective_height = scaling_info.get("effective_height") or screen_height
    effective_scale = scaling_info.get("effective_scale", 1.0)

    return (
        effective_width <= 1366
        or effective_height <= 800
        or (effective_scale >= 1.25 and effective_height <= 900)
    )


def resolve_ui_density(choice: str, screen_width: int, screen_height: int, scaling_info: dict | None = None) -> float:
    """Resolve shared window-size choice into a parser UI scale."""
    choice = normalise_window_size_choice(choice)

    if choice == "compact":
        return 0.78
    if choice == "normal":
        return 1.0
    if choice == "comfortable":
        return 1.08
    if choice == "large":
        return 1.18

    scaling_info = scaling_info or read_tk_scaling_info(None, screen_width, screen_height)
    effective_scale = scaling_info.get("effective_scale", 1.0)

    if is_compact_layout_required(choice, screen_width, screen_height, scaling_info):
        return 0.82 if effective_scale < 1.5 else 0.78
    if screen_width >= 2200 and screen_height >= 1300:
        return 1.06
    return 1.0


def resolve_list_rows(choice: str, screen_width: int, screen_height: int, scaling_info: dict | None = None) -> tuple[int, int]:
    """Return required/optional list heights suitable for the current display scale."""
    choice = normalise_window_size_choice(choice)
    scaling_info = scaling_info or read_tk_scaling_info(None, screen_width, screen_height)

    if is_compact_layout_required(choice, screen_width, screen_height, scaling_info):
        # True 720p needs short lists. Scaled/full-screen 1080p still has enough
        # logical height, so use more rows to avoid tiny list boxes in large cards.
        if screen_height <= 800:
            return 5, 3
        if screen_height <= 1100:
            return 8, 5
        return 10, 7
    if screen_height <= 950:
        return 8, 5
    return 12, 9


def build_parser_layout_decision(
    screen_width: int,
    screen_height: int,
    choice: str = "auto",
    scaling_info: dict | None = None,
) -> dict:
    """Build a testable parser layout decision for the current screen and scale."""
    choice = normalise_window_size_choice(choice)
    scaling_info = scaling_info or read_tk_scaling_info(None, screen_width, screen_height)
    density = resolve_ui_density(choice, screen_width, screen_height, scaling_info)
    required_rows, optional_rows = resolve_list_rows(choice, screen_width, screen_height, scaling_info)
    compact_layout = is_compact_layout_required(choice, screen_width, screen_height, scaling_info)

    if compact_layout:
        target_width = max(screen_width - 16, 980)
        target_height = max(screen_height - 56, 620)
        x = 0
        y = 0
        maximise = True
    else:
        target_width = min(max(1500, int(screen_width * 0.94)), max(screen_width - 24, 980))
        target_height = min(max(920, int(screen_height * 0.90)), max(screen_height - 60, 620))
        x = max((screen_width - target_width) // 2, 0)
        y = max((screen_height - target_height) // 2, 0)
        maximise = False

    return {
        "component": "parser",
        "screen_width": int(screen_width),
        "screen_height": int(screen_height),
        "tk_scaling": scaling_info.get("tk_scaling"),
        "pixels_per_inch": scaling_info.get("pixels_per_inch"),
        "effective_scale": scaling_info.get("effective_scale"),
        "effective_width": scaling_info.get("effective_width"),
        "effective_height": scaling_info.get("effective_height"),
        "window_size_option": choice,
        "resolved_ui_density": float(density),
        "small_screen": compact_layout,
        "target_width": int(target_width),
        "target_height": int(target_height),
        "x": int(x),
        "y": int(y),
        "maximised": maximise,
        "required_list_rows": int(required_rows),
        "optional_list_rows": int(optional_rows),
    }


def picker_cards_fill_available_space() -> bool:
    """Return True when only picker cards stretch their list area vertically."""
    return True


def parser_layout_debug_enabled() -> bool:
    """Return True when parser layout decisions should be emitted for AIO debug logs."""
    return os.environ.get("MISAR_AIO_DEBUG") == "1"


def emit_parser_layout_diagnostics(decision: dict) -> None:
    """Print parser layout diagnostics so the AIO debug logger can capture them."""
    if parser_layout_debug_enabled():
        print("misar_parser_layout_decision = " + json.dumps(decision, sort_keys=True), flush=True)


def read_project_versions() -> dict:
    return _read_version_json(VERSION_FILE_PATH)


def component_version(component: str) -> str:
    versions = read_project_versions()
    for key in VERSION_KEYS.get(component, ()):
        value = str(versions.get(key, "")).strip()
        if value:
            return value if value.lower().startswith("v") else f"v{value}"
    return ""


def title_with_version(title: str, version: str) -> str:
    return f"{title} - {version}" if version else title


APP_VERSION = component_version("parser")
DEPENDENCY_BUILD_FILES = [
    "pom.xml",
    "requirements.txt",
    "pyproject.toml",
    "Pipfile",
    "setup.py",
    "setup.cfg",
    "poetry.lock",
]
FORBIDDEN_PROJECT_CHARS = set('<>:/\\|?*"')

PALETTE = {
    "bg": "#eef2f7",
    "sidebar": "#101c36",
    "sidebar_text": "#b8c2d6",
    "sidebar_title": "#ffffff",
    "panel": "#ffffff",
    "panel_soft": "#f8fafc",
    "border": "#dbe3ef",
    "border_strong": "#cbd5e1",
    "title": "#162037",
    "text": "#334155",
    "muted": "#64748b",
    "input": "#f8fafc",
    "input_text": "#1e293b",
    "accent": "#2563eb",
    "accent_hover": "#1d4ed8",
    "accent_pressed": "#1e40af",
    "secondary": "#eef2f7",
    "secondary_hover": "#e2e8f0",
    "secondary_text": "#1e293b",
    "success": "#16a34a",
    "success_hover": "#15803d",
    "danger": "#dc2626",
    "danger_soft": "#fef2f2",
    "disabled": "#d9e1ec",
    "disabled_text": "#7b8797",
    "status_bg": "#eef2f8",
}


CARD_RADIUS = 10
CARD_SHADOW_OFFSET = 5
LISTBOX_ROWS = 3
UI_DENSITY = 1.0


def ui_size(value: int, minimum: int = 1) -> int:
    return max(int(round(value * UI_DENSITY)), minimum)


def ui_font(size: int = 11, weight: str = "normal"):
    try:
        family = tkfont.nametofont("TkDefaultFont").cget("family")
    except Exception:
        family = "Helvetica"
    scaled_size = ui_size(size, 8)
    return (family, scaled_size, weight) if weight != "normal" else (family, scaled_size)


def notify_setup_required() -> None:
    messagebox.showinfo(
        "Complete setup first",
        "Please first add the project name, project build directory, and output directory.",
    )

def compact_raw_path_for_display(raw_path: str) -> str:
    """Shorten a path for display while keeping the full path internally."""
    path_text = str(raw_path or "").strip()

    if not path_text:
        return ""

    trimmed = path_text.rstrip("/\\")

    if not trimmed:
        return path_text

    normalised = trimmed.replace("\\", "/")
    parts = [part for part in normalised.split("/") if part]

    if len(parts) >= 2:
        return f"../{parts[-2]}/{parts[-1]}"

    return trimmed


def compact_path_display(value: str) -> str:
    """Show only the parent folder and selected file/folder, preserving language badges."""
    text = str(value or "").strip()

    if not text:
        return ""

    raw_path = strip_language_badge(text)
    language_badge = ""

    if raw_path and text.startswith(raw_path):
        language_badge = text[len(raw_path):].strip()

    compact_path = compact_raw_path_for_display(raw_path or text)

    if language_badge:
        return f"{compact_path} {language_badge}"

    return compact_path


def copy_text_to_clipboard(widget, text: str) -> bool:
    """Copy text to the system clipboard from any Tkinter widget."""
    value = str(text or "").strip()

    if not value:
        return False

    try:
        root = widget.winfo_toplevel()
        root.clipboard_clear()
        root.clipboard_append(value)
        root.update_idletasks()
        return True
    except tk.TclError:
        return False


class EntrySnapshot:
    def __init__(self, value: str):
        self.value = value

    def get(self) -> str:
        return self.value


class ListboxSnapshot:
    def __init__(self, values: Iterable[str]):
        self.values = tuple(values)

    def size(self) -> int:
        return len(self.values)

    def get(self, start=0, end=None):
        if end is None:
            if not self.values:
                return ""
            return self.values[self._index(start)]

        start_index = self._index(start)
        end_index = len(self.values) - 1 if str(end) == "end" else self._index(end)
        if end_index < start_index:
            return tuple()
        return self.values[start_index:end_index + 1]

    def _index(self, value) -> int:
        if str(value) == "end":
            return max(len(self.values) - 1, 0)
        try:
            index = int(value)
        except Exception:
            return 0
        return min(max(index, 0), max(len(self.values) - 1, 0))


class RoundedButton(tk.Canvas):
    def __init__(self, master, text: str, command=None, variant: str = "primary", width: int = 132, disabled_command=None):
        super().__init__(master, width=ui_size(width), height=ui_size(38), highlightthickness=0, bd=0, cursor="hand2")
        self.text = text
        self.command = command
        self.disabled_command = disabled_command
        self.variant = variant
        self.enabled = True
        self.hovered = False
        self.pressed = False
        self.palette = PALETTE
        self.button_font = ui_font(11, "bold")
        self.configure(bg=PALETTE["panel"])
        self.bind("<Configure>", lambda _event: self._draw())
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<Return>", lambda _event: self.invoke())
        self.bind("<space>", lambda _event: self.invoke())
        self._draw()

    def apply_theme(self, palette: dict) -> None:
        self.palette = palette
        self.configure(bg=palette["panel"])
        self.button_font = ui_font(11, "bold")
        self._draw()

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = enabled
        self.configure(cursor="hand2")
        self._draw()

    def set_disabled_command(self, command) -> None:
        self.disabled_command = command

    def invoke(self) -> None:
        if self.enabled and self.command is not None:
            self.command()
        elif not self.enabled and self.disabled_command is not None:
            self.disabled_command()

    def _colours(self) -> tuple[str, str, str]:
        if not self.enabled:
            return self.palette["disabled"], self.palette["disabled_text"], self.palette["disabled"]
        if self.variant == "secondary":
            bg = self.palette["secondary_hover"] if self.hovered else self.palette["secondary"]
            return bg, self.palette["secondary_text"], self.palette["border_strong"]
        if self.variant == "success":
            bg = self.palette["success_hover"] if self.hovered else self.palette["success"]
            return bg, "#ffffff", bg
        bg = self.palette["accent_hover"] if self.hovered else self.palette["accent"]
        if self.pressed:
            bg = self.palette["accent_pressed"]
        return bg, "#ffffff", bg

    def _draw(self) -> None:
        self.delete("all")
        width = max(self.winfo_width(), 1)
        height = max(self.winfo_height(), 1)
        bg, fg, outline = self._colours()
        if self.enabled:
            self._rounded_rect(2, 4, width - 2, height - 1, 12, fill="#dfe6f1", outline="")
        self._rounded_rect(1, 1, width - 3, height - 4, 12, fill=bg, outline=outline)
        self.create_text((width - 2) / 2, (height - 3) / 2, text=self.text, fill=fg, font=self.button_font)

    def _rounded_rect(self, x1: int, y1: int, x2: int, y2: int, radius: int, **kwargs) -> None:
        points = [
            x1 + radius, y1, x2 - radius, y1, x2, y1, x2, y1 + radius,
            x2, y2 - radius, x2, y2, x2 - radius, y2, x1 + radius, y2,
            x1, y2, x1, y2 - radius, x1, y1 + radius, x1, y1,
        ]
        self.create_polygon(points, smooth=True, splinesteps=18, **kwargs)

    def _on_enter(self, _event) -> None:
        self.hovered = True
        self._draw()

    def _on_leave(self, _event) -> None:
        self.hovered = False
        self.pressed = False
        self._draw()

    def _on_press(self, _event) -> None:
        if self.enabled:
            self.pressed = True
            self._draw()

    def _on_release(self, _event) -> None:
        was_pressed = self.pressed
        self.pressed = False
        self._draw()
        if was_pressed or not self.enabled:
            self.invoke()


class BoxFrame(tk.Frame):
    def __init__(self, master, stretch_content: bool = False, **kwargs):
        super().__init__(master, bg=PALETTE["bg"], **kwargs)
        self.palette = PALETTE
        self.stretch_content = stretch_content
        self.canvas = tk.Canvas(self, highlightthickness=0, bd=0, bg=PALETTE["bg"])
        self.canvas.pack(fill="both", expand=True)
        self.content = tk.Frame(self.canvas, bg=PALETTE["panel"], padx=ui_size(14), pady=ui_size(10))
        self.window_id = self.canvas.create_window((0, 0), window=self.content, anchor="nw")
        self.content.bind("<Configure>", self._on_content_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)

    def grid_columnconfigure(self, index, cnf=None, **kw):
        return self.content.grid_columnconfigure(index, {} if cnf is None else cnf, **kw)

    def grid_rowconfigure(self, index, cnf=None, **kw):
        return self.content.grid_rowconfigure(index, {} if cnf is None else cnf, **kw)

    def _on_content_configure(self, event) -> None:
        height = event.height + CARD_SHADOW_OFFSET + 4
        if self.canvas.winfo_height() != height:
            self.canvas.configure(height=height)
        self._draw()

    def _on_canvas_configure(self, event) -> None:
        width = max(event.width - CARD_SHADOW_OFFSET - 2, 120)

        if self.stretch_content:
            height = max(event.height - CARD_SHADOW_OFFSET - 2, self.content.winfo_reqheight())
            self.canvas.itemconfigure(self.window_id, width=width, height=height)
        else:
            self.canvas.itemconfigure(self.window_id, width=width)

        self._draw()

    def _draw(self) -> None:
        self.canvas.delete("card")
        width = max(self.canvas.winfo_width(), 1)
        height = max(self.canvas.winfo_height(), self.content.winfo_reqheight() + CARD_SHADOW_OFFSET + 4)
        panel_width = max(width - CARD_SHADOW_OFFSET - 1, 1)
        panel_height = max(height - CARD_SHADOW_OFFSET - 1, 1)
        self._rounded_rect(3, 4, panel_width + 3, panel_height + 4, CARD_RADIUS, fill="#e8edf5", outline="", tags="card")
        self._rounded_rect(1, 2, panel_width + 1, panel_height + 2, CARD_RADIUS, fill="#f1f4f9", outline="", tags="card")
        self._rounded_rect(0, 0, panel_width, panel_height, CARD_RADIUS, fill=self.palette["panel"], outline=self.palette["border"], tags="card")
        self.canvas.tag_lower("card")

    def _rounded_rect(self, x1: int, y1: int, x2: int, y2: int, radius: int, **kwargs) -> None:
        points = [
            x1 + radius, y1, x2 - radius, y1, x2, y1, x2, y1 + radius,
            x2, y2 - radius, x2, y2, x2 - radius, y2, x1 + radius, y2,
            x1, y2, x1, y2 - radius, x1, y1 + radius, x1, y1,
        ]
        self.canvas.create_polygon(points, smooth=True, splinesteps=20, **kwargs)

    def apply_theme(self, palette: dict) -> None:
        self.palette = palette
        self.configure(bg=palette["bg"])
        self.canvas.configure(bg=palette["bg"])
        self.content.configure(bg=palette["panel"])
        self._draw()


class SectionHeader(ttk.Frame):
    def __init__(self, master, title: str, description: str):
        super().__init__(master, style="Root.TFrame")
        self.title = ttk.Label(self, text=title, style="SectionTitle.TLabel")
        self.description = ttk.Label(self, text=description, style="MutedRoot.TLabel", wraplength=330)
        self.title.grid(row=0, column=0, sticky="w")
        self.description.grid(row=1, column=0, sticky="ew", pady=(4, 10))
        self.grid_columnconfigure(0, weight=1)


class PathPicker:
    def __init__(self, master, label: str, helper: str, button_text: str, command):
        self.raw_path = ""
        self.box = BoxFrame(master)
        parent = self.box.content
        parent.grid_columnconfigure(1, weight=1)
        self.label = ttk.Label(parent, text=label, style="FieldTitle.TLabel")
        self.helper = ttk.Label(parent, text=helper, style="MutedCard.TLabel", wraplength=310)
        self.entry = tk.Entry(parent, relief="flat", font=ui_font(11), width=34)
        self.entry.configure(state="readonly")
        self.copy_menu = tk.Menu(parent, tearoff=0)
        self.entry.bind("<Control-c>", self.copy_display_path)
        self.entry.bind("<Command-c>", self.copy_display_path)
        self.entry.bind("<Control-Shift-C>", self.copy_full_path)
        self.entry.bind("<Command-Shift-C>", self.copy_full_path)
        self.entry.bind("<Button-3>", self.show_copy_menu)
        self.entry.bind("<Button-2>", self.show_copy_menu)
        self.button = RoundedButton(parent, button_text, command=command, variant="primary", width=124)
        self.error_label = ttk.Label(parent, text="", style="Error.TLabel")

        self.label.grid(row=0, column=0, sticky="w", columnspan=3)
        self.helper.grid(row=1, column=0, sticky="w", columnspan=3, pady=(ui_size(3), ui_size(10)))
        self.entry.grid(row=2, column=0, columnspan=2, sticky="ew", padx=(0, ui_size(12)), ipady=ui_size(8))
        self.button.grid(row=2, column=2, sticky="e")
        self.error_label.grid(row=3, column=0, columnspan=3, sticky="w", pady=(ui_size(8), 0))

    def grid(self, row: int, column: int = 0, columnspan: int = 1, sticky: str = "nsew", padx=None, pady=None) -> None:
        if padx is None:
            padx = (0, 0)
        if pady is None:
            pady = (0, 12)
        self.box.grid(row=row, column=column, columnspan=columnspan, sticky=sticky, padx=padx, pady=pady)

    def set_path(self, value: str) -> None:
        self.raw_path = str(value or "").strip()
        self.entry.configure(state="normal")
        self.entry.delete(0, tk.END)
        self.entry.insert(0, compact_path_display(self.raw_path))
        self.entry.configure(state="readonly")

    def get(self) -> str:
        return self.raw_path.strip() or self.entry.get().strip()

    def copy_display_path(self, _event=None):
        copy_text_to_clipboard(self.entry, self.entry.get())
        return "break"

    def copy_full_path(self, _event=None):
        copy_text_to_clipboard(self.entry, self.raw_path or self.entry.get())
        return "break"

    def show_copy_menu(self, event):
        self.copy_menu.delete(0, tk.END)
        self.copy_menu.add_command(label="Copy displayed path", command=self.copy_display_path)
        self.copy_menu.add_command(label="Copy full path", command=self.copy_full_path)
        self.copy_menu.tk_popup(event.x_root, event.y_root)
        return "break"

    def set_error(self, message: str) -> None:
        self.error_label.configure(text=message)
        self.entry.configure(readonlybackground=PALETTE["danger_soft"] if message else PALETTE["input"])

    def apply_theme(self, palette: dict) -> None:
        self.box.apply_theme(palette)
        self.entry.configure(
            bg=palette["input"],
            fg=palette["input_text"],
            readonlybackground=palette["input"],
            insertbackground=palette["input_text"],
            highlightthickness=1,
            highlightbackground=palette["border"],
            highlightcolor=palette["accent"],
        )
        self.button.apply_theme(palette)


class MultiPicker:
    def __init__(self, master, label: str, helper: str, add_text: str, add_command, delete_command, list_rows: int = LISTBOX_ROWS):
        self.box = BoxFrame(master, stretch_content=True)
        parent = self.box.content
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_columnconfigure(1, weight=0)
        parent.grid_columnconfigure(2, weight=0)
        parent.grid_rowconfigure(2, weight=1, minsize=ui_size(64))

        self.label = ttk.Label(parent, text=label, style="FieldTitle.TLabel")
        self.actions = tk.Frame(parent, bg=PALETTE["panel"])
        self.helper_label = ttk.Label(parent, text=helper, style="MutedCard.TLabel", wraplength=520)
        self.list_frame = tk.Frame(
            parent,
            bg=PALETTE["input"],
            highlightthickness=1,
            highlightbackground=PALETTE["border"],
            padx=ui_size(10),
            pady=ui_size(10),
        )
        self.listbox = tk.Listbox(
            self.list_frame,
            height=list_rows,
            activestyle="none",
            borderwidth=0,
            relief="flat",
            selectmode=tk.EXTENDED,
            font=ui_font(10),
            width=34,
            exportselection=False,
        )
        self.yscroll = ttk.Scrollbar(self.list_frame, orient="vertical", command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=self.yscroll.set)
        self.listbox.bind("<MouseWheel>", self._on_list_mousewheel)
        self.listbox.bind("<Button-4>", self._on_list_mousewheel)
        self.listbox.bind("<Button-5>", self._on_list_mousewheel)
        self.listbox.bind("<<ListboxSelect>>", self._remember_selection)
        self.listbox.bind("<Delete>", self._delete_from_keyboard)
        self.listbox.bind("<Control-c>", self.copy_selected_display_values)
        self.listbox.bind("<Command-c>", self.copy_selected_display_values)
        self.listbox.bind("<Control-Shift-C>", self.copy_selected_full_paths)
        self.listbox.bind("<Command-Shift-C>", self.copy_selected_full_paths)
        self.listbox.bind("<Button-3>", self.show_copy_menu)
        self.listbox.bind("<Button-2>", self.show_copy_menu)
        self.copy_menu = tk.Menu(self.listbox, tearoff=0)
        self._last_selection: tuple[int, ...] = ()
        self.item_values: dict[str, str] = {}
        self.add_button = RoundedButton(self.actions, add_text, command=add_command, variant="primary", width=112, disabled_command=notify_setup_required)
        self.delete_button = RoundedButton(self.actions, "Remove", command=delete_command, variant="secondary", width=104, disabled_command=notify_setup_required)
        self.error_label = ttk.Label(parent, text="", style="Error.TLabel")

        self.label.grid(row=0, column=0, sticky="w", padx=(0, ui_size(12)))
        self.actions.grid(row=0, column=1, sticky="e")
        self.add_button.pack(side="left", padx=(0, 8))
        self.delete_button.pack(side="left")
        self.helper_label.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(4, 10))
        self.list_frame.grid(row=2, column=0, columnspan=2, sticky="nsew")
        self.listbox.grid(row=0, column=0, sticky="nsew")
        self.yscroll.grid(row=0, column=1, sticky="ns", padx=(8, 0))
        self.list_frame.grid_rowconfigure(0, weight=1)
        self.list_frame.grid_columnconfigure(0, weight=1)
        self.error_label.grid(row=3, column=0, columnspan=2, sticky="w", pady=(ui_size(8), 0))

    def grid(self, row: int, column: int = 0, columnspan: int = 1, sticky: str = "nsew", padx=None, pady=None) -> None:
        if padx is None:
            padx = (0, 0)
        if pady is None:
            pady = (0, 12)
        self.box.grid(row=row, column=column, columnspan=columnspan, sticky=sticky, padx=padx, pady=pady)

    def _on_list_mousewheel(self, event):
        if getattr(event, "num", None) == 4:
            amount = -1
        elif getattr(event, "num", None) == 5:
            amount = 1
        else:
            delta = getattr(event, "delta", 0)
            if delta == 0:
                return "break"
            amount = -1 if delta > 0 else 1
        self.listbox.yview_scroll(amount, "units")
        return "break"

    def _remember_selection(self, _event=None) -> None:
        self._last_selection = tuple(int(index) for index in self.listbox.curselection())

    def _delete_from_keyboard(self, _event=None):
        self.remove_selected()
        return "break"

    def selected_display_values(self) -> list[str]:
        selected_indices = tuple(int(index) for index in self.listbox.curselection()) or self._last_selection
        selected_indices = tuple(index for index in selected_indices if 0 <= index < self.listbox.size())
        return [self.listbox.get(index) for index in selected_indices]

    def selected_full_paths(self) -> list[str]:
        return [
            self.item_values.get(display_value, strip_language_badge(display_value))
            for display_value in self.selected_display_values()
        ]

    def copy_selected_display_values(self, _event=None):
        copy_text_to_clipboard(self.listbox, "\n".join(self.selected_display_values()))
        return "break"

    def copy_selected_full_paths(self, _event=None):
        copy_text_to_clipboard(self.listbox, "\n".join(self.selected_full_paths()))
        return "break"

    def show_copy_menu(self, event):
        index = self.listbox.nearest(event.y)
        if 0 <= index < self.listbox.size() and index not in self.listbox.curselection():
            self.listbox.selection_clear(0, tk.END)
            self.listbox.selection_set(index)
            self._remember_selection()

        self.copy_menu.delete(0, tk.END)
        self.copy_menu.add_command(label="Copy displayed item", command=self.copy_selected_display_values)
        self.copy_menu.add_command(label="Copy full path", command=self.copy_selected_full_paths)
        self.copy_menu.tk_popup(event.x_root, event.y_root)
        return "break"

    def set_controls_enabled(self, enabled: bool) -> None:
        self.add_button.set_enabled(enabled)
        self.delete_button.set_enabled(enabled)

    def set_error(self, message: str) -> None:
        self.error_label.configure(text=message)
        self.listbox.configure(background=PALETTE["danger_soft"] if message else PALETTE["input"])

    def apply_theme(self, palette: dict) -> None:
        self.box.apply_theme(palette)
        self.actions.configure(bg=palette["panel"])
        self.list_frame.configure(bg=palette["input"], highlightbackground=palette["border"])
        self.listbox.configure(
            bg=palette["input"],
            fg=palette["input_text"],
            selectbackground=palette["accent"],
            selectforeground="#ffffff",
            highlightthickness=0,
        )
        self.add_button.apply_theme(palette)
        self.delete_button.apply_theme(palette)

    def display_name_for_path(self, value: str) -> str:
        """Show compact readable paths while preserving full paths internally."""
        return compact_path_display(value)

    def unique_display_value(self, display_value: str, raw_value: str, current: set[str]) -> str:
        if display_value not in current and display_value not in self.item_values:
            return display_value

        counter = 2
        candidate = f"{display_value} ({counter})"

        while candidate in current or candidate in self.item_values:
            counter += 1
            candidate = f"{display_value} ({counter})"

        return candidate

    def add_items(self, values: Iterable[str], formatter=None) -> int:
        added = 0
        current = set(self.listbox.get(0, tk.END))
        raw_current = {strip_language_badge(raw_value) for raw_value in self.item_values.values()}
        for value in values:
            text = str(value).strip()
            raw_text = strip_language_badge(text)
            if not raw_text or raw_text in raw_current:
                continue
            formatted_text = formatter(raw_text) if formatter else raw_text
            display_value = self.display_name_for_path(formatted_text)
            display_value = self.unique_display_value(display_value, raw_text, current)
            self.listbox.insert(tk.END, display_value)
            self.item_values[display_value] = raw_text
            current.add(display_value)
            raw_current.add(raw_text)
            added += 1
        return added

    def remove_selected(self) -> int:
        selected_indices = tuple(int(index) for index in self.listbox.curselection()) or self._last_selection
        selected_indices = tuple(index for index in selected_indices if 0 <= index < self.listbox.size())

        if not selected_indices:
            return 0

        for index in reversed(selected_indices):
            display_value = self.listbox.get(index)
            self.item_values.pop(display_value, None)
            self.listbox.delete(index)

        self._last_selection = ()
        return len(selected_indices)

    def size(self) -> int:
        return self.listbox.size()

    def values(self) -> List[str]:
        values = []
        for display_value in self.listbox.get(0, tk.END):
            values.append(self.item_values.get(display_value, strip_language_badge(display_value)))
        return values

class ProjectNameBox:
    def __init__(self, master, change_callback):
        self.box = BoxFrame(master)
        parent = self.box.content
        parent.grid_columnconfigure(0, weight=1)
        self.label = ttk.Label(parent, text="Project name", style="FieldTitle.TLabel")
        self.helper = ttk.Label(parent, text="Use the application or multi-module project name.", style="MutedCard.TLabel")
        self.entry = tk.Entry(parent, relief="flat", font=ui_font(11), width=34)
        self.error_label = ttk.Label(parent, text="", style="Error.TLabel")
        self.entry.bind("<KeyRelease>", lambda _event: change_callback())

        self.label.grid(row=0, column=0, sticky="w")
        self.helper.grid(row=1, column=0, sticky="w", pady=(ui_size(3), ui_size(10)))
        self.entry.grid(row=2, column=0, sticky="ew", ipady=ui_size(8))
        self.error_label.grid(row=3, column=0, sticky="w", pady=(ui_size(8), 0))

    def grid(self, row: int, column: int = 0, columnspan: int = 1, sticky: str = "nsew", padx=None, pady=None) -> None:
        if padx is None:
            padx = (0, 0)
        if pady is None:
            pady = (0, 12)
        self.box.grid(row=row, column=column, columnspan=columnspan, sticky=sticky, padx=padx, pady=pady)

    def set_error(self, message: str) -> None:
        self.error_label.configure(text=message)
        self.entry.configure(bg=PALETTE["danger_soft"] if message else PALETTE["input"])

    def apply_theme(self, palette: dict) -> None:
        self.box.apply_theme(palette)
        self.entry.configure(
            bg=palette["input"],
            fg=palette["input_text"],
            insertbackground=palette["input_text"],
            highlightthickness=1,
            highlightbackground=palette["border"],
            highlightcolor=palette["accent"],
        )


def active_monitor_bounds(root):
    pointer_x = root.winfo_pointerx()
    pointer_y = root.winfo_pointery()

    try:
        from screeninfo import get_monitors

        for monitor in get_monitors():
            if monitor.x <= pointer_x < monitor.x + monitor.width and monitor.y <= pointer_y < monitor.y + monitor.height:
                return monitor.x, monitor.y, monitor.width, monitor.height
    except Exception:
        pass

    return 0, 0, root.winfo_screenwidth(), root.winfo_screenheight()


def centre_and_focus_window(root, width: int = 1500, height: int = 920) -> None:
    root.update_idletasks()
    monitor_x, monitor_y, monitor_width, monitor_height = active_monitor_bounds(root)
    choice = getattr(root, "window_size_choice", configured_window_size_choice())
    scaling_info = read_tk_scaling_info(root, monitor_width, monitor_height)
    decision = build_parser_layout_decision(monitor_width, monitor_height, choice, scaling_info)
    emit_parser_layout_diagnostics(decision)

    x = monitor_x + decision["x"]
    y = monitor_y + decision["y"]
    root.geometry(f'{decision["target_width"]}x{decision["target_height"]}+{x}+{y}')
    root.deiconify()
    if decision["maximised"]:
        try:
            if sys.platform.startswith("win"):
                root.state("zoomed")
            else:
                root.attributes("-zoomed", True)
        except Exception:
            pass
    root.update_idletasks()

    root.lift()
    root.focus_force()

    try:
        root.attributes("-topmost", True)
        root.after(650, lambda: root.attributes("-topmost", False))
    except tk.TclError:
        pass


class MisarParserApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.automatic_importer_prompted_for: Optional[str] = None
        self.model_creation_running = False
        self.session_save_job = None
        self.restoring_session = False
        self.session_completed_successfully = False

        self.window_size_choice = configured_window_size_choice()
        self.screen_width = self.winfo_screenwidth()
        self.screen_height = self.winfo_screenheight()
        self.layout_decision = build_parser_layout_decision(
            self.screen_width,
            self.screen_height,
            self.window_size_choice,
            read_tk_scaling_info(self, self.screen_width, self.screen_height),
        )
        global UI_DENSITY
        UI_DENSITY = self.layout_decision["resolved_ui_density"]
        self.required_list_rows = self.layout_decision["required_list_rows"]
        self.optional_list_rows = self.layout_decision["optional_list_rows"]
        emit_parser_layout_diagnostics(self.layout_decision)

        self.title(title_with_version(APP_NAME, APP_VERSION))
        self.geometry("1500x920")
        self.minsize(980, 620)
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        self.style = ttk.Style(self)
        self._configure_base_style()
        self._build_layout()
        self.apply_theme()
        self.update_create_state()
        self.refresh_clear_session_button_visibility()
        self.after(80, lambda: centre_and_focus_window(self))
        self.after(900, self.ask_to_restore_previous_session)

        print("MiSAR parser startup PSM selection = {}".format(describe_psm_selection()))

    def _configure_base_style(self) -> None:
        try:
            self.style.theme_use("clam")
        except tk.TclError:
            pass
        for font_name in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont"):
            try:
                tkfont.nametofont(font_name).configure(size=ui_size(10, 8))
            except Exception:
                pass

    def _build_layout(self) -> None:
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self.sidebar = tk.Frame(self, width=ui_size(88), bg=PALETTE["sidebar"])
        self.sidebar.grid(row=0, column=0, sticky="ns")
        self.sidebar.grid_propagate(False)

        self.logo = tk.Label(self.sidebar, text="MiSAR", font=ui_font(14, "bold"), bg=PALETTE["sidebar"], fg=PALETTE["sidebar_title"])
        self.logo.pack(pady=(24, 4))
        self.logo_subtitle = tk.Label(self.sidebar, text="Parser", font=ui_font(11), bg=PALETTE["sidebar"], fg=PALETTE["sidebar_text"])
        self.logo_subtitle.pack()
        tk.Frame(self.sidebar, height=1, bg="#243454").pack(fill="x", padx=18, pady=20)

        if APP_VERSION:
            self.sidebar_version = tk.Label(self.sidebar, text=f"Parser\n{APP_VERSION}", font=ui_font(10, "bold"), justify="center", bg=PALETTE["sidebar"], fg=PALETTE["sidebar_text"])
            self.sidebar_version.pack(side="bottom", pady=18)
        else:
            self.sidebar_version = None

        self.main = ttk.Frame(self, style="Root.TFrame")
        self.main.grid(row=0, column=1, sticky="nsew")
        self.main.grid_rowconfigure(1, weight=1)
        self.main.grid_columnconfigure(0, weight=1)

        self.header = ttk.Frame(self.main, padding=(ui_size(24), ui_size(14), ui_size(24), ui_size(4)), style="Root.TFrame")
        self.header.grid(row=0, column=0, sticky="ew")
        self.header.grid_columnconfigure(0, weight=1)

        self.title_label = ttk.Label(self.header, text="Create a MiSAR PSM model", style="AppTitle.TLabel")
        self.title_label.grid(row=0, column=0, sticky="w")
        self.subtitle_label = ttk.Label(
            self.header,
            text="Parse YAML, XML, Java and Python artefacts into a MiSAR PSM model. Every input is visible on this screen.",
            style="MutedRoot.TLabel",
        )
        self.subtitle_label.grid(row=1, column=0, sticky="w", pady=(4, 0))

        self.content = ttk.Frame(self.main, padding=(ui_size(24), ui_size(6), ui_size(24), ui_size(10)), style="Root.TFrame")
        self.content.grid(row=1, column=0, sticky="nsew")
        for index in range(12):
            self.content.grid_columnconfigure(index, weight=1, uniform="parser_grid")
        for index in range(4):
            self.content.grid_rowconfigure(index, weight=1 if index in {1, 2} else 0)

        self._build_setup_section()
        self._build_required_section()
        self._build_optional_section()
        self._build_create_section()

        self.status_bar = tk.Frame(self, height=42, bg=PALETTE["status_bg"])
        self.status_bar.grid(row=1, column=0, columnspan=2, sticky="ew")
        self.status_label = tk.Label(self.status_bar, text="Ready", anchor="w", font=ui_font(11), bg=PALETTE["status_bg"], fg=PALETTE["text"])
        self.status_label.pack(side="left", padx=20)
        self.footer_label = tk.Label(self.status_bar, text="Brunel University London", anchor="e", font=ui_font(11), bg=PALETTE["status_bg"], fg=PALETTE["muted"])
        self.footer_label.pack(side="right", padx=20)

    def _build_setup_section(self) -> None:
        self.project_name = ProjectNameBox(self.content, self.handle_project_name_changed)
        self.project_name.grid(0, 0, 4, padx=(0, 10), pady=(0, 12))

        self.project_dir = PathPicker(
            self.content,
            "Project build directory",
            "Select the root build directory for the application.",
            "Browse",
            self.select_project_directory,
        )
        self.project_dir.grid(0, 4, 4, padx=(6, 6), pady=(0, 12))

        self.output_dir = PathPicker(
            self.content,
            "Output directory",
            "Choose where the generated PSM model should be saved.",
            "Browse",
            self.select_output_directory,
        )
        self.output_dir.grid(0, 8, 4, padx=(10, 0), pady=(0, 12))

    def _build_required_section(self) -> None:
        self.docker_compose = MultiPicker(
            self.content,
            "Docker Compose files",
            "Required. YAML and YML files discover services and build contexts.",
            "Add files",
            self.add_docker_compose_files,
            lambda: self.delete_items(self.docker_compose),
            list_rows=self.required_list_rows,
        )
        self.docker_compose.grid(1, 0, 6, padx=(0, 10), pady=(0, 12))

        self.module_build_dir = MultiPicker(
            self.content,
            "Microservice project folders",
            "Required. Select each microservice's source/build folder. MiSAR scans these folders for dependencies and language/framework details.",
            "Add folder",
            self.add_module_directory,
            lambda: self.delete_items(self.module_build_dir),
            list_rows=self.required_list_rows,
        )
        self.module_build_dir.grid(1, 6, 6, padx=(10, 0), pady=(0, 12))

    def _build_optional_section(self) -> None:
        self.app_build = MultiPicker(
            self.content,
            "Application dependency files",
            "Optional. Supports pom.xml, requirements.txt, pyproject.toml, Pipfile, setup files and poetry.lock.",
            "Add files",
            self.add_app_build_files,
            lambda: self.delete_items(self.app_build),
            list_rows=self.optional_list_rows,
        )
        self.app_build.grid(2, 0, 4, padx=(0, 10), pady=(0, 12))

        self.module_build = MultiPicker(
            self.content,
            "Module dependency files",
            "Optional. These can be auto-filled from selected module folders.",
            "Add files",
            self.add_module_build_files,
            lambda: self.delete_items(self.module_build),
            list_rows=self.optional_list_rows,
        )
        self.module_build.grid(2, 4, 4, padx=(6, 6), pady=(0, 12))

        self.app_config_dir = MultiPicker(
            self.content,
            "Centralised configuration directories",
            "Optional. Add folders used by shared configuration services.",
            "Add folder",
            self.add_config_directory,
            lambda: self.delete_items(self.app_config_dir),
            list_rows=self.optional_list_rows,
        )
        self.app_config_dir.grid(2, 8, 4, padx=(10, 0), pady=(0, 12))

    def _build_create_section(self) -> None:
        self.create_box = BoxFrame(self.content)
        self.create_box.grid(row=3, column=0, columnspan=12, sticky="ew", pady=(0, 4))
        parent = self.create_box.content
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_columnconfigure(1, weight=0)
        parent.grid_columnconfigure(2, weight=0)
        self.create_title = ttk.Label(parent, text="Create PSM", style="FieldTitle.TLabel")
        self.create_title.grid(row=0, column=0, sticky="w")
        self.readiness_label = ttk.Label(parent, text="Complete the required fields to continue.", style="MutedCard.TLabel")
        self.readiness_label.grid(row=1, column=0, sticky="w", pady=(4, 0))
        self.clear_session_button = RoundedButton(parent, "Clear saved session", command=self.clear_saved_session, variant="secondary", width=168)
        self.clear_session_button.grid(row=0, column=1, rowspan=2, sticky="e", padx=(18, 0))
        self.create_button = RoundedButton(parent, "Create PSM Model", command=self.create_model, variant="success", width=180)
        self.create_button.grid(row=0, column=2, rowspan=2, sticky="e", padx=(12, 0))

        self.progress_frame = tk.Frame(parent, bg=PALETTE["panel"])
        self.progress_frame.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(12, 0))
        self.progress_frame.grid_columnconfigure(1, weight=1)
        self.progress_title_label = ttk.Label(self.progress_frame, text="Progress", style="MutedCard.TLabel")
        self.progress_title_label.grid(row=0, column=0, sticky="w")
        self.progress_message_label = ttk.Label(self.progress_frame, text="Waiting to start.", style="MutedCard.TLabel")
        self.progress_message_label.grid(row=0, column=1, sticky="w", padx=(12, 0))
        self.progress_percent_label = ttk.Label(self.progress_frame, text="0%", style="MutedCard.TLabel")
        self.progress_percent_label.grid(row=0, column=2, sticky="e", padx=(12, 0))
        self.progress_bar = ttk.Progressbar(
            self.progress_frame,
            mode="determinate",
            maximum=100,
            value=0,
            style="Green.Horizontal.TProgressbar",
        )
        self.progress_bar.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(6, 0))

    def handle_project_name_changed(self) -> None:
        self.update_create_state()
        self.schedule_session_save()

    def refresh_clear_session_button_visibility(self) -> None:
        if not hasattr(self, "clear_session_button"):
            return

        saved_session = self.read_saved_session()
        if self.session_state_has_values(saved_session):
            self.clear_session_button.grid()
        else:
            self.clear_session_button.grid_remove()

    def session_values_from_picker(self, picker: MultiPicker) -> List[str]:
        return [strip_language_badge(value) for value in picker.values() if strip_language_badge(value)]

    def collect_session_state(self) -> dict:
        return {
            "project_name": self.project_name.entry.get().strip(),
            "project_dir": self.project_dir.get(),
            "output_dir": self.output_dir.get(),
            "docker_compose_files": self.session_values_from_picker(self.docker_compose),
            "app_build_files": self.session_values_from_picker(self.app_build),
            "module_build_dirs": self.session_values_from_picker(self.module_build_dir),
            "module_build_files": self.session_values_from_picker(self.module_build),
            "app_config_dirs": self.session_values_from_picker(self.app_config_dir),
        }

    def session_state_has_values(self, state: dict) -> bool:
        if not isinstance(state, dict):
            return False

        for value in state.values():
            if isinstance(value, list):
                if any(strip_language_badge(item) for item in value):
                    return True
            elif isinstance(value, str) and value.strip():
                return True

        return False

    def schedule_session_save(self) -> None:
        if self.restoring_session or self.model_creation_running:
            return
        if self.session_save_job is not None:
            self.after_cancel(self.session_save_job)
        self.session_save_job = self.after(350, self.save_session)

    def save_session(self) -> None:
        if self.restoring_session or self.model_creation_running:
            return
        self.session_save_job = None
        try:
            state = self.collect_session_state()
            if not self.session_state_has_values(state):
                SESSION_FILE_PATH.unlink(missing_ok=True)
                self.refresh_clear_session_button_visibility()
                return
            SESSION_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
            SESSION_FILE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")
            self.session_completed_successfully = False
            self.refresh_clear_session_button_visibility()
        except Exception:
            pass

    def read_saved_session(self) -> dict:
        try:
            if not SESSION_FILE_PATH.is_file():
                return {}
            data = json.loads(SESSION_FILE_PATH.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def ask_modal_yes_no(self, title: str, message: str) -> bool:
        try:
            self.deiconify()
            self.lift()
            self.focus_force()
            self.attributes("-topmost", True)
            self.update_idletasks()
            return messagebox.askyesno(title, message, parent=self)
        finally:
            try:
                self.after(250, lambda: self.attributes("-topmost", False))
            except tk.TclError:
                pass

    def ask_to_restore_previous_session(self) -> None:
        data = self.read_saved_session()
        if not self.session_state_has_values(data):
            self.refresh_clear_session_button_visibility()
            return

        restore_session = self.ask_modal_yes_no(
            "Restore previous session",
            "A saved parser session was found. Would you like to restore the previous paths and inputs?",
        )
        if restore_session:
            self.restore_session(data)
        else:
            self.set_status("Previous saved session was not restored.")
        self.refresh_clear_session_button_visibility()

    def restore_session_list(self, picker: MultiPicker, values, path_kind: str, formatter=None) -> tuple[int, int]:
        restored = 0
        skipped = 0
        if not isinstance(values, list):
            return restored, skipped

        valid_values = []
        for value in values:
            text = strip_language_badge(value)
            if not text:
                continue
            path = Path(text).expanduser()
            exists = path.is_file() if path_kind == "file" else path.is_dir()
            if exists:
                valid_values.append(str(path))
            else:
                skipped += 1

        picker.listbox.delete(0, tk.END)
        picker.item_values.clear()
        restored += picker.add_items(valid_values, formatter=formatter)
        return restored, skipped

    def restore_session(self, data: dict) -> None:
        if not data:
            return

        restored = 0
        skipped = 0
        self.restoring_session = True

        try:
            project_name = str(data.get("project_name", "")).strip()
            if project_name:
                self.project_name.entry.delete(0, tk.END)
                self.project_name.entry.insert(0, project_name)
                restored += 1

            project_dir = str(data.get("project_dir", "")).strip()
            if project_dir:
                path = Path(project_dir).expanduser()
                if path.is_dir():
                    self.project_dir.set_path(str(path))
                    restored += 1
                else:
                    skipped += 1

            output_dir = str(data.get("output_dir", "")).strip()
            if output_dir:
                path = Path(output_dir).expanduser()
                if path.is_dir():
                    self.output_dir.set_path(str(path))
                    restored += 1
                else:
                    skipped += 1

            for picker, key, path_kind, formatter in [
                (self.docker_compose, "docker_compose_files", "file", None),
                (self.app_build, "app_build_files", "file", None),
                (self.module_build_dir, "module_build_dirs", "directory", format_module_display_path),
                (self.module_build, "module_build_files", "file", None),
                (self.app_config_dir, "app_config_dirs", "directory", None),
            ]:
                restored_count, skipped_count = self.restore_session_list(picker, data.get(key, []), path_kind, formatter)
                restored += restored_count
                skipped += skipped_count
        finally:
            self.restoring_session = False

        self.update_create_state()
        if restored and skipped:
            self.set_status("Previous session restored. Some saved paths were skipped because they no longer exist.")
        elif restored:
            self.set_status("Previous session restored.")
        else:
            self.set_status("Saved session found, but no valid paths could be restored.")

    def clear_saved_session(self) -> None:
        if self.session_save_job is not None:
            self.after_cancel(self.session_save_job)
            self.session_save_job = None

        self.restoring_session = True
        try:
            SESSION_FILE_PATH.unlink(missing_ok=True)
        finally:
            self.restoring_session = False

        self.refresh_clear_session_button_visibility()
        self.set_status("Saved session cleared.")

    def delete_saved_session_after_success(self) -> None:
        if self.session_save_job is not None:
            self.after_cancel(self.session_save_job)
            self.session_save_job = None
        try:
            SESSION_FILE_PATH.unlink(missing_ok=True)
        except Exception:
            pass
        self.session_completed_successfully = True
        self.refresh_clear_session_button_visibility()

    def project_dialog_initial_dir(self) -> str:
        selected_project_dir = self.project_dir.get() if hasattr(self, "project_dir") else ""

        if selected_project_dir and Path(selected_project_dir).is_dir():
            return selected_project_dir

        return str(USER_HOME_DIR)

    def setup_fields_completed(self) -> bool:
        return bool(
            self.project_name.entry.get().strip()
            and self.project_dir.get().strip()
            and self.output_dir.get().strip()
        )

    def update_file_controls_state(self) -> None:
        if not all(hasattr(self, attr) for attr in ("docker_compose", "module_build_dir", "app_build", "module_build", "app_config_dir")):
            return

        enabled = self.setup_fields_completed()
        for picker in [self.docker_compose, self.module_build_dir, self.app_build, self.module_build, self.app_config_dir]:
            picker.set_controls_enabled(enabled)

    def select_project_directory(self) -> None:
        directory = filedialog.askdirectory(title="Select project build directory", initialdir=str(USER_HOME_DIR))
        if not directory:
            return
        self.project_dir.set_path(directory)
        self.project_dir.set_error("")
        self.set_status("Project build directory selected.")
        if self.docker_compose.size() > 0:
            self.offer_auto_importer(directory)
        self.update_create_state()
        self.save_session()

    def select_output_directory(self) -> None:
        directory = filedialog.askdirectory(title="Select output directory", initialdir=self.project_dialog_initial_dir())
        if not directory:
            return
        self.output_dir.set_path(directory)
        self.output_dir.set_error("")
        self.set_status("Output directory selected.")
        self.update_create_state()
        self.save_session()

    def add_docker_compose_files(self) -> None:
        files = filedialog.askopenfilenames(
            title="Select Docker Compose files",
            initialdir=self.project_dialog_initial_dir(),
            filetypes=(
                ("Docker Compose / YAML files", "*.yml *.yaml"),
                ("All files", "*.*"),
            ),
        )
        if not files:
            return

        validation_results = validate_docker_compose_files(tuple(files), log=True)
        docker_errors, docker_warnings = format_docker_compose_user_messages(validation_results)
        valid_files = [result.file_path for result in validation_results if result.is_valid]

        if docker_errors:
            self.docker_compose.set_error("One or more selected Docker Compose files are invalid.")
            messagebox.showerror(
                "Invalid Docker Compose file",
                "The following Docker Compose file(s) could not be added:\n\n"
                + "\n".join(f"- {error}" for error in docker_errors),
            )

        if docker_warnings:
            messagebox.showwarning(
                "Docker Compose warnings",
                "The selected Docker Compose file(s) can still be used, but MiSAR found warning(s):\n\n"
                + "\n".join(f"- {warning}" for warning in docker_warnings[:12])
                + ("\n..." if len(docker_warnings) > 12 else ""),
            )

        added = self.docker_compose.add_items(valid_files)
        if added:
            self.docker_compose.set_error("")
            self.set_status(f"Added {added} Docker Compose file{'s' if added != 1 else ''}.")
            if self.project_dir.get():
                self.offer_auto_importer(self.project_dir.get())
            self.save_session()
        elif not docker_errors:
            self.set_status("No new Docker Compose files were added.")

        self.update_create_state()

    def add_app_build_files(self) -> None:
        files = filedialog.askopenfilenames(title="Select application dependency files", initialdir=self.project_dialog_initial_dir())
        added = self.app_build.add_items(files)
        if added:
            self.set_status(f"Added {added} application dependency file{'s' if added != 1 else ''}.")
            self.save_session()
        self.update_create_state()

    def add_module_build_files(self) -> None:
        files = filedialog.askopenfilenames(title="Select module dependency files", initialdir=self.project_dialog_initial_dir())
        added = self.module_build.add_items(files)
        if added:
            self.set_status(f"Added {added} module dependency file{'s' if added != 1 else ''}.")
            self.save_session()
        self.update_create_state()

    def add_module_directory(self) -> None:
        directory = filedialog.askdirectory(title="Select microservice build directory", initialdir=self.project_dialog_initial_dir())
        if not directory:
            return
        added = self.module_build_dir.add_items([directory], formatter=format_module_display_path)
        if added:
            self.module_build_dir.set_error("")
            self.set_status("Microservice project folder added.")
            self.offer_dependency_scan(directory, self.module_build)
            self.save_session()
        self.update_create_state()

    def add_config_directory(self) -> None:
        directory = filedialog.askdirectory(title="Select centralised configuration directory", initialdir=self.project_dialog_initial_dir())
        if not directory:
            return
        added = self.app_config_dir.add_items([directory])
        if added:
            self.set_status("Configuration directory added.")
            self.save_session()
        self.update_create_state()

    def delete_items(self, picker: MultiPicker) -> None:
        removed_count = picker.remove_selected()

        if removed_count:
            self.set_status(f"Removed {removed_count} selected item{'s' if removed_count != 1 else ''}.")
        else:
            self.set_status("Select an item before removing it.")

        if removed_count:
            self.save_session()
        self.update_create_state()

    def offer_auto_importer(self, input_directory: str) -> None:
        if self.automatic_importer_prompted_for == input_directory:
            return
        self.automatic_importer_prompted_for = input_directory
        folder_name = Path(input_directory).name
        answer = messagebox.askquestion(
            "Automatic Importer",
            "Would you like MiSAR to try and automatically import required files from "
            f"{folder_name}? This can save time when the Docker Compose file contains build contexts.",
            icon="info",
        )
        if answer == "yes":
            added_dirs, added_app_files, added_module_files = self.auto_import(input_directory)
            self.set_status(
                f"Automatic import added {added_dirs} module folder(s), "
                f"{added_app_files} app dependency file(s) and {added_module_files} module dependency file(s)."
            )
            self.update_create_state()
            self.save_session()

    def auto_import(self, input_directory: str) -> tuple[int, int, int]:
        if yaml is None:
            messagebox.showerror("YAML unavailable", "The PyYAML package is required for automatic import.")
            return 0, 0, 0

        input_dir_path = Path(input_directory)
        candidate_directories: List[Path] = []
        for docker_compose_file in self.docker_compose.values():
            if not docker_compose_file.strip() or not docker_compose_file.endswith((".yml", ".yaml")):
                continue
            try:
                docker_compose_dict = self.yaml_to_dict(docker_compose_file)
            except Exception as exc:
                messagebox.showwarning("Docker Compose skipped", f"Could not read {docker_compose_file}:\n{exc}")
                continue
            services = docker_compose_dict.get("services", docker_compose_dict) if isinstance(docker_compose_dict, dict) else {}
            for container_name, service_definition in services.items():
                service_name_dir = input_dir_path / str(container_name)
                if service_name_dir.is_dir():
                    candidate_directories.append(service_name_dir)
                build_definition = service_definition.get("build", "") if isinstance(service_definition, dict) else ""
                build_context = ""
                if isinstance(build_definition, str):
                    build_context = build_definition
                elif isinstance(build_definition, dict):
                    build_context = build_definition.get("context", "")
                if build_context:
                    build_path = (input_dir_path / build_context).resolve()
                    if build_path.is_dir():
                        candidate_directories.append(build_path)

        added_dirs = 0
        added_module_files = 0
        for target_directory in candidate_directories:
            added_dirs += self.module_build_dir.add_items([str(target_directory)], formatter=format_module_display_path)
            added_module_files += self.add_dependency_files_for_directory(target_directory, self.module_build)
        added_app_files = self.add_dependency_files_for_directory(input_dir_path, self.app_build)
        return added_dirs, added_app_files, added_module_files

    def offer_dependency_scan(self, directory: str, target_picker: MultiPicker) -> None:
        folder_name = Path(directory).name
        answer = messagebox.askquestion(
            "Build / Dependency Scanner",
            f"Would you like to add dependency files that exist within {folder_name}?",
            icon="info",
        )
        if answer == "yes":
            added = self.add_dependency_files_for_directory(Path(directory), target_picker)
            if added:
                self.set_status(f"Added {added} dependency file{'s' if added != 1 else ''}.")
                self.save_session()

    def add_dependency_files_for_directory(self, input_directory: Path, target_picker: MultiPicker) -> int:
        input_path = Path(input_directory)
        dependency_files = []
        for dependency_file in DEPENDENCY_BUILD_FILES:
            candidate = input_path / dependency_file
            if candidate.is_file():
                dependency_files.append(str(candidate))
        return target_picker.add_items(dependency_files)

    def yaml_to_dict(self, filename: str) -> dict:
        with open(filename, encoding="utf-8") as file:
            return yaml.load(file, Loader=yaml.FullLoader) or {}

    def validate_selected_docker_compose_files(self, show_errors: bool = False) -> tuple[list[str], list[str]]:
        docker_compose_files = [
            strip_language_badge(file_path)
            for file_path in self.docker_compose.values()
            if strip_language_badge(file_path)
        ]
        validation_results = validate_docker_compose_files(docker_compose_files, log=show_errors)
        return format_docker_compose_user_messages(validation_results)

    def validate(self, show_errors: bool = False) -> List[str]:
        errors = []
        project_name = self.project_name.entry.get().strip()

        self.project_name.set_error("")
        self.project_dir.set_error("")
        self.output_dir.set_error("")
        self.docker_compose.set_error("")
        self.module_build_dir.set_error("")

        if not project_name:
            errors.append("Application project name is missing.")
            if show_errors:
                self.project_name.set_error("Enter a project name.")
        elif any(char in FORBIDDEN_PROJECT_CHARS for char in project_name):
            errors.append('Application project name has forbidden characters: < > : " / \\ | ? *')
            if show_errors:
                self.project_name.set_error('Remove forbidden characters: < > : " / \\ | ? *')

        if not self.project_dir.get():
            errors.append("Application project build directory is missing.")
            if show_errors:
                self.project_dir.set_error("Choose the project build directory.")
        if self.docker_compose.size() == 0:
            errors.append("Docker Compose files are missing.")
            if show_errors:
                self.docker_compose.set_error("Add at least one Docker Compose file.")
        else:
            docker_errors, docker_warnings = self.validate_selected_docker_compose_files(show_errors=show_errors)
            errors.extend(docker_errors)
            if show_errors and docker_errors:
                self.docker_compose.set_error("Fix or remove invalid Docker Compose file(s).")
            elif show_errors and docker_warnings:
                print("misar_validation_warning = Docker Compose warnings found; continuing with supported fields.")
                self.set_status("Docker Compose warnings found; continuing with supported fields.")
        if self.module_build_dir.size() == 0:
            errors.append("Microservice project folders are missing.")
            if show_errors:
                self.module_build_dir.set_error("Add at least one microservice project folder.")
        if not self.output_dir.get():
            errors.append("Output directory is missing.")
            if show_errors:
                self.output_dir.set_error("Choose the output directory.")

        return errors

    def update_create_state(self) -> None:
        if not hasattr(self, "create_button"):
            return

        self.update_file_controls_state()
        if self.model_creation_running:
            self.create_button.set_enabled(False)
            self.readiness_label.configure(text="Creating the PSM model. Please wait.")
            return

        errors = self.validate(show_errors=False)
        ready = not errors and create_psm_instance is not None
        self.create_button.set_enabled(ready)
        if create_psm_instance is None:
            self.readiness_label.configure(text="Parser backend could not be imported. Check the project environment.")
        elif ready:
            self.readiness_label.configure(text="Ready to create the PSM model.")
        else:
            self.readiness_label.configure(text=f"{len(errors)} required item{'s' if len(errors) != 1 else ''} remaining.")

    def create_model(self) -> None:
        errors = self.validate(show_errors=True)
        if errors:
            messagebox.showerror(
                "Missing required information",
                "Please fix the following before creating the PSM model:\n\n" + "\n".join(f"- {error}" for error in errors),
            )
            self.set_status("Required fields need attention.")
            self.update_create_state()
            return
        if create_psm_instance is None:
            messagebox.showerror("Parser backend unavailable", str(BACKEND_IMPORT_ERROR))
            self.set_status("Parser backend unavailable.")
            return

        self.model_creation_running = True
        self.create_button.set_enabled(False)
        self.update_file_controls_state()
        self.set_status("Creating PSM model...")
        self.set_progress(0, "Starting model generation...")
        parser_inputs = self.snapshot_parser_inputs()

        worker = threading.Thread(target=self._run_create_model_worker, args=(parser_inputs,), daemon=True)
        worker.start()

    def snapshot_parser_inputs(self):
        return (
            EntrySnapshot(self.project_name.entry.get().strip()),
            EntrySnapshot(self.project_dir.get()),
            None,
            ListboxSnapshot(self.docker_compose.values()),
            ListboxSnapshot(self.app_build.values()),
            ListboxSnapshot(self.module_build_dir.values()),
            ListboxSnapshot(self.module_build.values()),
            ListboxSnapshot(self.app_config_dir.values()),
            EntrySnapshot(self.output_dir.get()),
        )

    def set_progress(self, value: int, message: str) -> None:
        value = max(0, min(int(value), 100))
        self.progress_bar.configure(value=value)
        self.progress_percent_label.configure(text=f"{value}%")
        self.progress_message_label.configure(text=message)

    def _progress_callback(self, value: int, message: str) -> None:
        self.after(0, lambda value=value, message=message: self.set_progress(value, message))

    def _run_create_model_worker(self, parser_inputs) -> None:
        try:
            output_path = create_psm_instance(*parser_inputs, progress_callback=self._progress_callback)
            self.after(0, lambda: self.finish_create_model(None, output_path))
        except Exception as exc:
            self.after(0, lambda error=exc: self.finish_create_model(error, None))

    def finish_create_model(self, error, output_path) -> None:
        self.model_creation_running = False

        if error is not None:
            self.set_progress(0, "Model generation failed.")
            messagebox.showerror("Operation failed", str(error) or "An unexpected error occurred.")
            self.set_status("Operation failed.")
        else:
            self.set_progress(100, "Model generation complete.")
            self.delete_saved_session_after_success()
            success_message = "The MiSAR PSM model was created successfully."
            if output_path:
                output_path = Path(output_path)
                success_message += "\n\nCreated in folder:\n" + str(output_path.parent)
                success_message += "\n\nFile:\n" + str(output_path)
            messagebox.showinfo("PSM model created", success_message)
            self.set_status("PSM model created successfully. Saved session deleted.")

        self.update_create_state()

    def set_status(self, message: str) -> None:
        self.status_label.configure(text=message)

    def apply_theme(self) -> None:
        palette = PALETTE
        self.configure(bg=palette["bg"])

        self.style.configure("Root.TFrame", background=palette["bg"])
        self.style.configure("AppTitle.TLabel", background=palette["bg"], foreground=palette["title"], font=ui_font(22, "bold"))
        self.style.configure("SectionTitle.TLabel", background=palette["bg"], foreground=palette["title"], font=ui_font(15, "bold"))
        self.style.configure("MutedRoot.TLabel", background=palette["bg"], foreground=palette["muted"], font=ui_font(11))
        self.style.configure("FieldTitle.TLabel", background=palette["panel"], foreground=palette["title"], font=ui_font(12, "bold"))
        self.style.configure("MutedCard.TLabel", background=palette["panel"], foreground=palette["muted"], font=ui_font(11))
        self.style.configure("Error.TLabel", background=palette["panel"], foreground=palette["danger"], font=ui_font(10))
        self.style.configure("Vertical.TScrollbar", background=palette["secondary"], troughcolor=palette["bg"], bordercolor=palette["bg"], arrowcolor=palette["muted"])
        self.style.configure("Horizontal.TScrollbar", background=palette["secondary"], troughcolor=palette["bg"], bordercolor=palette["bg"], arrowcolor=palette["muted"])
        self.style.configure(
            "Green.Horizontal.TProgressbar",
            background=palette["success"],
            troughcolor=palette["secondary"],
            bordercolor=palette["border"],
            lightcolor=palette["success"],
            darkcolor=palette["success"],
        )

        self.project_name.apply_theme(palette)
        for picker in [self.project_dir, self.output_dir]:
            picker.apply_theme(palette)
        for picker in [self.docker_compose, self.module_build_dir, self.app_build, self.module_build, self.app_config_dir]:
            picker.apply_theme(palette)
        self.create_box.apply_theme(palette)
        self.clear_session_button.apply_theme(palette)
        self.create_button.apply_theme(palette)
        if hasattr(self, "progress_frame"):
            self.progress_frame.configure(bg=palette["panel"])

    def on_close(self) -> None:
        if not self.session_completed_successfully:
            self.save_session()
        self.quit()
        self.destroy()


def installer(location, _target_link="") -> bool:
    if Repo is None:
        return False
    install_path = USER_HOME_DIR / Path(location)
    try:
        Repo.clone_from("https://github.com/MicroServiceArchitectureRecovery/misar-plantUML.git", install_path, branch="main")
        return os.path.isfile(install_path / "Runnable Jar File" / "MiSAR.jar")
    except Exception:
        return False


def uninstaller(location) -> None:
    target_link = ""
    read_only = True
    location_path = USER_HOME_DIR / Path(location)
    while read_only:
        read_only = False
        try:
            os.rmdir(location_path)
        except OSError:
            try:
                shutil.rmtree(location_path)
            except PermissionError as fail:
                fail_text = str(fail)
                comma_active = False
                for char in fail_text:
                    if char == "'" and comma_active:
                        comma_active = False
                    elif comma_active:
                        target_link += char
                    elif char == "'" and not comma_active:
                        comma_active = True
                target_path = Path(target_link)
                os.chmod(target_path, stat.S_IWRITE)
                os.unlink(target_path)
                try:
                    shutil.rmtree(target_path)
                except FileNotFoundError:
                    pass
                target_link = ""
                read_only = True


if __name__ == "__main__":
    app = MisarParserApp()
    app.mainloop()