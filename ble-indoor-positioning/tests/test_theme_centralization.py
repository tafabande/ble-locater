import re
from unittest.mock import MagicMock

from admin.admin_gui import SystemAdminApp
from collector.collector_gui import DataCollectorApp
from collector.setup_gui import SetupApp
from core.theme import (
    DEFAULT_ANCHOR_COLORS,
    SLATE_THEME,
    ZINC_THEME,
    apply_base_ttk_styles,
    get_theme,
)
from training.model_benchmark_view import ModelBenchmarkWindow
from training.trainer_gui import ModelTrainerApp

HEX_COLOR_REGEX = re.compile(r"^#[0-9A-Fa-f]{6}$")

REQUIRED_BASE_KEYS = {
    "bg", "panel", "card", "border", "text", "subtext",
    "green", "red", "amber", "terminal_bg"
}


def test_zinc_theme_contract():
    """Verify ZINC_THEME contains all fundamental operational tokens and valid hex codes."""
    assert REQUIRED_BASE_KEYS.issubset(ZINC_THEME.keys())
    for key, value in ZINC_THEME.items():
        assert isinstance(value, str), f"Token {key} is not a string"
        assert HEX_COLOR_REGEX.match(value), f"Token {key} ({value}) is not a valid 6-char hex code"


def test_slate_theme_contract():
    """Verify SLATE_THEME contains all studio tokens and valid hex codes."""
    slate_required = REQUIRED_BASE_KEYS | {"primary", "gold", "entry_bg"}
    assert slate_required.issubset(SLATE_THEME.keys())
    for key, value in SLATE_THEME.items():
        assert isinstance(value, str), f"Token {key} is not a string"
        assert HEX_COLOR_REGEX.match(value), f"Token {key} ({value}) is not a valid 6-char hex code"


def test_anchor_colors_contract():
    """Verify 4-corner spatial anchor palette has distinct valid colors."""
    assert set(DEFAULT_ANCHOR_COLORS.keys()) == {"ANCHOR_01", "ANCHOR_02", "ANCHOR_03", "ANCHOR_04"}
    colors = list(DEFAULT_ANCHOR_COLORS.values())
    assert len(set(colors)) == 4, "Anchor colors must be visually distinct"
    for c in colors:
        assert HEX_COLOR_REGEX.match(c)


def test_consumer_themes_intact():
    """Verify all 5 GUI consumers expose their expected theme contracts."""
    # 1. Collector GUI
    assert DataCollectorApp.THEME["bg"] == "#121214"
    assert DataCollectorApp.ANCHOR_COLORS == DEFAULT_ANCHOR_COLORS

    # 2. Setup GUI
    assert SetupApp.THEME["danger"] == "#EF4444"
    assert SetupApp.THEME["warning"] == "#F59E0B"
    assert SetupApp.THEME["terminal_text"] == "#E4E4E7"

    # 3. System Admin Console — must retain intentional crisp neutral Zinc 200 accent
    assert SystemAdminApp.THEME["accent"] == "#E4E4E7"
    assert SystemAdminApp.THEME["bg"] == "#121214"

    # 4. Model Trainer GUI
    assert ModelTrainerApp.THEME["bg"] == "#0B0F17"
    assert ModelTrainerApp.THEME["primary"] == "#3B82F6"
    assert ModelTrainerApp.THEME["card_nested"] == "#131C2D"

    # 5. Model Benchmark View
    assert ModelBenchmarkWindow.THEME["bg"] == "#0B0F17"
    assert ModelBenchmarkWindow.THEME["neutral_btn"] == "#182234"
    assert ModelBenchmarkWindow.THEME["blue"] == "#3B82F6"


def test_get_theme_copy_isolation():
    """Verify get_theme returns independent mutable copies without mutating source constants."""
    z_copy = get_theme("zinc")
    z_copy["bg"] = "#FFFFFF"
    assert ZINC_THEME["bg"] == "#121214"

    s_copy = get_theme("slate")
    s_copy["bg"] = "#FFFFFF"
    assert SLATE_THEME["bg"] == "#0B0F17"


def test_apply_base_ttk_styles_mock():
    """Verify apply_base_ttk_styles configures core ttk components."""
    mock_style = MagicMock()
    apply_base_ttk_styles(mock_style, ZINC_THEME)

    mock_style.theme_use.assert_called_with("clam")
    configured_styles = {call.args[0] for call in mock_style.configure.call_args_list}
    expected_styles = {"TFrame", "Panel.TFrame", "Card.TFrame", "TLabel", "Header.TLabel", "Muted.TLabel"}
    assert expected_styles.issubset(configured_styles)
