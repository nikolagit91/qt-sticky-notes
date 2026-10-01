"""The NotesManager window — lists active and trashed notes with bulk actions."""

import html
from typing import TYPE_CHECKING

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QFrame,
    QScrollArea, QTabWidget, QTabBar, QMessageBox, QLineEdit, QSizePolicy, QMenu,
)
from PyQt6.QtCore import Qt, QSize, QPoint
from PyQt6.QtGui import QIcon, QTextDocument, QShortcut, QKeySequence, QColor

from .icons import (
    _SVG_TRASH, _SVG_EYE_OPEN, _SVG_EYE_CLOSED, _SVG_ARCHIVE,
    _SVG_STAR, _SVG_STAR_O,
    _make_lock_icon, _set_btn_icon, _HAS_SVG,
)
from .theme import (UI, _btn_primary, _btn_secondary, _btn_danger, note_ink, menu_style,
                    message_box_style, effective_note_color)
from .i18n import tr

if TYPE_CHECKING:
    from .app import StickyNotesApp


class ElidingLabel(QLabel):
    """A QLabel that shows '…' when its text is too wide for the available
    space (a plain QLabel would just clip it), and exposes the full text as a
    tooltip. Lets a long first-line note name stay the real name while the row
    keeps a tidy single-line display that adapts to the window width."""

    def __init__(self, text: str = "", parent=None):
        super().__init__(parent)
        self._full = text
        # Don't demand width for the full text — take what the layout gives and
        # elide into it; otherwise a long name would stretch the whole window.
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self._apply()

    def setText(self, text: str):
        self._full = text
        self._apply()

    def fullText(self) -> str:
        return self._full

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._apply()

    def _apply(self):
        fm = self.fontMetrics()
        elided = fm.elidedText(self._full, Qt.TextElideMode.ElideRight, max(self.width(), 0))
        super().setText(elided)
        # Tooltip only when actually truncated, so short names stay tooltip-free.
        # Cap it to a short preview (a long first line — e.g. a whole paragraph —
        # shouldn't fill a giant tooltip) and wrap it as light rich text so it
        # stays readable and doesn't stretch across the screen.
        if elided != self._full:
            preview = self._full if len(self._full) <= 200 else self._full[:200].rstrip() + "…"
            self.setToolTip(
                f"<div style='max-width:360px; white-space:pre-wrap; color:#f0f0f0'>"
                f"{html.escape(preview)}</div>"
            )
        else:
            self.setToolTip("")


class NotesManager(QWidget):

    def __init__(self, app_ref: "StickyNotesApp"):
        super().__init__()
        self.app_ref = app_ref
        self._active_rows = []   # (row_widget, lowercased full search text)
        self._archived_rows = []
        self._trash_rows = []
        # Give the Manager the SAME window setup as the Settings/About dialogs
        # (see app._show_window): a NORMAL-type top-level with explicit
        # min/max/close hints. Both windows being the same TYPE is what lets the WM
        # stack them by raise order — opening the Manager brings it in front of an
        # open Settings — instead of keeping DIALOG-type windows above the (normal)
        # Manager, which is what made it sink behind Settings. The explicit button
        # hints keep the title-bar minimize/maximize buttons working (a bare
        # DIALOG-type window on GNOME only gets a close button).
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.WindowMinimizeButtonHint
            | Qt.WindowType.WindowMaximizeButtonHint
            | Qt.WindowType.WindowCloseButtonHint
        )
        self.setWindowTitle(tr("Notes Manager"))
        self.setMinimumWidth(520)
        self.setMinimumHeight(360)
        self.resize(560, 600)
        self._apply_root_style()
        self._build_ui()
        self.refresh()

    def _apply_root_style(self):
        """The Manager's root stylesheet. Its `QWidget` rule cascades into
        message boxes parented here, so message_box_style() rides along. Split
        out of __init__ so retheme() can re-apply it live."""
        self.setStyleSheet(f"""
            QWidget {{ background: {UI.WINDOW_BG}; font-size: 13px; }}
            QToolTip {{
                background-color: #2b2b2b;
                color: #f0f0f0;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 4px 6px;
            }}
        """ + message_box_style())

    def retheme(self):
        """Rebuild the Manager's content in place for a live theme change — the
        top-level widget is kept (never recreated), so the dock icon is safe.
        Preserves the active tab and the search text."""
        from PyQt6.QtWidgets import QWidget
        # hasattr, NOT `getattr(self, "tabs", None)`: the question here is "has
        # _build_ui run yet", and hasattr answers it without touching the widget.
        # The getattr form evaluates the widget's truthiness, which raises from
        # inside getattr when the C++ object is gone — surfacing as a baffling
        # "SystemError: getattr returned a result with an exception set".
        tab = self.tabs.currentIndex() if hasattr(self, "tabs") else 0
        query = self._search.text() if hasattr(self, "_search") else ""
        old = self.layout()
        if old is not None:
            QWidget().setLayout(old)      # reparents old layout + children → deleted
        self._apply_root_style()
        self._build_ui()
        self.refresh()
        self.tabs.setCurrentIndex(tab)
        self._search.setText(query)       # re-applies the filter via textChanged

    def closeEvent(self, event):
        self.app_ref._manager = None   # break circular reference
        self.deleteLater()             # schedule Qt C++ destruction + all child widgets
        super().closeEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close()
            return
        super().keyPressEvent(event)

    def _build_ui(self):
        if self.layout():
            return  # already built
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        # ── Header ────────────────────────────────────────────────────────────
        top = QHBoxLayout()
        title = QLabel(tr("Notes Manager"))
        title.setStyleSheet(f"font-size: 17px; font-weight: 600; color: {UI.TEXT};")
        top.addWidget(title)
        top.addStretch()

        count_lbl = QLabel()
        count_lbl.setStyleSheet(f"color: {UI.TEXT_MUTED}; font-size: 13px;")
        self._count_lbl = count_lbl
        top.addWidget(count_lbl)

        btn_new = QPushButton("+")
        btn_new.setFixedSize(34, 34)
        btn_new.setToolTip(tr("New Note"))
        btn_new.setStyleSheet(f"""
            QPushButton {{
                background: {UI.ACCENT}; color: #ffffff;
                border: none; border-radius: 6px;
                font-size: 22px; font-weight: 500;
            }}
            QPushButton:hover  {{ background: {UI.ACCENT_HOVER}; }}
            QPushButton:pressed {{ background: {UI.ACCENT_PRESS}; }}
        """)
        btn_new.clicked.connect(lambda: self.app_ref.create_new_note())
        top.addSpacing(8)
        top.addWidget(btn_new)
        layout.addLayout(top)

        # ── Search box ────────────────────────────────────────────────────────
        # Filters both tabs live by full note text (not just the cached preview).
        self._search = QLineEdit()
        self._search.setPlaceholderText(tr("Search notes…"))
        self._search.setClearButtonEnabled(True)
        self._search.setStyleSheet(f"""
            QLineEdit {{
                background: {UI.SURFACE}; color: {UI.TEXT};
                border: 1px solid {UI.BORDER}; border-radius: 6px;
                padding: 7px 10px; font-size: 13px;
            }}
            QLineEdit:focus {{ border: 1px solid {UI.ACCENT}; }}
        """)
        self._search.textChanged.connect(self._apply_filter)
        layout.addWidget(self._search)

        # ── Tabs: Active / Closed ─────────────────────────────────────────────
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{ border: 1px solid {UI.BORDER}; border-radius: 6px; }}
            QTabBar::tab {{ padding: 8px 20px; border-radius: 4px; font-size: 13px;
                color: {UI.TEXT_MUTED}; }}
            QTabBar::tab:selected {{ background: {UI.SURFACE}; color: {UI.TEXT};
                font-weight: 600; }}
        """)

        # Active notes tab
        self.active_scroll = QScrollArea()
        self.active_scroll.setWidgetResizable(True)
        self.active_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.active_container = QWidget()
        self.active_layout = QVBoxLayout(self.active_container)
        self.active_layout.setSpacing(6)
        self.active_layout.addStretch()
        self.active_scroll.setWidget(self.active_container)

        # Archive tab
        self.archive_scroll = QScrollArea()
        self.archive_scroll.setWidgetResizable(True)
        self.archive_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.archive_container = QWidget()
        self.archive_layout = QVBoxLayout(self.archive_container)
        self.archive_layout.setSpacing(6)
        self.archive_layout.addStretch()
        self.archive_scroll.setWidget(self.archive_container)

        # Trash tab
        self.trash_scroll = QScrollArea()
        self.trash_scroll.setWidgetResizable(True)
        self.trash_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.trash_container = QWidget()
        self.trash_layout = QVBoxLayout(self.trash_container)
        self.trash_layout.setSpacing(6)
        self.trash_layout.addStretch()
        self.trash_scroll.setWidget(self.trash_container)

        self.tabs.addTab(self.active_scroll, tr("Active"))
        self.tabs.addTab(self.archive_scroll, tr("Archive"))
        self.tabs.addTab(self.trash_scroll, tr("Trash"))
        layout.addWidget(self.tabs)

        # ── Bottom buttons (tab-conditional) ─────────────────────────────────
        btn_row = QHBoxLayout()

        # Active tab buttons
        self._btn_show_all = QPushButton(tr("Show All"))
        self._btn_show_all.clicked.connect(self.app_ref.show_all_notes)
        self._btn_show_all.setStyleSheet(_btn_primary())

        self._btn_close_all = QPushButton(tr("Hide All"))
        self._btn_close_all.clicked.connect(self.app_ref.hide_all_notes)
        self._btn_close_all.setStyleSheet(_btn_secondary())

        self._btn_refresh = QPushButton(tr("Refresh"))
        self._btn_refresh.clicked.connect(self.refresh)
        self._btn_refresh.setStyleSheet(_btn_secondary())

        # Archive tab buttons
        self._btn_arch_restore_all = QPushButton(tr("Restore All"))
        self._btn_arch_restore_all.clicked.connect(self._restore_all_archive)
        self._btn_arch_restore_all.setStyleSheet(_btn_primary())

        self._btn_arch_export_all = QPushButton(tr("Export All"))
        self._btn_arch_export_all.setToolTip(tr("Export all archived notes to a JSON file."))
        self._btn_arch_export_all.clicked.connect(
            lambda: self.app_ref.export_archived_notes(self))
        self._btn_arch_export_all.setStyleSheet(_btn_secondary())

        # Trash tab buttons
        self._btn_restore_all = QPushButton(tr("Restore All"))
        self._btn_restore_all.clicked.connect(self._restore_all)
        self._btn_restore_all.setStyleSheet(_btn_primary())

        self._btn_delete_all = QPushButton(tr("Delete All"))
        self._btn_delete_all.clicked.connect(self._delete_all_trash)
        self._btn_delete_all.setStyleSheet(_btn_danger())

        for btn in (self._btn_show_all, self._btn_close_all, self._btn_refresh,
                    self._btn_arch_restore_all, self._btn_arch_export_all,
                    self._btn_restore_all, self._btn_delete_all):
            btn_row.addWidget(btn)

        layout.addLayout(btn_row)

        self.tabs.currentChanged.connect(self._on_tab_changed)
        self._on_tab_changed(0)

        self._sc_help = QShortcut(QKeySequence("F1"), self)
        self._sc_help.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self._sc_help.activated.connect(self.app_ref.show_shortcuts)

    def _on_tab_changed(self, index: int):
        is_active  = (index == 0)
        is_archive = (index == 1)
        is_trash   = (index == 2)
        self._btn_show_all.setVisible(is_active)
        self._btn_close_all.setVisible(is_active)
        self._btn_refresh.setVisible(is_active)
        self._btn_arch_restore_all.setVisible(is_archive)
        self._btn_arch_export_all.setVisible(is_archive)
        self._btn_restore_all.setVisible(is_trash)
        self._btn_delete_all.setVisible(is_trash)

    # ── Restore helpers (respect the Active hard limit) ───────────────────────
    def _restore_one(self, data: dict, restore_fn):
        """Restore a single note to Active; if Active is full, say so once."""
        from .config import ACTIVE_LIMIT
        if not restore_fn(data):
            QMessageBox.information(
                self, tr("Active Full"),
                tr("You already have {} active notes — the maximum.\nArchive or delete one first.").format(ACTIVE_LIMIT))
            return
        self.refresh()

    def _bulk_restore(self, source_list, restore_fn):
        """Restore as many notes as fit under the Active limit, then report once
        if some were skipped (avoids one dialog per note)."""
        from .config import ACTIVE_LIMIT
        items = list(source_list)
        capacity = ACTIVE_LIMIT - len(self.app_ref.notes)
        if capacity <= 0:
            QMessageBox.information(
                self, tr("Active Full"),
                tr("You already have {} active notes — the maximum.").format(ACTIVE_LIMIT))
            return
        for data in items[:capacity]:
            restore_fn(data)
        self.refresh()
        if len(items) > capacity:
            QMessageBox.information(
                self, tr("Partly Restored"),
                tr("Restored {} note(s). {} could not be restored — the active limit ({}) was reached.").format(
                    capacity, len(items) - capacity, ACTIVE_LIMIT))

    def _restore_all(self):
        self._bulk_restore(self.app_ref.trash_notes, self.app_ref.restore_from_trash)

    def _restore_all_archive(self):
        self._bulk_restore(self.app_ref.archived_notes, self.app_ref.unarchive_note)

    def _archive_one(self, note_id: str):
        """Archive an active note from the Manager; if Archive is full, say so."""
        from .config import ARCHIVE_LIMIT
        if not self.app_ref.archive_note(note_id):
            QMessageBox.information(
                self, tr("Archive Full"),
                tr("Archive is full ({} notes).\nRemove something from the Archive first.").format(ARCHIVE_LIMIT))
            return
        self.refresh()

    def _delete_all_trash(self):
        count = len(self.app_ref.trash_notes)
        if count == 0:
            return
        msg = QMessageBox(self)
        msg.setWindowTitle(tr("Delete All"))
        msg.setText(tr("Permanently delete all {} note(s) in Trash?\nThis cannot be undone.").format(count))
        msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg.setDefaultButton(QMessageBox.StandardButton.No)
        choice = msg.exec()
        msg.deleteLater()
        if choice == QMessageBox.StandardButton.Yes:
            self.app_ref.empty_trash()

    def _show_note_row_menu(self, row, pos, data):
        """Right-click menu for an active or archived note: rename it (active
        only) or export just it. Anchored just left of the row's pin/restore icon
        (not the cursor) and kept compact — a bit shorter than the row."""
        menu = QMenu(self)
        menu.setStyleSheet(menu_style())
        # Rename goes through the note's OWN dialog, so there is one rename path
        # in the app (and set_title already refreshes this list). An archived note
        # has no live widget behind its row, so it gets Export only rather than a
        # second, divergent rename path.
        note = self.app_ref.notes.get(data.get("id"))
        act_rename = menu.addAction(tr("Rename")) if note is not None else None
        act_export = menu.addAction(tr("Export"))
        anchor = getattr(row, "_menu_anchor", None)
        if anchor is not None:
            # Sit just to the LEFT of the icon, vertically centred on the row.
            w = menu.sizeHint().width()
            btn_tl = anchor.mapToGlobal(QPoint(0, 0))
            x = btn_tl.x() - w - 10
            y = btn_tl.y() + (anchor.height() - menu.sizeHint().height()) // 2
            point = QPoint(x, y)
        else:
            point = row.mapToGlobal(QPoint(14, row.height() - 2))
        chosen = menu.exec(point)
        if act_rename is not None and chosen is act_rename:
            note._open_rename_dialog(parent=self)   # keep the note where it is
        elif chosen is act_export:
            self.app_ref.export_single_note(data, self)

    def _make_note_row(self, data: dict, kind: str) -> QWidget:
        """kind is one of 'active', 'archive', 'trash'."""
        is_active = (kind == "active")
        # Each row is painted in the note's own colour, so its label and icons
        # must contrast against THAT (a dark note needs light text/icons) — same
        # ink the note widget uses, honouring the global auto-contrast toggle.
        row_color = effective_note_color(
            data.get('color', '#fff59d'), data.get('color_dark', ''),
            getattr(self.app_ref, "_theme", "light") == "dark")
        ink = note_ink(QColor(row_color),
                       auto=getattr(self.app_ref, "_auto_contrast", True))
        row = QWidget()
        row.setStyleSheet(f"""
            QWidget {{
                background: {row_color};
                border-radius: 8px;
                border: 1px solid rgba(0,0,0,0.1);
            }}
        """)

        if kind in ("active", "archive"):
            # Right-click a note to export just that one.
            row.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            row.customContextMenuRequested.connect(
                lambda pos, d=data, r=row: self._show_note_row_menu(r, pos, d))

        hl = QHBoxLayout(row)
        hl.setContentsMargins(10, 8, 10, 8)
        hl.setSpacing(8)

        # Note name: custom title, else first line (display_title); fall back to
        # the cached preview for notes saved before titles existed.
        label = (data.get("display_title") or "").strip() \
                or data.get("preview", "").strip() or "(empty)"

        lbl = ElidingLabel(label)
        lbl.setStyleSheet(f"background: transparent; border: none; font-size: 14px; color: {ink.text};")

        # Favourite star — left of the name (a status marker, kept out of the
        # right-hand action cluster). Active rows only.
        if is_active:
            note0 = self.app_ref.notes.get(data["id"])
            btn_fav = QPushButton()
            btn_fav.setFixedSize(26, 26)
            btn_fav.setToolTip(tr("Favorite"))
            if _HAS_SVG:
                # Star keeps its own status colours (gold when favourited, gray
                # outline otherwise) — it is a marker, not chrome.
                btn_fav.setIcon(_make_lock_icon(
                    _SVG_STAR if (note0 and note0._favorite) else _SVG_STAR_O, 18))
                btn_fav.setIconSize(QSize(18, 18))
            else:
                btn_fav.setText("★" if (note0 and note0._favorite) else "☆")
            btn_fav.setStyleSheet(f"""
                QPushButton {{ background: transparent; border: none; border-radius: 4px; }}
                QPushButton:hover {{ background: {ink.hover_bg}; }}
            """)
            if note0:
                btn_fav.clicked.connect(lambda _, n=note0: n.toggle_favorite())
            hl.addWidget(btn_fav)

        hl.addWidget(lbl, 1)

        if is_active:
            note = self.app_ref.notes.get(data["id"])
            is_visible = note.isVisible() if note else False

            # ── Pin button ───────────────────────────────────────────
            btn_pin = QPushButton()
            btn_pin.setFixedSize(30, 30)
            btn_pin.setToolTip(tr("Always on Top"))
            pin_icon = note._icon_pinned if note else QIcon()

            def refresh_pin_btn(btn, n):
                if _HAS_SVG:
                    btn.setIcon(n._icon_pinned)
                    btn.setIconSize(QSize(16, 16))
                    btn.setText("")
                else:
                    btn.setText("📌")
                if n._pinned:
                    btn.setStyleSheet(f"""
                        QPushButton {{ background: {ink.hover_bg}; border: none;
                            border-radius: 4px; }}
                        QPushButton:hover {{ background: {ink.active_bg}; }}
                    """)
                else:
                    btn.setStyleSheet(f"""
                        QPushButton {{ background: transparent; border: none;
                            border-radius: 4px; }}
                        QPushButton:hover {{ background: {ink.hover_bg}; }}
                    """)

            if note:
                refresh_pin_btn(btn_pin, note)
                # _toggle_pin refreshes the Manager itself, which rebuilds this
                # row — so don't touch btn afterwards (it's been deleted).
                btn_pin.clicked.connect(lambda _, n=note: n._toggle_pin())
            hl.addWidget(btn_pin)
            row._menu_anchor = btn_pin   # right-click Export menu appears left of this

            # ── Lock toggle button ────────────────────────────────────────
            btn_lock = QPushButton()
            btn_lock.setFixedSize(30, 30)
            btn_lock.setToolTip(tr("Lock / Unlock"))

            def refresh_lock_btn(btn, n):
                if _HAS_SVG:
                    btn.setIcon(n._icon_locked if n.locked else n._icon_unlocked)
                    btn.setIconSize(QSize(16, 16))
                    btn.setText("")
                else:
                    btn.setText("🔒" if n.locked else "🔓")
                btn.setStyleSheet(f"""
                    QPushButton {{ background: transparent; border: none; border-radius: 4px; }}
                    QPushButton:hover {{ background: {ink.hover_bg}; }}
                """)
            if note:
                refresh_lock_btn(btn_lock, note)
                def toggle_lock_from_manager(checked, n=note, btn=btn_lock):
                    n.toggle_lock()
                    refresh_lock_btn(btn, n)
                btn_lock.clicked.connect(toggle_lock_from_manager)
            hl.addWidget(btn_lock)

            btn_toggle = QPushButton()
            btn_toggle.setFixedSize(30, 30)
            icon_show = _make_lock_icon(_SVG_EYE_OPEN,   18, fill=ink.icon)
            icon_hide = _make_lock_icon(_SVG_EYE_CLOSED, 18, fill=ink.icon)

            def update_toggle(btn, visible):
                if _HAS_SVG:
                    btn.setIcon(icon_show if visible else icon_hide)
                    btn.setIconSize(QSize(18, 18))
                    btn.setText("")
                else:
                    btn.setText("👁" if visible else "—")
                btn.setToolTip(tr("Hide Note") if visible else "Show Note")

            update_toggle(btn_toggle, is_visible)
            btn_toggle.setStyleSheet(f"""
                QPushButton {{ background: transparent; border: none;
                    border-radius: 4px; }}
                QPushButton:hover {{ background: {ink.hover_bg}; }}
            """)

            def toggle_visibility(checked, n=note, btn=btn_toggle):
                now_hidden = n.isVisible()      # visible now → we're hiding it
                n.set_hidden(now_hidden)         # persists the intent across restarts
                self.app_ref.save_notes()
                update_toggle(btn, not now_hidden)

            if note:
                btn_toggle.clicked.connect(toggle_visibility)
            hl.addWidget(btn_toggle)

            # ── Archive button ────────────────────────────────────────────
            btn_arch = QPushButton()
            btn_arch.setFixedSize(30, 30)
            btn_arch.setToolTip(tr("Archive"))
            _set_btn_icon(btn_arch, _SVG_ARCHIVE, 18, "🗄", fill=ink.icon)
            btn_arch.setStyleSheet(f"""
                QPushButton {{ background: transparent; border: none;
                    border-radius: 4px; }}
                QPushButton:hover {{ background: {ink.hover_bg}; }}
            """)
            btn_arch.clicked.connect(lambda _, nid=data["id"]: self._archive_one(nid))
            hl.addWidget(btn_arch)
        else:
            # Restore button (Archive and Trash both restore to Active).
            restore_fn = (self.app_ref.unarchive_note if kind == "archive"
                          else self.app_ref.restore_from_trash)
            btn_restore = QPushButton(tr("Restore"))
            btn_restore.setFixedSize(68, 30)
            btn_restore.setStyleSheet(f"""
                QPushButton {{ background: {ink.hover_bg}; border: none;
                    border-radius: 4px; font-size: 13px; color: {ink.text}; }}
                QPushButton:hover {{ background: {ink.active_bg}; }}
            """)
            btn_restore.clicked.connect(lambda _, d=data, fn=restore_fn: self._restore_one(d, fn))
            hl.addWidget(btn_restore)
            row._menu_anchor = btn_restore   # archive right-click Export menu anchors here

        btn_del = QPushButton()
        btn_del.setFixedSize(30, 30)
        _set_btn_icon(btn_del, _SVG_TRASH, 18, "🗑", fill=ink.icon)
        btn_del.setStyleSheet(f"""
            QPushButton {{ background: transparent; border: none;
                border-radius: 4px; font-size: 12px; color: {UI.TEXT_MUTED}; }}
            QPushButton:hover {{ background: #e53935; color: white; }}
        """)
        if kind == "active":
            btn_del.setToolTip(tr("Move to Trash"))
            btn_del.clicked.connect(lambda _, nid=data["id"]: (
                self.app_ref.move_note_to_trash(nid), self.refresh()
            ))
        elif kind == "archive":
            btn_del.setToolTip(tr("Move to Trash"))
            btn_del.clicked.connect(lambda _, d=data: (
                self.app_ref.archive_to_trash(d), self.refresh()
            ))
        else:
            btn_del.setToolTip(tr("Delete permanently"))
            btn_del.clicked.connect(lambda _, d=data: self.app_ref.delete_from_trash(d))
        hl.addWidget(btn_del)

        return row

    def refresh(self):
        for lay in (self.active_layout, self.archive_layout, self.trash_layout):
            while lay.count() > 1:
                item = lay.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

        self._active_rows = []
        self._archived_rows = []
        self._trash_rows = []

        # Populate active — favourites first (most recently favourited at top),
        # then the rest. (Pin no longer affects this order; it's desktop-only.)
        sorted_notes = sorted(
            self.app_ref.notes.values(),
            key=lambda n: (0 if n._favorite else 1, -getattr(n, '_fav_time', 0.0))
        )
        for note in sorted_notes:
            data = note.get_data()
            row = self._make_note_row(data, kind="active")
            self.active_layout.insertWidget(self.active_layout.count() - 1, row)
            self._active_rows.append((row, self._note_search_text(data, note)))

        # Populate archive
        for data in self.app_ref.archived_notes:
            row = self._make_note_row(data, kind="archive")
            self.archive_layout.insertWidget(self.archive_layout.count() - 1, row)
            self._archived_rows.append((row, self._note_search_text(data, None)))

        # Populate trash
        for data in self.app_ref.trash_notes:
            row = self._make_note_row(data, kind="trash")
            self.trash_layout.insertWidget(self.trash_layout.count() - 1, row)
            self._trash_rows.append((row, self._note_search_text(data, None)))

        self._apply_filter()   # re-applies any active query + sets counts/labels

    # ── Search ──────────────────────────────────────────────────────────────────
    def _note_search_text(self, data: dict, note) -> str:
        """Full lowercased match text for a note — delegates to the shared helper
        in search.py so the Manager and the global search palette stay in sync."""
        from .search import note_search_text
        return note_search_text(data, note)

    def _apply_filter(self):
        q = self._search.text().strip().lower()
        a_vis = r_vis = t_vis = 0
        for row, text in self._active_rows:
            show = (q in text) if q else True
            row.setVisible(show)
            a_vis += show
        for row, text in self._archived_rows:
            show = (q in text) if q else True
            row.setVisible(show)
            r_vis += show
        for row, text in self._trash_rows:
            show = (q in text) if q else True
            row.setVisible(show)
            t_vis += show

        total_a = len(self._active_rows)
        total_r = len(self._archived_rows)
        total_t = len(self._trash_rows)
        if q:
            self.tabs.setTabText(0, tr("Active ({}/{})").format(a_vis, total_a))
            self.tabs.setTabText(1, tr("Archive ({}/{})").format(r_vis, total_r))
            self.tabs.setTabText(2, tr("Trash ({}/{})").format(t_vis, total_t))
            self._count_lbl.setText(tr("{} matches").format(a_vis + r_vis + t_vis))
        else:
            self.tabs.setTabText(0, tr("Active ({})").format(total_a))
            self.tabs.setTabText(1, tr("Archive ({})").format(total_r))
            self.tabs.setTabText(2, tr("Trash ({})").format(total_t))
            self._count_lbl.setText(tr("{} active · {} archived · {} in trash").format(total_a, total_r, total_t))

