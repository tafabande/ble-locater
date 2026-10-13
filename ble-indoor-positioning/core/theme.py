"""Indoor Positioning — Shared GUI Design Tokens & Theme Palettes.

Provides centralized color tokens, typography scales, and ttk styling
helpers for the desktop operational tools. Preserves distinct palette
families (Zinc Operations vs. Midnight Slate Studio) with zero visual drift.
"""
from __future__ import annotations

from typing import Any

# ── FAMILY 1: NEUTRAL ZINC PALETTE (Hardware Operations & Diagnostics) ────────
# Used by: Collector GUI, ESP32 Provisioner/Setup GUI, System Admin Console
ZINC_THEME: dict[str, str] = {
    "bg": "#121214",          # Deep Neutral Dark
    "panel": "#18181B",       # Zinc 900
    "card": "#27272A",        # Zinc 800
    "card_hover": "#323238",
    "border": "#3F3F46",      # Zinc 700
    "text": "#FAFAFA",        # Zinc 50
    "subtext": "#A1A1AA",     # Zinc 400
    "accent": "#10B981",      # Emerald 500 (Clean, professional green)
    "accent_hover": "#059669",
    "green": "#10B981",       # Emerald 500
    "green_dark": "#064E3B",
    "red": "#EF4444",         # Rose 500
    "red_dark": "#7F1D1D",
    "amber": "#F59E0B",       # Amber 500
    "amber_dark": "#78350F",
    "danger": "#EF4444",      # Rose 500 alias
    "warning": "#F59E0B",     # Amber 500 alias
    "terminal_bg": "#09090B", # Jet Black
    "terminal_text": "#E4E4E7",
}

# Standard 4-corner spatial anchor palette (SW=Emerald, SE=Amber, NW=Rose, NE=Teal)
DEFAULT_ANCHOR_COLORS: dict[str, str] = {
    "ANCHOR_01": "#10B981",  # Node A (SW) - Emerald
    "ANCHOR_02": "#F59E0B",  # Node B (SE) - Amber
    "ANCHOR_03": "#F43F5E",  # Node C (NW) - Rose
    "ANCHOR_04": "#14B8A6",  # Node D (NE) - Teal
}


# ── FAMILY 2: MIDNIGHT SLATE PALETTE (WCAG AAA Contrast AI Studio) ────────────
# Used by: Model Trainer GUI, Benchmark & Evaluation View
SLATE_THEME: dict[str, str] = {
    "bg": "#0B0F17",           # Deep Midnight Slate canvas
    "panel": "#111827",        # Slate 900 elevated surface
    "card": "#182234",         # Slate 850 card with clear boundary
    "card_nested": "#131C2D",  # Nested card surface
    "card_hover": "#223048",   # Subtle card hover
    "border": "#28374E",       # Distinct crisp border (high contrast)
    "border_subtle": "#1B273B",# Subtle separator
    "border_focus": "#3B82F6", # Electric Blue focus border
    "text": "#F8FAFC",         # Slate 50 (crisp readable text, no glare)
    "subtext": "#94A3B8",      # Slate 400 (comfortable secondary gray)
    "text_muted": "#64748B",   # Slate 500 (labels/hints)
    "primary": "#3B82F6",      # Electric Blue 500 (actionable primary)
    "primary_hover": "#2563EB",# Electric Blue 600
    "cyan": "#0EA5E9",         # Sky 500 (telemetry)
    "green": "#10B981",        # Emerald 500 (success / champion)
    "green_bg": "#064E3B",     # Deep Emerald container
    "green_card": "#0F2A21",   # Emerald-tinted card
    "amber": "#F59E0B",        # Amber 500 (training in progress)
    "amber_bg": "#451A03",     # Deep Amber container
    "gold": "#FBBF24",         # Amber Gold 400 (champion awards)
    "rose": "#F43F5E",         # Rose 500 (errors)
    "purple": "#8B5CF6",       # Violet 500
    "entry_bg": "#0D1525",     # Slate 925 high-contrast entry
    "entry_fg": "#F8FAFC",     # Slate 50 entry text
    "entry_border": "#334561", # Slate 700 distinct border
    "terminal_bg": "#070B12",  # Ultra-deep console surface
    "terminal_fg": "#E2E8F0",  # Slate 200 console text
    # Analytical & Benchmark View aliases
    "accent": "#3B82F6",
    "neutral_btn": "#182234",
    "neutral_hover": "#28374E",
    "yellow": "#F59E0B",
    "red": "#EF4444",
    "slate": "#94A3B8",
    "blue": "#3B82F6",
}


def get_theme(name: str = "zinc") -> dict[str, str]:
    """Return a fresh copy of the requested theme dictionary."""
    if name.lower() in ("slate", "midnight", "studio", "trainer"):
        return dict(SLATE_THEME)
    return dict(ZINC_THEME)


def apply_base_ttk_styles(style: Any, theme: dict[str, str]) -> None:
    """Apply universal baseline TTK styles across frames, panels, and labels."""
    try:
        style.theme_use("clam")
    except Exception:
        pass

    style.configure("TFrame", background=theme["bg"])
    style.configure("Panel.TFrame", background=theme["panel"])
    style.configure("Card.TFrame", background=theme["card"])
    style.configure("TLabel", background=theme["panel"], foreground=theme["text"], font=("Segoe UI", 9))
    style.configure("Header.TLabel", background=theme["panel"], foreground=theme["text"], font=("Segoe UI", 11, "bold"))
    style.configure("Muted.TLabel", background=theme["panel"], foreground=theme["subtext"], font=("Segoe UI", 8))
