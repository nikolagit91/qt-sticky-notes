"""Global quick-search palette — a slim, centred, always-on-top overlay for
finding a note from anywhere (bound to a GNOME global shortcut, see hotkey.py /
app.show_search). Type to filter notes by title and body; ↑/↓ to move through
results; Enter reveals and raises the selected note; Esc dismisses.

Deliberately lightweight compared to the full Notes Manager: it appears, you
pick a note, it disappears — so it barely disturbs window stacking (unlike
popping the whole Manager in front of what you were doing).
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFrame, QLineEdit, QListWidget, QListWidgetItem,
    QLabel, QStyledItemDelegate, QStyle, QAbstractItemView,
)
from PyQt6.QtGui import QColor
from PyQt6.QtCore import Qt, QEvent, QTimer, QSize, QRect

from .theme import UI
from .i18n import tr
from .search import find_live_matches

_ROW_H = 52


class _ResultDelegate(QStyledItemDelegate):
    """Two-line result row: note title above, a context snippet below. Painted
    by hand so the selected row gets the accent background with legible light
    text, independent of the platform palette."""

    def sizeHint(self, option, index):
        return QSize(option.rect.width(), _ROW_H)

    def paint(self, painter, option, index):
        painter.save()
        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        if selected:
            painter.fillRect(option.rect, QColor(UI.ACCENT))
        title, snippet = index.data(Qt.ItemDataRole.UserRole) or ("", "")
        r = option.rect.adjusted(14, 0, -14, 0)
        title_rect = QRect(r.left(), r.top() + 8,  r.width(), 20)
        snip_rect  = QRect(r.left(), r.top() + 28, r.width(), 18)

        f = painter.font()
        f.setPointSizeF(13)
        painter.setFont(f)
        painter.setPen(QColor("#ffffff" if selected else UI.TEXT))
        fm = painter.fontMetrics()
        painter.drawText(title_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                         fm.elidedText(title or tr("Untitled"),
                                       Qt.TextElideMode.ElideRight, title_rect.width()))
        if snippet:
            f.setPointSizeF(11)
            painter.setFont(f)
            painter.setPen(QColor("#dde7fb" if selected else UI.TEXT_MUTED))
            fm = painter.fontMetrics()
            painter.drawText(snip_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                             fm.elidedText(snippet, Qt.TextElideMode.ElideRight, snip_rect.width()))
        painter.restore()


class SearchPalette(QDialog):
    def __init__(self, app_ref):
        super().__init__()
        self.app_ref = app_ref
        self._row_notes = []
        self._armed = False          # gate WindowDeactivate-close until shown
        self.setWindowTitle(tr("Search notes"))
        self.setModal(False)
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        frame = QFrame()
        frame.setObjectName("paletteFrame")
        self._frame = frame
        outer.addWidget(frame)

        lay = QVBoxLayout(frame)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(8)

        self.search = QLineEdit()
        self.search.setPlaceholderText(tr("Search notes…"))
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self._refresh)
        self.search.installEventFilter(self)
        lay.addWidget(self.search)

        self.list = QListWidget()
        self.list.setItemDelegate(_ResultDelegate(self.list))
        self.list.setUniformItemSizes(True)
        self.list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.list.setFocusPolicy(Qt.FocusPolicy.NoFocus)   # keep typing focus in the search box
        self.list.setStyleSheet("QListWidget { border: none; background: transparent; }")
        # Highlight follows the pointer, like a launcher: without tracking on the
        # VIEWPORT (which receives the moves) Qt only emits itemEntered while a
        # button is held, so the selection stayed wherever the arrows left it.
        # Selecting on hover — not just painting a hover state — keeps the click
        # and Enter paths acting on the row the user is actually looking at.
        self.list.setMouseTracking(True)
        self.list.viewport().setMouseTracking(True)
        self.list.itemEntered.connect(self.list.setCurrentItem)
        self.list.itemClicked.connect(lambda *_: self._activate())
        lay.addWidget(self.list)

        self.empty = QLabel(tr("No matching notes"))
        self.empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty.hide()
        lay.addWidget(self.empty)

        self._apply_style()
        self.resize(560, 430)
        self._refresh()

    def _apply_style(self):
        """Bake the current UI.* colours into the stylesheets. Split out of
        __init__ because the palette is built once and reused: retheme() must
        re-apply these on a live theme change, or the frame and search box stay
        in the theme of the first open while the rows (painted by the delegate)
        follow the new one."""
        self._frame.setStyleSheet(
            f"#paletteFrame {{ background: {UI.WINDOW_BG}; "
            f"border: 1px solid {UI.BORDER}; border-radius: 10px; }}"
        )
        self.search.setStyleSheet(f"""
            QLineEdit {{
                padding: 9px 11px; border: 1px solid {UI.BORDER};
                border-radius: 7px; background: {UI.SURFACE};
                font-size: 14px; color: {UI.TEXT};
            }}
            QLineEdit:focus {{ border: 1px solid {UI.ACCENT}; }}
        """)
        self.empty.setStyleSheet(f"color: {UI.TEXT_MUTED}; font-size: 13px; padding: 14px 4px;")

    def retheme(self):
        """Live theme change: restyle in place (the window is kept, never
        recreated) and repaint the delegate-drawn rows."""
        self._apply_style()
        self.list.viewport().update()

    # ── results ───────────────────────────────────────────────────────────────
    def _refresh(self):
        matches = find_live_matches(self.search.text(), self.app_ref.notes)
        self.list.clear()
        self._row_notes = []
        for note, title, snippet in matches:
            item = QListWidgetItem(self.list)
            item.setData(Qt.ItemDataRole.UserRole, (title, snippet))
            item.setSizeHint(QSize(0, _ROW_H))
            self._row_notes.append(note)
        has = bool(self._row_notes)
        self.list.setVisible(has)
        self.empty.setVisible(not has)
        if has:
            self.list.setCurrentRow(0)

    def _move(self, delta):
        n = self.list.count()
        if n:
            self.list.setCurrentRow((self.list.currentRow() + delta) % n)

    def _activate(self):
        row = self.list.currentRow()
        if 0 <= row < len(self._row_notes):
            note = self._row_notes[row]
            self.close()
            self.app_ref.reveal_note(note)

    # ── keys / focus ────────────────────────────────────────────────────────────
    def eventFilter(self, obj, event):
        if obj is self.search and event.type() == QEvent.Type.KeyPress:
            key = event.key()
            if key == Qt.Key.Key_Down:
                self._move(1);  return True
            if key == Qt.Key.Key_Up:
                self._move(-1); return True
            if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                self._activate(); return True
            if key == Qt.Key.Key_Escape:
                self.close(); return True
        return super().eventFilter(obj, event)

    def event(self, e):
        # Click away (palette loses activation) → dismiss, like a real launcher.
        # Armed only after it has settled so the initial show can't self-close.
        if e.type() == QEvent.Type.WindowDeactivate and self._armed:
            self.close()
        return super().event(e)

    def showEvent(self, e):
        super().showEvent(e)
        scr = self.app_ref.primaryScreen().availableGeometry()
        self.move(scr.center().x() - self.width() // 2,
                  scr.top() + scr.height() // 5)        # spotlight-ish, above centre
        self.search.setFocus()
        self.search.selectAll()
        self._armed = False
        QTimer.singleShot(250, lambda: setattr(self, "_armed", True))
