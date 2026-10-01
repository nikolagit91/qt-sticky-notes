"""The StickyNote widget — a single draggable, editable, frameless note window."""

import uuid
import datetime
import os

from PyQt6.QtWidgets import (
    QAbstractButton,
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QPushButton,
    QLabel, QFrame, QSizePolicy, QLineEdit, QColorDialog, QMessageBox,
    QMenu, QSizeGrip, QDialog, QSpinBox, QFontDialog, QListWidget,
    QFileDialog, QDateTimeEdit,
)
from PyQt6.QtCore import (
    Qt, QTimer, QRectF, QSize, QPropertyAnimation, QEasingCurve, QDateTime, QEvent,
)
from PyQt6.QtGui import (
    QIcon, QColor, QPainter, QPixmap, QPen, QBrush, QCursor, QFont,
    QPainterPath, QTextListFormat, QTextCharFormat, QTextBlockFormat, QTextCursor,
    QTextFormat, QShortcut, QKeySequence,
)

from .config import DATA_FILE, TRASH_FILE, SETTINGS_FILE, APP_VERSION, ARCHIVE_LIMIT
from .icons import (
    _SVG_LOCKED, _SVG_UNLOCKED, _SVG_PIN, _SVG_TOOLBAR, _SVG_BELL,
    _make_lock_icon, _set_btn_icon, _HAS_SVG,
)
from .theme import (
    UI, HEADER_BTN_STYLE, CLOSE_BTN_STYLE, TEXT_COLOR_BTN_STYLE,
    make_header_btn, _btn_primary, _btn_secondary,
    note_ink, effective_note_color, fmt_btn_style, size_label_style, sep_style,
    header_btn_style, family_btn_style, close_btn_style, progress_label_style,
    text_color_btn_style, text_edit_style, menu_style, border_visible,
)
from .widgets import (NoteTextEdit, NoteHeader, CHECK_EMPTY, CHECK_DONE,
                      LIST_INDENT_WIDTH)
from .note_dialogs import NoteDialogsMixin
from .note_model import NoteData
from . import export
from . import x11
from . import snap as snaplib
from .i18n import tr


# Consistent typography for the note's own dialogs (reminder, rename) so they
# match the rest of the app's 13px dialogs instead of inheriting the larger
# point-sized note font.
class StickyNote(NoteDialogsMixin, QWidget):

    NOTE_COLORS = {
        "Yellow":  "#fff59d",
        "Pink":    "#FCE4EC",
        "Blue":    "#E3F2FD",
        "Green":   "#E8F5E9",
        "Orange":  "#FFF3E0",
        "Purple":  "#F3E5F5",
        "Peach":   "#FFE0B2",
        "Cyan":    "#E0F7FA",
    }

    # Modern, muted dark fills offered by the picker while the app is in dark
    # mode. All dark enough that auto-contrast gives them light ink. Existing
    # notes keep their stored colour; only the picker + new-note default change.
    DARK_NOTE_COLORS = {
        "Charcoal": "#2b2b30",
        "Graphite": "#34383f",
        "Slate":    "#2c3542",
        "Teal":     "#1f3638",
        "Forest":   "#273630",
        "Wine":     "#3b2a31",
        "Plum":     "#322a3f",
        "Umber":    "#3a3129",
    }

    TEXT_COLORS = [
        "#000000", "#434343", "#666666", "#999999",
        "#e53935", "#e67c13", "#f9a825", "#2e7d32",
        "#1565c0", "#6a1b9a", "#ad1457", "#00838f",
        "#ffffff", "#fce4ec", "#e8f5e9", "#e3f2fd",
    ]

    def __init__(self, app_ref: "StickyNotesApp", note_id: str = None, data: dict = None):
        super().__init__()
        self.app_ref      = app_ref
        self.note_id      = note_id or str(uuid.uuid4())
        # Parse the persisted record once through the model (single source of
        # truth for the schema + legacy fallbacks). _raw is kept only for the
        # one place that must distinguish "key absent" from "value is default":
        # the favorites migration below.
        _raw = data or {}
        d = NoteData.from_dict(_raw)
        self.locked       = False
        self._pinned      = d.pinned
        self._pin_time    = d.pin_time  # must be set before _build_ui
        # Favorite drives "float to top of the Manager list"; Pin is now purely
        # desktop always-on-top. One-time migration: notes saved before
        # favorites existed have no "favorite" key, so an already-pinned note
        # becomes a favorite (keeping the top-of-list spot Pin used to give it),
        # carrying pin_time over as fav_time so the order is unchanged.
        if "favorite" in _raw:
            self._favorite = d.favorite
            self._fav_time = d.fav_time
        else:
            self._favorite = self._pinned
            self._fav_time = self._pin_time
        self._hidden      = d.hidden     # user hid it (eye/X); persists across restarts
        self._reminder    = d.reminder   # epoch seconds, or None
        self._title       = d.title      # custom name; "" = auto (first line)
        self._color_light = "#fff59d"
        self._color_dark  = ""
        self.color        = "#fff59d"   # effective (recomputed from the slots on load)
        self._qcolor_base   = QColor(self.color)
        self._qcolor_header = self._qcolor_base.darker(112)
        self._qcolor_border = self._qcolor_base.darker(128)
        self._qcolor_grip   = self._qcolor_base.darker(180)   # overwritten by _apply_ink
        self._initializing = True
        self._clean_mode = False        # global auto-hide-chrome mode (set via _set_clean_mode)
        self._chrome_revealed = True     # is the header currently shown?
        self._toolbar_pref = True        # user's toolbar choice, remembered across clean mode
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)

        # Header SVG-icon fill — retinted per note colour by _apply_ink; starts at
        # the legacy dark so icons look right before the first _apply_ink.
        self._icon_fill = "#494c4e"
        # Cache lock icons — fromTheme is expensive, no need to call every refresh
        self._icon_locked   = _make_lock_icon(_SVG_LOCKED, fill=self._icon_fill)
        self._icon_unlocked = _make_lock_icon(_SVG_UNLOCKED, fill=self._icon_fill)
        self._icon_pinned   = _make_lock_icon(_SVG_PIN, fill=self._icon_fill)
        self._save_timer.timeout.connect(self.app_ref.save_notes)

        # Debounce timer for snap-on-release: while a drag/resize is in progress
        # moveEvent/resizeEvent fire repeatedly and keep restarting this; ~150 ms
        # after motion stops it snaps the note into place.
        self._snap_timer = QTimer(self)
        self._snap_timer.setSingleShot(True)
        self._snap_timer.timeout.connect(self._apply_snap)

        self._build_ui()

        if data:
            self.text_edit.blockSignals(True)
            content      = d.content
            content_type = d.content_type
            if content_type == "html":
                self.text_edit.setHtml(content)
            elif content.strip().startswith("<"):
                self.text_edit.setHtml(content)   # legacy fallback
            else:
                self.text_edit.setPlainText(content)
            self.text_edit.normalize_checkboxes()   # keep boxes neutral after reload
            self.text_edit.blockSignals(False)

            self._color_light = d.color
            self._color_dark  = d.color_dark
            self.color        = self._effective_color()
            self.locked    = d.locked
            self._font_size = d.font_size
            self.font_size_label.setText(str(self._font_size))

            saved_family = d.font_family
            if saved_family:
                self._current_font_family = saved_family
                self.btn_font_family.setText(saved_family.split()[0][:6])

            geo = d.geometry
            if geo and len(geo) == 4:
                self.setGeometry(*geo)

            self._apply_color()
            self._apply_state()

        self._initializing = False   # restore complete, events can save now
        self._refresh_reminder_ui()  # show the bell if a reminder was restored
        self._refresh_window_title()
        self._update_check_progress()  # show the badge if a loaded note has boxes

        # Detach BEFORE the window is ever mapped. The debug logs proved that
        # stripping WM_CLIENT_LEADER / WM_TRANSIENT_FOR AFTER the note is shown is
        # useless: Mutter fixes a window's group membership at MAP time (when Qt
        # still has client_leader = the shared leader window) and ignores our
        # later property changes. Forcing the native X window to exist now (winId)
        # without mapping it lets us clear those properties while it's still
        # unmapped, so Mutter reads a clean, standalone window when show() maps it.
        self.winId()            # realize the native window without mapping it
        self._detach_group()
        self._apply_skip_taskbar()   # hide from taskbar/Alt-Tab BEFORE first map

        # A note must stay passive when its window is merely activated (login,
        # or another app closing) — otherwise Qt auto-focuses the first tabbable
        # child and a caret/ring appears with no user intent. The editor is
        # already ClickFocus; make every chrome button NoFocus too, so NO child
        # is an auto-focus target. Buttons remain fully mouse-operable; focus
        # lands only on an explicit click or setFocus (see create_new_note).
        for _btn in self.findChildren(QAbstractButton):
            _btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        # Start in clean mode if the app-wide setting is on (no-op when off).
        self._set_clean_mode(getattr(self.app_ref, "_clean_mode", False))

    # ── UI construction ───────────────────────────────────────────────────────
    def _build_ui(self):
        # Notes are frameless Qt.Window (normal top-levels). On the user's Qt 6.4 +
        # Mutter, Qt.Tool (utility) windows got grouped and pinning one dragged the
        # whole group up; Qt.Window stacks each note independently and fixes that.
        # Being a normal window it would show in the taskbar / Alt-Tab, so
        # _apply_skip_taskbar hides it there (what Qt.Tool used to do for free).
        # Pin (always-on-top) is NOT a Qt flag here — it's applied via EWMH
        # _NET_WM_STATE_ABOVE (see _apply_pin_above). Qt's WindowStaysOnTopHint
        # recreates the native window (flicker + drops skip-taskbar → dock dot);
        # the EWMH message leaves the window intact, so a pinned note stays out of
        # the dock. Notes therefore never carry WindowStaysOnTopHint.
        flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMinimumSize(240, 168)
        self.resize(440, 300)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Header ─────────────────────────────────────────────────
        self.header = NoteHeader(self)
        self.header.setObjectName("NoteHeader")
        self.header.setFixedHeight(38)

        hl = QHBoxLayout(self.header)
        hl.setContentsMargins(6, 4, 6, 4)
        hl.setSpacing(3)

        # Left group: [+] [lock] [pin]
        self.btn_add  = make_header_btn("+", tr("New Note"),      font_size=24, w=26, h=26)
        self.btn_lock = QPushButton()
        self.btn_lock.setFixedSize(26, 26)
        self.btn_lock.setToolTip(tr("Lock / Unlock"))
        self.btn_lock.setStyleSheet(HEADER_BTN_STYLE.format(fs=14))

        self.btn_pin = QPushButton()
        self.btn_pin.setFixedSize(26, 26)
        self.btn_pin.setToolTip(tr("Always on Top"))
        self.btn_pin.setStyleSheet(HEADER_BTN_STYLE.format(fs=13))

        # Reminder bell — only shown while a reminder is set (see _refresh_reminder_ui)
        self.btn_bell = QPushButton()
        self.btn_bell.setFixedSize(26, 26)
        self.btn_bell.setToolTip(tr("Reminder"))
        self.btn_bell.setStyleSheet(HEADER_BTN_STYLE.format(fs=13))
        self.btn_bell.setVisible(False)

        # Right group: [⊟] [∨] [≡] [✕]
        self.btn_toolbar_toggle = make_header_btn("", tr("Toggle Toolbar"), font_size=14, w=26, h=26)
        _set_btn_icon(self.btn_toolbar_toggle, _SVG_TOOLBAR, 16, "Aa", fill=self._icon_fill)
        self.btn_menu  = make_header_btn("≡", tr("Note Options"),  font_size=21, w=26, h=26)
        self.btn_close = QPushButton("✕")
        self.btn_close.setFixedSize(26, 26)
        self.btn_close.setToolTip(tr("Hide Note"))
        self.btn_close.setStyleSheet(CLOSE_BTN_STYLE)

        self.btn_add.clicked.connect(lambda: self.app_ref.create_new_note())
        self.btn_lock.clicked.connect(lambda: self.toggle_lock())
        self.btn_pin.clicked.connect(self._toggle_pin)
        self.btn_bell.clicked.connect(self._open_reminder_dialog)
        self.btn_toolbar_toggle.clicked.connect(lambda: self._toggle_toolbar())
        self.btn_menu.clicked.connect(self._open_note_menu)
        self.btn_close.clicked.connect(self._hide_note)

        # Checklist progress (e.g. "2/5") — shown only when the note has boxes.
        self.check_progress = QLabel("")
        self.check_progress.setToolTip(tr("Checklist progress (done / total)"))
        self.check_progress.setStyleSheet(
            f"QLabel {{ color: {UI.TEXT_MUTED}; font-size: 12px; padding: 0 4px; }}")
        self.check_progress.setVisible(False)

        hl.addWidget(self.btn_add)
        hl.addWidget(self.btn_lock)
        hl.addWidget(self.btn_pin)
        hl.addWidget(self.btn_bell)
        hl.addStretch()
        hl.addWidget(self.check_progress)
        hl.addWidget(self.btn_toolbar_toggle)
        hl.addWidget(self.btn_menu)
        hl.addWidget(self.btn_close)

        self.header.setMouseTracking(True)

        root.addWidget(self.header)

        # ── Formatting toolbar ───────────────────────────────────────
        self.toolbar = QWidget()
        self.toolbar.setFixedHeight(32)
        tb_layout = QHBoxLayout(self.toolbar)
        tb_layout.setContentsMargins(8, 0, 8, 0)
        tb_layout.setSpacing(2)

        def make_fmt_btn(text, tooltip):
            btn = QPushButton(text)
            btn.setFixedSize(28, 26)
            btn.setCheckable(True)
            btn.setToolTip(tooltip)
            return btn   # styled by _apply_ink()

        self.btn_bold      = make_fmt_btn("B",  tr("Bold (Ctrl+B)"))
        self.btn_italic    = make_fmt_btn("I",  tr("Italic (Ctrl+I)"))
        self.btn_underline = make_fmt_btn("U",  tr("Underline (Ctrl+U)"))
        self.btn_strike    = make_fmt_btn("S",  tr("Strikethrough (Ctrl+S)"))
        self.btn_bullet    = make_fmt_btn("•≡", tr("Bullet list"))
        self.btn_check     = make_fmt_btn("☑", tr("Checklist — Tab to indent, drag a box or Alt+↑/↓ to reorder"))
        self.btn_check.setCheckable(False)
        self.btn_code = make_fmt_btn("{ }", tr("Code block"))
        self.btn_code.setVisible(getattr(self.app_ref, "_code_blocks", False))
        self.btn_inline_code = make_fmt_btn("<>", tr("Inline code"))
        self.btn_inline_code.setVisible(getattr(self.app_ref, "_code_blocks", False))

        # (B/I/U/S visual decorations are applied in _apply_ink via `decos`.)

        # Font size controls — clickable number opens direct-entry popup
        self.font_size_label = QPushButton("13")
        self.font_size_label.setFixedSize(28, 26)
        self.font_size_label.setToolTip(tr("Click to set exact size"))
        self.font_size_label.clicked.connect(self._open_font_size_entry)   # styled by _apply_ink()

        self._font_size = 13

        self.btn_font_up   = make_fmt_btn("▲", tr("Increase font size"))
        self.btn_font_down = make_fmt_btn("▼", tr("Decrease font size"))
        self.btn_font_up.setCheckable(False)
        self.btn_font_down.setCheckable(False)
        self.btn_font_up.setFixedSize(20, 26)
        self.btn_font_down.setFixedSize(20, 26)

        # Separator helper
        def make_sep():
            sep = QFrame()
            sep.setFrameShape(QFrame.Shape.VLine)
            sep.setFixedWidth(1)
            return sep   # coloured by _apply_ink()

        self._sep1 = make_sep()
        self._sep2 = make_sep()
        self._sep3 = make_sep()

        self.btn_text_color = make_fmt_btn("A", tr("Text Colour"))
        self.btn_text_color.setCheckable(False)
        self._text_color = "#000000"   # styled by _apply_ink()

        # Font family button
        self._sep4 = make_sep()
        self.btn_font_family = QPushButton("Sans")
        self.btn_font_family.setFixedSize(46, 26)
        self.btn_font_family.setCheckable(False)
        self.btn_font_family.setToolTip(tr("Font family"))   # styled by _apply_ink()
        self._current_font_family = self.app_ref._default_font_family
        short = self._current_font_family.split()[0][:6]
        self.btn_font_family.setText(short)

        tb_layout.addWidget(self.btn_bold)
        tb_layout.addWidget(self.btn_italic)
        tb_layout.addWidget(self.btn_underline)
        tb_layout.addWidget(self.btn_strike)
        tb_layout.addWidget(self._sep1)
        tb_layout.addWidget(self.btn_bullet)
        tb_layout.addWidget(self.btn_check)
        tb_layout.addWidget(self.btn_code)
        tb_layout.addWidget(self.btn_inline_code)
        tb_layout.addWidget(self._sep2)
        tb_layout.addWidget(self.btn_text_color)
        tb_layout.addWidget(self._sep3)
        tb_layout.addWidget(self.btn_font_down)
        tb_layout.addWidget(self.font_size_label)
        tb_layout.addWidget(self.btn_font_up)
        tb_layout.addWidget(self._sep4)
        tb_layout.addWidget(self.btn_font_family)
        tb_layout.addStretch()

        self._toolbar_visible = True

        # Create animation once — reuse by changing start/end values each toggle.
        # valueChanged → self.update(): the note is translucent and paints its own
        # rounded body + border over the full w×h in paintEvent. As the chrome
        # collapses, the transparent, rectangular text edit expands over the freed
        # strip and clears it; without a full repaint each frame the note's border
        # there is never painted back, so it vanished on the top/sides while
        # remnants lingered at the bottom bar and in the rounded corners.
        self._toolbar_anim = QPropertyAnimation(self.toolbar, b"maximumHeight", self)
        self._toolbar_anim.setDuration(150)
        self._toolbar_anim.finished.connect(self._on_toolbar_anim_finished)
        self._toolbar_anim.valueChanged.connect(lambda *_: self.update())

        # Header collapse animation (mirrors the toolbar) for clean mode.
        self._header_anim = QPropertyAnimation(self.header, b"maximumHeight", self)
        self._header_anim.setDuration(150)
        self._header_anim.finished.connect(self._on_header_anim_finished)
        self._header_anim.valueChanged.connect(lambda *_: self.update())

        # Hide-debounce for clean mode: a real Leave starts it, any Enter/MouseMove
        # cancels it — so moving between the note's own child widgets doesn't hide
        # the chrome, only truly leaving the note does. (Event-based, because on
        # Wayland QCursor.pos() freezes once the pointer leaves our surfaces.)
        self._hide_debounce = QTimer(self)
        self._hide_debounce.setSingleShot(True)
        self._hide_debounce.setInterval(80)
        self._hide_debounce.timeout.connect(self._maybe_hide)

        # Reveal only after the cursor DWELLS in a thin strip at the very top edge
        # — so aiming at / clicking the first line of text (below the strip) never
        # pops the header out from under the cursor, and a fast overshoot to the
        # top doesn't reveal either.
        self._reveal_dwell = QTimer(self)
        self._reveal_dwell.setSingleShot(True)
        self._reveal_dwell.setInterval(60)
        self._reveal_dwell.timeout.connect(self._reveal_chrome)

        # Connect formatting actions
        self.btn_bold.clicked.connect(lambda: self._fmt_bold())
        self.btn_italic.clicked.connect(lambda: self._fmt_italic())
        self.btn_underline.clicked.connect(lambda: self._fmt_underline())
        self.btn_strike.clicked.connect(lambda: self._fmt_strike())
        self.btn_bullet.clicked.connect(lambda: self._open_bullet_picker())
        self.btn_check.clicked.connect(lambda: self._toggle_checklist())
        self.btn_code.clicked.connect(lambda: self._toggle_code_block())
        self.btn_inline_code.clicked.connect(lambda: self._toggle_inline_code())
        self.btn_text_color.clicked.connect(lambda: self._open_text_color_picker())
        self.btn_font_family.clicked.connect(lambda: self._open_font_picker())
        self.btn_font_up.clicked.connect(lambda: self._change_font_size(+1))
        self.btn_font_down.clicked.connect(lambda: self._change_font_size(-1))

        root.addWidget(self.toolbar)

        # ── Text area ───────────────────────────────────────────────
        self.text_edit = NoteTextEdit()
        # No stylesheet font-size (the old `font-size:16px` was PIXEL-based, the
        # root of the pixel-vs-point conflicts). The document default font then
        # falls back to the application font, which _apply_base_font sets to a
        # POINT-based 13pt — so unformatted text, the caret, the toolbar size box
        # and the serialized HTML all agree in points. We deliberately do NOT tie
        # the default to the live "default size for new notes" setting here: that
        # would retroactively resize EXISTING notes whenever the setting changes.
        # New notes get that setting applied by create_new_note instead.
        self.text_edit.setPlaceholderText(tr("Write your note here…"))
        # Bullet lists indent by (level × indentWidth); shrink it from Qt's default
        # 40 so bullets don't sit far in (checklists get a matching base inset).
        self.text_edit.document().setIndentWidth(LIST_INDENT_WIDTH)
        self.text_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.text_edit.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        # No horizontal scrollbar either — long lines (code or a long URL) wrap
        # like the rest of the note instead of showing a horizontal scroll strip.
        self.text_edit.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.text_edit.checkbox_text_color = self._text_color
        self.text_edit.note_bg_color = self.color
        self.text_edit.textChanged.connect(lambda: self._save_timer.start(600))
        self.text_edit.textChanged.connect(self._on_text_changed)
        self.text_edit.textChanged.connect(self._update_check_progress)

        # Connect toolbar state updates AFTER text_edit is created
        self.text_edit.cursorPositionChanged.connect(self._update_toolbar_state)
        self.text_edit.selectionChanged.connect(self._update_toolbar_state)
        self.text_edit.list_exited.connect(self._update_toolbar_state)

        # ── Keyboard shortcuts (Ctrl+B/I/U/S, Ctrl+M inline code) ───────────
        self.text_edit._fmt_shortcuts = {
            Qt.Key.Key_B: self._fmt_bold,
            Qt.Key.Key_I: self._fmt_italic,
            Qt.Key.Key_U: self._fmt_underline,
            Qt.Key.Key_S: self._fmt_strike,
            # Ctrl+M inline code — gated on _code_blocks here (the <> button is
            # hidden when off; the shared _toggle_inline_code handler stays
            # ungated so it can't break other callers).
            Qt.Key.Key_M: self._inline_code_shortcut,
        }

        root.addWidget(self.text_edit)

        # ── Bottom bar (holds size grip) ────────────────────────────
        self.bottom_bar = QWidget()
        self.bottom_bar.setFixedHeight(17)
        bb_layout = QHBoxLayout(self.bottom_bar)
        bb_layout.setContentsMargins(0, 0, 0, 0)
        bb_layout.addStretch()

        self._grip = QSizeGrip(self)
        self._grip.setFixedSize(24, 24)
        bb_layout.addWidget(self._grip)
        root.addWidget(self.bottom_bar)

        # Static transparent stylesheets — set once, never change
        self.header.setStyleSheet("QFrame#NoteHeader { background: transparent; }")
        self.header.setAutoFillBackground(False)
        self.toolbar.setStyleSheet("background: transparent;")
        self.toolbar.setAutoFillBackground(False)
        self.bottom_bar.setStyleSheet("background: transparent;")
        self.bottom_bar.setAutoFillBackground(False)

        # ── Note-level keyboard shortcuts (fire even with the cursor in the
        # text editor via WidgetWithChildrenShortcut) ───────────────────────
        from . import shortcuts as _sc
        wc = Qt.ShortcutContext.WidgetWithChildrenShortcut
        self._sc_duplicate = QShortcut(QKeySequence(_sc.DUPLICATE), self)
        self._sc_duplicate.setContext(wc)
        self._sc_duplicate.activated.connect(self._copy_note)
        self._sc_export = QShortcut(QKeySequence(_sc.EXPORT), self)
        self._sc_export.setContext(wc)
        self._sc_export.activated.connect(self._open_export_menu)
        self._sc_trash = QShortcut(QKeySequence(_sc.TRASH), self)
        self._sc_trash.setContext(wc)
        self._sc_trash.activated.connect(self._move_to_trash)
        self._sc_help = QShortcut(QKeySequence("F1"), self)
        self._sc_help.setContext(wc)
        self._sc_help.activated.connect(self.app_ref.show_shortcuts)
        # Note-level commands that were previously mouse-only. Each is a QShortcut
        # (not a _fmt_shortcuts entry) so it fires with the cursor in the text OR
        # the header focused, matching Ctrl+D/E/W above. Ctrl+Shift+M can't live in
        # _fmt_shortcuts at all (that path is pure-Ctrl only).
        self._sc_rename = QShortcut(QKeySequence("F2"), self)
        self._sc_rename.setContext(wc)
        self._sc_rename.activated.connect(self._open_rename_dialog)   # anchored on the note
        self._sc_pin = QShortcut(QKeySequence("Ctrl+P"), self)
        self._sc_pin.setContext(wc)
        self._sc_pin.activated.connect(self._toggle_pin)
        self._sc_lock = QShortcut(QKeySequence("Ctrl+L"), self)
        self._sc_lock.setContext(wc)
        self._sc_lock.activated.connect(lambda: self.toggle_lock())
        # Font size: ± relative to each run. Ctrl++ (i.e. Ctrl+Shift+=) aliases
        # Ctrl+= so the "grow" key works with or without Shift on a US layout.
        self._sc_font_up = QShortcut(QKeySequence("Ctrl+="), self)
        self._sc_font_up.setContext(wc)
        self._sc_font_up.activated.connect(lambda: self._change_font_size(+1))
        self._sc_font_up2 = QShortcut(QKeySequence("Ctrl++"), self)
        self._sc_font_up2.setContext(wc)
        self._sc_font_up2.activated.connect(lambda: self._change_font_size(+1))
        self._sc_font_down = QShortcut(QKeySequence("Ctrl+-"), self)
        self._sc_font_down.setContext(wc)
        self._sc_font_down.activated.connect(lambda: self._change_font_size(-1))
        # Code block — gated on the code-blocks setting, like Ctrl+M inline.
        self._sc_code_block = QShortcut(QKeySequence("Ctrl+Shift+M"), self)
        self._sc_code_block.setContext(wc)
        self._sc_code_block.activated.connect(self._code_block_shortcut)

        self._apply_color()
        self._apply_state()
        _set_btn_icon(self.btn_toolbar_toggle, _SVG_TOOLBAR, 16, "Aa", fill=self._icon_fill)

    # ── Colour ────────────────────────────────────────────────────────────────
    def _bg_alpha(self) -> int:
        """Alpha (0–255) for the note's painted background, from the app-wide
        'Background opacity' setting (a percentage, default 100). Only the paper
        fill is made translucent — the text is drawn by the transparent QTextEdit
        on top, so its glyphs stay fully opaque and crisp."""
        pct = getattr(self.app_ref, "_note_opacity", 100)
        return max(0, min(255, round(pct * 255 / 100)))

    def _apply_ink(self):
        """Recolour all text-based note chrome + the default typed-text colour so
        they stay readable against the current note colour (light ink on a dark
        note, today's dark ink otherwise). Idempotent; called from _apply_color.

        SVG-icon header buttons (lock/pin/bell/toolbar-toggle) are NOT handled
        here — their colour lives inside the icon, not QSS — and are left as-is
        for a follow-up. Text the user explicitly coloured keeps its own char
        format; only the QTextEdit default text colour is set here."""
        ink = note_ink(self._qcolor_base,
                       auto=getattr(self.app_ref, "_auto_contrast", True))
        self._qcolor_header = ink.header
        self._qcolor_border = ink.border
        self._qcolor_grip = ink.grip
        self._icon_fill = ink.icon

        self.text_edit.setStyleSheet(text_edit_style(ink))

        # Checklist boxes/text carry an explicit colour (an anchor, so they'd
        # otherwise be link-blue), so unlike normal text they don't follow the
        # QTextEdit default. Point them at the ink's text colour and recolour any
        # existing default-coloured ones, so boxes stay visible on dark notes.
        old_box = self.text_edit.checkbox_text_color
        self.text_edit.checkbox_text_color = ink.text
        self.text_edit.recolor_checklist(old_box, ink.text)
        # Links carry an explicit colour, so they don't follow the QTextEdit
        # default either — repoint them at the light/dark variant for this note
        # (fixed colours were unreadable on dark fills).
        self.text_edit.link_dark = ink.dark
        self.text_edit.recolor_links()
        self.text_edit.code_bg_color = ink.code_bg
        self.text_edit.code_fg_color = ink.code_fg
        self.text_edit.code_revert_family = self._current_font_family
        self.text_edit.normalize_code_blocks()
        # Inline code stays a subtle translucent overlay (a few characters read
        # fine with the note's own ink); only the multi-line BLOCK gets the dark
        # box + light text. inline_bg is a stronger version of the block overlay.
        self.text_edit.inline_bg_color = QColor(ink.inline_bg)
        # Inline code inside a code block sits on the box, not the paper: it gets
        # its own overlay derived from the box (see theme._code_inline_bg).
        self.text_edit.code_inline_bg_color = QColor(ink.code_inline_bg)
        self.text_edit.normalize_inline_code()

        decos = {
            self.btn_bold:      "font-weight: bold;",
            self.btn_italic:    "font-style: italic;",
            self.btn_underline: "text-decoration: underline;",
            self.btn_strike:    "text-decoration: line-through;",
        }
        for b in (self.btn_bold, self.btn_italic, self.btn_underline,
                  self.btn_strike, self.btn_bullet, self.btn_check, self.btn_code,
                  self.btn_inline_code, self.btn_font_up, self.btn_font_down):
            b.setStyleSheet(fmt_btn_style(ink, decos.get(b, "")))

        self.font_size_label.setStyleSheet(size_label_style(ink))
        for s in (self._sep1, self._sep2, self._sep3, self._sep4):
            s.setStyleSheet(sep_style(ink))
        self.btn_font_family.setStyleSheet(family_btn_style(ink))
        self.btn_text_color.setStyleSheet(text_color_btn_style(ink, self._text_color))
        self.check_progress.setStyleSheet(progress_label_style(ink))

        # Text-glyph header buttons (keep their individual font sizes).
        self.btn_add.setStyleSheet(header_btn_style(ink, 24))
        self.btn_menu.setStyleSheet(header_btn_style(ink, 21))
        self.btn_close.setStyleSheet(close_btn_style(ink))

        # SVG-icon header buttons — match their hover/press to the ink (the icon
        # glyph is retinted below). The toolbar toggle keeps its dim overlay when
        # the toolbar is hidden. Pin is styled by _refresh_pin_ui (it also carries
        # the persistent pinned-background overlay) so it isn't set here.
        for b in (self.btn_lock, self.btn_bell):
            b.setStyleSheet(header_btn_style(ink, 14))
        tt_style = header_btn_style(ink, 14)
        if not getattr(self, "_toolbar_visible", True):
            tt_style += "QPushButton { color: rgba(85,85,85,100); }"
        self.btn_toolbar_toggle.setStyleSheet(tt_style)

        self._retint_header_icons()
        self._refresh_pin_ui()   # pin icon + ink-aware hover/pinned background
        self.update()

    def _retint_header_icons(self):
        """Recolour the header's SVG icons (lock/pin/bell/toolbar-toggle) to the
        note's ink so they stay visible on dark notes. Icon colour lives inside
        the SVG (QSS can't touch it), so we re-render with `self._icon_fill`. Only
        the icon is re-applied — no state side effects — so this is safe to call
        on every colour change (unlike the full _refresh_* methods)."""
        if not _HAS_SVG:
            return
        fill = self._icon_fill
        self._icon_locked   = _make_lock_icon(_SVG_LOCKED, fill=fill)
        self._icon_unlocked = _make_lock_icon(_SVG_UNLOCKED, fill=fill)
        self._icon_pinned   = _make_lock_icon(_SVG_PIN, fill=fill)
        self.btn_lock.setIcon(self._icon_locked if self.locked else self._icon_unlocked)
        # The pin glyph is state-independent (pinned-ness shows via background),
        # so always re-apply it — otherwise an unpinned note's pin icon never
        # follows the colour and stays dark on a dark note until first clicked.
        self.btn_pin.setIcon(self._icon_pinned)
        if self._reminder is not None:
            self.btn_bell.setIcon(_make_lock_icon(_SVG_BELL, 15, fill=fill))
        if not self.locked and getattr(self, "_toolbar_visible", True):
            self.btn_toolbar_toggle.setIcon(_make_lock_icon(_SVG_TOOLBAR, 16, fill=fill))

    def _reapply_theme(self):
        """Re-resolve this note's fill for the app's current theme and re-ink —
        used on a live theme change (no restart). A repaint/re-ink only: the
        document, selection, and caret are untouched."""
        self.color = self._effective_color()
        self._apply_color()

    def _apply_opacity(self):
        """Re-derive only what the background-opacity setting can actually change.

        Opacity alters the note's ALPHA and nothing else. The ink set is chosen
        from the fill's luminance, which ignores alpha (`_rel_luminance`), and
        every ink field is a fixed constant — so the ~15 stylesheets and the
        three document-wide recolour sweeps that `_apply_ink` runs would all
        recompute values identical to the ones already in place. Only the three
        derived colours (header / border / grip) carry the new alpha.

        Worth its own path because the opacity slider emits on EVERY step of a
        drag: routing that through `_apply_color` measured ~139 ms per step at
        50 notes, i.e. a slider that could not be dragged."""
        base = QColor(self.color)
        base.setAlpha(self._bg_alpha())
        self._qcolor_base = base
        ink = note_ink(base, auto=getattr(self.app_ref, "_auto_contrast", True))
        self._qcolor_header = ink.header
        self._qcolor_border = ink.border
        self._qcolor_grip   = ink.grip
        self.text_edit.paper_alpha = self._bg_alpha()   # code box follows the note's opacity
        self.update()
        self.text_edit.viewport().update()              # repaint the code box at the new alpha

    def _apply_color(self):
        base = QColor(self.color)
        base.setAlpha(self._bg_alpha())          # header/border inherit the alpha
        self._qcolor_base = base
        self.text_edit.note_bg_color = self.color   # drag insertion line contrast
        self.text_edit.paper_alpha = self._bg_alpha()   # code box follows the note's opacity
        self._apply_ink()                           # header/border/text/chrome + repaint

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        base   = self._qcolor_base
        header = self._qcolor_header
        border = self._qcolor_border
        w, h   = self.width(), self.height()
        # When the header is collapsed/hidden (clean mode), draw no header band —
        # else the painted stripe + separator would linger with no buttons on it.
        hh     = self.header.height() if self.header.isVisible() else 0
        r      = 10.0

        # 1. Body fill — full widget size so no width mismatch with children
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(base))
        painter.drawRoundedRect(QRectF(0, 0, w, h), r, r)

        # 2. Header stripe — same full-width path, clipped to header height
        painter.save()
        painter.setClipRect(0, 0, w, hh)
        painter.setBrush(QBrush(header))
        painter.drawRoundedRect(QRectF(0, 0, w, h), r, r)
        painter.restore()

        # 3. Header separator line (skip when the header is collapsed away)
        if hh > 0:
            painter.setPen(QPen(border, 1))
            painter.drawLine(0, hh, w, hh)

        # 4. Outer border — OFF by default (borderless card); opt-in via
        # Settings → Note. Its own pen, independent of the header separator above,
        # so it draws in every chrome state (the separator's pen only ran when the
        # header was shown). Inset 0.5px to land exactly on the 1px boundary.
        if border_visible(getattr(self.app_ref, "_note_border", "off"), self._qcolor_base):
            painter.setPen(QPen(border, 1))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(QRectF(0.5, 0.5, w - 1, h - 1), r, r)

        # 5. Resize grip indicator — three diagonal lines in bottom-right corner.
        # Ink-aware (lighter on dark notes) so it doesn't vanish like a fixed
        # base.darker() did on a dark fill.
        pen = QPen(self._qcolor_grip, 1.5)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        margin = 7
        for i in range(3):
            offset = margin + i * 5
            painter.drawLine(w - margin, h - offset,
                             w - offset, h - margin)

        painter.end()

    def _effective_color(self) -> str:
        """The fill actually shown, per the app's chrome theme (delegates to the
        shared theme helper so the Manager renders the same colour)."""
        dark = getattr(self.app_ref, "_theme", "light") == "dark"
        return effective_note_color(self._color_light, self._color_dark, dark)

    def _set_color(self, hex_color: str):
        # Write only the slot for the active theme so the other mode's colour is
        # preserved across theme switches.
        if getattr(self.app_ref, "_theme", "light") == "dark":
            self._color_dark = hex_color
        else:
            self._color_light = hex_color
        self.color = self._effective_color()
        self._apply_color()
        self.app_ref.save_notes()

    # ── Lock ──────────────────────────────────────────────────────────────────
    def toggle_lock(self, forced: bool = None):
        self.locked = (not self.locked) if forced is None else forced
        self._apply_state()
        self.app_ref.save_notes()
        self.app_ref._refresh_manager()

    def _apply_state(self):
        """Central state update — always call this instead of individual refresh methods."""
        self._refresh_lock_ui()
        self._refresh_pin_ui()
        self._update_toolbar_state()

    def _refresh_lock_ui(self):
        locked = self.locked

        icon = self._icon_locked if locked else self._icon_unlocked
        if _HAS_SVG:
            self.btn_lock.setIcon(icon)
            self.btn_lock.setIconSize(QSize(16, 16))
            self.btn_lock.setText("")
        else:
            self.btn_lock.setIcon(QIcon())
            self.btn_lock.setText("🔒" if locked else "🔓")

        self.text_edit.setReadOnly(locked)
        self._grip.setVisible(not locked)
        if locked and self._toolbar_visible:
            self._toggle_toolbar(force_hide=True)
        elif (not locked and not self._toolbar_visible
                and self._chrome_revealed and self._toolbar_pref):
            # Restore the toolbar ONLY when it is actually wanted. Restoring it
            # unconditionally trampled two states: in clean mode it dropped the
            # bar below a collapsed header (where it hung until the next full
            # hover cycle, since only _maybe_hide closes it), and anywhere it
            # resurrected a toolbar the user had manually put away. Same rule
            # _reveal_chrome uses: the chrome must be shown AND the user must
            # want the bar.
            self._toggle_toolbar(force_hide=False)

        self.btn_add.setEnabled(True)
        self.btn_toolbar_toggle.setEnabled(not locked)
        if locked and _HAS_SVG:
            # Disabled buttons get Qt's auto-faded icon — override with our own
            # gray so it matches the toolbar-hidden state exactly
            icon_gray = _make_lock_icon(_SVG_TOOLBAR, 16, fill="#6e6e6e")
            disabled_icon = QIcon()
            px = icon_gray.pixmap(16, 16)
            disabled_icon.addPixmap(px, QIcon.Mode.Normal)
            disabled_icon.addPixmap(px, QIcon.Mode.Disabled)
            self.btn_toolbar_toggle.setIcon(disabled_icon)
            self.btn_toolbar_toggle.setIconSize(QSize(16, 16))
        self.btn_close.setEnabled(not locked)

    def _toggle_pin(self):
        self._pinned = not self._pinned
        if self._pinned:
            self._pin_time = datetime.datetime.now().timestamp()
        else:
            self._pin_time = 0.0
        # Apply always-on-top via EWMH _NET_WM_STATE_ABOVE (x11.set_above) instead
        # of Qt's WindowStaysOnTopHint. The Qt flag recreates the native window
        # (visible flicker + drops skip-taskbar → dock dot); the EWMH client
        # message leaves the window untouched, so there's no flicker and the note
        # stays hidden from the dock, pinned or not.
        self._apply_pin_above()
        self._refresh_pin_ui()
        self.app_ref.save_notes()
        # Safety net: Mutter can propagate _NET_WM_STATE_ABOVE across windows it
        # considers grouped, dragging siblings up with the pinned note. Re-detach
        # every note (each its own group) so only this one rises. Deferred so it
        # runs after Mutter has applied the ABOVE; the later pass catches a slow WM.
        QTimer.singleShot(0,   self.app_ref._reconcile_pin_stacking)
        QTimer.singleShot(250, self.app_ref._reconcile_pin_stacking)
        # Keep the Manager's per-row pin button in sync when pinning from the
        # note itself (mirrors toggle_favorite). Pin no longer affects the list
        # order, so this just rebuilds rows with the current pin state.
        self.app_ref._refresh_manager()

    def _surface_for_reminder(self):
        """Bring this note to the very front when its reminder fires — above even
        an always-on-top application — via EWMH _NET_WM_STATE_ABOVE (no native
        window recreation, so no flicker). Drop the ABOVE a moment later unless the
        note is pinned (a pinned note keeps it)."""
        self._hidden = False   # a fired reminder surfaces the note → no longer hidden
        try:
            if self.isMinimized():
                self.showNormal()
            else:
                self.show()
        except RuntimeError:
            return
        self.app_ref._ensure_on_screen(self)
        x11.set_above(int(self.winId()), True)   # surface above other on-top windows
        self.raise_()
        self.activateWindow()

        def _drop_on_top():
            # Once surfaced, stop forcing on-top unless the note is actually pinned.
            try:
                if not self._pinned:
                    x11.set_above(int(self.winId()), False)
            except RuntimeError:
                pass

        QTimer.singleShot(1500, _drop_on_top)

    def toggle_favorite(self):
        """Toggle favorite — controls 'float to top' in the Manager list only.
        No desktop effect (that's Pin). Most-recently-favorited sorts highest."""
        self._favorite = not self._favorite
        self._fav_time = datetime.datetime.now().timestamp() if self._favorite else 0.0
        self.app_ref.save_notes()
        self.app_ref._refresh_manager()

    def _refresh_pin_ui(self):
        if _HAS_SVG:
            self.btn_pin.setIcon(self._icon_pinned)
            self.btn_pin.setIconSize(QSize(16, 16))
            self.btn_pin.setText("")
        else:
            self.btn_pin.setIcon(QIcon())
            self.btn_pin.setText("📌")
        # Follow the note's ink (light on dark notes). The pinned state is a
        # persistent ink-tinted background so it — and the hover — stay visible
        # on any note colour, instead of the old fixed dark rgba(0,0,0,…) overlay.
        ink = note_ink(getattr(self, "_qcolor_base", QColor(self.color)),
                       auto=getattr(self.app_ref, "_auto_contrast", True))
        style = header_btn_style(ink, 13)
        if self._pinned:
            style += f"QPushButton {{ background: {ink.active_bg}; }}"
        self.btn_pin.setStyleSheet(style)

    # ── Reminders ──────────────────────────────────────────────────────────────
    def set_reminder(self, when):
        """Set (epoch seconds) or clear (None) this note's reminder, refresh the
        bell, and persist. Called by the dialog and by the scheduler on fire/snooze."""
        self._reminder = when
        self._refresh_reminder_ui()
        self.app_ref.save_notes()

    def reminder_preview(self) -> str:
        """First non-empty line of the note, for the notification body."""
        for line in self.text_edit.toPlainText().splitlines():
            if line.strip():
                return line.strip()[:80]
        return tr("(empty note)")

    # ── Title / name ───────────────────────────────────────────────────────────
    def _first_line(self) -> str:
        """First non-empty line of the body — the automatic title."""
        for line in self.text_edit.toPlainText().splitlines():
            s = line.strip()
            if s:
                # Drop a leading checklist box so the title reads "Buy milk",
                # not "☐ Buy milk".
                if s[:1] in (CHECK_EMPTY, CHECK_DONE):
                    s = s[1:].strip()
                if s:
                    return s
        return ""

    def display_title(self) -> str:
        """Effective name: custom title if set, else first line, else placeholder."""
        return self._title.strip() or self._first_line() or tr("Untitled")

    def _refresh_window_title(self):
        """Window/taskbar title from the note name, capped so an extremely long
        first line doesn't make an absurd title (the WM truncates anyway, but a
        hard cap keeps it sane). The full name still lives in the note body."""
        t = self.display_title()
        if len(t) > 60:
            t = t[:59].rstrip() + "…"
        self.setWindowTitle(t)

    def set_title(self, text: str):
        """Set a custom name ("" reverts to the automatic first-line title),
        update the window title, persist, and refresh the manager if open."""
        self._title = (text or "").strip()
        self._refresh_window_title()
        self.app_ref.save_notes()
        self.app_ref._refresh_manager()


    def _refresh_reminder_ui(self):
        active = self._reminder is not None
        self.btn_bell.setVisible(active)
        if not active:
            return
        if _HAS_SVG:
            self.btn_bell.setIcon(_make_lock_icon(_SVG_BELL, 15, fill=self._icon_fill))
            self.btn_bell.setIconSize(QSize(15, 15))
            self.btn_bell.setText("")
        else:
            self.btn_bell.setIcon(QIcon())
            self.btn_bell.setText("🔔")
        when = datetime.datetime.fromtimestamp(self._reminder)
        self.btn_bell.setToolTip(tr("Reminder: ") + when.strftime("%a %b %d, %H:%M"))


    def _on_text_changed(self):
        # During construction/restore the document is transiently empty; running
        # the empty-note cleanup then would stamp a default typing font that
        # _update_toolbar_state writes back into _current_font_family, clobbering
        # the note's saved family. The cleanup is only for USER-emptied notes.
        if self._initializing:
            return
        if self.text_edit.document().isEmpty():
            cursor = self.text_edit.textCursor()
            if self.text_edit._is_code_block(cursor.block()):
                if self.text_edit._pending_empty_code:
                    # A freshly-toggled empty code block ({ } then type) — keep it.
                    self.text_edit._pending_empty_code = False
                    return
                # Otherwise the user deleted all the code (Ctrl+A + Delete): fall
                # through to reset the block to a clean plain line, clearing the
                # code background so it isn't left as a lingering monospace block.
            self.text_edit.blockSignals(True)
            lst = cursor.currentList()
            if lst:
                lst.remove(cursor.block())   # fully detach from QTextList
            # Reset the block format, the block char format, and the typing
            # (current char) format to the note's clean point-based default.
            # Pasting rich web text then Select All + Delete leaves the remaining
            # empty block carrying that content's format: the block format
            # (indent / margins / alignment) offsets the caret and first typed
            # chars; the block CHAR format keeps the deleted text's size —
            # importantly its PIXEL size (web text is pixel-sized) — so the empty
            # line's caret stays as tall as the deleted text. Now that the base
            # font is point-based, assigning an explicit point size to the block
            # char format gives a normal caret (with the old pixel base it
            # collapsed the line), so we can reset all three for a truly fresh
            # empty note.
            neutral = QTextCharFormat()
            neutral.setFontPointSize(self.app_ref._default_font_size)
            # Also restore the note's family so a lingering monospace (e.g. after
            # deleting a code block) doesn't stick to the empty line's typing.
            neutral.setFontFamilies([self.text_edit.code_revert_family
                                     or self.app_ref._default_font_family])
            # Merge these resets INTO the delete that just emptied the doc (one
            # undo step), so Ctrl+Z brings the text back instead of only undoing
            # the format reset. Order matters: reset the block CHAR format (which
            # clears the retained pixel size and restores a normal caret height)
            # BEFORE the block format. Doing the block format first collapses the
            # empty line's height.
            cursor.joinPreviousEditBlock()
            cursor.setBlockCharFormat(neutral)
            cursor.setBlockFormat(QTextBlockFormat())
            cursor.endEditBlock()
            self.text_edit.setCurrentCharFormat(neutral)
            self.text_edit.blockSignals(False)
            self.text_edit.setPlaceholderText(tr("Write your note here…"))
            self.btn_bullet.setChecked(False)
            self._update_toolbar_state()   # sync toolbar (bold off, size back to default)

    def _selection_all(self, prop: str) -> bool:
        """Return True if every character in the selection has the given property active."""
        cursor = self.text_edit.textCursor()

        if not cursor.hasSelection():
            fmt = self.text_edit.currentCharFormat()
            return {
                "bold":      fmt.fontWeight() >= QFont.Weight.DemiBold,
                "italic":    fmt.fontItalic(),
                "strike":    fmt.fontStrikeOut(),
                "underline": fmt.fontUnderline(),
            }.get(prop, False)

        # charFormat() returns format of the character BEFORE the cursor position,
        # so we set the cursor to pos+1 to check the character at pos.
        doc = self.text_edit.document()
        c   = QTextCursor(doc)
        for pos in range(cursor.selectionStart(), cursor.selectionEnd()):
            c.setPosition(pos + 1)
            fmt = c.charFormat()
            if prop == "bold"      and fmt.fontWeight() < QFont.Weight.DemiBold: return False
            if prop == "italic"    and not fmt.fontItalic():                      return False
            if prop == "strike"    and not fmt.fontStrikeOut():                   return False
            if prop == "underline" and not fmt.fontUnderline():                   return False
        return True

    QUICK_FONTS = [
        ("Ubuntu",           "Ubuntu"),
        ("Ubuntu Sans",      "Ubuntu Sans"),
        ("Noto Sans",        "Noto Sans"),
        ("Noto Serif",       "Noto Serif"),
        ("Liberation Sans",  "Liberation Sans"),
        ("DejaVu Sans",      "DejaVu Sans"),
        ("Courier New",      "Courier New"),
        ("Ubuntu Mono",      "Ubuntu Mono"),
    ]



    def _apply_font_family(self, family: str):
        self._current_font_family = family
        self.text_edit.code_revert_family = family
        short = family.split()[0][:6]
        self.btn_font_family.setText(short)
        self.text_edit.setFocus()
        cursor = self.text_edit.textCursor()
        fmt = QTextCharFormat()
        fmt.setFontFamilies([family])
        cursor.mergeCharFormat(fmt)
        self.text_edit.setTextCursor(cursor)


    def _apply_text_color(self, hex_color: str):
        self._text_color = hex_color
        self.text_edit.checkbox_text_color = hex_color
        self.btn_text_color.setStyleSheet(
            text_color_btn_style(note_ink(self._qcolor_base), hex_color))
        self.text_edit.setFocus()
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(hex_color))
        # Skip link characters — recolouring a link would strip the cue that
        # tells the user it IS a link, while it still opens on click.
        self.text_edit.merge_format_preserving_links(fmt)

    def _toggle_checklist(self):
        """Toolbar ☑ button: toggle checklist boxes on the current line/selection."""
        if self.locked:
            return
        self.text_edit.toggle_checklist()
        self._update_check_progress()

    def _toggle_code_block(self):
        if self.locked:
            return   # locked = read-only; the { } button is hidden then, guard the key too
        self.text_edit.toggle_code_block()
        self._update_toolbar_state()

    def _code_block_shortcut(self):
        """Ctrl+Shift+M: toggle a code block, but only when code features are on
        (mirrors _inline_code_shortcut and the { } button's visibility gate)."""
        if getattr(self.app_ref, "_code_blocks", False):
            self._toggle_code_block()

    def _inline_code_shortcut(self):
        """Ctrl+M: toggle inline code, but only when code features are enabled
        (mirrors the <> button's visibility gate)."""
        if getattr(self.app_ref, "_code_blocks", False):
            self._toggle_inline_code()

    def _toggle_inline_code(self):
        self.text_edit.toggle_inline_code()
        # prefer_current so the button reflects the NEW typing format immediately
        # (else it reads the still-inline char to the left and stays highlighted
        # until you type a non-inline character).
        self._update_toolbar_state(prefer_current=True)

    def _update_check_progress(self):
        """Refresh the "done/total" badge; hidden when the note has no checkboxes."""
        done, total = self.text_edit.checklist_progress()
        if total:
            self.check_progress.setText(f"{done}/{total}")
            self.check_progress.setVisible(True)
        else:
            self.check_progress.setVisible(False)

    def _on_toolbar_anim_finished(self):
        tb_height = 32
        if not self._toolbar_visible:
            self.toolbar.setVisible(False)
            self.toolbar.setFixedHeight(tb_height)
        else:
            self.toolbar.setFixedHeight(tb_height)
            self._clear_toolbar_hover()
        self.toolbar.setMinimumHeight(0)
        self.toolbar.setMaximumHeight(tb_height)
        self.update()   # settle the note's border after the bar lands (see valueChanged)

    def _clear_toolbar_hover(self):
        """Reset stale :hover on the toolbar buttons after the bar animates open.
        While the bar grows under the pointer, buttons receive HoverEnter but the
        matching HoverLeave can be dropped as their clip rect changes, leaving
        several stuck highlighted. Force a Leave so QSS re-evaluates; the button
        genuinely under the cursor re-lights on the next real mouse move."""
        from PyQt6.QtWidgets import QApplication
        for btn in self.toolbar.findChildren(QPushButton):
            btn.setAttribute(Qt.WidgetAttribute.WA_UnderMouse, False)
            QApplication.sendEvent(btn, QEvent(QEvent.Type.Leave))

    _HEADER_H = 38     # matches self.header.setFixedHeight(38)
    _REVEAL_EDGE = 10  # top strip that triggers a reveal; meets the text's 10px pad
                       # (if the first line pops the header, bump the text pad instead)

    def _on_header_anim_finished(self):
        hh = self._HEADER_H
        if not self._chrome_revealed:
            self.header.setVisible(False)
        self.header.setFixedHeight(hh)
        self.header.setMinimumHeight(0)
        self.header.setMaximumHeight(hh)
        self.update()   # settle the note's border after the header lands (see valueChanged)

    def _reveal_chrome(self):
        """Animate the header open and restore the toolbar to the user's choice."""
        self._reveal_dwell.stop()
        if self._chrome_revealed:
            return
        self._chrome_revealed = True
        self.header.setVisible(True)
        self._header_anim.stop()
        self._header_anim.setEasingCurve(QEasingCurve.Type.OutQuad)
        self._header_anim.setStartValue(0)
        self._header_anim.setEndValue(self._HEADER_H)
        self._header_anim.start()
        # A locked note is read-only — it has nothing to format, so reveal only
        # the header, never the toolbar (its buttons are disabled/hidden anyway).
        if self._toolbar_pref and not self._toolbar_visible and not self.locked:
            self._toggle_toolbar(force_hide=False)

    def _hide_chrome(self):
        """Animate the header shut and collapse the toolbar with it."""
        if not self._chrome_revealed:
            return
        self._chrome_revealed = False
        self._header_anim.stop()
        self._header_anim.setEasingCurve(QEasingCurve.Type.InQuad)
        self._header_anim.setStartValue(self._HEADER_H)
        self._header_anim.setEndValue(0)
        self._header_anim.start()
        if self._toolbar_visible:
            self._toggle_toolbar(force_hide=True)

    def _set_clean_mode(self, enabled: bool):
        """Enter/leave clean mode. On: collapse the chrome and watch for hover
        via an event filter. Off: stop watching and restore the header (and
        toolbar) to normal.

        Deliberately does NOT touch `_toolbar_pref`. It used to capture it from
        the toolbar's current visibility, on the assumption that visibility ==
        the user's choice — but the bar may have just been forced down by
        something else (a lock, or an earlier clean-mode collapse). That poisoned
        the preference to False for good, and `_reveal_chrome` then never brought
        the toolbar back for that note. `_toolbar_pref` is written in exactly one
        place: a MANUAL toggle in `_toggle_toolbar`, which is the only event that
        actually expresses what the user wants."""
        self._clean_mode = enabled
        if enabled:
            self._install_hover_filter(True)
            self._hide_chrome()
        else:
            self._hide_debounce.stop()
            self._reveal_dwell.stop()
            self._install_hover_filter(False)
            self._reveal_chrome()

    def _toggle_chrome_lock(self):
        """Double-click on the header: pin THIS note's chrome open, so a long
        editing session doesn't mean travelling to the top edge for every reveal.
        Double-click again to hand the note back to auto-hide.

        Locking is just leaving clean mode for this note — _set_clean_mode(False)
        already stops the timers, drops the hover filter and reveals the chrome,
        which is exactly what "stop auto-hiding" means. Only meaningful while the
        app-wide setting is on; with it off there is nothing to disable.

        Not persisted: a temporary editing aid, so a restart (or toggling the
        setting, which re-pushes it to every note) returns the note to clean mode.
        """
        if not getattr(self.app_ref, "_clean_mode", False):
            return
        self._set_clean_mode(not self._clean_mode)

    def _hover_widgets(self):
        """Widgets covering the note that must all report hover so the chrome
        doesn't hide while the pointer moves between them."""
        return [self, self.header, self.toolbar, self.text_edit,
                self.text_edit.viewport()]

    def _install_hover_filter(self, on: bool):
        for wgt in self._hover_widgets():
            if on:
                wgt.setMouseTracking(True)   # get MouseMove without a button held
                wgt.installEventFilter(self)
            else:
                wgt.removeEventFilter(self)

    def _chrome_zone_h(self):
        """Height of the currently shown chrome (header + toolbar if shown).
        While hidden, the reveal trigger is just the header strip."""
        if not self._chrome_revealed:
            return self._HEADER_H
        return self._HEADER_H + (32 if self._toolbar_visible else 0)

    def eventFilter(self, obj, event):
        if self._clean_mode:
            et = event.type()
            if et == QEvent.Type.Enter:
                self._hide_debounce.stop()
            elif et == QEvent.Type.Leave:
                self._reveal_dwell.stop()
                if not self._hide_debounce.isActive():
                    self._hide_debounce.start()   # truly left only if no Enter follows
            elif et == QEvent.Type.MouseMove:
                y = self.mapFromGlobal(event.globalPosition().toPoint()).y()
                if not self._chrome_revealed:
                    self._hide_debounce.stop()
                    # Reveal only after dwelling in the thin top edge — so aiming
                    # at the first line (below the edge) never pops the header.
                    if 0 <= y <= self._REVEAL_EDGE:
                        if not self._reveal_dwell.isActive():
                            self._reveal_dwell.start()
                    else:
                        self._reveal_dwell.stop()
                elif 0 <= y <= self._chrome_zone_h():
                    self._hide_debounce.stop()          # over the chrome → keep it
                elif not self._hide_debounce.isActive():
                    self._hide_debounce.start()          # dropped into the body → hide
            elif et == QEvent.Type.MouseButtonPress and obj in (
                    self.text_edit, self.text_edit.viewport()):
                # Clicking into the body = intent to write. Hide the chrome now
                # instead of waiting for a stray mouse move (the click moves focus
                # off the header, so _maybe_hide's focus guard lets it collapse).
                if self._chrome_revealed and not self._hide_debounce.isActive():
                    self._hide_debounce.start()
            elif et == QEvent.Type.WindowDeactivate and obj is self:
                # Clicking another window doesn't move the pointer off our surface
                # on Wayland (no Leave), so nothing collapsed the chrome. End any
                # keyboard-move and re-check; the popup/child guard in _maybe_hide
                # still keeps the chrome while a dialog spawned from the note runs.
                self.header.clearFocus()
                if self._chrome_revealed and not self._hide_debounce.isActive():
                    self._hide_debounce.start()
        return super().eventFilter(obj, event)

    def _maybe_hide(self):
        """Collapse the chrome unless a menu/dialog spawned from this note is
        open (clicking a toolbar/header control that opens a popup pulls the
        pointer onto the popup — don't treat that as leaving the note)."""
        from PyQt6.QtWidgets import QApplication
        # Outside clean mode the chrome is always shown, so hiding is never right
        # — including when this note's chrome is locked open by a header
        # double-click. _set_clean_mode already stops the debounce, so this is a
        # safety net against any late/queued fire rather than a live path.
        if not self._clean_mode:
            return
        # The header holds keyboard focus while the user arrow-moves the note.
        # Arrow keys shift the note out from under the stationary pointer, which
        # fires a Leave and would collapse the header — but hiding it steals the
        # focus and kills the arrow keys mid-move. Keep the chrome while focused;
        # the next hide check after the user clicks away will collapse it.
        if self.header.hasFocus():
            return
        if (QApplication.activePopupWidget() is not None
                or QApplication.activeModalWidget() is not None):
            self._hide_debounce.start()   # re-check once the popup closes
            return
        w = QApplication.activeWindow()
        if w is not None and w is not self:   # a CHILD dialog of this note is active?
            p = w.parent()
            while p is not None:
                if p is self:
                    self._hide_debounce.start()
                    return
                p = p.parent()
        self._hide_chrome()

    def _toggle_toolbar(self, force_hide: bool = None):
        if force_hide is None:
            self._toolbar_visible = not self._toolbar_visible
            # A manual toggle is the user's real choice — remember it so a later
            # clean-mode reveal restores THIS state, not the one captured when
            # clean mode was first entered. (Reveal/hide pass force_hide, so the
            # animated collapse/restore never clobbers the preference.)
            self._toolbar_pref = self._toolbar_visible
        else:
            self._toolbar_visible = not force_hide

        tb_height = 32
        self.toolbar.setVisible(True)

        self._toolbar_anim.stop()
        self._toolbar_anim.setEasingCurve(QEasingCurve.Type.InQuad if not self._toolbar_visible else QEasingCurve.Type.OutQuad)

        if not self._toolbar_visible:
            self._toolbar_anim.setStartValue(tb_height)
            self._toolbar_anim.setEndValue(0)
        else:
            self._toolbar_anim.setStartValue(0)
            self._toolbar_anim.setEndValue(tb_height)

        self._toolbar_anim.start()

        if self._toolbar_visible:
            if _HAS_SVG:
                self.btn_toolbar_toggle.setIcon(_make_lock_icon(_SVG_TOOLBAR, 16, fill=self._icon_fill))
                self.btn_toolbar_toggle.setIconSize(QSize(16, 16))
                self.btn_toolbar_toggle.setText("")
            else:
                self.btn_toolbar_toggle.setText("Aa")
            self.btn_toolbar_toggle.setStyleSheet(header_btn_style(note_ink(self._qcolor_base), 14))
        else:
            if _HAS_SVG:
                self.btn_toolbar_toggle.setIcon(_make_lock_icon(_SVG_TOOLBAR, 16, fill="#6e6e6e"))
                self.btn_toolbar_toggle.setIconSize(QSize(16, 16))
                self.btn_toolbar_toggle.setText("")
            else:
                self.btn_toolbar_toggle.setText("Aa")
            self.btn_toolbar_toggle.setStyleSheet(
                header_btn_style(note_ink(self._qcolor_base), 14) +
                "QPushButton { color: rgba(85,85,85,100); }"
            )

    def _fmt_underline(self):
        self.text_edit.setFocus()
        fmt = QTextCharFormat()
        fmt.setFontUnderline(not self._selection_all("underline"))
        # Skip link characters: a link's underline is one of the two cues that
        # mark it as a link (the other is its colour). See _apply_text_color.
        self.text_edit.merge_format_preserving_links(fmt)
        self._update_toolbar_state(prefer_current=True)

    def _fmt_bold(self):
        self.text_edit.setFocus()
        cursor = self.text_edit.textCursor()
        fmt = QTextCharFormat()
        fmt.setFontWeight(QFont.Weight.Normal if self._selection_all("bold") else QFont.Weight.Bold)
        cursor.mergeCharFormat(fmt)
        self.text_edit.setTextCursor(cursor)
        self._update_toolbar_state(prefer_current=True)

    def _fmt_italic(self):
        self.text_edit.setFocus()
        cursor = self.text_edit.textCursor()
        fmt = QTextCharFormat()
        fmt.setFontItalic(not self._selection_all("italic"))
        cursor.mergeCharFormat(fmt)
        self.text_edit.setTextCursor(cursor)
        self._update_toolbar_state(prefer_current=True)

    def _fmt_strike(self):
        self.text_edit.setFocus()
        cursor = self.text_edit.textCursor()
        fmt = QTextCharFormat()
        fmt.setFontStrikeOut(not self._selection_all("strike"))
        cursor.mergeCharFormat(fmt)
        self.text_edit.setTextCursor(cursor)
        self._update_toolbar_state(prefer_current=True)

    # Available bullet/list styles: (label, QTextListFormat.Style)
    BULLET_STYLES = [
        (tr("●  Disc"),        QTextListFormat.Style.ListDisc),
        (tr("▪  Square"),      QTextListFormat.Style.ListSquare),
        (tr("1.  Decimal"),    QTextListFormat.Style.ListDecimal),
        (tr("a.  Lower alpha"), QTextListFormat.Style.ListLowerAlpha),
        (tr("i.  Lower roman"), QTextListFormat.Style.ListLowerRoman),
    ]


    def _fmt_bullet(self, style=None):
        """Apply a list style, or remove the list when style is None."""
        try:
            cursor = self.text_edit.textCursor()
            start  = cursor.selectionStart()
            end    = cursor.selectionEnd()

            c = self.text_edit.textCursor()
            c.setPosition(start)
            currently_in_list = bool(c.currentList())

            cursor.beginEditBlock()
            if style is None:
                # Remove list — detach each block from QTextList
                c.setPosition(start)
                while True:
                    lst = c.currentList()
                    if lst:
                        lst.remove(c.block())
                    block_fmt = c.blockFormat()
                    block_fmt.setIndent(0)
                    c.setBlockFormat(block_fmt)
                    if c.block().position() + c.block().length() > end:
                        break
                    if not c.movePosition(c.MoveOperation.NextBlock):
                        break
                self.text_edit.setPlaceholderText(tr("Write your note here…"))
            else:
                fmt = QTextListFormat()
                fmt.setStyle(style)
                existing = c.currentList()
                if existing:
                    # Already in a list — create a nested sub-list at a deeper
                    # indent level with the chosen style, rather than restyling
                    # the whole existing list
                    existing_indent = existing.format().indent()
                    fmt.setIndent(existing_indent + 1)
                    cursor.createList(fmt)
                else:
                    was_empty = not self.text_edit.toPlainText()
                    if was_empty:
                        cursor.movePosition(cursor.MoveOperation.Start)
                        cursor.insertBlock()
                        cursor.movePosition(cursor.MoveOperation.Start)
                        cursor.createList(fmt)
                        char_fmt = QTextCharFormat()
                        char_fmt.setFontPointSize(self._font_size)
                        char_fmt.setFontFamilies([self._current_font_family])
                        cursor.mergeCharFormat(char_fmt)
                    else:
                        cursor.createList(fmt)
                self.text_edit.setPlaceholderText("")
            cursor.endEditBlock()

            self.text_edit.setTextCursor(cursor)
            self.text_edit.setFocus()
            self.btn_bullet.setChecked(style is not None)
        except Exception as e:
            print(f"[bullet] error: {e}")

    def _apply_font_size(self, size: int, cursor=None):
        """Set an ABSOLUTE point size on `cursor`'s selection (or on the typing
        format if it has none). Bullet/number markers on touched blocks scale to
        match; web PIXEL sizes are cleared so the point size takes effect.

        The caller MUST pass the cursor captured BEFORE the toolbar took focus:
        reading the live cursor here would miss the selection, because clicking a
        ▲▼ button or opening the size popup can collapse it — which is why a
        resize looked like it did nothing (it only changed the typing format)."""
        size = max(8, min(96, int(size)))
        if cursor is None:
            cursor = self.text_edit.textCursor()
        self._font_size = size
        self.font_size_label.setText(str(size))
        doc = self.text_edit.document()

        if not cursor.hasSelection():
            cf = self.text_edit.currentCharFormat()
            cf.setFontPointSize(size)
            cf.clearProperty(QTextFormat.Property.FontPixelSize)
            self.text_edit.setCurrentCharFormat(cf)
            self.text_edit.setFocus()
            return

        start, end = cursor.selectionStart(), cursor.selectionEnd()
        self._resize_selection(start, end, lambda _old: size)
        # Restore + keep the selection highlighted so the user can keep adjusting.
        keep = QTextCursor(doc)
        keep.setPosition(start)
        keep.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
        self.text_edit.setTextCursor(keep)
        self.text_edit.setFocus()

    def _change_font_size(self, delta: int):
        """▲▼ buttons: shift the size by ±delta RELATIVE to each run's OWN size.
        A mixed-size selection (e.g. a pasted heading + body) therefore keeps its
        relationships — everything grows/shrinks together instead of collapsing
        to one size (absolute ▲▼ made a selected 20pt heading jump to 14pt when
        the box read the body's 13). The size POPUP still sets an exact absolute
        size. Capture the cursor before this click can affect focus/selection."""
        if self.locked:
            return   # locked = read-only; the ▲▼ buttons are hidden then, guard the keys too
        cursor = self.text_edit.textCursor()
        doc = self.text_edit.document()

        if not cursor.hasSelection():
            cf = self.text_edit.currentCharFormat()
            new = max(8, min(96, self._effective_point_size(cf) + delta))
            cf.setFontPointSize(new)
            cf.clearProperty(QTextFormat.Property.FontPixelSize)
            self.text_edit.setCurrentCharFormat(cf)
            self._font_size = new
            self.font_size_label.setText(str(new))
            self.text_edit.setFocus()
            return

        start, end = cursor.selectionStart(), cursor.selectionEnd()
        self._resize_selection(start, end,
                               lambda old: max(8, min(96, old + delta)))
        keep = QTextCursor(doc)
        keep.setPosition(start)
        keep.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
        self.text_edit.setTextCursor(keep)
        self.text_edit.setFocus()
        self._update_toolbar_state()

    def _resize_selection(self, start, end, new_size_for):
        """Apply new font sizes across [start, end). `new_size_for(old_pt)`
        returns the new int point size for a run currently at `old_pt` (absolute
        resize ignores it; relative ▲▼ adds a delta).

        Iterates block by block over REAL characters only — the trailing block
        separator (the newline) is skipped, so a selection that spills into the
        next block never resizes that block's separator or its empty body. The
        block loop is bounded by the last selected character (end-1); a selection
        whose caret lands at the very start of the next row therefore leaves that
        row untouched. Each touched block's char format is scaled too, so list
        markers and empty-line caret height follow the text."""
        doc = self.text_edit.document()
        last = end - 1
        edit = QTextCursor(doc)
        edit.beginEditBlock()
        blk = doc.findBlock(start)
        while blk.isValid() and blk.position() <= last:
            b_start = blk.position()
            b_text_end = b_start + blk.length() - 1        # excludes separator
            pos = max(start, b_start)
            stop = min(end, b_text_end)
            while pos < stop:
                ch = QTextCursor(doc)
                ch.setPosition(pos)
                ch.setPosition(pos + 1, QTextCursor.MoveMode.KeepAnchor)
                f = ch.charFormat()
                f.setFontPointSize(new_size_for(self._effective_point_size(f)))
                f.clearProperty(QTextFormat.Property.FontPixelSize)
                ch.setCharFormat(f)
                pos += 1
            # Block char format (list markers / empty-line caret) for this block.
            bc = QTextCursor(doc)
            bc.setPosition(b_start)
            mf = bc.blockCharFormat()
            mf.setFontPointSize(new_size_for(self._effective_point_size(mf)))
            mf.clearProperty(QTextFormat.Property.FontPixelSize)
            bc.setBlockCharFormat(mf)
            blk = blk.next()
        edit.endEditBlock()

    def _effective_point_size(self, fmt) -> int:
        """Point size to show in the toolbar for a character format. Text pasted
        from the web is pixel-sized, so fmt.fontPointSize() reports 0 for it —
        which made the size box always fall back to 13 no matter which
        differently-sized sentence you clicked. Fall back to the pixel size
        converted to points (CSS 96 dpi) so the number tracks the real size."""
        pt = fmt.fontPointSize()
        if pt <= 0:
            px = fmt.font().pixelSize()
            if px > 0:
                pt = px * 72.0 / 96.0
        if pt <= 0:
            # No explicit size → the character renders at the document default.
            pt = self.text_edit.document().defaultFont().pointSizeF()
        return int(round(pt)) if pt > 0 else self._font_size

    def _update_toolbar_state(self, prefer_current=False):
        """Sync toolbar state (size, family, bold/italic/…) with the character
        format AT the cursor.

        Qt's currentCharFormat() reports the format that would be typed NEXT — at
        a boundary between two runs (e.g. a big word next to a small one) that can
        be unset or the wrong side, so clicking a differently-sized word wouldn't
        update the size box (it kept showing the last-applied size). To mirror what
        the user actually clicked into, probe the character to the LEFT of the
        caret when there's no selection; fall back to currentCharFormat() at the
        very start of the document or for a selection.

        `prefer_current=True` (used right after an explicit bold/italic/… toggle
        with no selection) forces currentCharFormat() — the format that will be
        TYPED NEXT — so the button flips IMMEDIATELY instead of only once you type
        the next character (the left-of-caret char is still the old run)."""
        cursor = self.text_edit.textCursor()
        if cursor.hasSelection():
            # Reflect the FIRST selected character. currentCharFormat() reads the
            # format AT the selection end, which for a line-select sits in the
            # empty next block — a phantom value; and the last selected position
            # can be a block separator (never resized) reading as the default.
            # The start of a selection is always a real character.
            s = cursor.selectionStart()
            probe = QTextCursor(cursor)
            probe.setPosition(s)
            probe.setPosition(s + 1, QTextCursor.MoveMode.KeepAnchor)
            fmt = probe.charFormat()
        elif (not prefer_current and cursor.position() > 0
              and cursor.position() != cursor.block().position()):
            # Probe the character to the LEFT — but not when the caret sits at the
            # very start of a block, where "left" is the previous block's trailing
            # separator (which shows that block's size, not this empty row's).
            probe = QTextCursor(cursor)
            probe.setPosition(cursor.position() - 1)
            probe.setPosition(cursor.position(), QTextCursor.MoveMode.KeepAnchor)
            fmt = probe.charFormat()
        else:
            fmt = self.text_edit.currentCharFormat()

        self.btn_bold.setChecked(fmt.fontWeight() >= QFont.Weight.DemiBold)
        self.btn_italic.setChecked(fmt.fontItalic())
        self.btn_underline.setChecked(fmt.fontUnderline())
        self.btn_strike.setChecked(fmt.fontStrikeOut())
        self.btn_bullet.setChecked(bool(cursor.currentList()))
        self.btn_code.setChecked(self.text_edit._is_code_block(cursor.block()))
        self.btn_inline_code.setChecked(self.text_edit._is_inline_code(fmt))
        size = self._effective_point_size(fmt)
        self.font_size_label.setText(str(size))
        # Reflect the cursor's font family on the family button too.
        family = fmt.fontFamilies()
        if family:
            self._current_font_family = family[0]
            self.btn_font_family.setText(family[0].split()[0][:6])

    # ── Note options menu ─────────────────────────────────────────────────────
    def _open_note_menu(self):
        menu = QMenu(self)
        menu.setStyleSheet(menu_style())

        color_act = menu.addAction(tr("Change Colour…"))
        color_act.triggered.connect(self._open_color_palette)

        copy_act = menu.addAction(tr("Copy Note"))
        copy_act.triggered.connect(self._copy_note)

        rename_act = menu.addAction(tr("Rename…"))
        rename_act.triggered.connect(self._open_rename_dialog)

        fav_act = menu.addAction(tr("Remove from Favorites") if self._favorite else tr("Add to Favorites"))
        fav_act.triggered.connect(self.toggle_favorite)

        if self._reminder is not None:
            when = datetime.datetime.fromtimestamp(self._reminder).strftime("%b %d, %H:%M")
            rem_act = menu.addAction(tr("Reminder: {} — change…").format(when))
        else:
            rem_act = menu.addAction(tr("Set reminder…"))
        rem_act.triggered.connect(self._open_reminder_dialog)

        export_menu = self._build_export_menu(menu)
        menu.addMenu(export_menu)

        menu.addSeparator()
        arch_act = menu.addAction(tr("Archive"))
        arch_act.triggered.connect(self._archive)
        del_act = menu.addAction(tr("Move to Trash"))
        del_act.triggered.connect(self._move_to_trash)

        menu.exec(QCursor.pos())

    def _copy_note(self):
        g = self.geometry()
        note = self.app_ref.create_new_note(
            content = self.text_edit.toHtml(),
            color      = self._color_light,
            color_dark = self._color_dark,
            width   = g.width(),
            height  = g.height(),
            origin  = self,
        )
        if note is None:
            return
        if self._pinned:
            note._toggle_pin()

    def _build_export_menu(self, parent) -> "QMenu":
        """Build the Export submenu (txt/odt/pdf). Shared by the context menu
        and the Ctrl+E shortcut so the format list lives in one place."""
        from PyQt6.QtWidgets import QMenu
        m = QMenu(tr("Export"), parent)
        m.setStyleSheet(menu_style())
        m.addAction(tr("Plain text (.txt)")).triggered.connect(lambda: self._export_as("txt"))
        m.addAction(tr("OpenDocument (.odt)")).triggered.connect(lambda: self._export_as("odt"))
        m.addAction(tr("PDF (.pdf)")).triggered.connect(lambda: self._export_as("pdf"))
        m.addAction(tr("Image (.png)")).triggered.connect(lambda: self._export_as("png"))
        return m

    def _open_export_menu(self):
        """Ctrl+E: pop the export format chooser at the cursor."""
        self._build_export_menu(self).exec(QCursor.pos())

    def _export_as(self, fmt: str):
        """Export this note to a plain-text, OpenDocument, or PDF file."""
        doc   = self.text_edit.document()
        plain = self.text_edit.toPlainText()
        base  = export.suggest_filename(plain)

        filters = {
            "txt": tr("Text files (*.txt)"),
            "odt": tr("OpenDocument (*.odt)"),
            "pdf": tr("PDF (*.pdf)"),
            "png": tr("PNG image (*.png)"),
        }
        default_path = os.path.join(os.path.expanduser("~"), f"{base}.{fmt}")
        path, _ = QFileDialog.getSaveFileName(self, tr("Export Note"), default_path, filters[fmt])
        self.app_ref._trim_memory()   # return file-dialog memory to the OS
        if not path:
            return
        if not os.path.splitext(path)[1]:
            path += f".{fmt}"          # append extension only if the user gave none

        try:
            if fmt == "pdf":
                export.to_pdf(doc, path, self.color)
            elif fmt == "png":
                export.render_note_png(self, path)
            elif fmt == "odt":
                export.to_odt(doc, path)
            else:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(export.to_plain_text(doc))
        except Exception as e:
            QMessageBox.warning(self, tr("Export Failed"), str(e))


    def _move_to_trash(self):
        """Move note to Trash (not permanently deleted)."""
        self.app_ref.move_note_to_trash(self.note_id)

    def _archive(self):
        """Archive this note (kept but closed; restorable from the Manager).
        Refused with a note if the Archive is already full."""
        if not self.app_ref.archive_note(self.note_id):
            QMessageBox.information(
                self, tr("Archive Full"),
                tr("Archive is full ({} notes).\nRemove something from the Archive first.").format(ARCHIVE_LIMIT))


    def get_data(self) -> dict:
        g       = self.geometry()
        html    = self.text_edit.toHtml()
        plain   = self.text_edit.toPlainText().strip()
        preview = plain[:40] + ("…" if len(plain) > 40 else "")
        return NoteData(
            id=self.note_id,
            content=html,
            content_type="html",
            preview=preview,
            title=self._title,
            display_title=self.display_title(),
            color=self._color_light,
            color_dark=self._color_dark,
            locked=self.locked,
            pinned=self._pinned,
            pin_time=self._pin_time,
            favorite=self._favorite,
            fav_time=self._fav_time,
            hidden=self._hidden,
            reminder=self._reminder,
            font_size=self._font_size,
            font_family=self._current_font_family,
            geometry=[g.x(), g.y(), g.width(), g.height()],
        ).to_dict()

    def set_hidden(self, hidden: bool):
        """Single source of truth for hide/show. Records the user's INTENT in
        self._hidden (persisted via get_data) — not the transient widget
        visibility, which also changes on minimize/teardown — so a hidden note
        stays hidden across restarts. Callers do the save/refresh."""
        self._hidden = hidden
        if hidden:
            self.hide()
        else:
            self.app_ref._bring_to_front(self)

    def _hide_note(self):
        self.set_hidden(True)
        self.app_ref.save_notes()
        self.app_ref._refresh_manager()

    # ── Events ────────────────────────────────────────────────────────────────
    def moveEvent(self, event):
        super().moveEvent(event)
        if not self._initializing:
            self._save_timer.start(400)
            if self.app_ref._snap_enabled():
                self._snap_timer.start(150)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if not self._initializing:
            self._save_timer.start(600)
            if self.app_ref._snap_enabled():
                self._snap_timer.start(150)

    def _apply_snap(self):
        """Snap this note's geometry once movement/resize has settled, per the
        app's snap toggles. Position snapping (grid and/or other-note edges) and
        size snapping are independent. Re-applying is idempotent — an already
        snapped note snaps to itself — so the setGeometry below won't loop."""
        app = self.app_ref
        use_grid  = getattr(app, "_snap_to_grid", False)
        use_notes = getattr(app, "_snap_to_notes", False)
        use_size  = getattr(app, "_snap_size", False)
        if self.locked or not (use_grid or use_notes or use_size):
            return
        grid = max(1, getattr(app, "_grid_size", 20))
        g = self.geometry()
        x, y, w, h = g.x(), g.y(), g.width(), g.height()
        nx, ny, nw, nh = x, y, w, h
        if use_size:
            nw, nh = snaplib.snap_size(w, h, grid)
        if use_grid or use_notes:
            others = [(o.x(), o.y(), o.width(), o.height())
                      for o in app.notes.values()
                      if o is not self and o.isVisible()]
            nx, ny = snaplib.snap_position(x, y, nw, nh, others, grid, use_grid, use_notes)
            # Screen-edge snap: a note's edge grabs the work-area edge when close.
            # Computed from the ORIGINAL position and applied per axis so it wins
            # over grid rounding at the boundary — otherwise grid rounding fights
            # the edge and the note visibly bounces off it (e.g. the GNOME top
            # panel makes availableGeometry().top() a non-grid value, so grid
            # snapping would push the note back down). Then a final clamp keeps
            # the note fully on the work area no matter what.
            scr = self.screen().availableGeometry()
            sx, sy, sw, sh = scr.left(), scr.top(), scr.width(), scr.height()
            ex, ey, x_hit, y_hit = snaplib.snap_to_edges(x, y, nw, nh, sx, sy, sw, sh)
            if x_hit:
                nx = ex
            if y_hit:
                ny = ey
            nx = max(sx, min(nx, sx + sw - nw))
            ny = max(sy, min(ny, sy + sh - nh))
        if (nx, ny, nw, nh) != (x, y, w, h):
            self.setGeometry(nx, ny, nw, nh)

    def _detach_group(self):
        """Give this note its own X11 window group so Mutter stops stacking it
        with the app's other windows. Best-effort; no-op off X11. Must run on show
        AND after every window-flag change — setFlags recreates the native window
        and re-attaches it to the shared group, so it has to be re-detached.
        Wrapped because it is also called deferred (QTimer), by when the note may
        already be gone."""
        try:
            x11.detach_window_group(int(self.winId()))
        except RuntimeError:
            pass

    def _apply_skip_taskbar(self):
        """Hide this note from the taskbar / dash / Alt-Tab (notes are normal
        Qt.Window top-levels now — Qt.Tool used to do this for free). Best-effort;
        no-op off X11. Most effective before the first map.

        ⚠️ INVARIANT: this REPLACES the whole `_NET_WM_STATE` property, so it
        WIPES `_NET_WM_STATE_ABOVE` — i.e. it silently unpins the note. Every
        caller must therefore run `_apply_pin_above()` AFTER it, which is what
        `__init__` and `_reassert_window_state` do. Do not call this on its own
        from a new code path without restoring the pin."""
        try:
            x11.set_skip_taskbar(int(self.winId()))
        except RuntimeError:
            pass

    def _apply_pin_above(self):
        """Apply the pin state via EWMH _NET_WM_STATE_ABOVE (add if pinned, remove
        if not). No native-window recreation → no flicker, and skip-taskbar is
        preserved so a pinned note stays out of the dock. Called on pin toggle and
        on every show (so a loaded-pinned note re-asserts ABOVE after mapping).
        Best-effort; no-op off X11."""
        try:
            x11.set_above(int(self.winId()), self._pinned)
        except RuntimeError:
            pass


    def changeEvent(self, event):
        # When the note stops being the active window (the user clicked away, or
        # focus moved to another app), drop whatever child held focus. Otherwise
        # Qt remembers the focused editor and RESTORES the caret every time the WM
        # later re-activates the note — e.g. another window closing hands focus
        # back — which is the "cursor keeps coming back after I clicked away" bug.
        # After this, re-activation shows a caret only on a fresh click. Editing
        # is unaffected: the window stays active while you type.
        if event.type() == QEvent.Type.ActivationChange and not self.isActiveWindow():
            fw = self.focusWidget()
            if fw is not None:
                fw.clearFocus()
        super().changeEvent(event)

    def showEvent(self, event):
        super().showEvent(event)
        # spontaneous() == the show came from the WINDOW MANAGER, not from us.
        self._reassert_window_state(spontaneous=event.spontaneous())

    def _reassert_window_state(self, spontaneous: bool):
        """Re-apply the window-level state a note needs after being mapped.

        Detach from Qt's shared X11 group (see _detach_group). The immediate
        call runs while the window is being mapped; the deferred one runs on the
        next event-loop pass, AFTER Qt/Mutter have finished mapping and
        (re)grouping — which is when the shared group tends to reappear. Doing
        both makes the detach actually stick. _apply_pin_above re-asserts the pin
        (EWMH ABOVE) after mapping — needed for a loaded-pinned note and after
        any re-show, since ABOVE lives on the window, not a Qt flag.

        SKIPPED ON A SPONTANEOUS SHOW. Measured on GNOME: switching workspaces
        makes Mutter unmap and re-map the notes, so this ran on every single
        workspace switch — six X11 operations per note — and the notes were
        reported jumping in front of other applications on the way back. All of
        this exists to re-assert state after WE map a window; on a WM-driven
        re-map the properties are still on the window, so the work is redundant
        and only risks a restack (changing WM_TRANSIENT_FOR on a mapped window,
        and REPLACE-writing _NET_WM_STATE, both make Mutter re-evaluate it).
        """
        if spontaneous:
            return
        self._detach_group()
        self._apply_skip_taskbar()
        self._apply_pin_above()
        QTimer.singleShot(0, self._detach_group)
        QTimer.singleShot(0, self._apply_skip_taskbar)
        QTimer.singleShot(0, self._apply_pin_above)

    def stop_timers(self):
        """Stop every timer and animation this note owns.

        Qt would destroy them anyway — all six are parented to the note — but
        `deleteLater()` is DEFERRED, and in that gap they keep firing and doing
        pointless work on a note that is on its way out (a snap recalculation,
        a chrome animation on a widget nobody will see again).

        Kept here, next to where the timers are created, so the list can't drift
        out of sync with them. It previously lived in app._close_note_widget and
        covered only two of the six, which read like a complete list and wasn't."""
        for t in (self._save_timer, self._snap_timer,
                  self._hide_debounce, self._reveal_dwell):
            if t is not None:
                t.stop()
        for a in (self._toolbar_anim, self._header_anim):
            if a is not None:
                a.stop()

    def closeEvent(self, event):
        # Break references and stop timers so the widget can be garbage-collected
        # promptly instead of lingering in a reference cycle (app_ref ↔ note)
        self.stop_timers()
        super().closeEvent(event)


