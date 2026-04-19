"""Colour palette and ttk styling.

The values mirror the website's Tailwind/shadcn theme in
``OS-Project/src/index.css`` and ``OS-Project/tailwind.config.js`` so the
desktop app looks visually consistent with the web version.
"""

from __future__ import annotations

import tkinter.font as tkfont
from tkinter import ttk


def _pick_font(*candidates: str, default: str = "TkDefaultFont") -> str:
    """Return the first installed font family, else ``default``."""
    try:
        available = set(tkfont.families())
    except Exception:
        return default
    for name in candidates:
        if name in available:
            return name
    return default


# ---------------------------------------------------------------------------
# Palettes
# ---------------------------------------------------------------------------

# Process block colours (same ordering as the website's MemoryBlock.jsx).
PROCESS_COLORS: list[str] = [
    "#6366f1",  # indigo-500
    "#06b6d4",  # cyan-500
    "#f59e0b",  # amber-500
    "#ec4899",  # pink-500
    "#84cc16",  # lime-500
    "#10b981",  # emerald-500
    "#f97316",  # orange-500
    "#8b5cf6",  # violet-500
]

FREE_COLOR = "#334155"   # slate-700 (free hole)
CANVAS_BG = "#0b1220"    # darker than slate-900 for contrast
SCAN_OUTLINE = "#fbbf24"  # amber-400 (being scanned)
FIT_OUTLINE = "#22d3ee"  # cyan-400 (chosen fit)


DARK = {
    "background": "#0f172a",    # slate-900
    "card":       "#1e293b",    # slate-800
    "card_alt":   "#172033",
    "border":     "#263244",
    "foreground": "#f1f5f9",    # slate-100
    "muted":      "#94a3b8",    # slate-400
    "subtle":     "#64748b",    # slate-500
    "primary":    "#6366f1",    # indigo-500
    "primary_fg": "#ffffff",
    "danger":     "#ef4444",
    "success":    "#10b981",
    "warning":    "#f59e0b",
    "accent":     "#06b6d4",
    "canvas":     CANVAS_BG,
    "free":       FREE_COLOR,
    "free_text":  "#cbd5e1",
    "header":     "#1e293b",
}

LIGHT = {
    "background": "#f6f8fb",
    "card":       "#ffffff",
    "card_alt":   "#eef3f8",
    "border":     "#c7d2df",
    "foreground": "#162033",
    "muted":      "#526173",
    "subtle":     "#718096",
    "primary":    "#4f46e5",
    "primary_fg": "#ffffff",
    "danger":     "#dc2626",
    "success":    "#047857",
    "warning":    "#b45309",
    "accent":     "#0e7490",
    "canvas":     "#eaf1f8",
    "free":       "#d8e3ee",
    "free_text":  "#334155",
    "header":     "#ffffff",
}


# ---------------------------------------------------------------------------
# ttk style application
# ---------------------------------------------------------------------------


def color_for_process(color_index: int) -> str:
    return PROCESS_COLORS[color_index % len(PROCESS_COLORS)]


def apply_theme(root, dark: bool = True) -> dict:
    """Configure ttk styles and return the active palette dict.

    The function is safe to call repeatedly (e.g. when the user toggles
    dark/light mode).
    """
    palette = DARK if dark else LIGHT

    # Resolve best available fonts (Inter / SF Pro / Segoe UI / system).
    ui_font = _pick_font("Inter", "SF Pro Text", "Segoe UI", "Helvetica Neue",
                         default="TkDefaultFont")
    mono_font = _pick_font("JetBrains Mono", "Cascadia Mono", "Consolas",
                           "Menlo", default="TkFixedFont")
    palette["font_ui"] = ui_font
    palette["font_mono"] = mono_font

    try:
        root.configure(bg=palette["background"])
    except Exception:  # pragma: no cover - root may not support bg
        pass

    style = ttk.Style(root)
    # 'clam' gives us the most control over ttk colours on all platforms.
    try:
        style.theme_use("clam")
    except Exception:  # pragma: no cover
        pass

    bg = palette["background"]
    card = palette["card"]
    fg = palette["foreground"]
    border = palette["border"]
    muted = palette["muted"]
    primary = palette["primary"]
    primary_fg = palette["primary_fg"]

    style.configure(".", background=bg, foreground=fg, fieldbackground=card)

    # Containers
    style.configure("TFrame", background=bg)
    style.configure("Card.TFrame", background=card, borderwidth=0, relief="flat")
    style.configure("Header.TFrame", background=palette.get("header", card))
    style.configure("TLabelframe", background=card, foreground=fg, bordercolor=border)
    style.configure("TLabelframe.Label", background=card, foreground=muted)

    # Text
    style.configure("TLabel", background=bg, foreground=fg)
    style.configure("Card.TLabel", background=card, foreground=fg)
    style.configure("Muted.TLabel", background=card, foreground=muted, font=("Segoe UI", 11))
    style.configure("SectionTitle.TLabel",
                    background=card, foreground=muted,
                    font=("Segoe UI", 10, "bold"))
    style.configure("Heading.TLabel",
                    background=card, foreground=fg,
                    font=("Segoe UI", 13, "bold"))
    style.configure("BigStat.TLabel",
                    background=card, foreground=fg,
                    font=("Segoe UI", 16, "bold"))
    style.configure("AppTitle.TLabel",
                    background=palette.get("header", card), foreground=fg,
                    font=("Segoe UI Semibold", 14))
    style.configure("AppSubtitle.TLabel",
                    background=palette.get("header", card), foreground=muted,
                    font=("Segoe UI", 10))
    style.configure("Badge.TLabel",
                    background=primary, foreground=primary_fg,
                    padding=(6, 2), font=("Consolas", 8, "bold"))
    style.configure("LiveBadge.TLabel",
                    background=palette["warning"], foreground="#0b1220",
                    padding=(6, 2), font=("Consolas", 8, "bold"))

    # Buttons
    style.configure("TButton",
                    background=card, foreground=fg, bordercolor=border,
                    padding=(12, 8), relief="flat",
                    font=("Segoe UI", 10))
    style.map("TButton",
              background=[("active", palette["card_alt"])],
              foreground=[("disabled", muted)])

    style.configure("Primary.TButton",
                    background=primary, foreground=primary_fg,
                    padding=(14, 9), relief="flat",
                    font=("Segoe UI", 11, "bold"))
    style.map("Primary.TButton",
              background=[("active", "#4f46e5")])

    style.configure("Danger.TButton",
                    background=palette["danger"], foreground="#ffffff",
                    padding=(12, 8), relief="flat",
                    font=("Segoe UI", 10, "bold"))

    style.configure("Secondary.TButton",
                    background=palette["card_alt"], foreground=fg,
                    bordercolor=border, padding=(12, 8),
                    relief="flat", font=("Segoe UI", 10, "bold"))
    style.map("Secondary.TButton",
              background=[("active", border)])

    style.configure("Ghost.TButton",
                    background=bg, foreground=muted, padding=(8, 4),
                    relief="flat")
    style.map("Ghost.TButton",
              background=[("active", palette["card_alt"])],
              foreground=[("active", fg)])

    # Inputs
    input_border = palette["card_alt"] if dark else border
    style.configure("TEntry",
                    fieldbackground=palette["card_alt"], foreground=fg,
                    bordercolor=input_border, lightcolor=input_border,
                    darkcolor=input_border, insertcolor=fg, padding=6,
                    relief="flat", font=("Segoe UI", 11))
    style.configure("TCombobox",
                    fieldbackground=palette["card_alt"], foreground=fg,
                    background=palette["card_alt"], bordercolor=input_border,
                    lightcolor=input_border, darkcolor=input_border,
                    arrowcolor=muted, padding=6, relief="flat",
                    font=("Segoe UI", 11))
    style.map("TCombobox",
              fieldbackground=[("readonly", palette["card_alt"])],
              foreground=[("readonly", fg)])

    # Checkbutton / Radiobutton
    style.configure("TCheckbutton", background=card, foreground=fg,
                    font=("Segoe UI", 11))
    style.configure("TRadiobutton", background=card, foreground=fg,
                    font=("Segoe UI", 11))
    style.map("TCheckbutton", background=[("active", card)])

    # Scrollbar
    style.configure("Vertical.TScrollbar",
                    background=card, troughcolor=bg, bordercolor=border,
                    arrowcolor=muted)

    # Treeview (process table)
    style.configure("Treeview",
                    background=palette["card_alt"], fieldbackground=palette["card_alt"],
                    foreground=fg, bordercolor=palette["card"], rowheight=30,
                    font=("Segoe UI", 11))
    style.configure("Treeview.Heading",
                    background=palette["card_alt"], foreground=muted,
                    relief="flat", font=("Segoe UI", 10, "bold"))
    style.map("Treeview",
              background=[("selected", primary)],
              foreground=[("selected", primary_fg)])

    # Scale (speed slider)
    style.configure("Horizontal.TScale", background=card, troughcolor=border)

    return palette
