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


APP_NAME = "MiSAR Parser"
USER_HOME_DIR = Path.home()
PARSER_UI_DIR = Path(__file__).resolve().parent
PROJECT_ROOT_DIR = PARSER_UI_DIR.parent
MISAR_DIR = USER_HOME_DIR / "MiSAR"
PARSER_DIR = MISAR_DIR / "Parser"
VERSION_FILE_PATH = PROJECT_ROOT_DIR / "MISAR.versions.json"
VERSION_KEYS = {"parser": ("misar.parser",)}


def _read_version_json(file_path: Path) -> dict:
    try:
        if not file_path.is_file():
            return {}
        data = json.loads(file_path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


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
    "bg": "#f5f7fb",
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


def ui_font(size: int = 11, weight: str = "normal"):
    try:
        family = tkfont.nametofont("TkDefaultFont").cget("family")
    except Exception:
        family = "Helvetica"
    return (family, size, weight) if weight != "normal" else (family, size)


def notify_setup_required() -> None:
    messagebox.showinfo(
        "Complete setup first",
        "Please first add the project name, project build directory, and output directory.",
    )

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
        super().__init__(master, width=width, height=38, highlightthickness=0, bd=0, cursor="hand2")
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
    def __init__(self, master, **kwargs):
        super().__init__(master, bg=PALETTE["bg"], **kwargs)
        self.palette = PALETTE
        self.canvas = tk.Canvas(self, highlightthickness=0, bd=0, bg=PALETTE["bg"])
        self.canvas.pack(fill="both", expand=True)
        self.content = tk.Frame(self.canvas, bg=PALETTE["panel"], padx=14, pady=10)
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
        self.box = BoxFrame(master)
        parent = self.box.content
        parent.grid_columnconfigure(1, weight=1)
        self.label = ttk.Label(parent, text=label, style="FieldTitle.TLabel")
        self.helper = ttk.Label(parent, text=helper, style="MutedCard.TLabel", wraplength=310)
        self.entry = tk.Entry(parent, relief="flat", font=ui_font(11), width=34)
        self.entry.configure(state="readonly")
        self.button = RoundedButton(parent, button_text, command=command, variant="primary", width=124)
        self.error_label = ttk.Label(parent, text="", style="Error.TLabel")

        self.label.grid(row=0, column=0, sticky="w", columnspan=3)
        self.helper.grid(row=1, column=0, sticky="w", columnspan=3, pady=(3, 10))
        self.entry.grid(row=2, column=0, columnspan=2, sticky="ew", padx=(0, 12), ipady=8)
        self.button.grid(row=2, column=2, sticky="e")
        self.error_label.grid(row=3, column=0, columnspan=3, sticky="w", pady=(8, 0))

    def grid(self, row: int, column: int = 0, columnspan: int = 1, sticky: str = "nsew", padx=None, pady=None) -> None:
        if padx is None:
            padx = (0, 0)
        if pady is None:
            pady = (0, 12)
        self.box.grid(row=row, column=column, columnspan=columnspan, sticky=sticky, padx=padx, pady=pady)

    def set_path(self, value: str) -> None:
        self.entry.configure(state="normal")
        self.entry.delete(0, tk.END)
        self.entry.insert(0, value)
        self.entry.configure(state="readonly")

    def get(self) -> str:
        return self.entry.get().strip()

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
        self.box = BoxFrame(master)
        parent = self.box.content
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_columnconfigure(1, weight=0)
        parent.grid_rowconfigure(2, weight=1)

        self.label = ttk.Label(parent, text=label, style="FieldTitle.TLabel")
        self.actions = tk.Frame(parent, bg=PALETTE["panel"])
        self.helper_label = ttk.Label(parent, text=helper, style="MutedCard.TLabel", wraplength=520)
        self.list_frame = tk.Frame(
            parent,
            bg=PALETTE["input"],
            highlightthickness=1,
            highlightbackground=PALETTE["border"],
            padx=10,
            pady=10,
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
        self._last_selection: tuple[int, ...] = ()
        self.add_button = RoundedButton(self.actions, add_text, command=add_command, variant="primary", width=112, disabled_command=notify_setup_required)
        self.delete_button = RoundedButton(self.actions, "Remove", command=delete_command, variant="secondary", width=104, disabled_command=notify_setup_required)
        self.error_label = ttk.Label(parent, text="", style="Error.TLabel")

        self.label.grid(row=0, column=0, sticky="w", padx=(0, 12))
        self.actions.grid(row=0, column=1, sticky="e")
        self.add_button.pack(side="left", padx=(0, 8))
        self.delete_button.pack(side="left")
        self.helper_label.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(4, 10))
        self.list_frame.grid(row=2, column=0, columnspan=2, sticky="nsew")
        self.listbox.grid(row=0, column=0, sticky="nsew")
        self.yscroll.grid(row=0, column=1, sticky="ns", padx=(8, 0))
        self.list_frame.grid_rowconfigure(0, weight=1)
        self.list_frame.grid_columnconfigure(0, weight=1)
        self.error_label.grid(row=3, column=0, columnspan=2, sticky="w", pady=(8, 0))

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

    def add_items(self, values: Iterable[str], formatter=None) -> int:
        added = 0
        current = set(self.listbox.get(0, tk.END))
        raw_current = {strip_language_badge(item) for item in current}
        for value in values:
            text = str(value).strip()
            if not text or text in current or text in raw_current:
                continue
            display_value = formatter(text) if formatter else text
            if display_value not in current:
                self.listbox.insert(tk.END, display_value)
                current.add(display_value)
                raw_current.add(strip_language_badge(display_value))
                added += 1
        return added

    def remove_selected(self) -> int:
        selected_indices = tuple(int(index) for index in self.listbox.curselection()) or self._last_selection
        selected_indices = tuple(index for index in selected_indices if 0 <= index < self.listbox.size())

        if not selected_indices:
            return 0

        for index in reversed(selected_indices):
            self.listbox.delete(index)

        self._last_selection = ()
        return len(selected_indices)

    def size(self) -> int:
        return self.listbox.size()

    def values(self) -> List[str]:
        return list(self.listbox.get(0, tk.END))

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
        self.helper.grid(row=1, column=0, sticky="w", pady=(3, 10))
        self.entry.grid(row=2, column=0, sticky="ew", ipady=8)
        self.error_label.grid(row=3, column=0, sticky="w", pady=(8, 0))

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
    target_width = min(max(width, int(monitor_width * 0.94)), max(monitor_width - 24, 900))
    target_height = min(max(height, int(monitor_height * 0.90)), max(monitor_height - 60, 680))
    x = monitor_x + max((monitor_width - target_width) // 2, 0)
    y = monitor_y + max((monitor_height - target_height) // 2, 0)

    root.geometry(f"{target_width}x{target_height}+{x}+{y}")
    root.deiconify()
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

        self.title(title_with_version(APP_NAME, APP_VERSION))
        self.geometry("1500x920")
        self.minsize(1280, 780)
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        self.style = ttk.Style(self)
        self._configure_base_style()
        self._build_layout()
        self.apply_theme()
        self.update_create_state()
        self.after(80, lambda: centre_and_focus_window(self))

        print("MiSAR parser startup PSM selection = {}".format(describe_psm_selection()))

    def _configure_base_style(self) -> None:
        try:
            self.style.theme_use("clam")
        except tk.TclError:
            pass
        for font_name in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont"):
            try:
                tkfont.nametofont(font_name).configure(size=10)
            except Exception:
                pass

    def _build_layout(self) -> None:
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self.sidebar = tk.Frame(self, width=92, bg=PALETTE["sidebar"])
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

        self.header = ttk.Frame(self.main, padding=(28, 18, 28, 4), style="Root.TFrame")
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

        self.content = ttk.Frame(self.main, padding=(28, 8, 28, 12), style="Root.TFrame")
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
        self.project_name = ProjectNameBox(self.content, self.update_create_state)
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
            list_rows=12,
        )
        self.docker_compose.grid(1, 0, 6, padx=(0, 10), pady=(0, 12))

        self.module_build_dir = MultiPicker(
            self.content,
            "Microservice build directories",
            "Required. Each folder can be scanned for dependency files.",
            "Add folder",
            self.add_module_directory,
            lambda: self.delete_items(self.module_build_dir),
            list_rows=12,
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
            list_rows=9,
        )
        self.app_build.grid(2, 0, 4, padx=(0, 10), pady=(0, 12))

        self.module_build = MultiPicker(
            self.content,
            "Module dependency files",
            "Optional. These can be auto-filled from selected module folders.",
            "Add files",
            self.add_module_build_files,
            lambda: self.delete_items(self.module_build),
            list_rows=9,
        )
        self.module_build.grid(2, 4, 4, padx=(6, 6), pady=(0, 12))

        self.app_config_dir = MultiPicker(
            self.content,
            "Centralised configuration directories",
            "Optional. Add folders used by shared configuration services.",
            "Add folder",
            self.add_config_directory,
            lambda: self.delete_items(self.app_config_dir),
            list_rows=9,
        )
        self.app_config_dir.grid(2, 8, 4, padx=(10, 0), pady=(0, 12))

    def _build_create_section(self) -> None:
        self.create_box = BoxFrame(self.content)
        self.create_box.grid(row=3, column=0, columnspan=12, sticky="ew", pady=(0, 4))
        parent = self.create_box.content
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_columnconfigure(1, weight=0)
        self.create_title = ttk.Label(parent, text="Create model", style="FieldTitle.TLabel")
        self.create_title.grid(row=0, column=0, sticky="w")
        self.readiness_label = ttk.Label(parent, text="Complete the required fields to continue.", style="MutedCard.TLabel")
        self.readiness_label.grid(row=1, column=0, sticky="w", pady=(4, 0))
        self.create_button = RoundedButton(parent, "Create PSM Model", command=self.create_model, variant="success", width=180)
        self.create_button.grid(row=0, column=1, rowspan=2, sticky="e", padx=(18, 0))

        self.progress_frame = tk.Frame(parent, bg=PALETTE["panel"])
        self.progress_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(12, 0))
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

    def select_output_directory(self) -> None:
        directory = filedialog.askdirectory(title="Select output directory", initialdir=self.project_dialog_initial_dir())
        if not directory:
            return
        self.output_dir.set_path(directory)
        self.output_dir.set_error("")
        self.set_status("Output directory selected.")
        self.update_create_state()

    def add_docker_compose_files(self) -> None:
        files = filedialog.askopenfilenames(
            title="Select Docker Compose files",
            initialdir=self.project_dialog_initial_dir(),
            filetypes=(
                ("Docker Compose / YAML files", "*.yml *.yaml"),
                ("All files", "*.*"),
            ),
        )
        added = self.docker_compose.add_items(files)
        if added:
            self.docker_compose.set_error("")
            self.set_status(f"Added {added} Docker Compose file{'s' if added != 1 else ''}.")
            if self.project_dir.get():
                self.offer_auto_importer(self.project_dir.get())
        self.update_create_state()

    def add_app_build_files(self) -> None:
        files = filedialog.askopenfilenames(title="Select application dependency files", initialdir=self.project_dialog_initial_dir())
        added = self.app_build.add_items(files)
        if added:
            self.set_status(f"Added {added} application dependency file{'s' if added != 1 else ''}.")
        self.update_create_state()

    def add_module_build_files(self) -> None:
        files = filedialog.askopenfilenames(title="Select module dependency files", initialdir=self.project_dialog_initial_dir())
        added = self.module_build.add_items(files)
        if added:
            self.set_status(f"Added {added} module dependency file{'s' if added != 1 else ''}.")
        self.update_create_state()

    def add_module_directory(self) -> None:
        directory = filedialog.askdirectory(title="Select microservice build directory", initialdir=self.project_dialog_initial_dir())
        if not directory:
            return
        added = self.module_build_dir.add_items([directory], formatter=format_module_display_path)
        if added:
            self.module_build_dir.set_error("")
            self.set_status("Microservice build directory added.")
            self.offer_dependency_scan(directory, self.module_build.listbox)
        self.update_create_state()

    def add_config_directory(self) -> None:
        directory = filedialog.askdirectory(title="Select centralised configuration directory", initialdir=self.project_dialog_initial_dir())
        if not directory:
            return
        added = self.app_config_dir.add_items([directory])
        if added:
            self.set_status("Configuration directory added.")
        self.update_create_state()

    def delete_items(self, picker: MultiPicker) -> None:
        removed_count = picker.remove_selected()

        if removed_count:
            self.set_status(f"Removed {removed_count} selected item{'s' if removed_count != 1 else ''}.")
        else:
            self.set_status("Select an item before removing it.")

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
            added_module_files += self.add_dependency_files_for_directory(target_directory, self.module_build.listbox)
        added_app_files = self.add_dependency_files_for_directory(input_dir_path, self.app_build.listbox)
        return added_dirs, added_app_files, added_module_files

    def offer_dependency_scan(self, directory: str, target_listbox: tk.Listbox) -> None:
        folder_name = Path(directory).name
        answer = messagebox.askquestion(
            "Build / Dependency Scanner",
            f"Would you like to add dependency files that exist within {folder_name}?",
            icon="info",
        )
        if answer == "yes":
            added = self.add_dependency_files_for_directory(Path(directory), target_listbox)
            if added:
                self.set_status(f"Added {added} dependency file{'s' if added != 1 else ''}.")

    def add_dependency_files_for_directory(self, input_directory: Path, target_listbox: tk.Listbox) -> int:
        added = 0
        input_path = Path(input_directory)
        current = set(target_listbox.get(0, tk.END))
        for dependency_file in DEPENDENCY_BUILD_FILES:
            candidate = input_path / dependency_file
            candidate_text = str(candidate)
            if candidate.is_file() and candidate_text not in current:
                target_listbox.insert(tk.END, candidate_text)
                current.add(candidate_text)
                added += 1
        return added

    def yaml_to_dict(self, filename: str) -> dict:
        with open(filename, encoding="utf-8") as file:
            return yaml.load(file, Loader=yaml.FullLoader) or {}

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
        if self.module_build_dir.size() == 0:
            errors.append("Microservice project build directories are missing.")
            if show_errors:
                self.module_build_dir.set_error("Add at least one microservice build directory.")
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
            success_message = "The MiSAR PSM model was created successfully."
            if output_path:
                success_message += "\n\nSaved at:\n" + str(output_path)
            messagebox.showinfo("PSM model created", success_message)
            self.set_status("PSM model created successfully.")

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
        self.create_button.apply_theme(palette)
        if hasattr(self, "progress_frame"):
            self.progress_frame.configure(bg=palette["panel"])

    def on_close(self) -> None:
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