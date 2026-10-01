"""Note dialogs, extracted from note.py to keep that file focused (review #3 A4).

This is a mixin: StickyNote inherits it, so every method still operates on
`self` (the note) exactly as before — pure code relocation, no behaviour change.
All dependencies come from neutral modules (theme / i18n / PyQt6), so there is
no import cycle with note.py.
"""
import datetime

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QWidget,
    QLabel, QLineEdit, QDateTimeEdit, QPushButton, QFontDialog,
    QSpinBox, QFrame, QColorDialog, QDateEdit, QTimeEdit,
)
from PyQt6.QtCore import Qt, QDateTime, QDate, QTime
from PyQt6.QtGui import QFont, QTextCharFormat, QTextCursor, QColor

from .i18n import tr
from .theme import (
    UI, _btn_primary, _btn_secondary,
)

def _dialog_style() -> str:
    """Root style for the note's rename/reminder dialogs, read live from the
    current chrome palette (must be a function, not a frozen module constant).

    The inputs must NAME their colours rather than inherit them. These dialogs
    can be parented to a themed window (the Manager raises the rename dialog),
    whose root sheet cascades a dark background into them — while an unstyled
    QLineEdit keeps the palette's default black text, i.e. black on #1e1f22.
    Stating both here also makes the inputs match Settings' spin/combo boxes."""
    return (
        f"QDialog {{ background: {UI.WINDOW_BG}; }} "
        f"QLabel {{ background: transparent; font-size: 13px; color: {UI.TEXT}; }} "
        f"QLineEdit, QDateTimeEdit, QDateEdit, QTimeEdit, QSpinBox {{ "
        f"  font-size: 13px; background: {UI.SURFACE}; color: {UI.TEXT}; "
        f"  border: 1px solid {UI.BORDER}; border-radius: 6px; padding: 3px 6px; }} "
        f"QLineEdit:focus, QDateTimeEdit:focus, QDateEdit:focus, QTimeEdit:focus, "
        f"QSpinBox:focus {{ border: 1px solid {UI.ACCENT}; }}"
    )


class NoteDialogsMixin:
    """Rename and reminder dialogs for StickyNote."""

    def _open_rename_dialog(self, parent=None):
        """Rename this note. `parent` is where the dialog belongs on screen: the
        note itself by default (its own context menu), but the Manager passes
        itself, because a dialog is transient-for its parent — parenting it to
        the note makes the WM pull that note forward, and un-hide it, just to
        rename it from the list."""
        existing = getattr(self, "_rename_dlg", None)
        if existing is not None and existing.isVisible():
            existing.raise_(); existing.activateWindow(); return
        dlg = QDialog(parent if parent is not None else self)
        dlg.setWindowTitle(tr("Rename note"))
        dlg.setStyleSheet(_dialog_style())
        v = QVBoxLayout(dlg)
        v.setContentsMargins(16, 14, 16, 14)
        v.setSpacing(8)
        name_lbl = QLabel(tr("Note name:"))
        name_lbl.setStyleSheet(UI.LABEL_STYLE)
        v.addWidget(name_lbl)
        edit = QLineEdit(self._title)
        edit.setPlaceholderText(self._first_line() or tr("Untitled"))
        edit.setMinimumWidth(260)
        v.addWidget(edit)
        hint = QLabel(tr("Leave empty to use the automatic name (first line of the note)."))
        hint.setStyleSheet(UI.HINT_STYLE)
        v.addWidget(hint)
        row = QHBoxLayout()
        row.addStretch()
        cancel = QPushButton(tr("Cancel"))
        cancel.setStyleSheet(_btn_secondary())
        cancel.clicked.connect(dlg.reject)
        ok = QPushButton(tr("Save"))
        ok.setStyleSheet(_btn_primary())
        ok.setDefault(True)
        ok.clicked.connect(dlg.accept)
        row.addWidget(cancel)
        row.addWidget(ok)
        v.addLayout(row)
        edit.returnPressed.connect(dlg.accept)
        dlg.accepted.connect(lambda: self.set_title(edit.text()))
        self._rename_dlg = dlg
        dlg.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        dlg.destroyed.connect(lambda *_: setattr(self, "_rename_dlg", None))
        dlg.show(); dlg.raise_(); dlg.activateWindow()

    def _open_reminder_dialog(self):
        existing = getattr(self, "_reminder_dlg", None)
        if existing is not None and existing.isVisible():
            existing.raise_(); existing.activateWindow(); return
        dlg = QDialog(self)
        dlg.setWindowTitle(tr("Reminder"))
        dlg.setMinimumWidth(360)
        dlg.setStyleSheet(_dialog_style())
        v = QVBoxLayout(dlg)
        v.setContentsMargins(16, 14, 16, 14)
        v.setSpacing(8)

        now = datetime.datetime.now()

        def set_to(dt):
            self.set_reminder(dt.timestamp())
            dlg.accept()

        if self._reminder is not None:
            cur = datetime.datetime.fromtimestamp(self._reminder)
            lbl = QLabel(tr("Current: ") + cur.strftime("%a %b %d, %H:%M"))
            lbl.setStyleSheet(UI.VALUE_STYLE)
            v.addWidget(lbl)

        quick_lbl = QLabel(tr("Quick options:"))
        quick_lbl.setStyleSheet(UI.LABEL_STYLE)
        v.addWidget(quick_lbl)

        grid = QGridLayout()
        grid.setSpacing(6)

        def quick(label, dt, r, c):
            b = QPushButton(label)
            b.setStyleSheet(_btn_secondary())
            b.clicked.connect(lambda: set_to(dt))
            grid.addWidget(b, r, c)

        quick(tr("In 10 min"), now + datetime.timedelta(minutes=10), 0, 0)
        quick(tr("In 30 min"), now + datetime.timedelta(minutes=30), 0, 1)
        quick(tr("In 1 hour"),  now + datetime.timedelta(hours=1),   1, 0)
        quick(tr("In 3 hours"), now + datetime.timedelta(hours=3),   1, 1)
        quick(tr("In 8 hours"), now + datetime.timedelta(hours=8),   2, 0)
        quick(tr("In 24 hours"), now + datetime.timedelta(hours=24), 2, 1)
        v.addLayout(grid)

        v.addSpacing(4)
        time_lbl = QLabel(tr("Or a specific date and time:"))
        time_lbl.setStyleSheet(UI.LABEL_STYLE)
        v.addWidget(time_lbl)

        # Separate date (calendar dropdown) and time (spinner) controls. Default
        # to the CURRENT minute (so it matches the system clock) and refuse the
        # past: when today is selected the time can't go below the current
        # minute, so a reminder is always in the future.
        now_dt   = QDateTime.currentDateTime()
        cur_min  = QTime(now_dt.time().hour(), now_dt.time().minute())

        # Ista logika kao Settings (BEZ min-height, gumbi popunjavaju kutiju), ali
        # malo krupnije — reminder je cesta radnja pa treba biti ugodan za klik.
        # font 14 + padding 4 -> kutija ~31px; gumbi 15px (pola visine) je popune,
        # strelice 13. Provjereno renderiranjem.
        _dt_style = f"""
            QDateEdit, QTimeEdit {{
                font-size: 14px; padding: 4px 8px;
                background: {UI.SURFACE}; color: {UI.TEXT};
                border: 1px solid {UI.BORDER}; border-radius: 6px;
            }}
            QDateEdit::up-button, QTimeEdit::up-button {{
                subcontrol-origin: border; subcontrol-position: top right;
                width: 22px; height: 15px;
            }}
            QDateEdit::down-button, QTimeEdit::down-button {{
                subcontrol-origin: border; subcontrol-position: bottom right;
                width: 22px; height: 15px;
            }}
            QDateEdit::up-arrow, QTimeEdit::up-arrow {{ width: 13px; height: 13px; }}
            QDateEdit::down-arrow, QTimeEdit::down-arrow {{ width: 13px; height: 13px; }}
        """

        date_row = QHBoxLayout()
        _d_lbl = QLabel(tr("Date"))
        _d_lbl.setStyleSheet(UI.LABEL_STYLE)
        date_row.addWidget(_d_lbl)
        date_edit = QDateEdit(now_dt.date())
        date_edit.setCalendarPopup(True)
        date_edit.setDisplayFormat("dd.MM.yyyy")
        date_edit.setMinimumDate(now_dt.date())
        date_edit.setStyleSheet(_dt_style)
        date_row.addWidget(date_edit)
        date_row.addStretch()
        v.addLayout(date_row)

        time_row = QHBoxLayout()
        _t_lbl = QLabel(tr("Time"))
        _t_lbl.setStyleSheet(UI.LABEL_STYLE)
        time_row.addWidget(_t_lbl)
        time_edit = QTimeEdit(cur_min)
        time_edit.setDisplayFormat("HH:mm")
        time_edit.setStyleSheet(_dt_style)
        time_row.addWidget(time_edit)
        time_row.addStretch()
        v.addLayout(time_row)

        def _clamp_time_min():
            # Only today constrains the time; future dates allow any time.
            if date_edit.date() == QDate.currentDate():
                tn = QTime.currentTime()
                time_edit.setMinimumTime(QTime(tn.hour(), tn.minute()))
            else:
                time_edit.setMinimumTime(QTime(0, 0))
        date_edit.dateChanged.connect(lambda *_: _clamp_time_min())
        _clamp_time_min()

        set_btn = QPushButton(tr("Set"))
        set_btn.setStyleSheet(_btn_primary())

        def _set_specific():
            set_to(QDateTime(date_edit.date(), time_edit.time()).toPyDateTime())

        set_btn.clicked.connect(_set_specific)
        v.addWidget(set_btn)

        if self._reminder is not None:
            v.addSpacing(4)
            rm = QPushButton(tr("Remove reminder"))
            rm.setStyleSheet(_btn_secondary())
            rm.clicked.connect(lambda: (self.set_reminder(None), dlg.accept()))
            v.addWidget(rm)

        self._reminder_dlg = dlg
        dlg.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        dlg.destroyed.connect(lambda *_: setattr(self, "_reminder_dlg", None))
        dlg.show(); dlg.raise_(); dlg.activateWindow()

    def _open_font_picker(self):
        dlg = QDialog(self, Qt.WindowType.Popup)
        dlg.setStyleSheet(f"""
            QDialog {{ background: {UI.SURFACE}; border: 1px solid {UI.BORDER}; border-radius: 8px; }}
            QPushButton {{
                background: transparent; border: none; border-radius: 4px;
                padding: 5px 10px; font-size: 13px; text-align: left;
                color: {UI.TEXT};
            }}
            QPushButton:hover {{ background: {UI.HOVER_OVERLAY}; }}
            QPushButton[current="true"] {{ background: {UI.HOVER_OVERLAY_STRONG}; font-weight: bold; }}
        """)
        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(2)

        for label, family in self.QUICK_FONTS:
            btn = QPushButton(label)
            btn.setFixedHeight(28)
            btn.setFont(QFont(family, 12))
            if family == self._current_font_family:
                btn.setProperty("current", "true")
                btn.style().unpolish(btn)
                btn.style().polish(btn)
            btn.clicked.connect(lambda _, f=family: (self._apply_font_family(f), dlg.accept()))
            layout.addWidget(btn)

        sep = QWidget()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background-color: {UI.BORDER};")
        layout.addWidget(sep)

        more_btn = QPushButton(tr("More fonts…"))
        more_btn.setFixedHeight(28)
        more_btn.clicked.connect(lambda: (dlg.accept(), self._open_full_font_picker()))
        layout.addWidget(more_btn)

        pos = self.btn_font_family.mapToGlobal(self.btn_font_family.rect().bottomLeft())
        screen = self.screen().availableGeometry()
        x, y = pos.x(), pos.y()
        dlg.adjustSize()
        if x + dlg.width() > screen.right():
            x = screen.right() - dlg.width()
        if y + dlg.height() > screen.bottom():
            y = pos.y() - dlg.height() - self.btn_font_family.height()
        dlg.move(x, y)
        dlg.exec()
        dlg.deleteLater()

    def _open_full_font_picker(self):
        font, ok = QFontDialog.getFont(
            QFont(self._current_font_family),
            self,
            tr("Choose Font"),
            QFontDialog.FontDialogOption.DontUseNativeDialog
        )
        if ok:
            self._apply_font_family(font.family())
            if font.pointSize() > 0:
                self._font_size = max(8, min(72, font.pointSize()))
                self.font_size_label.setText(str(self._font_size))
                self.text_edit.setFocus()
                cursor = self.text_edit.textCursor()
                fmt = QTextCharFormat()
                fmt.setFontPointSize(self._font_size)
                cursor.mergeCharFormat(fmt)
                self.text_edit.setTextCursor(cursor)

    def _open_text_color_picker(self):
        dlg = QDialog(self, Qt.WindowType.Popup)
        dlg.setStyleSheet(f"""
            QDialog {{
                background: {UI.SURFACE};
                border: 1px solid {UI.BORDER};
                border-radius: 8px;
            }}
        """)

        grid = QGridLayout(dlg)
        grid.setContentsMargins(10, 10, 10, 10)
        grid.setSpacing(2)
        cols = 4

        for i, hex_c in enumerate(self.TEXT_COLORS):
            btn = QPushButton()
            btn.setFixedSize(32, 32)
            is_current = (hex_c == self._text_color)
            border = f"2px solid {UI.TEXT}" if is_current else "1px solid rgba(0,0,0,0.15)"
            if hex_c == "#ffffff":
                border = f"1px solid {UI.BORDER}"
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {hex_c};
                    border: {border};
                    border-radius: 4px;
                }}
                QPushButton:hover {{ border: 2px solid {UI.TEXT_MUTED}; }}
            """)
            btn.clicked.connect(lambda _, c=hex_c: (self._apply_text_color(c), dlg.accept()))
            grid.addWidget(btn, i // cols, i % cols)

        pos = self.btn_text_color.mapToGlobal(self.btn_text_color.rect().bottomLeft())
        screen = self.screen().availableGeometry()
        x, y = pos.x(), pos.y()
        dlg.adjustSize()
        if x + dlg.width() > screen.right():
            x = screen.right() - dlg.width()
        if y + dlg.height() > screen.bottom():
            y = pos.y() - dlg.height() - self.btn_text_color.height()
        dlg.move(x, y)
        dlg.exec()
        dlg.deleteLater()

    def _open_bullet_picker(self):
        """Popup to choose a list style, or remove the list if already in one."""
        cursor = self.text_edit.textCursor()
        in_list = bool(cursor.currentList())

        dlg = QDialog(self, Qt.WindowType.Popup)
        dlg.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(2)

        container = QWidget()
        container.setObjectName("pickerBox")
        container.setStyleSheet(f"""
            QWidget#pickerBox {{ background: {UI.SURFACE}; border: 1px solid {UI.BORDER}; border-radius: 8px; }}
            QPushButton {{ background: transparent; border: none; text-align: left;
                padding: 7px 14px; font-size: 14px; border-radius: 4px; color: {UI.TEXT}; }}
            QPushButton:hover {{ background: {UI.HOVER_OVERLAY}; }}
        """)
        inner = QVBoxLayout(container)
        inner.setContentsMargins(5, 5, 5, 5)
        inner.setSpacing(1)

        for label, style in self.BULLET_STYLES:
            b = QPushButton(label)
            b.clicked.connect(lambda _, s=style: (dlg.accept(), self._fmt_bullet(s)))
            inner.addWidget(b)

        if in_list:
            sep = QWidget()
            sep.setFixedHeight(1)
            sep.setStyleSheet(f"background-color: {UI.BORDER};")
            inner.addWidget(sep)
            remove_btn = QPushButton(tr("✕  Remove list"))
            remove_btn.clicked.connect(lambda: (dlg.accept(), self._fmt_bullet(None)))
            inner.addWidget(remove_btn)

        layout.addWidget(container)

        pos = self.btn_bullet.mapToGlobal(self.btn_bullet.rect().bottomLeft())
        screen = self.screen().availableGeometry()
        dlg.adjustSize()
        x, y = pos.x(), pos.y()
        if x + dlg.width() > screen.right():
            x = screen.right() - dlg.width()
        if y + dlg.height() > screen.bottom():
            y = self.btn_bullet.mapToGlobal(self.btn_bullet.rect().topLeft()).y() - dlg.height()
        dlg.move(x, y)
        dlg.exec()
        dlg.deleteLater()

    def _open_font_size_entry(self):
        """Popup with a number field — sets the selection (or the typing format)
        to one exact size via the shared _apply_font_size."""
        # Capture the selection BEFORE the popup opens and steals focus — reading
        # it after would find the selection collapsed, so the resize would silently
        # do nothing on the selected text.
        sel_cursor = self.text_edit.textCursor()
        dlg = QDialog(self, Qt.WindowType.Popup)
        dlg.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        outer = QVBoxLayout(dlg)
        outer.setContentsMargins(6, 6, 6, 6)

        box = QWidget()
        box.setObjectName("sizeBox")
        box.setStyleSheet(f"""
            QWidget#sizeBox {{ background: {UI.SURFACE}; border: 1px solid {UI.BORDER}; border-radius: 8px; }}
            QSpinBox {{ border: 1px solid {UI.BORDER}; border-radius: 4px; padding: 4px;
                background: {UI.SURFACE}; color: {UI.TEXT};
                font-size: 14px; min-width: 60px; }}
            QPushButton {{ background: #555; color: white; border: none; border-radius: 4px;
                padding: 5px 12px; font-size: 13px; }}
            QPushButton:hover {{ background: #333; }}
        """)
        inner = QHBoxLayout(box)
        inner.setContentsMargins(8, 8, 8, 8)
        inner.setSpacing(6)

        spin = QSpinBox()
        spin.setRange(8, 96)
        spin.setValue(self._font_size)
        inner.addWidget(spin)

        apply_btn = QPushButton(tr("Set"))
        def apply_size():
            self._apply_font_size(spin.value(), sel_cursor)   # captured selection
            dlg.accept()
        apply_btn.clicked.connect(apply_size)
        spin.lineEdit().returnPressed.connect(apply_size)
        inner.addWidget(apply_btn)

        outer.addWidget(box)

        pos = self.font_size_label.mapToGlobal(self.font_size_label.rect().bottomLeft())
        screen = self.screen().availableGeometry()
        dlg.adjustSize()
        x, y = pos.x(), pos.y()
        if x + dlg.width() > screen.right():
            x = screen.right() - dlg.width()
        if y + dlg.height() > screen.bottom():
            y = self.font_size_label.mapToGlobal(self.font_size_label.rect().topLeft()).y() - dlg.height()
        dlg.move(x, y)
        spin.setFocus()
        spin.selectAll()
        dlg.exec()
        dlg.deleteLater()

    def _note_palette(self) -> dict:
        """Swatch set for the colour picker, per the app's chrome theme: modern
        dark fills in dark mode, the pastels in light mode. Existing notes keep
        their stored colour regardless of the active theme."""
        if getattr(self.app_ref, "_theme", "light") == "dark":
            return self.DARK_NOTE_COLORS
        return self.NOTE_COLORS

    def _open_color_palette(self):
        dlg = QDialog(self, Qt.WindowType.Popup)
        dlg.setWindowTitle("")
        dlg.setStyleSheet(f"""
            QDialog {{
                background: {UI.SURFACE};
                border: 1px solid {UI.BORDER};
                border-radius: 8px;
            }}
        """)

        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # ── Colour grid ───────────────────────────────────────────────────────
        grid = QGridLayout()
        grid.setSpacing(6)

        colors = list(self._note_palette().items())
        cols = 4
        for i, (name, hex_c) in enumerate(colors):
            btn = QPushButton()
            btn.setFixedSize(32, 32)
            btn.setToolTip(name)
            is_current = (hex_c == self.color)
            border = f"2px solid {UI.TEXT}" if is_current else "1px solid rgba(0,0,0,0.15)"
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {hex_c};
                    border: {border};
                    border-radius: 6px;
                }}
                QPushButton:hover {{ border: 2px solid {UI.TEXT_MUTED}; }}
            """)
            btn.clicked.connect(lambda _, c=hex_c: (self._set_color(c), dlg.accept()))
            grid.addWidget(btn, i // cols, i % cols)

        layout.addLayout(grid)

        # ── Separator ────────────────────────────────────────────────────────
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color: {UI.BORDER};")
        layout.addWidget(sep)

        # ── Custom hex input ──────────────────────────────────────────────────
        hex_label = QLabel(tr("Custom colour:"))
        hex_label.setStyleSheet(f"font-size: 12px; color: {UI.TEXT_MUTED};")
        layout.addWidget(hex_label)

        row = QHBoxLayout()
        row.setSpacing(6)

        # Preview swatch — klikabilno, otvara color picker
        preview = QPushButton()
        preview.setFixedSize(28, 28)
        preview.setToolTip(tr("Click to open colour picker"))
        preview.setStyleSheet(f"""
            QPushButton {{
                background: {self.color};
                border: 1px solid {UI.BORDER};
                border-radius: 5px;
            }}
            QPushButton:hover {{ border: 2px solid {UI.TEXT_MUTED}; }}
        """)

        # Hex input
        hex_input = QLineEdit()
        hex_input.setPlaceholderText("#RRGGBB")
        hex_input.setMaxLength(7)
        hex_input.setText(self.color)
        hex_input.setStyleSheet(f"""
            QLineEdit {{
                background: {UI.SURFACE}; color: {UI.TEXT};
                border: 1px solid {UI.BORDER};
                border-radius: 5px;
                padding: 4px 7px;
                font-size: 13px;
                font-family: monospace;
            }}
            QLineEdit:focus {{ border-color: {UI.TEXT_MUTED}; }}
        """)

        def on_hex_changed(text):
            if len(text) == 7 and text.startswith("#"):
                if QColor(text).isValid():
                    preview.setStyleSheet(f"""
                        QPushButton {{
                            background: {text};
                            border: 1px solid {UI.BORDER};
                            border-radius: 5px;
                        }}
                        QPushButton:hover {{ border: 2px solid {UI.TEXT_MUTED}; }}
                    """)

        def open_color_picker():
            initial = QColor(hex_input.text() if QColor(hex_input.text()).isValid() else self.color)
            chosen = QColorDialog.getColor(
                initial, dlg, "Pick a Colour",
                QColorDialog.ColorDialogOption.DontUseNativeDialog
            )
            if chosen.isValid():
                hex_val = chosen.name()
                hex_input.setText(hex_val)
                preview.setStyleSheet(f"""
                    QPushButton {{
                        background: {hex_val};
                        border: 1px solid {UI.BORDER};
                        border-radius: 5px;
                    }}
                    QPushButton:hover {{ border: 2px solid {UI.TEXT_MUTED}; }}
                """)
                self._set_color(hex_val)
                dlg.accept()

        def apply_hex():
            text = hex_input.text().strip()
            if not text.startswith("#"):
                text = "#" + text
            color = QColor(text)
            if color.isValid():
                self._set_color(text)
                dlg.accept()
            else:
                hex_input.setStyleSheet(hex_input.styleSheet() +
                    "QLineEdit { border-color: #e53935; }")

        hex_input.textChanged.connect(on_hex_changed)
        hex_input.returnPressed.connect(apply_hex)
        preview.clicked.connect(open_color_picker)

        apply_btn = QPushButton(tr("Apply"))
        apply_btn.setFixedHeight(28)
        apply_btn.setStyleSheet("""
            QPushButton {
                background: #555;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 0 10px;
                font-size: 12px;
            }
            QPushButton:hover { background: #333; }
        """)
        apply_btn.clicked.connect(apply_hex)

        row.addWidget(preview)
        row.addWidget(hex_input)
        row.addWidget(apply_btn)
        layout.addLayout(row)

        # Position near menu button, but keep within screen bounds
        dlg.adjustSize()
        pos   = self.btn_menu.mapToGlobal(self.btn_menu.rect().bottomLeft())
        screen = self.screen().availableGeometry()
        x = pos.x()
        y = pos.y()
        if x + dlg.width() > screen.right():
            x = screen.right() - dlg.width()
        if y + dlg.height() > screen.bottom():
            y = pos.y() - dlg.height() - self.btn_menu.height()
        dlg.move(x, y)
        dlg.exec()
        dlg.deleteLater()

    # ── Lifecycle ─────────────────────────────────────────────────────────────
