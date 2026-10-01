"""Design system: colour palette, text styles, and button style helpers.

A minimal, professional look — neutral chrome with one blue accent — so the
user's coloured notes stand out against a quiet UI.
"""

from dataclasses import dataclass, replace
from typing import Optional

from PyQt6.QtWidgets import QPushButton
from PyQt6.QtGui import QColor

# ── Design system: swappable Light/Dark chrome palette ─────────────────────────
# Minimal, professional palette: neutral chrome + one blue accent. Keeps the UI
# quiet so the user's coloured notes stand out. The `UI` slots are rebound at
# runtime by apply_theme(); LIGHT_UI preserves the original look exactly.
LIGHT_UI = {
    "ACCENT": "#2f6fed", "ACCENT_HOVER": "#2a63d4", "ACCENT_PRESS": "#2356bb",
    "DANGER": "#e0463c", "DANGER_HOVER": "#cc3f36", "DANGER_PRESS": "#b5372f",
    "NEUTRAL_BG": "#f0f1f3", "NEUTRAL_HOVER": "#e4e6e9", "NEUTRAL_PRESS": "#d6d9dd",
    "TEXT": "#2b2d31", "TEXT_MUTED": "#6b6f76", "BORDER": "#dcdee1",
    "SURFACE": "#ffffff", "WINDOW_BG": "#f7f8fa",
    # Translucent hover/press overlays for transparent chrome buttons (popups).
    "HOVER_OVERLAY": "rgba(0,0,0,0.07)", "HOVER_OVERLAY_STRONG": "rgba(0,0,0,0.10)",
}
DARK_UI = {
    "ACCENT": "#4b83f0", "ACCENT_HOVER": "#5a8ef2", "ACCENT_PRESS": "#3f76e0",
    "DANGER": "#e0574d", "DANGER_HOVER": "#e8675e", "DANGER_PRESS": "#c9463d",
    "NEUTRAL_BG": "#34363b", "NEUTRAL_HOVER": "#3e4046", "NEUTRAL_PRESS": "#46484e",
    "TEXT": "#e8e9ec", "TEXT_MUTED": "#9a9ea6", "BORDER": "#3a3d42",
    "SURFACE": "#2b2d31", "WINDOW_BG": "#1e1f22",
    "HOVER_OVERLAY": "rgba(255,255,255,0.09)", "HOVER_OVERLAY_STRONG": "rgba(255,255,255,0.14)",
}

class UI:
    """Current chrome palette. Slots are rebound by apply_theme() (default light)."""
    ACCENT        = LIGHT_UI["ACCENT"]         # primary actions
    ACCENT_HOVER  = LIGHT_UI["ACCENT_HOVER"]
    ACCENT_PRESS  = LIGHT_UI["ACCENT_PRESS"]
    DANGER        = LIGHT_UI["DANGER"]         # destructive actions
    DANGER_HOVER  = LIGHT_UI["DANGER_HOVER"]
    DANGER_PRESS  = LIGHT_UI["DANGER_PRESS"]
    NEUTRAL_BG    = LIGHT_UI["NEUTRAL_BG"]     # secondary buttons
    NEUTRAL_HOVER = LIGHT_UI["NEUTRAL_HOVER"]
    NEUTRAL_PRESS = LIGHT_UI["NEUTRAL_PRESS"]
    TEXT          = LIGHT_UI["TEXT"]           # primary text
    TEXT_MUTED    = LIGHT_UI["TEXT_MUTED"]     # secondary text
    BORDER        = LIGHT_UI["BORDER"]
    SURFACE       = LIGHT_UI["SURFACE"]
    WINDOW_BG     = LIGHT_UI["WINDOW_BG"]      # dialog/manager window background
    HOVER_OVERLAY = LIGHT_UI["HOVER_OVERLAY"]        # translucent button hover
    HOVER_OVERLAY_STRONG = LIGHT_UI["HOVER_OVERLAY_STRONG"]
    # Reusable text styles — LIVE attributes on UI (rebuilt on theme swap). They
    # MUST live on the shared UI class, not module globals: consumers do
    # `from .theme import UI` (a live class ref) but `from .theme import LABEL_STYLE`
    # would snapshot the string at import and never see a theme change.
    LABEL_STYLE   = ""   # standard field label
    VALUE_STYLE   = ""   # emphasised value
    HINT_STYLE    = ""   # helper/hint text
    SECTION_STYLE = ""   # section header

def _rebuild_text_styles():
    """Recompute the live text-style attributes from the current UI palette."""
    UI.LABEL_STYLE   = f"font-size: 13px; color: {UI.TEXT};"
    UI.VALUE_STYLE   = f"font-size: 13px; color: {UI.TEXT}; font-weight: 600;"
    UI.HINT_STYLE    = f"font-size: 12px; color: {UI.TEXT_MUTED};"
    UI.SECTION_STYLE = (f"font-size: 11px; color: {UI.TEXT_MUTED}; "
                        "font-weight: 600; letter-spacing: 1px;")

_CURRENT_THEME = "light"

def apply_theme(name: str) -> None:
    """Swap the UI chrome palette to 'light'/'dark' (unknown → 'light').
    Rebinds UI slots and rebuilds the module-level text-style constants so
    already-imported style strings pick up the new colours on next read."""
    global _CURRENT_THEME
    palette = DARK_UI if name == "dark" else LIGHT_UI
    _CURRENT_THEME = "dark" if name == "dark" else "light"
    for slot, value in palette.items():
        setattr(UI, slot, value)
    _rebuild_text_styles()

def current_theme() -> str:
    return _CURRENT_THEME

_rebuild_text_styles()   # build once at import (light default)

def _btn_primary(min_w: int = 0) -> str:
    return f"""
        QPushButton {{
            background: {UI.ACCENT}; color: #ffffff; border: none;
            border-radius: 6px; padding: 7px 16px; font-size: 13px;
            font-weight: 500; {'min-width: %dpx;' % min_w if min_w else ''}
        }}
        QPushButton:hover  {{ background: {UI.ACCENT_HOVER}; }}
        QPushButton:pressed {{ background: {UI.ACCENT_PRESS}; }}
        QPushButton:disabled {{ background: #b9c4d6; color: #eef1f6; }}
    """

def _btn_secondary(min_w: int = 0) -> str:
    return f"""
        QPushButton {{
            background: {UI.NEUTRAL_BG}; color: {UI.TEXT};
            border: 1px solid {UI.BORDER};
            border-radius: 6px; padding: 6px 16px; font-size: 13px;
            font-weight: 500; {'min-width: %dpx;' % min_w if min_w else ''}
        }}
        QPushButton:hover  {{ background: {UI.NEUTRAL_HOVER}; border-color: #c4c7cc; }}
        QPushButton:pressed {{ background: {UI.NEUTRAL_PRESS}; }}
        QPushButton:disabled {{ color: #aeb2b8; border-color: #e8eaec; }}
    """

def _btn_danger(min_w: int = 0) -> str:
    return f"""
        QPushButton {{
            background: {UI.DANGER}; color: #ffffff; border: none;
            border-radius: 6px; padding: 7px 16px; font-size: 13px;
            font-weight: 500; {'min-width: %dpx;' % min_w if min_w else ''}
        }}
        QPushButton:hover  {{ background: {UI.DANGER_HOVER}; }}
        QPushButton:pressed {{ background: {UI.DANGER_PRESS}; }}
        QPushButton:disabled {{ background: #e6a8a3; color: #fbeceb; }}
    """


# ── Button factory ────────────────────────────────────────────────────────────
HEADER_BTN_STYLE = """
    QPushButton {{
        background: transparent;
        border: none;
        border-radius: 4px;
        font-size: {fs}px;
        color: #555;
        padding: 0;
    }}
    QPushButton:hover  {{ background: rgba(0,0,0,0.13); color: #222; }}
    QPushButton:pressed {{ background: rgba(0,0,0,0.22); }}
"""

CLOSE_BTN_STYLE = """
    QPushButton {
        background: transparent;
        border: none;
        border-radius: 4px;
        font-size: 17px;
        color: #666;
        padding: 0;
    }
    QPushButton:hover  { background: #e53935; color: white; }
    QPushButton:pressed { background: #b71c1c; color: white; }
"""


def make_header_btn(text: str, tooltip: str, font_size: int = 14, w: int = 24, h: int = 24) -> QPushButton:
    btn = QPushButton(text)
    btn.setFixedSize(w, h)
    btn.setToolTip(tooltip)
    btn.setStyleSheet(HEADER_BTN_STYLE.format(fs=font_size))
    return btn


TEXT_COLOR_BTN_STYLE = """
    QPushButton {{
        background: transparent;
        border: none;
        border-radius: 3px;
        color: {color};
        font-weight: bold;
        font-size: 16px;
        padding: 0;
    }}
    QPushButton:hover {{ background: rgba(0,0,0,0.07); }}
"""


# ── Per-note auto-contrast ink ────────────────────────────────────────────────
@dataclass(frozen=True)
class Ink:
    """Colours the note chrome uses, chosen for contrast against the note fill."""
    ink: str            # primary icon idle
    ink_dim: str        # secondary idle (header buttons, family, progress)
    ink_hover: str      # hover text
    ink_active: str     # checked/active text
    hover_bg: str       # button hover background
    active_bg: str      # button checked background
    separator: str      # toolbar/header separators
    selection_bg: str   # text selection highlight
    text: str           # default typed-text colour
    icon: str           # header SVG-icon fill (lock/pin/bell/toolbar-toggle)
    code_bg: Optional[QColor] = None   # code-block background (opaque dark box)
    code_fg: Optional[QColor] = None   # code-block text colour (light on the box)
    inline_bg: Optional[QColor] = None  # inline-code background (subtle translucent overlay)
    code_inline_bg: Optional[QColor] = None  # inline code INSIDE a code block (overlay on the box)
    header: Optional[QColor] = None   # note header fill (per-note)
    border: Optional[QColor] = None   # note border   (per-note)
    grip: Optional[QColor] = None     # resize-grip lines (per-note, contrast-aware)
    dark: bool = False                # True when this is a DARK note (light-ink set)


# DARK ink = today's values, for light notes (do NOT change — preserves look).
DARK_INK = Ink(
    ink="#888888", ink_dim="#555555", ink_hover="#444444", ink_active="#222222",
    hover_bg="rgba(0,0,0,0.07)", active_bg="rgba(0,0,0,0.10)",
    separator="rgba(0,0,0,0.12)", selection_bg="rgba(0,0,0,0.18)", text="#333333",
    icon="#494c4e", code_bg=QColor(0, 0, 0, 18), inline_bg=QColor(0, 0, 0, 66),
)

# LIGHT ink = mirrored, for clearly-dark notes.
LIGHT_INK = Ink(
    ink="#cccccc", ink_dim="#bbbbbb", ink_hover="#eeeeee", ink_active="#ffffff",
    hover_bg="rgba(255,255,255,0.18)", active_bg="rgba(255,255,255,0.26)",
    separator="rgba(255,255,255,0.16)", selection_bg="rgba(255,255,255,0.22)",
    text="#f0f0f0", icon="#cccccc", code_bg=QColor(255, 255, 255, 26),
    inline_bg=QColor(255, 255, 255, 86),
)

LIGHT_INK_THRESHOLD = 0.18   # flip to light ink only when clearly dark


def _blend(a: QColor, b: QColor, t: float) -> QColor:
    """Linear RGB blend a→b by fraction t (0..1). Used to lighten toward white in
    a way that works on pure black — unlike QColor.lighter(), which scales the HSV
    value and so leaves black (value 0) black."""
    return QColor(round(a.red()   + (b.red()   - a.red())   * t),
                  round(a.green() + (b.green() - a.green()) * t),
                  round(a.blue()  + (b.blue()  - a.blue())  * t))


def _code_box(base: QColor) -> QColor:
    """A dark, saturated version of `base`'s own hue, for a code block's box.
    Pastel notes carry a real hue but almost no saturation, so darkening toward
    black just greys out; instead keep the hue, amplify saturation into a rich
    colour, and force a low lightness. Light-blue → navy, yellow → dark amber,
    pink → deep maroon. Opaque so it reads as a solid box."""
    h, s, l, _a = base.getHslF()
    # Hue: keep the note's own. Saturation: amplify a pastel's faint tint into a
    # rich colour, but a NEAR-GREY note (e.g. #2b2b30, a hair of blue) has a real
    # hue with almost no saturation — boosting it would invent a colour that
    # isn't there, so keep it neutral. Every deliberately-tinted note sits well
    # above the threshold (lowest is ~0.16).
    if h < 0 or s < 0.13:           # achromatic / near-grey — no hue to deepen
        hue, sat = 0.0, 0.0
    else:
        hue, sat = h, max(0.45, min(s, 0.62))
    # Lightness: a fixed dark box reads great on a LIGHT note but vanishes into a
    # DARK note (both end up ~0.18). On a dark note there's no room to go darker
    # and keep the hue, so lift the box into a lighter "panel" that stays visible
    # and still carries the colour; light text remains readable (~7:1). The 0.25
    # floor keeps the panel visible even on a pure-black note (a +0.13 lift there
    # left it nearly black). Light and mid notes keep the classic dark box.
    box_l = min(max(l + 0.13, 0.25), 0.38) if l < 0.30 else 0.18
    box = QColor.fromHslF(hue, sat, box_l)
    box.setAlpha(255)
    return box


# How much an inline chip inside a code block must stand out from the box
# (WCAG contrast ratio). A chip on the note paper sits at ~1.86 on light notes,
# which reads fine, so aim a touch under that; the code text on the chip must
# still clear 4.5:1.
CODE_INLINE_TARGET = 1.7
CODE_INLINE_MAX_ALPHA = 128   # past ~50% a tint stops being a tint and reads as a hole


def _code_inline_bg(box: QColor, fg: QColor) -> QColor:
    """Translucent overlay for inline code INSIDE a code block, derived from the
    box, not the paper. The paper chip (ink.inline_bg) is a dark tint on light
    notes, which vanished on the dark box (contrast 1.13-1.31), and a light tint
    on dark notes, which lifted the box under the light code text (text 2.4-3.5).
    Try a white and a black overlay, each at the smallest alpha that reaches
    CODE_INLINE_TARGET against the box; keep the one that leaves the code text
    more readable. In practice: a lighter chip on the classic dark box, a darker
    one on a dark note's lifted panel."""
    def over(c: QColor) -> QColor:
        a = c.alpha() / 255
        return QColor(round(c.red() * a + box.red() * (1 - a)),
                      round(c.green() * a + box.green() * (1 - a)),
                      round(c.blue() * a + box.blue() * (1 - a)))
    def ratio(a: QColor, b: QColor) -> float:
        la, lb = _rel_luminance(a), _rel_luminance(b)
        return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)
    best = None
    for rgb in ((255, 255, 255), (0, 0, 0)):
        for alpha in range(1, CODE_INLINE_MAX_ALPHA + 1):
            tint = QColor(*rgb, alpha)
            chip = over(tint)
            if ratio(chip, box) >= CODE_INLINE_TARGET:
                text = ratio(fg, chip)
                if best is None or text > best[0]:
                    best = (text, tint)
                break
    # Unreachable within the cap (not the case for any colour _code_box makes):
    # fall back to the strongest light tint rather than nothing.
    return best[1] if best else QColor(255, 255, 255, CODE_INLINE_MAX_ALPHA)


def _rel_luminance(c: QColor) -> float:
    """WCAG relative luminance of an sRGB colour (alpha ignored)."""
    def lin(v: int) -> float:
        v = v / 255.0
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * lin(c.red()) + 0.7152 * lin(c.green()) + 0.0722 * lin(c.blue())


# Link colours as (light-note, dark-note) pairs. The dark variants are lifted
# because the light ones collapse on dark fills — violet measured 1.72:1 on
# charcoal, i.e. effectively unreadable. Every dark variant clears 4.5:1 on the
# darkest and the lightest of the built-in dark note colours.
LINK_COLORS = {
    "web":    ("#1a73e8", "#8ab4f8"),   # http/https — familiar blue
    "folder": ("#b35900", "#f5b167"),   # local folders — warm amber
    "file":   ("#7b1fa2", "#d7a8f0"),   # local files — violet
}


def link_color(kind: str, dark: bool) -> str:
    """Colour for a link of `kind` on a light or dark note. Unknown kinds fall
    back to the web pair."""
    light, dk = LINK_COLORS.get(kind, LINK_COLORS["web"])
    return dk if dark else light


BORDER_MODES = ("off", "always", "auto")

# A note at/above this relative luminance is "light" enough to warrant an outer
# border in auto mode. SEPARATE from LIGHT_INK_THRESHOLD on purpose: the border
# question ("does this note risk blending into a light background?") is not the
# auto-contrast question ("is the note too dark for dark text?"). Starts at the
# same value; raise it later to restrict the border to genuinely pale notes
# without touching auto-contrast.
BORDER_LIGHT_THRESHOLD = 0.18


def coerce_border_mode(value) -> str:
    """Normalise a persisted border setting to a known mode. Migrates the old
    bool (True->'always', False->'off') and falls back to 'off' for anything
    unrecognised."""
    if value is True:
        return "always"
    if value is False:
        return "off"
    return value if value in BORDER_MODES else "off"


def border_visible(mode: str, base: QColor) -> bool:
    """Whether a note of colour `base` draws its outer border under `mode`:
    'always' -> yes; 'auto' -> only when the note is light (luminance >=
    BORDER_LIGHT_THRESHOLD); 'off' or any unknown mode -> no."""
    if mode == "always":
        return True
    if mode == "auto":
        return _rel_luminance(base) >= BORDER_LIGHT_THRESHOLD
    return False


def effective_note_color(color_light: str, color_dark: str, dark: bool) -> str:
    """The fill a note actually shows for the active chrome theme: the dark slot
    (or the dark default if unset) in dark mode, the light slot otherwise. Shared
    by StickyNote and the Manager so both render the same colour."""
    if dark:
        return color_dark or "#2b2b30"
    return color_light or "#fff59d"


def note_ink(base: QColor, auto: bool = True) -> Ink:
    """Ink set for a note of colour `base`. Conservative: only clearly-dark
    notes flip to the light-ink set; the whole middle/light band keeps dark ink.
    `header`/`border` are derived from `base` (darker on light notes, lighter on
    dark ones) so the header stays visible either way. Alpha is preserved.

    `auto=False` disables the flip entirely — every note keeps the fixed dark ink
    and darker header/border (the app's look before auto-contrast); used when the
    user turns the auto-contrast setting off."""
    # Code blocks render as a DARK, SATURATED version of the note's own hue (the
    # "mockup look"): light-blue note → navy block, yellow → dark amber, pink →
    # deep maroon, and so on. Keep the note's hue, amplify the pastel's faint
    # saturation into a rich colour, and force a low lightness so light text
    # always reads. Opaque, so it looks like a solid box.
    code_box = _code_box(base)
    code_text = QColor("#ececec")
    code_inline = _code_inline_bg(code_box, code_text)
    # Inline code stays a SUBTLE, NEUTRAL translucent tint (from the ink set): a
    # low-alpha hue tint just washed out to grey, so it wasn't worth the colour —
    # inline is meant to be quiet ("this is code"), the block carries the colour.
    if auto and _rel_luminance(base) < LIGHT_INK_THRESHOLD:
        # Dark note: LIGHTEN the grip — darker(180) went darker-than-dark and
        # vanished, the same reason text/icons flip to light ink here. Blend
        # toward white (not lighter(), which leaves a pure-black note black).
        return replace(LIGHT_INK, header=base.lighter(118), border=base.lighter(135),
                       grip=_blend(base, QColor("#ffffff"), 0.42), dark=True,
                       code_bg=code_box, code_fg=code_text, code_inline_bg=code_inline)
    return replace(DARK_INK, header=base.darker(112), border=base.darker(128),
                   grip=base.darker(180),   # light note (or auto off): classic look
                   code_bg=code_box, code_fg=code_text, code_inline_bg=code_inline)


def fmt_btn_style(ink: Ink, extra: str = "") -> str:
    """Toolbar formatting button (B/I/U/S/bullet/check/font ▲▼)."""
    tail = f"\n    QPushButton {{ {extra} }}" if extra else ""
    return f"""
    QPushButton {{
        background: transparent; border: none; border-radius: 3px;
        color: {ink.ink}; font-size: 15px; padding: 0;
    }}
    QPushButton:hover   {{ color: {ink.ink_hover}; background: {ink.hover_bg}; }}
    QPushButton:checked {{ color: {ink.ink_active}; background: {ink.active_bg}; }}{tail}
    """


def size_label_style(ink: Ink) -> str:
    return f"""
    QPushButton {{ color: {ink.ink}; font-size: 13px; background: transparent;
        border: none; border-radius: 3px; }}
    QPushButton:hover {{ background: {ink.hover_bg}; color: {ink.ink_hover}; }}
    """


def sep_style(ink: Ink) -> str:
    return f"color: {ink.separator};"


def header_btn_style(ink: Ink, fs: int = 14) -> str:
    return f"""
    QPushButton {{
        background: transparent; border: none; border-radius: 4px;
        font-size: {fs}px; color: {ink.ink_dim}; padding: 0;
    }}
    QPushButton:hover   {{ background: {ink.hover_bg}; color: {ink.ink_active}; }}
    QPushButton:pressed {{ background: {ink.active_bg}; }}
    """


def family_btn_style(ink: Ink) -> str:
    return f"""
    QPushButton {{
        background: transparent; border: none; border-radius: 3px;
        font-size: 11px; color: {ink.ink_dim}; padding: 0 2px;
    }}
    QPushButton:hover {{ background: {ink.hover_bg}; }}
    """


def close_btn_style(ink: Ink) -> str:
    """Close X — idle follows ink, but keeps its red destructive hover."""
    return f"""
    QPushButton {{
        background: transparent; border: none; border-radius: 4px;
        font-size: 17px; color: {ink.ink_dim}; padding: 0;
    }}
    QPushButton:hover   {{ background: #e53935; color: white; }}
    QPushButton:pressed {{ background: #b71c1c; color: white; }}
    """


def progress_label_style(ink: Ink) -> str:
    return f"QLabel {{ color: {ink.ink_dim}; font-size: 12px; padding: 0 4px; }}"


def text_color_btn_style(ink: Ink, glyph_color: str) -> str:
    """The 'A' button — glyph shows the text colour to be applied (user's
    choice); only the hover background follows the note's ink."""
    return f"""
    QPushButton {{
        background: transparent; border: none; border-radius: 3px;
        color: {glyph_color}; font-weight: bold; font-size: 16px; padding: 0;
    }}
    QPushButton:hover {{ background: {ink.hover_bg}; }}
    """


def settings_dialog_style(check_icon: str = "") -> str:
    """Root stylesheet for the Settings dialog. Themes inputs (spin boxes, combo
    boxes) so their text stays readable on the dark window, and — only in dark
    mode — gives checkbox indicators a visible border + accent-filled checked
    state with a white tick (`check_icon` = path to a checkmark PNG). Styled in
    BOTH themes so the indicator never inherits the native (system-themed) look —
    with the app in light theme but GNOME set to a dark system theme, Qt paints
    the native checkbox from the dark system palette (a solid black box); an
    explicit surface background keeps it correct regardless of the system theme."""
    tick = f"image: url({check_icon});" if check_icon else ""
    base = f"""
        QDialog {{ background: {UI.WINDOW_BG}; }}
        QSpinBox, QDateEdit, QTimeEdit {{ font-size: 14px; background: {UI.SURFACE}; color: {UI.TEXT};
            border: 1px solid {UI.BORDER}; border-radius: 6px; padding: 4px 8px; }}
        QSpinBox:focus, QDateEdit:focus, QTimeEdit:focus {{ border: 1px solid {UI.ACCENT}; }}
        /* Styling the box disables Qt's native sub-controls, so the up/down
           buttons + arrows must be re-specified or they vanish (same reason the
           reminder dialog does this). NO min-height: that inflates the box
           (min-height is content height, so Qt adds padding+border on top → a
           34px box that the buttons can't fill, leaving a mid gap). At natural
           height (~31px with font 14 / padding 4), 15px halves tile it — no gap,
           no overflow. Matches the reminder dialog. Verified by rendering. */
        QSpinBox::up-button, QDateEdit::up-button, QTimeEdit::up-button {{
            subcontrol-origin: border; subcontrol-position: top right;
            width: 22px; height: 15px; }}
        QSpinBox::down-button, QDateEdit::down-button, QTimeEdit::down-button {{
            subcontrol-origin: border; subcontrol-position: bottom right;
            width: 22px; height: 15px; }}
        QSpinBox::up-arrow, QDateEdit::up-arrow, QTimeEdit::up-arrow {{ width: 13px; height: 13px; }}
        QSpinBox::down-arrow, QDateEdit::down-arrow, QTimeEdit::down-arrow {{ width: 13px; height: 13px; }}
        QComboBox {{ font-size: 14px; background: {UI.SURFACE}; color: {UI.TEXT};
            border: 1px solid {UI.BORDER}; border-radius: 6px; padding: 4px 8px; }}
        QComboBox QAbstractItemView {{ background: {UI.SURFACE}; color: {UI.TEXT};
            selection-background-color: {UI.ACCENT}; selection-color: #ffffff; }}
        QCheckBox::indicator {{ width: 16px; height: 16px; border: 1px solid {UI.TEXT_MUTED};
            border-radius: 4px; background: {UI.SURFACE}; }}
        QCheckBox::indicator:hover {{ border-color: {UI.ACCENT}; }}
        QCheckBox::indicator:checked {{ background: {UI.ACCENT}; border-color: {UI.ACCENT}; {tick} }}
    """ + message_box_style()   # confirmations raised from Settings inherit this
    return base


def message_box_style() -> str:
    """QSS for QMessageBox, meant to be APPENDED to the root sheet of any themed
    window that can parent one (Manager, Settings, Backups).

    Qt style sheets cascade into child windows, so a message box parented to a
    themed window already inherits its dark background — but not a text colour,
    leaving the label and the native buttons at the palette default (black) and
    all but invisible on dark. Stating both here fixes every box parented to
    that window at once, including ones raised from other modules."""
    return f"""
        QMessageBox {{ background: {UI.WINDOW_BG}; }}
        QMessageBox QLabel {{ background: transparent; color: {UI.TEXT}; font-size: 13px; }}
        QMessageBox QPushButton {{
            background: {UI.NEUTRAL_BG}; color: {UI.TEXT};
            border: 1px solid {UI.BORDER}; border-radius: 6px;
            padding: 6px 16px; font-size: 13px; font-weight: 500; min-width: 72px;
        }}
        QMessageBox QPushButton:hover {{ background: {UI.NEUTRAL_HOVER}; }}
        QMessageBox QPushButton:pressed {{ background: {UI.NEUTRAL_PRESS}; }}
        QMessageBox QPushButton:default {{
            background: {UI.ACCENT}; color: #ffffff; border-color: {UI.ACCENT};
        }}
        QMessageBox QPushButton:default:hover {{ background: {UI.ACCENT_HOVER}; }}
    """


def menu_style() -> str:
    """QSS for popup menus (note context menu, colour picker, tray menu), themed
    live from the current chrome palette."""
    return f"""
        QMenu {{
            background: {UI.SURFACE}; color: {UI.TEXT};
            border: 1px solid {UI.BORDER}; border-radius: 6px; padding: 4px;
        }}
        QMenu::item {{ padding: 5px 22px 5px 12px; border-radius: 4px; }}
        QMenu::item:selected {{ background: {UI.ACCENT}; color: #ffffff; }}
        QMenu::separator {{ height: 1px; background: {UI.BORDER}; margin: 4px 6px; }}
        QMenu::icon {{ padding-left: 6px; }}
    """


def text_edit_style(ink: Ink) -> str:
    return f"""
    QTextEdit {{
        background-color: transparent; border: none; padding: 11px 11px 10px;
        color: {ink.text}; selection-background-color: {ink.selection_bg};
    }}
    """
