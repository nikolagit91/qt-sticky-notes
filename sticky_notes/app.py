"""The main QApplication subclass: tray, persistence, and note lifecycle."""

import os
import sys
import json
import signal
import subprocess
import uuid
import shlex
import shutil
import datetime

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QLineEdit, QDialog, QComboBox, QCheckBox, QSpinBox, QFileDialog,
    QMessageBox, QSystemTrayIcon, QMenu, QTabWidget, QTabBar, QListWidget,
    QTextEdit, QToolTip, QSlider, QTimeEdit, QFrame,
)
from PyQt6.QtCore import Qt, QTimer, QTime, QUrl, QSize
from PyQt6.QtGui import QFont, QFontDatabase, QPixmapCache, QDesktopServices
from PyQt6 import sip

from .config import (
    DATA_DIR, DATA_FILE, TRASH_FILE, ARCHIVE_FILE, SETTINGS_FILE, APP_VERSION,
    ACTIVE_LIMIT, ARCHIVE_LIMIT, TRASH_LIMIT, DONATE_URL, GITHUB_URL,
)
from .icons import create_tray_icon, checkmark_png_path, about_icon_pixmap, coffee_button_icon
from .theme import (
    UI, apply_theme, settings_dialog_style, message_box_style,
    _btn_primary, _btn_secondary,
)
from .note import StickyNote
from .manager import NotesManager
from .ipc import SingleInstance
from .reminders import ReminderScheduler
from .theme_schedule import ThemeScheduler, coerce_hhmm, scheduled_theme_now
from .i18n import tr, set_language, LANGUAGES


from .app_storage import StorageMixin
from .app_settings import SettingsMixin
from .app_tray import TrayMixin


class StickyNotesApp(StorageMixin, SettingsMixin, TrayMixin, QApplication):

    def __init__(self, argv):
        super().__init__(argv)
        self.setQuitOnLastWindowClosed(False)
        self.setApplicationName("sticky-notes")
        self.setDesktopFileName("sticky-notes")

        # ── Single-instance guard (D-Bus) ─────────────────────────────────────
        # Runs before any heavy init: a second invocation forwards its intent to
        # the already-running instance and exits, instead of starting a duplicate
        # app. This is also what makes the global "new note" hotkey work — the
        # key is bound at the GNOME/compositor level and the launched command is
        # routed here over D-Bus (Wayland blocks in-process key grabs for
        # unfocused windows).
        self._is_secondary = False
        self._ipc = SingleInstance(self)
        if not self._ipc.is_primary:
            if "--new-note" in argv:
                self._ipc.send_new_note()
            elif "--new-note-from-clipboard" in argv:
                self._ipc.send_new_note_from_clipboard()
            elif "--search" in argv:
                self._ipc.send_search()
            else:
                self._ipc.send_raise()   # plain re-launch → surface existing notes
            self._is_secondary = True
            return

        self.setWindowIcon(create_tray_icon())
        # Global tooltip style — without this, translucent note windows render
        # tooltips with a black background
        self.setStyleSheet("""
            QToolTip {
                background-color: #2b2b2b;
                color: #f0f0f0;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 2px 6px;
                font-size: 14px;
            }
        """)
        self.notes: dict[str, StickyNote] = {}
        self.trash_notes: list[dict] = []
        self.archived_notes: list[dict] = []
        self._storage_alerts: list[str] = []   # user-facing messages from corrupt-file recovery
        self._notes_load_failed = False         # suppress the welcome note if notes couldn't load
        self._manager = None
        self._search_palette = None
        self._open_windows: list = []           # non-modal top-level dialogs (settings/about)
        self._backup_interval_minutes = 0
        self._autostart_enabled = True          # default; overwritten by _load_backup_settings
        self._ui_scale = 1.0                    # default; overwritten by _load_backup_settings
        self._hotkey_enabled = True             # default ON; overwritten by _load_backup_settings
        self._hotkey_binding = "<Super><Alt>n"  # GTK accelerator; overwritten by settings.
                                                # Must match hotkey.NEW_NOTE.default_binding
                                                # — plain Super+N is eaten by GNOME's overview.
        self._hotkey_clip_enabled = True        # "new note from clipboard" shortcut
        self._hotkey_clip_binding = "<Super><Shift>n"
        self._hotkey_search_enabled = True      # global "search notes" palette shortcut
        self._hotkey_search_binding = "<Super><Shift>f"
        self._language = "en"                   # UI language; overwritten by settings below
        self._snap_to_grid  = True              # snap note position to a grid (default ON)
        self._snap_to_notes = False             # snap note position to other notes' edges
        self._snap_size     = True              # snap note size to the grid (default ON)
        self._grid_size     = 20                # grid cell size in px
        self._tray_scroll_enabled = True        # scroll tray icon → raise visible notes (default ON)
        # Use actual system font as default
        self._default_font_family = self.font().family() or "Ubuntu"
        self._default_note_width  = 440   # overwritten by _load_backup_settings
        self._default_note_height = 300
        self._note_opacity        = 100   # background opacity %, applies to all notes
        self._auto_contrast       = True  # adapt chrome/text colour to note bg (default ON)
        self._clean_mode          = False  # auto-hide header/toolbar until hovered (default OFF)
        self._code_blocks         = False  # show the { } code-block button (default OFF)
        self._note_border         = "off"  # note border mode: off/always/auto (default off)
        self._pending_restart     = False  # a restart-only setting (scale/language) changed
        self._pending_ui_scale    = None   # staged UI scale; applied+saved only on Restart
        self._pending_language    = None   # staged language; applied+saved only on Restart
        self._theme               = "light"  # EFFECTIVE chrome theme: only ever "light"/"dark"
        self._theme_mode          = "light"  # what the user picked: "light"/"dark"/"auto"
        self._theme_dark_start    = "20:00"  # auto mode: dark period start (HH:MM)
        self._theme_dark_end      = "07:00"  # auto mode: dark period end   (HH:MM)
        self._theme_override      = None     # manual flip while in auto; MEMORY ONLY
        self._default_font_size   = 13
        self._backup_timer = QTimer(self)
        self._backup_timer.timeout.connect(self._force_backup)

        # Global save scheduler — max one save per second regardless of note count
        self._global_save_timer = QTimer(self)
        self._global_save_timer.setSingleShot(True)
        self._global_save_timer.setInterval(1000)
        self._global_save_timer.timeout.connect(self._do_save)

        # Periodic autosave — safety net in case of crash
        self._autosave_timer = QTimer(self)
        self._autosave_timer.setInterval(30000)
        self._autosave_timer.timeout.connect(self._do_save)
        self._autosave_timer.start()

        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT,  self._handle_signal)

        # Load the saved UI language BEFORE building the tray/notes so every
        # widget is created in the right language. (The rest of the settings
        # load just below; the language is read again there for consistency.)
        try:
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, encoding="utf-8") as _f:
                    _early = json.load(_f)
                    self._language = _early.get("language", self._language)
                    _mode = _early.get("theme", self._theme_mode)
                    self._theme_mode = _mode if _mode in ("light", "dark", "auto") else "light"
                    self._theme_dark_start = coerce_hhmm(
                        _early.get("theme_dark_start", self._theme_dark_start), self._theme_dark_start)
                    self._theme_dark_end = coerce_hhmm(
                        _early.get("theme_dark_end", self._theme_dark_end), self._theme_dark_end)
        except Exception:
            pass
        set_language(self._language)
        # Auto mode: the app must be BORN in the scheduled theme (no flash of the
        # wrong one) — compute the effective theme before the first apply.
        if self._theme_mode == "auto":
            self._theme = scheduled_theme_now(self._theme_dark_start, self._theme_dark_end)
        else:
            self._theme = self._theme_mode
        apply_theme(self._theme)   # chrome palette must be set before any window is built

        self._build_tray()
        self._load_backup_settings()   # must run BEFORE _ensure_autostart to read saved preference
        self._apply_base_font()
        self._ensure_autostart()
        self._ensure_global_hotkey()
        self._load_trash_notes()
        self._load_archived_notes()
        self._load_notes()
        self._migrate_old_bak()   # one-time: fold legacy <file>.bak into the backups/ folder

        # Reminders fire while the app runs; start polling once notes are loaded.
        self._reminders = ReminderScheduler(self)
        self._reminders.start()
        self._theme_scheduler = ThemeScheduler(self)
        self._theme_scheduler.start()

        if "--new-note" in argv:
            # Cold start triggered by the global hotkey (app wasn't running yet):
            # open a fresh note on top of whatever loaded, so the key behaves the
            # same whether or not the app was already running.
            self.create_new_note()
        elif "--new-note-from-clipboard" in argv:
            self.create_note_from_clipboard()
        elif not self.notes and not self._notes_load_failed and "--search" not in argv:
            self.create_new_note()

        # A data file was corrupt — tell the user (once the event loop is up)
        # where the damaged file went and whether a backup was used.
        if self._storage_alerts:
            QTimer.singleShot(0, self._report_storage_alerts)

        if "--search" in argv:
            # Cold start from the global search shortcut → open the palette.
            QTimer.singleShot(0, self.show_search)

        if "--open-settings" in argv:
            # Relaunched from the Settings 'Restart now' button — reopen Settings
            # so the user lands back where they were and sees the change applied.
            QTimer.singleShot(0, self.show_settings)

    def _handle_signal(self, signum, frame):
        QTimer.singleShot(0, self.quit_app)

    def _default_note_color(self) -> str:
        """Starting fill for a brand-new note, per the active chrome theme.
        Dark theme starts notes dark; auto-contrast makes them readable.

        NOT the path create_new_note takes. Since per-theme note colours landed,
        a new note gets `color="#fff59d"` + an empty dark slot, and _effective_color
        derives the dark default at paint time — so the value below is computed a
        second time, independently, further down. Keep the two in step: this method
        is what test_theme_startup / test_dark_palette assert against, so changing
        the dark default in only one of the two places fails there rather than
        silently shipping two different "defaults"."""
        return "#2b2b30" if self._theme == "dark" else "#fff59d"

    # ── Tray ──────────────────────────────────────────────────────────────────
    def create_new_note(self, content: str = "", color: str = None, color_dark: str = None, width: int = None, height: int = None, origin: "StickyNote" = None) -> "StickyNote":
        if len(self.notes) >= ACTIVE_LIMIT:
            msg = QMessageBox()
            msg.setWindowTitle(tr("Limit Reached"))
            msg.setText(tr("Maximum of {} active notes reached.\nArchive or move some notes to Trash before creating new ones.").format(ACTIVE_LIMIT))
            msg.setIcon(QMessageBox.Icon.Information)
            msg.exec()
            msg.deleteLater()
            return None
        w = width  or self._default_note_width
        h = height or self._default_note_height
        # Light slot always defaults to yellow; the dark slot defaults to "" which
        # _effective_color renders as the dark default (#2b2b30) in dark mode — so a
        # new note is right in whichever mode it's created, no theme check needed.
        data = {"content": content, "color": color or "#fff59d",
                "color_dark": color_dark or "", "geometry": [0, 0, w, h]}
        note = StickyNote(self, data=data)
        self.notes[note.note_id] = note
        # Apply default font only on empty notes — don't override existing HTML formatting
        if not content:
            font = QFont(self._default_font_family)
            font.setPointSize(self._default_font_size)
            note.text_edit.setFont(font)
            note._font_size = self._default_font_size
            note.font_size_label.setText(str(self._default_font_size))
        # Cascade diagonally from centre — wraps every 10 notes
        screen = self.primaryScreen().availableGeometry()
        n    = len(self.notes) - 1   # 0-based index (note already added above)
        step = 30
        cx = screen.center().x() - note.width()  // 2 + (n % 10) * step
        cy = screen.center().y() - note.height() // 2 + (n % 10) * step
        cx = max(screen.left(), min(cx, screen.right()  - note.width()))
        cy = max(screen.top(),  min(cy, screen.bottom() - note.height()))
        note.move(cx, cy)
        note.show()
        self._bring_to_front(note)
        # A user-created note IS meant to be typed into right away. Notes no
        # longer auto-focus on activation (that caused a spurious caret at login),
        # so ask for it explicitly here — this path is only ever user-initiated
        # (tray New Note, the --new-note hotkey, duplicate); the login restore
        # path builds notes directly and stays passive.
        note.text_edit.setFocus()
        self.save_notes()
        self._refresh_manager()
        return note

    def create_note_from_clipboard(self) -> "StickyNote":
        """Create a new note pre-filled with the clipboard contents. The insert
        goes through the editor's normal paste path, so a copied URL becomes a
        clickable link, file/folder paths become file links, etc."""
        note = self.create_new_note()
        if note is None:
            return None
        md = self.clipboard().mimeData()
        if md is not None and (md.hasText() or md.hasUrls() or md.hasHtml()):
            note.text_edit.insertFromMimeData(md)
            self.save_notes()
        note.text_edit.setFocus()
        self._bring_to_front(note)
        return note

    def _push_trash(self, data: dict):
        """Insert into Trash (newest first) and enforce the FIFO cap — the oldest
        trashed note is evicted once past TRASH_LIMIT (it's already on its way
        out, so this loses nothing the user meant to keep)."""
        self.trash_notes.insert(0, data)
        del self.trash_notes[TRASH_LIMIT:]
        self._save_trash_notes()

    def _close_note_widget(self, note):
        """Tear down a live note widget (hide, stop its timers, schedule Qt
        destruction). Shared by the Trash and Archive paths."""
        note.hide()
        note.stop_timers()      # all six — see StickyNote.stop_timers
        note.deleteLater()

    def move_note_to_trash(self, note_id: str):
        """Move note to Trash (FIFO-capped at TRASH_LIMIT). Deleting a note no
        longer re-raises the other notes — each note is an independent window and
        stays where it is (deleting one shouldn't yank the rest to the front)."""
        if note_id not in self.notes:
            return
        note = self.notes[note_id]
        self._push_trash(note.get_data())
        self._close_note_widget(note)
        del self.notes[note_id]
        self.save_notes()
        self._refresh_manager()
        QTimer.singleShot(2000, self._trim_memory)

    def restore_from_trash(self, note_data: dict) -> bool:
        """Restore a note from Trash back to Active. Returns False (without
        restoring) if Active is already at ACTIVE_LIMIT, so nothing is silently
        dropped; the caller surfaces the reason."""
        if len(self.notes) >= ACTIVE_LIMIT:
            return False
        note = StickyNote(self, note_data.get("id"), note_data)
        self.notes[note.note_id] = note
        self.trash_notes = [n for n in self.trash_notes if n["id"] != note_data["id"]]
        self._save_trash_notes()
        note.set_hidden(False)     # a restored note is shown (clear a stale hidden flag)
        self.save_notes()
        self._refresh_manager()
        return True

    # ── Archive ───────────────────────────────────────────────────────────────
    def delete_from_trash(self, note_data: dict):
        """Permanently remove one note from Trash. Clean entry point so the
        Manager doesn't mutate `trash_notes` / call the private saver itself."""
        nid = note_data.get("id")
        self.trash_notes = [n for n in self.trash_notes if n.get("id") != nid]
        self._save_trash_notes()
        self._refresh_manager()

    def empty_trash(self):
        """Permanently remove every note from Trash."""
        self.trash_notes.clear()
        self._save_trash_notes()
        self._refresh_manager()

    def archive_note(self, note_id: str) -> bool:
        """Archive an active note: keep it (data preserved) but close its window,
        exactly like Trash except restorable to Active and never auto-evicted.
        HARD stop — returns False (without archiving) if Archive is full.
        Like Trash, archiving one note no longer re-raises the others."""
        if note_id not in self.notes:
            return False
        if len(self.archived_notes) >= ARCHIVE_LIMIT:
            return False
        note = self.notes[note_id]
        self.archived_notes.insert(0, note.get_data())
        self._save_archived_notes()
        self._close_note_widget(note)
        del self.notes[note_id]
        self.save_notes()
        self._refresh_manager()
        QTimer.singleShot(2000, self._trim_memory)
        return True

    def unarchive_note(self, note_data: dict) -> bool:
        """Restore a note from Archive back to Active. Returns False (without
        restoring) if Active is at ACTIVE_LIMIT."""
        if len(self.notes) >= ACTIVE_LIMIT:
            return False
        note = StickyNote(self, note_data.get("id"), note_data)
        self.notes[note.note_id] = note
        self.archived_notes = [n for n in self.archived_notes if n["id"] != note_data["id"]]
        self._save_archived_notes()
        note.set_hidden(False)     # an unarchived note is shown (clear a stale hidden flag)
        self.save_notes()
        self._refresh_manager()
        return True

    def archive_to_trash(self, note_data: dict):
        """Move an archived note straight into Trash (Archive → Trash), applying
        the Trash FIFO cap. No Active slot is used, so no limit check needed."""
        self.archived_notes = [n for n in self.archived_notes if n["id"] != note_data["id"]]
        self._save_archived_notes()
        self._push_trash(note_data)
        self._refresh_manager()

    def _apply_note_opacity(self):
        """Re-derive every note's colours at the current background opacity and
        repaint. Called live from the Settings slider so the change is visible
        immediately across all open notes (each note reads self._note_opacity).

        Uses the note's alpha-only path: the slider emits on every step of a
        drag, and a full re-ink per note made that unusable at 50 notes (see
        StickyNote._apply_opacity)."""
        for n in self.notes.values():
            n._apply_opacity()

    def _apply_auto_contrast(self):
        """Re-ink every open note after the auto-contrast setting is toggled
        (each note reads self._auto_contrast via _apply_ink)."""
        for n in self.notes.values():
            n._apply_ink()

    def _apply_clean_mode(self):
        """Push the clean-mode setting to every open note (each collapses or
        restores its chrome via _set_clean_mode)."""
        for n in self.notes.values():
            n._set_clean_mode(self._clean_mode)

    def _apply_note_border(self):
        """Repaint every open note after the border toggle changes (each note's
        paintEvent reads self._note_border)."""
        for n in self.notes.values():
            n.update()

    def _set_theme(self, name: str) -> None:
        """Historical entry point: pick a FIXED theme. Kept because existing
        tests and call sites use it; new code goes through _set_theme_mode."""
        self._set_theme_mode("dark" if name == "dark" else "light")

    def _set_theme_mode(self, mode: str) -> None:
        """User picked Light / Dark / Auto (Settings combo; tray in fixed mode).
        Persists the MODE; the effective theme follows from it. A mode change
        ends any temporary override."""
        mode = mode if mode in ("light", "dark", "auto") else "light"
        if mode == self._theme_mode:
            return
        self._theme_mode = mode
        self._theme_override = None
        effective = (scheduled_theme_now(self._theme_dark_start, self._theme_dark_end)
                     if mode == "auto" else mode)
        if effective != self._theme:
            self._apply_effective_theme(effective)   # saves at the end
        else:
            self._save_backup_settings()             # mode changed, look didn't

    def _apply_effective_theme(self, name: str) -> None:
        """Switch the EFFECTIVE theme live (no restart). Does NOT touch
        _theme_mode: in auto mode the schedule/override decide the look while
        settings keep saying "auto" — saving here persists mode+times only."""
        name = "dark" if name == "dark" else "light"
        if name == self._theme:
            return
        self._theme = name
        self._apply_theme_live(name)
        self._save_backup_settings()

    def _toggle_theme(self) -> None:
        """Tray 'Toggle theme'. Fixed mode: flip the mode, as it always did.
        Auto mode: a TEMPORARY override until the next schedule boundary — the
        mode stays 'auto' and the flip never touches the disk (user decision,
        spec 2026-07-20 §3)."""
        opposite = "light" if self._theme == "dark" else "dark"
        if self._theme_mode == "auto":
            self._theme_override = opposite
            self._apply_effective_theme(opposite)
        else:
            self._set_theme_mode(opposite)

    def _apply_theme_live(self, name: str) -> None:
        """Apply the theme to the OPEN ui in place — swap the palette, re-ink
        every note, rebuild the content of open chrome windows (Settings/Manager)
        inside their existing top-level window, and update the tray icon. Never
        recreates a top-level window (that is what dropped the dock icon)."""
        apply_theme(name)
        for n in self.notes.values():
            n._reapply_theme()
        # Rebuild open chrome windows' CONTENT in place. Deferred so a toggle
        # fired from a widget inside one of them (the Settings combobox) doesn't
        # tear its tree down mid-signal. Windows that don't opt in (no _retheme)
        # simply pick up the theme next time they are opened.
        for w in list(self._open_windows):
            hook = getattr(w, "_retheme", None)
            if hook is not None:
                QTimer.singleShot(0, lambda win=w, h=hook: self._run_if_alive(win, h))
        if self._manager is not None and hasattr(self._manager, "retheme"):
            mgr = self._manager
            QTimer.singleShot(0, lambda m=mgr: self._run_if_alive(m, m.retheme))
        palette = getattr(self, "_search_palette", None)
        if palette is not None:
            QTimer.singleShot(0, lambda w=palette: self._run_if_alive(w, w.retheme))
        self._update_tray_icon(name == "dark")

    @staticmethod
    def _run_if_alive(widget, fn):
        """Run `fn` only while `widget`'s underlying C++ object still exists.

        The theme rebuilds above are DEFERRED (singleShot), so the window can be
        closed — and destroyed — between scheduling and firing; the bound method
        keeps working long enough to touch a dead QWidget and raise RuntimeError.

        Note this must be sip.isdeleted: the `getattr(self, "_x", None)` idiom
        does NOT detect a deleted Qt object (it returns a live Python wrapper,
        and evaluating it raises from inside getattr itself)."""
        if not sip.isdeleted(widget):
            fn()

    def _apply_code_blocks(self):
        """Show/hide the code-block buttons on every open note (opt-in feature;
        existing code blocks keep rendering regardless)."""
        for n in self.notes.values():
            n.btn_code.setVisible(self._code_blocks)
            n.btn_inline_code.setVisible(self._code_blocks)

    def _ensure_on_screen(self, widget):
        """If the widget sits entirely outside every connected screen (e.g. it
        was saved on a monitor that's since been unplugged, or the layout
        changed), clamp it back onto the primary screen so it can't get
        stranded off-view. No-op while it's at least partially visible."""
        try:
            frame = widget.frameGeometry()
        except RuntimeError:
            return
        for scr in QApplication.screens():
            if scr.availableGeometry().intersects(frame):
                return   # visible on some screen — leave it alone
        avail = self.primaryScreen().availableGeometry()
        x = min(max(widget.x(), avail.left()), max(avail.left(), avail.right()  - widget.width()))
        y = min(max(widget.y(), avail.top()),  max(avail.top(),  avail.bottom() - widget.height()))
        widget.move(x, y)

    def _bring_to_front(self, widget):
        """Bring widget to front. For note windows, show() re-detaches them from
        the shared X11 group (showEvent) so Mutter won't lift every note; then
        raise_/activateWindow surfaces it. Deliberately NOT the old always-on-top
        flag toggle — that recreated the native window, which (a) left a
        pinned-then-unpinned note unable to reappear on Show All and (b) lifted
        the whole note group (Qt re-attaches a recreated window to the shared
        leader, undoing the per-note detach). Same surface pattern the search
        palette uses, and it never recreates the window."""
        try:
            widget.show()
            self._ensure_on_screen(widget)   # rescue notes stranded on an unplugged monitor
            widget.raise_()
            widget.activateWindow()
        except RuntimeError:
            pass

    def show_all_notes(self):
        """Manager has last word — show every note regardless of pin or lock state."""
        for n in self.notes.values():
            n.set_hidden(False)
        self.save_notes()          # persist so they stay shown across restarts
        self._refresh_manager()

    def raise_visible_notes(self):
        """Bring every visible (non-hidden), non-pinned note to the front.

        Triggered by the tray scroll-up gesture. Pinned notes are already
        always-on-top so they're left untouched; hidden notes stay hidden (this
        does NOT un-hide anything or change any persisted state). Uses the same
        per-note bring-to-front as Show All, which reliably fronts notes above
        other windows on GNOME. Dropping notes back behind a window is left to
        the user (click a work window) — that is the only reliable path here."""
        for n in self.notes.values():
            if not n._hidden and not n._pinned:
                self._bring_to_front(n)

    def show_search(self):
        """Open the global quick-search palette (reused across invocations)."""
        if getattr(self, "_search_palette", None) is None:
            from .search_palette import SearchPalette
            self._search_palette = SearchPalette(self)
        p = self._search_palette
        p.search.clear()
        p._refresh()
        p.show()
        p.raise_()
        p.activateWindow()
        p.search.setFocus()

    def reveal_note(self, note):
        """Surface a single note: restore it if minimized, then bring it to the
        front (used when a search result is chosen)."""
        try:
            if note.isMinimized():
                note.showNormal()
        except RuntimeError:
            return
        note.set_hidden(False)     # revealing a hidden note un-hides it (persisted)
        self.save_notes()

    def _refresh_manager(self):
        """Refresh the Notes Manager iff it's open. Single choke point so every
        mutation keeps it in sync without repeating the visibility guard — a
        forgotten copy of that guard is exactly what caused the pin-sync bug."""
        if self._manager is not None and self._manager.isVisible():
            self._manager.refresh()

    def show_manager(self):
        if self._manager is None:
            self._manager = NotesManager(self)
            # NOTE: no re-raise of notes when the Manager closes — same reasoning
            # as Settings/About: closing it should return to whatever was behind
            # it, not pull every note to the front of other apps.
        self._manager.refresh()
        screen = self.primaryScreen().availableGeometry()
        self._manager.move(
            screen.center().x() - self._manager.width()  // 2,
            screen.center().y() - self._manager.height() // 2,
        )
        # The Manager and the Settings/About dialogs are all NORMAL-type windows
        # now (see NotesManager.__init__ and _show_window), so the WM stacks them
        # by raise order instead of keeping DIALOG-type windows above the Manager
        # (which is what made it sink behind an open Settings). raise/activate then
        # decides the order.
        self._bring_to_front(self._manager)

    def _reconcile_pin_stacking(self):
        """Re-detach every visible note so the window manager stops stacking them
        together. Qt marks each note WM_TRANSIENT_FOR a shared leader window, and
        Mutter keeps all transients of one parent stacked together — so pinning
        one note (which gets _NET_WM_STATE_ABOVE) drags its transient siblings up
        too. Re-detaching each note clears that transient relationship (see
        x11.detach_window_group), making them independent top-levels.

        Runs deferred after a pin toggle: pinning recreates the pinned window
        (setFlags), which makes Qt re-set WM_TRANSIENT_FOR on it, and can prompt
        the WM to re-group — so we clear it again once things have settled.
        """
        for n in list(self.notes.values()):
            try:
                if n.isVisible():
                    n._detach_group()
            except (RuntimeError, ValueError):
                pass

    def hide_all_notes(self):
        """Manager has last word — hide every note regardless of pin or lock state."""
        for n in self.notes.values():
            n.set_hidden(True)
        self.save_notes()          # persist so they stay hidden across restarts
        self._refresh_manager()

    def lock_all_notes(self):
        for n in self.notes.values():
            n.locked = True
            n._apply_state()
        self.save_notes()
        self._refresh_manager()

    def unlock_all_notes(self):
        for n in self.notes.values():
            n.locked = False
            n._apply_state()
        self.save_notes()
        self._refresh_manager()

    # ── Autostart ─────────────────────────────────────────────────────────────
    def _ensure_autostart(self):
        """Create or remove ~/.config/autostart entry based on self._autostart_enabled."""
        autostart_dir  = os.path.expanduser("~/.config/autostart")
        autostart_file = os.path.join(autostart_dir, "sticky_notes.desktop")
        # Parent of the sticky_notes/ package dir — the folder `-m sticky_notes`
        # must run from. (app.py -> sticky_notes/ -> parent)
        pkg_parent     = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        wrapper_path   = os.path.join(DATA_DIR, "start.sh")

        os.makedirs(autostart_dir, exist_ok=True)
        os.makedirs(os.path.dirname(wrapper_path), exist_ok=True)

        # Wrapper script + app .desktop are always kept (needed for app launcher).
        # NOTE: must launch the package via `-m sticky_notes`, NOT `python3 app.py`
        # — app.py uses relative imports and crashes if run as a top-level script.
        # "$@" forwards args so the global hotkey can pass --new-note through it.
        wrapper = f"""#!/bin/bash
unset DESKTOP_STARTUP_ID
cd {shlex.quote(pkg_parent)} || exit 1
exec /usr/bin/env python3 -m sticky_notes "$@"
"""
        try:
            with open(wrapper_path, "w") as f:
                f.write(wrapper)
            os.chmod(wrapper_path, 0o755)
        except Exception as e:
            print(f"[autostart] could not write wrapper: {e}")

        # Save icon for the desktop entry (the GNOME dash/dock icon via .desktop
        # Icon=). Kept as the single, consistent brand icon regardless of theme:
        # GNOME Shell (esp. Wayland) caches the dash icon by app-id and won't
        # refresh it live — a theme-switching dock icon is not achievable from the
        # app (confirmed), and a stable icon beats one stuck mid-switch. The tray
        # icon (pushed live via Ayatana) is themed separately.
        icon_path = os.path.join(DATA_DIR, "icon.png")
        try:
            create_tray_icon().pixmap(128, 128).save(icon_path)
        except Exception:
            pass

        app_desktop_dir  = os.path.expanduser("~/.local/share/applications")
        app_desktop_file = os.path.join(app_desktop_dir, "sticky-notes.desktop")
        os.makedirs(app_desktop_dir, exist_ok=True)

        app_desktop = f"""[Desktop Entry]
Type=Application
Name=Sticky Notes
Comment=Lightweight sticky notes for Ubuntu
Exec={shlex.quote(wrapper_path)}
Icon={icon_path}
StartupWMClass=sticky-notes
Categories=Utility;
"""
        try:
            with open(app_desktop_file, "w") as f:
                f.write(app_desktop)
        except Exception as e:
            print(f"[autostart] could not write app desktop: {e}")

        # Autostart entry: create if enabled, remove if disabled
        if self._autostart_enabled:
            desktop_entry = f"""[Desktop Entry]
Type=Application
Name=Sticky Notes
Comment=Lightweight sticky notes for Ubuntu
Exec={shlex.quote(wrapper_path)}
Icon={icon_path}
Hidden=false
NoDisplay=false
StartupNotify=false
StartupWMClass=sticky-notes
X-GNOME-Autostart-enabled=true
"""
            try:
                with open(autostart_file, "w") as f:
                    f.write(desktop_entry)
            except Exception as e:
                print(f"[autostart] could not write: {e}")
        else:
            try:
                if os.path.exists(autostart_file):
                    os.remove(autostart_file)
            except Exception as e:
                print(f"[autostart] could not remove: {e}")

    # ── Global hotkey ─────────────────────────────────────────────────────────
    def _ensure_global_hotkey(self):
        """Register or remove our GNOME shortcuts to match the saved preferences.

        On startup we only *create* a shortcut when it is missing — if it already
        exists we leave its binding alone, so a key the user changed via GNOME
        Settings is respected rather than reset on every launch.
        """
        from . import hotkey
        if not hotkey.is_supported():
            return
        # Never touch the user's real GNOME keybindings from a headless/offscreen
        # run (tests, smokes) — that once wrote a temp DATA_DIR path into the live
        # search shortcut and silently broke it.
        if self.platformName() == "offscreen":
            return
        self._sync_hotkey(hotkey.NEW_NOTE, self._hotkey_enabled, "_hotkey_binding")
        self._sync_hotkey(hotkey.NEW_NOTE_CLIP, self._hotkey_clip_enabled,
                          "_hotkey_clip_binding")
        self._sync_hotkey(hotkey.SEARCH, self._hotkey_search_enabled,
                          "_hotkey_search_binding")

    def _sync_hotkey(self, hk, enabled: bool, binding_attr: str):
        from . import hotkey
        is_registered, current = hotkey.get_state(hk)
        if enabled:
            if not is_registered:
                hotkey.register(hk, getattr(self, binding_attr))
            elif getattr(hk, "migrate_from", None) and current == hk.migrate_from:
                # The live accelerator is a superseded default the user never
                # really chose (bare <Super>n — GNOME's overview eats it). Upgrade
                # it to the current default instead of adopting it, and persist so
                # the Settings hint and settings.json agree. Only the EXACT old
                # value migrates; any other accelerator is a real user choice.
                if hotkey.register(hk, hk.default_binding):
                    setattr(self, binding_attr, hk.default_binding)
                    self._save_backup_settings()
            else:
                if current:
                    setattr(self, binding_attr, current)   # respect a binding changed elsewhere
                # Self-heal a stale COMMAND (e.g. app moved, or a headless test
                # once wrote a temp path into dconf) while keeping the user's
                # accelerator — otherwise the shortcut silently runs a dead path.
                if not hotkey.command_is_current(hk):
                    hotkey.register(hk, current or getattr(self, binding_attr))
        elif is_registered:
            hotkey.unregister(hk)

    # ── Dialogs ───────────────────────────────────────────────────────────────
    def _apply_base_font(self):
        """Set the base application font at its unscaled size. The actual UI
        scaling is done by Qt's high-DPI scaling (QT_SCALE_FACTOR), set from the
        saved scale at startup — so text, fixed sizes and vector icons all scale
        crisply and uniformly, and this font stays at its base 13pt."""
        base_font = self.font()
        base_font.setPointSizeF(13)
        self.setFont(base_font)

    def _snap_enabled(self) -> bool:
        """True if any snap mode is on — notes only run snap logic when it is."""
        return self._snap_to_grid or self._snap_to_notes or self._snap_size

    def restart(self, reopen_settings: bool = False):
        """Relaunch the app to apply settings that only take effect at startup
        (UI scale, language). Spawns a detached watcher that waits for THIS
        process to fully exit — which releases the single-instance D-Bus name —
        and only then starts a fresh instance, then quits. Waiting for the real
        exit (rather than a fixed delay) avoids a race where the new instance
        would see the old name still owned and merely forward + exit.

        reopen_settings: pass --open-settings to the new instance so it reopens
        the Settings window — used by the Settings 'Restart now' button so the
        user lands back where they were and sees the change applied."""
        self._save_backup_settings()
        self.save_notes()
        try:
            pid = os.getpid()
            py = sys.executable
            extra = " --open-settings" if reopen_settings else ""
            cmd = (f'while kill -0 {pid} 2>/dev/null; do sleep 0.05; done; '
                   f'exec "{py}" -m sticky_notes{extra}')
            subprocess.Popen(["sh", "-c", cmd], start_new_session=True)
        except Exception as e:
            print(f"[restart] could not relaunch: {e}")
            return
        self.quit()

    def _show_window(self, dlg):
        """Show a top-level dialog non-modally so it never blocks other windows
        (the manager, other dialogs). Tracked so it stays alive until closed."""
        dlg.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        # Make these helper dialogs NORMAL-type windows (not Qt's default DIALOG
        # type) with explicit min/max/close hints. Two reasons: (1) so the WM
        # stacks them with the Manager by raise order instead of keeping DIALOG
        # windows pinned above the (normal) Manager — the "Manager opens behind
        # Settings" bug; (2) a bare DIALOG window on GNOME only gets a close button,
        # so its minimize/maximize buttons didn't work. Set before show(): the WM
        # reads the window type at map time.
        dlg.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.WindowMinimizeButtonHint
            | Qt.WindowType.WindowMaximizeButtonHint
            | Qt.WindowType.WindowCloseButtonHint
        )
        self._open_windows.append(dlg)

        def _on_destroyed(*_):
            if dlg in self._open_windows:
                self._open_windows.remove(dlg)
            # NOTE: deliberately no re-raise of notes here. Closing a transient
            # dialog (Settings/About) should return focus/stacking to whatever
            # was behind it — e.g. a maximized browser — not yank every note in
            # front of it. (Pinning a note is the way to keep it always on top.)

        dlg.destroyed.connect(_on_destroyed)
        dlg.show()
        dlg.raise_()
        dlg.activateWindow()

    def _raise_if_open(self, title: str) -> bool:
        """If a tracked window with this title is already open, focus it."""
        for w in self._open_windows:
            if w.windowTitle() == title and w.isVisible():
                w.raise_()
                w.activateWindow()
                return True
        return False

    def _apply_pending_and_restart(self):
        """Commit the staged restart-only settings (scale/language), then restart.
        These are staged rather than applied live: scale needs a fresh
        QT_SCALE_FACTOR and language is bound at startup, so both take effect only
        on the relaunch. Closing Settings instead discards them (never saved)."""
        if self._pending_ui_scale is not None:
            self._ui_scale = self._pending_ui_scale
        if self._pending_language is not None:
            self._language = self._pending_language
            set_language(self._language)
        self._save_backup_settings()
        self.restart(reopen_settings=True)

    def show_settings(self):
        if self._raise_if_open(tr("Settings")):
            return
        # Fresh open discards any restart-only change that was staged but not
        # applied (the user closed last time without restarting). A live-theme
        # rebuild goes through _build_settings_content, NOT here, so an in-progress
        # staged change survives a retheme.
        self._pending_restart = False
        self._pending_ui_scale = None
        self._pending_language = None
        dlg = QDialog()
        self._build_settings_content(dlg)
        # Open at the size the built content needs. The hint labels are word-
        # wrapped, so their height depends on a width Qt doesn't know at show()
        # time; leaving the initial size to the show-time sizeHint let GNOME
        # under-size the window and squash the current tab toward its minimum
        # (the intermittent "Settings opens squished"). Pinning the geometry here
        # — on first open only, not in _build_settings_content, which also runs on
        # a live retheme and must not stomp a size the user chose — makes it
        # deterministic. sizeHint spans the tallest tab, so every tab fits.
        # Width, though, can undershoot the tab bar's own width in longer-label
        # languages (German/French) — that would show scroll arrows — so widen to
        # fit the tab bar plus the layout margins whenever the hint falls short.
        hint = dlg.sizeHint()
        tabbar_w = dlg._tabs.tabBar().sizeHint().width()
        margins = 2 * 16 + 6   # main_layout L+R contentsMargins + small slack
        dlg.resize(max(hint.width(), tabbar_w + margins), hint.height())
        self._show_window(dlg)

    def _build_settings_content(self, dlg, active_tab=0):
        # Clear prior content so this can rebuild in place on a live theme change
        # (the top-level dialog is kept — never recreated → the dock icon is safe).
        old = dlg.layout()
        if old is not None:
            QWidget().setLayout(old)      # reparents the old layout + children → deleted
        dlg.setWindowTitle(tr("Settings"))
        dlg.setMinimumWidth(560)
        dlg.setMinimumHeight(280)
        dlg.setStyleSheet(settings_dialog_style(checkmark_png_path()))

        main_layout = QVBoxLayout(dlg)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        tabs = QTabWidget()
        tabs.setStyleSheet(f"""
            QTabWidget::pane {{ border: 1px solid {UI.BORDER}; border-radius: 6px; }}
            QTabBar::tab {{ padding: 7px 18px; border-radius: 4px; font-size: 13px;
                color: {UI.TEXT_MUTED}; }}
            QTabBar::tab:selected {{ background: {UI.SURFACE}; color: {UI.TEXT}; }}
        """)

        # ── General tab ───────────────────────────────────────────────────────
        general_tab = QWidget()
        gl = QVBoxLayout(general_tab)
        gl.setContentsMargins(16, 16, 16, 16)
        gl.setSpacing(14)

        autostart_row = QHBoxLayout()
        autostart_chk = QCheckBox(tr("Start automatically on login"))
        autostart_chk.setChecked(self._autostart_enabled)
        autostart_chk.setStyleSheet(f"""
            QCheckBox {{ font-size: 13px; color: {UI.TEXT}; }}
            QCheckBox::indicator {{ width: 18px; height: 18px; }}
        """)
        autostart_hint = QLabel(tr("Creates an autostart entry in ~/.config/autostart/"))
        autostart_hint.setStyleSheet(UI.HINT_STYLE)

        def on_autostart_changed(state):
            self._autostart_enabled = (state == 2)   # Qt.CheckState.Checked == 2
            self._ensure_autostart()
            self._save_backup_settings()

        autostart_chk.stateChanged.connect(on_autostart_changed)
        gl.addWidget(autostart_chk)
        gl.addWidget(autostart_hint)

        # ── Global hotkey ─────────────────────────────────────────────────────
        from . import hotkey as _hotkey
        gl.addSpacing(8)
        _hk_supported = _hotkey.is_supported()

        hotkey_chk = QCheckBox(tr("Global shortcut for new note"))
        hotkey_chk.setChecked(self._hotkey_enabled and _hk_supported)
        hotkey_chk.setEnabled(_hk_supported)
        hotkey_chk.setStyleSheet(f"""
            QCheckBox {{ font-size: 13px; color: {UI.TEXT}; }}
            QCheckBox::indicator {{ width: 18px; height: 18px; }}
        """)
        hotkey_hint = QLabel()
        hotkey_hint.setStyleSheet(UI.HINT_STYLE)
        hotkey_hint.setWordWrap(True)

        def _refresh_hotkey_hint():
            if not _hk_supported:
                hotkey_hint.setText(
                    tr("Requires GNOME (gsettings). Bind a shortcut manually instead."))
                return
            _, b = _hotkey.get_state(_hotkey.NEW_NOTE)
            label = _hotkey.accel_to_label(b or self._hotkey_binding)
            if self._hotkey_enabled:
                hotkey_hint.setText(
                    tr("Press {} anywhere to create a new note. Rebind it in GNOME Settings → Keyboard → Custom Shortcuts.").format(label))
            else:
                hotkey_hint.setText(
                    tr("Registers a GNOME shortcut ({}) to create a new note.").format(label))

        _refresh_hotkey_hint()

        def on_hotkey_changed(state):
            self._hotkey_enabled = (state == 2)   # Qt.CheckState.Checked == 2
            self._ensure_global_hotkey()
            self._save_backup_settings()
            _refresh_hotkey_hint()

        hotkey_chk.stateChanged.connect(on_hotkey_changed)
        gl.addWidget(hotkey_chk)
        gl.addWidget(hotkey_hint)

        # ── Global hotkey: new note from clipboard ────────────────────────────
        gl.addSpacing(8)
        clip_chk = QCheckBox(tr("Global shortcut for new note from clipboard"))
        clip_chk.setChecked(self._hotkey_clip_enabled and _hk_supported)
        clip_chk.setEnabled(_hk_supported)
        clip_chk.setStyleSheet(f"""
            QCheckBox {{ font-size: 13px; color: {UI.TEXT}; }}
            QCheckBox::indicator {{ width: 18px; height: 18px; }}
        """)
        clip_hint = QLabel()
        clip_hint.setStyleSheet(UI.HINT_STYLE)
        clip_hint.setWordWrap(True)

        def _refresh_clip_hint():
            if not _hk_supported:
                clip_hint.setText(
                    tr("Requires GNOME (gsettings). Bind a shortcut manually instead."))
                return
            _, b = _hotkey.get_state(_hotkey.NEW_NOTE_CLIP)
            label = _hotkey.accel_to_label(b or self._hotkey_clip_binding)
            if self._hotkey_clip_enabled:
                clip_hint.setText(
                    tr("Press {} anywhere to create a note from the clipboard. Rebind it in GNOME Settings → Keyboard → Custom Shortcuts.").format(label))
            else:
                clip_hint.setText(
                    tr("Registers a GNOME shortcut ({}) to create a note pre-filled with the clipboard contents.").format(label))

        _refresh_clip_hint()

        def on_clip_changed(state):
            self._hotkey_clip_enabled = (state == 2)   # Qt.CheckState.Checked == 2
            self._ensure_global_hotkey()
            self._save_backup_settings()
            _refresh_clip_hint()

        clip_chk.stateChanged.connect(on_clip_changed)
        gl.addWidget(clip_chk)
        gl.addWidget(clip_hint)

        # ── Global hotkey: search notes ───────────────────────────────────────
        gl.addSpacing(8)
        search_chk = QCheckBox(tr("Global shortcut for searching notes"))
        search_chk.setChecked(self._hotkey_search_enabled and _hk_supported)
        search_chk.setEnabled(_hk_supported)
        search_chk.setStyleSheet(f"""
            QCheckBox {{ font-size: 13px; color: {UI.TEXT}; }}
            QCheckBox::indicator {{ width: 18px; height: 18px; }}
        """)
        search_hint = QLabel()
        search_hint.setStyleSheet(UI.HINT_STYLE)
        search_hint.setWordWrap(True)

        def _refresh_search_hint():
            if not _hk_supported:
                search_hint.setText(
                    tr("Requires GNOME (gsettings). Bind a shortcut manually instead."))
                return
            _, b = _hotkey.get_state(_hotkey.SEARCH)
            label = _hotkey.accel_to_label(b or self._hotkey_search_binding)
            if self._hotkey_search_enabled:
                search_hint.setText(
                    tr("Press {} anywhere to open the search palette. Rebind it in GNOME Settings → Keyboard → Custom Shortcuts.").format(label))
            else:
                search_hint.setText(
                    tr("Registers a GNOME shortcut ({}) to open a search box for finding a note from anywhere.").format(label))

        _refresh_search_hint()

        def on_search_changed(state):
            self._hotkey_search_enabled = (state == 2)   # Qt.CheckState.Checked == 2
            self._ensure_global_hotkey()
            self._save_backup_settings()
            _refresh_search_hint()

        search_chk.stateChanged.connect(on_search_changed)
        gl.addWidget(search_chk)
        gl.addWidget(search_hint)

        # ── UI Scale ──────────────────────────────────────────────────────────
        gl.addSpacing(8)
        scale_lbl = QLabel(tr("UI Scale"))
        scale_lbl.setStyleSheet(UI.LABEL_STYLE)
        gl.addWidget(scale_lbl)

        scale_row = QHBoxLayout()
        scale_pct = QLabel(f"{int((self._pending_ui_scale or self._ui_scale) * 100)}%")
        scale_pct.setFixedWidth(48)
        scale_pct.setAlignment(Qt.AlignmentFlag.AlignCenter)
        scale_pct.setStyleSheet(UI.VALUE_STYLE)

        def change_scale(delta):
            base = self._pending_ui_scale if self._pending_ui_scale is not None else self._ui_scale
            new_scale = max(1.0, min(2.0, round(base + delta, 2)))
            if new_scale == base:
                return
            self._pending_ui_scale = new_scale   # staged; applied + saved only on Restart
            scale_pct.setText(f"{int(new_scale * 100)}%")
            scale_restart.setText(tr("Restart Sticky Notes to apply the new scale."))
            self._pending_restart = True
            restart_btn.setVisible(True)

        btn_scale_down = QPushButton("−")
        btn_scale_down.setFixedSize(32, 32)
        btn_scale_down.setStyleSheet(f"""
            QPushButton {{ background: {UI.NEUTRAL_BG}; color: {UI.TEXT};
                border: 1px solid {UI.BORDER}; border-radius: 6px;
                font-size: 18px; font-weight: 600; }}
            QPushButton:hover  {{ background: {UI.NEUTRAL_HOVER}; border-color: {UI.BORDER}; }}
            QPushButton:pressed {{ background: {UI.NEUTRAL_PRESS}; }}
        """)
        btn_scale_up = QPushButton("+")
        btn_scale_up.setFixedSize(32, 32)
        btn_scale_up.setStyleSheet(f"""
            QPushButton {{ background: {UI.NEUTRAL_BG}; color: {UI.TEXT};
                border: 1px solid {UI.BORDER}; border-radius: 6px;
                font-size: 18px; font-weight: 600; }}
            QPushButton:hover  {{ background: {UI.NEUTRAL_HOVER}; border-color: {UI.BORDER}; }}
            QPushButton:pressed {{ background: {UI.NEUTRAL_PRESS}; }}
        """)
        btn_scale_down.clicked.connect(lambda: change_scale(-0.1))
        btn_scale_up.clicked.connect(lambda: change_scale(+0.1))

        scale_row.addWidget(btn_scale_down)
        scale_row.addWidget(scale_pct)
        scale_row.addWidget(btn_scale_up)
        scale_row.addStretch()
        gl.addLayout(scale_row)

        scale_hint = QLabel(
            tr("Scales the whole interface, text and icons (100%–200%).")
            + " "
            + tr("For the sharpest result, keep system scaling at 100% and use this."))
        scale_hint.setStyleSheet(UI.HINT_STYLE)
        scale_hint.setWordWrap(True)
        gl.addWidget(scale_hint)

        scale_restart = QLabel("")
        scale_restart.setStyleSheet(f"font-size: 12px; color: {UI.ACCENT};")
        scale_restart.setWordWrap(True)
        gl.addWidget(scale_restart)

        gl.addStretch()

        # ── Language tab ──────────────────────────────────────────────────────
        language_tab = QWidget()
        ll = QVBoxLayout(language_tab)
        ll.setContentsMargins(16, 16, 16, 16)
        ll.setSpacing(14)
        lang_row = QHBoxLayout()
        lang_lbl = QLabel(tr("Language"))
        lang_lbl.setStyleSheet(UI.LABEL_STYLE)
        lang_combo = QComboBox()
        _shown_lang = self._pending_language or self._language
        for code, name in LANGUAGES:
            lang_combo.addItem(name, code)
            if code == _shown_lang:
                lang_combo.setCurrentIndex(lang_combo.count() - 1)
        lang_combo.setStyleSheet("font-size: 13px;")
        lang_row.addWidget(lang_lbl)
        lang_row.addStretch()
        lang_row.addWidget(lang_combo)
        lang_hint = QLabel(tr("Language changes apply after restart."))
        lang_hint.setStyleSheet(UI.HINT_STYLE)

        def on_language_changed(idx):
            code = lang_combo.itemData(idx)
            current = self._pending_language or self._language
            if code and code != current:
                self._pending_language = code   # staged; applied + saved only on Restart
                self._pending_restart = True
                restart_btn.setVisible(True)

        lang_combo.currentIndexChanged.connect(on_language_changed)
        ll.addLayout(lang_row)
        ll.addWidget(lang_hint)
        ll.addStretch()

        tabs.addTab(general_tab, tr("General"))

        # ── Snapping tab ──────────────────────────────────────────────────────
        snapping_tab = QWidget()
        sl = QVBoxLayout(snapping_tab)
        sl.setContentsMargins(16, 16, 16, 16)
        sl.setSpacing(14)
        chk_css = f"QCheckBox {{ font-size: 13px; color: {UI.TEXT}; }}"

        snap_grid_chk = QCheckBox(tr("Snap to grid"))
        snap_grid_chk.setChecked(self._snap_to_grid)
        snap_grid_chk.setStyleSheet(chk_css)
        snap_grid_chk.stateChanged.connect(
            lambda s: (setattr(self, "_snap_to_grid", s == 2), self._save_backup_settings()))
        sl.addWidget(snap_grid_chk)

        snap_notes_chk = QCheckBox(tr("Snap to other notes"))
        snap_notes_chk.setChecked(self._snap_to_notes)
        snap_notes_chk.setStyleSheet(chk_css)
        snap_notes_chk.stateChanged.connect(
            lambda s: (setattr(self, "_snap_to_notes", s == 2), self._save_backup_settings()))
        sl.addWidget(snap_notes_chk)

        snap_size_chk = QCheckBox(tr("Snap size to grid"))
        snap_size_chk.setChecked(self._snap_size)
        snap_size_chk.setStyleSheet(chk_css)
        snap_size_chk.stateChanged.connect(
            lambda s: (setattr(self, "_snap_size", s == 2), self._save_backup_settings()))
        sl.addWidget(snap_size_chk)

        grid_row = QHBoxLayout()
        grid_lbl = QLabel(tr("Grid size"))
        grid_lbl.setStyleSheet(UI.LABEL_STYLE)
        grid_spin = QSpinBox()
        grid_spin.setRange(5, 100)
        grid_spin.setSingleStep(5)
        grid_spin.setSuffix(" px")
        grid_spin.setValue(self._grid_size)
        grid_spin.setStyleSheet("font-size: 13px;")
        grid_spin.valueChanged.connect(
            lambda v: (setattr(self, "_grid_size", v), self._save_backup_settings()))
        grid_row.addWidget(grid_lbl)
        grid_row.addStretch()
        grid_row.addWidget(grid_spin)
        sl.addLayout(grid_row)

        snap_hint = QLabel(tr("Notes snap when you drop them or finish resizing. Snap to grid and snap size to grid align a note's position and size to an invisible grid; snap to other notes lines edges up with nearby notes. The grid size below sets the spacing."))
        snap_hint.setStyleSheet(UI.HINT_STYLE)
        snap_hint.setWordWrap(True)
        sl.addWidget(snap_hint)

        # ── Tray ───────────────────────────────────────────────────────────────
        # Gray divider between the Snapping and Tray sections (matches Backup/Note).
        sl.addSpacing(10)
        _snap_tray_sep = QWidget()
        _snap_tray_sep.setFixedHeight(1)
        _snap_tray_sep.setStyleSheet(f"background-color: {UI.BORDER};")
        sl.addWidget(_snap_tray_sep)
        sl.addSpacing(10)
        tray_head = QLabel(tr("Tray"))
        tray_head.setStyleSheet(UI.SECTION_STYLE)
        sl.addWidget(tray_head)
        tray_scroll_chk = QCheckBox(tr("Scroll the tray icon to bring notes to front"))
        tray_scroll_chk.setChecked(self._tray_scroll_enabled)
        tray_scroll_chk.setStyleSheet(chk_css)
        tray_scroll_chk.stateChanged.connect(
            lambda s: (setattr(self, "_tray_scroll_enabled", s == 2), self._save_backup_settings()))
        sl.addWidget(tray_scroll_chk)
        tray_hint = QLabel(tr("Scroll up on the tray icon to raise your visible notes above "
                              "other windows. Pinned notes are unaffected."))
        tray_hint.setStyleSheet(UI.HINT_STYLE)
        tray_hint.setWordWrap(True)
        sl.addWidget(tray_hint)
        sl.addStretch()

        # "&&" so Qt shows a literal "&" instead of treating it as a mnemonic
        # (a single "&" underlines the next char / renders as an underscore).
        tabs.addTab(snapping_tab, tr("Snapping && Tray"))

        # ── Font tab ──────────────────────────────────────────────────────────
        font_tab = QWidget()
        fl = QVBoxLayout(font_tab)
        fl.setContentsMargins(16, 16, 16, 16)
        fl.setSpacing(12)

        font_row = QHBoxLayout()
        _ff_lbl = QLabel(tr("Font family"))
        _ff_lbl.setStyleSheet(UI.LABEL_STYLE)
        font_row.addWidget(_ff_lbl)
        font_row.addStretch()

        font_btn = QPushButton(self._default_font_family)
        font_btn.setFixedWidth(200)
        font_btn.setStyleSheet(f"""
            QPushButton {{ background: {UI.SURFACE}; border: 1px solid {UI.BORDER};
                border-radius: 6px; padding: 6px 10px;
                text-align: left; font-size: 13px; color: {UI.TEXT}; }}
            QPushButton:hover {{ border-color: {UI.ACCENT}; }}
        """)
        # Track selected font in a mutable container so closures can update it
        selected_font = [self._default_font_family]

        def choose_font():
            picker = QDialog(dlg)
            picker.setWindowTitle(tr("Choose Font"))
            picker.setFixedSize(340, 460)
            # A child top-level dialog does NOT inherit the Settings sheet, and the
            # search box + font list carry no colour of their own — so in dark mode
            # the big white list made the whole picker read as light. Theme it here,
            # like show_backups/message_box_style do for their windows.
            picker.setStyleSheet(f"""
                QDialog {{ background: {UI.WINDOW_BG}; }}
                QLineEdit {{ background: {UI.SURFACE}; color: {UI.TEXT};
                    border: 1px solid {UI.BORDER}; border-radius: 6px; }}
                QListWidget {{ background: {UI.SURFACE}; color: {UI.TEXT};
                    border: 1px solid {UI.BORDER}; border-radius: 6px; }}
                QListWidget::item:selected {{ background: {UI.ACCENT}; color: #ffffff; }}
            """)
            pl = QVBoxLayout(picker)
            pl.setContentsMargins(10, 10, 10, 10)
            pl.setSpacing(8)

            search = QLineEdit()
            search.setPlaceholderText(tr("Search fonts…"))
            search.setStyleSheet("padding: 5px; font-size: 14px;")
            pl.addWidget(search)

            lst = QListWidget()
            lst.setStyleSheet("font-size: 14px;")
            lst.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            if not hasattr(self, '_font_list_cache'):
                from PyQt6.QtGui import QFontDatabase
                self._font_list_cache = sorted(QFontDatabase.families())
            lst.addItems(self._font_list_cache)
            # Scroll to current selection
            matches = lst.findItems(selected_font[0], Qt.MatchFlag.MatchExactly)
            if matches:
                lst.setCurrentItem(matches[0])
                lst.scrollToItem(matches[0])
            pl.addWidget(lst)

            def on_search(text):
                for i in range(lst.count()):
                    item = lst.item(i)
                    item.setHidden(text.lower() not in item.text().lower())
            search.textChanged.connect(on_search)

            def confirm():
                if lst.currentItem():
                    selected_font[0] = lst.currentItem().text()
                    font_btn.setText(selected_font[0])
                picker.accept()

            lst.itemDoubleClicked.connect(lambda _: confirm())

            btn_row = QHBoxLayout()
            btn_ok = QPushButton(tr("Select"))
            btn_ok.setStyleSheet(_btn_primary())
            btn_ok.clicked.connect(confirm)
            btn_cancel = QPushButton(tr("Cancel"))
            btn_cancel.setStyleSheet(_btn_secondary())
            btn_cancel.clicked.connect(picker.reject)
            btn_row.addStretch()
            btn_row.addWidget(btn_cancel)
            btn_row.addWidget(btn_ok)
            pl.addLayout(btn_row)
            picker.exec()
            picker.deleteLater()

        font_btn.clicked.connect(choose_font)
        font_row.addWidget(font_btn)
        fl.addLayout(font_row)

        size_row = QHBoxLayout()
        _fs_lbl = QLabel(tr("Default font size"))
        _fs_lbl.setStyleSheet(UI.LABEL_STYLE)
        size_row.addWidget(_fs_lbl)
        size_row.addStretch()
        size_spin = QSpinBox()
        size_spin.setRange(8, 72)
        size_spin.setValue(self._default_font_size)
        size_spin.setFixedWidth(80)
        size_spin.setStyleSheet(f"""
            QSpinBox {{ border: 1px solid {UI.BORDER}; border-radius: 6px;
                padding: 4px 6px; font-size: 13px; color: {UI.TEXT}; }}
        """)
        size_row.addWidget(size_spin)
        fl.addLayout(size_row)

        # Font section gets its own apply button (font family + size only).
        btn_apply_font = QPushButton(tr("Apply to New Notes"))
        btn_apply_font.setStyleSheet(_btn_primary())
        def apply_font():
            self._default_font_family = selected_font[0]
            self._default_font_size   = size_spin.value()
            self._save_backup_settings()
        btn_apply_font.clicked.connect(apply_font)
        _font_apply_row = QHBoxLayout()
        _font_apply_row.addStretch()
        _font_apply_row.addWidget(btn_apply_font)
        fl.addLayout(_font_apply_row)

        # Separator between the font options and the note-size options (matches
        # the divider style used on the Backup tab).
        fl.addSpacing(10)
        _note_sep = QWidget()
        _note_sep.setFixedHeight(1)
        _note_sep.setStyleSheet(f"background-color: {UI.BORDER};")
        fl.addWidget(_note_sep)
        fl.addSpacing(10)

        # Default size for NEW notes (existing notes keep their own size).
        dim_lbl = QLabel(tr("Default size for new notes"))
        dim_lbl.setStyleSheet(UI.SECTION_STYLE)
        fl.addWidget(dim_lbl)

        dim_row = QHBoxLayout()
        _w_lbl = QLabel(tr("Width"))
        _w_lbl.setStyleSheet(UI.LABEL_STYLE)
        dim_row.addWidget(_w_lbl)
        width_spin = QSpinBox()
        width_spin.setRange(240, 1200)
        width_spin.setSingleStep(1)
        width_spin.setValue(self._default_note_width)
        width_spin.setStyleSheet(size_spin.styleSheet())
        dim_row.addWidget(width_spin)
        dim_row.addSpacing(18)
        _h_lbl = QLabel(tr("Height"))
        _h_lbl.setStyleSheet(UI.LABEL_STYLE)
        dim_row.addWidget(_h_lbl)
        height_spin = QSpinBox()
        height_spin.setRange(168, 1000)
        height_spin.setSingleStep(1)
        height_spin.setValue(self._default_note_height)
        height_spin.setStyleSheet(size_spin.styleSheet())
        dim_row.addWidget(height_spin)
        dim_row.addStretch()
        fl.addLayout(dim_row)

        # When "Snap size to grid" is on, make the arrows step by the grid and
        # keep the value on a grid multiple — the same rounding notes get from
        # snap.snap_to_grid, so the default can't preview a size a snapped note
        # would never actually take. (grid_spin / snap_size_chk are locals built
        # earlier in this method, still in scope here.)
        def _snap_spin_to_grid(spin):
            g = self._grid_size
            if g <= 0:
                return
            lo, hi = spin.minimum(), spin.maximum()
            v = ((spin.value() + g // 2) // g) * g          # nearest multiple
            v = max(((lo + g - 1) // g) * g, min((hi // g) * g, v))  # clamp to in-range multiple
            if v != spin.value():
                spin.blockSignals(True); spin.setValue(v); spin.blockSignals(False)

        def _sync_size_grid_step():
            step = self._grid_size if self._snap_size else 1
            width_spin.setSingleStep(step)
            height_spin.setSingleStep(step)
            if self._snap_size:
                _snap_spin_to_grid(width_spin)
                _snap_spin_to_grid(height_spin)

        _sync_size_grid_step()                               # initial state
        grid_spin.valueChanged.connect(lambda _v: _sync_size_grid_step())
        snap_size_chk.toggled.connect(lambda _c: _sync_size_grid_step())
        width_spin.editingFinished.connect(
            lambda: _snap_spin_to_grid(width_spin) if self._snap_size else None)
        height_spin.editingFinished.connect(
            lambda: _snap_spin_to_grid(height_spin) if self._snap_size else None)

        # Note-size section gets its own apply button (width + height only).
        btn_apply_size = QPushButton(tr("Apply to New Notes"))
        btn_apply_size.setStyleSheet(_btn_primary())
        def apply_size():
            self._default_note_width  = width_spin.value()
            self._default_note_height = height_spin.value()
            self._save_backup_settings()
        btn_apply_size.clicked.connect(apply_size)
        _size_apply_row = QHBoxLayout()
        _size_apply_row.addStretch()
        _size_apply_row.addWidget(btn_apply_size)
        fl.addLayout(_size_apply_row)

        # Auto-contrast — adapt each note's icon/text colour to its background.
        fl.addSpacing(10)
        _ac_sep = QWidget()
        _ac_sep.setFixedHeight(1)
        _ac_sep.setStyleSheet(f"background-color: {UI.BORDER};")
        fl.addWidget(_ac_sep)
        fl.addSpacing(10)

        ac_chk = QCheckBox(tr("Adjust text & icon colour to note background"))
        ac_chk.setStyleSheet(
            f"QCheckBox {{ font-size: 13px; color: {UI.TEXT}; }}"
            "QCheckBox::indicator { width: 18px; height: 18px; }")
        ac_chk.setChecked(self._auto_contrast)
        def on_auto_contrast(checked):
            self._auto_contrast = checked
            self._apply_auto_contrast()      # re-ink every open note live
            self._save_backup_settings()
        ac_chk.toggled.connect(on_auto_contrast)
        fl.addWidget(ac_chk)

        _ac_hint = QLabel(tr("Dark notes get light icons and text automatically. Turn off to keep the classic dark ink."))
        _ac_hint.setStyleSheet(UI.HINT_STYLE)
        _ac_hint.setWordWrap(True)
        fl.addWidget(_ac_hint)

        cm_chk = QCheckBox(tr("Auto-hide toolbar and header until you hover the note"))
        cm_chk.setStyleSheet(
            f"QCheckBox {{ font-size: 13px; color: {UI.TEXT}; }}"
            "QCheckBox::indicator { width: 18px; height: 18px; }")
        cm_chk.setChecked(self._clean_mode)
        def on_clean_mode(checked):
            self._clean_mode = checked
            self._apply_clean_mode()         # collapse/restore every open note live
            self._save_backup_settings()
        cm_chk.toggled.connect(on_clean_mode)
        fl.addWidget(cm_chk)

        _cm_hint = QLabel(tr("Notes show only their text at rest; hover the top of a note to bring the controls back. "
                             "A single click on the header keeps the controls up and lets you nudge the note with the arrow keys; click elsewhere to hide them again. "
                             "Double-click a note's header to keep its controls open while you edit it; "
                             "double-click again to hand that note back to auto-hide."))
        _cm_hint.setStyleSheet(UI.HINT_STYLE)
        _cm_hint.setWordWrap(True)
        fl.addWidget(_cm_hint)

        cb_chk = QCheckBox(tr("Enable code blocks"))
        cb_chk.setStyleSheet(
            f"QCheckBox {{ font-size: 13px; color: {UI.TEXT}; }}"
            "QCheckBox::indicator { width: 18px; height: 18px; }")
        cb_chk.setChecked(self._code_blocks)
        def on_code_blocks(checked):
            self._code_blocks = checked
            self._apply_code_blocks()        # show/hide the { } button on every note
            self._save_backup_settings()
        cb_chk.toggled.connect(on_code_blocks)
        fl.addWidget(cb_chk)

        _cb_hint = QLabel(tr("Adds code-block { } and inline-code buttons to the toolbar, and enables their shortcuts (Ctrl+M for inline code, Ctrl+Shift+M for a code block). Niche — off by default."))
        _cb_hint.setStyleSheet(UI.HINT_STYLE)
        _cb_hint.setWordWrap(True)
        fl.addWidget(_cb_hint)

        # Set off with a rule and a section header, and put the dropdown on its
        # own line beneath the label (left-aligned, styled with a border) — as a
        # far-right unstyled combo it blended into the panel and read as invisible.
        fl.addSpacing(10)
        _bd_sep = QWidget()
        _bd_sep.setFixedHeight(1)
        _bd_sep.setStyleSheet(f"background-color: {UI.BORDER};")
        fl.addWidget(_bd_sep)
        fl.addSpacing(10)

        bd_lbl = QLabel(tr("Note border"))
        bd_lbl.setStyleSheet(UI.SECTION_STYLE)
        fl.addWidget(bd_lbl)

        bd_combo = QComboBox()
        bd_combo.setStyleSheet(f"""
            QComboBox {{ border: 1px solid {UI.BORDER}; border-radius: 6px;
                padding: 5px 10px; font-size: 13px; color: {UI.TEXT};
                background: {UI.SURFACE}; }}
            QComboBox:hover {{ border-color: {UI.ACCENT}; }}
            QComboBox::drop-down {{ border: none; width: 22px; }}
        """)
        bd_combo.addItem(tr("Off"), "off")
        bd_combo.addItem(tr("Always"), "always")
        bd_combo.addItem(tr("Auto (light notes only)"), "auto")
        bd_combo.setCurrentIndex(max(0, bd_combo.findData(self._note_border)))
        def on_note_border(_i):
            self._note_border = bd_combo.currentData()
            self._apply_note_border()        # repaint every open note
            self._save_backup_settings()
        bd_combo.currentIndexChanged.connect(on_note_border)
        bd_row = QHBoxLayout()
        bd_row.addWidget(bd_combo)
        bd_row.addStretch()                  # keep the combo at its natural width, left-aligned
        fl.addLayout(bd_row)

        _bd_hint = QLabel(tr("Auto shows a border only on light notes, where it helps them stand out from a light background."))
        _bd_hint.setStyleSheet(UI.HINT_STYLE)
        _bd_hint.setWordWrap(True)
        fl.addWidget(_bd_hint)

        fl.addStretch()

        tabs.insertTab(1, font_tab, tr("Note"))

        # ── Appearance tab (window theme + background opacity) ────────────────
        appearance_tab = QWidget()
        al = QVBoxLayout(appearance_tab)
        al.setContentsMargins(16, 16, 16, 16)
        al.setSpacing(12)

        # Window theme (Light/Dark). Applied immediately to new windows/notes;
        # already-open windows update on restart (reveals the shared Restart btn).
        _ap_lbl = QLabel(tr("Window theme"))
        _ap_lbl.setStyleSheet(UI.SECTION_STYLE)
        al.addWidget(_ap_lbl)

        theme_row = QHBoxLayout()
        theme_lbl = QLabel(tr("Theme"))
        theme_lbl.setStyleSheet(UI.LABEL_STYLE)
        theme_combo = QComboBox()
        theme_combo.addItem(tr("Light"), "light")
        theme_combo.addItem(tr("Dark"), "dark")
        theme_combo.addItem(tr("Auto"), "auto")
        _ti = theme_combo.findData(self._theme_mode)
        theme_combo.setCurrentIndex(_ti if _ti >= 0 else 0)
        theme_row.addWidget(theme_lbl)
        theme_row.addStretch()
        theme_row.addWidget(theme_combo)
        al.addLayout(theme_row)

        # Auto schedule row — visible only while the mode is Auto.
        sched_row = QHBoxLayout()
        sched_row.setContentsMargins(0, 0, 0, 0)   # align with theme_row (added as a
                                                   # bare layout, no wrapper margins)
        sched_lbl = QLabel(tr("Dark from"))
        sched_lbl.setStyleSheet(UI.LABEL_STYLE)
        t_start = QTimeEdit(QTime.fromString(self._theme_dark_start, "HH:mm"))
        t_start.setDisplayFormat("HH:mm")
        until_lbl = QLabel(tr("until"))
        until_lbl.setStyleSheet(UI.LABEL_STYLE)
        t_end = QTimeEdit(QTime.fromString(self._theme_dark_end, "HH:mm"))
        t_end.setDisplayFormat("HH:mm")
        sched_row.addWidget(sched_lbl)
        sched_row.addStretch()
        sched_row.addWidget(t_start)
        sched_row.addWidget(until_lbl)
        sched_row.addWidget(t_end)
        sched_box = QWidget()
        sched_box.setLayout(sched_row)
        sched_box.setVisible(self._theme_mode == "auto")
        al.addWidget(sched_box)

        _sched_hint = QLabel(tr("Auto switches to Dark between these times; the theme changes within a minute of each boundary. The tray's Toggle theme then lasts only until the next boundary."))
        _sched_hint.setStyleSheet(UI.HINT_STYLE)
        _sched_hint.setWordWrap(True)
        _sched_hint.setVisible(self._theme_mode == "auto")
        al.addWidget(_sched_hint)

        def on_sched_time(_t):
            self._theme_dark_start = t_start.time().toString("HH:mm")
            self._theme_dark_end   = t_end.time().toString("HH:mm")
            self._save_backup_settings()
            self._theme_scheduler._tick()   # effect now, not in <=60 s
        t_start.timeChanged.connect(on_sched_time)
        t_end.timeChanged.connect(on_sched_time)

        def on_theme_changed(_i):
            mode = theme_combo.currentData()
            self._set_theme_mode(mode)      # applied live — no restart needed
            sched_box.setVisible(mode == "auto")
            _sched_hint.setVisible(mode == "auto")
        theme_combo.currentIndexChanged.connect(on_theme_changed)

        _ap_hint = QLabel(tr("Sets the look of the app's windows, menus and notes. Switching to Dark gives every note without its own dark colour a dark default; each note keeps separate colours for Light and Dark, so switching back restores the light one. Notes and the main windows recolour instantly; a few helper windows (About, the shortcut list, search) update the next time you open them — no restart needed."))
        _ap_hint.setStyleSheet(UI.HINT_STYLE)
        _ap_hint.setWordWrap(True)
        al.addWidget(_ap_hint)

        # Background opacity — applies live to ALL notes (existing and new).
        # Only the paper is made translucent; note text stays opaque.
        al.addSpacing(10)
        _op_sep = QWidget()
        _op_sep.setFixedHeight(1)
        _op_sep.setStyleSheet(f"background-color: {UI.BORDER};")
        al.addWidget(_op_sep)
        al.addSpacing(10)

        _op_lbl = QLabel(tr("Background opacity"))
        _op_lbl.setStyleSheet(UI.SECTION_STYLE)
        al.addWidget(_op_lbl)

        op_row = QHBoxLayout()
        op_slider = QSlider(Qt.Orientation.Horizontal)
        op_slider.setRange(40, 100)          # below ~40% text over a busy backdrop
        op_slider.setValue(self._note_opacity)  # gets hard to read → floor at 40%
        op_slider.setFixedWidth(220)
        op_val = QLabel(f"{self._note_opacity}%")
        op_val.setStyleSheet(UI.VALUE_STYLE)
        op_val.setFixedWidth(48)
        _op_save = QTimer(dlg)               # debounce disk writes while dragging
        _op_save.setSingleShot(True)
        _op_save.timeout.connect(self._save_backup_settings)

        def on_opacity(v):
            self._note_opacity = v
            op_val.setText(f"{v}%")
            self._apply_note_opacity()       # live repaint of every open note
            _op_save.start(250)
        op_slider.valueChanged.connect(on_opacity)   # connected AFTER setValue,
        op_slider.sliderReleased.connect(self._save_backup_settings)  # so opening
        op_row.addWidget(op_slider)          # Settings doesn't re-fire it
        op_row.addSpacing(10)
        op_row.addWidget(op_val)
        op_row.addStretch()
        al.addLayout(op_row)

        _op_hint = QLabel(tr("Makes the note paper see-through; text stays sharp. Applies to all current and future notes."))
        _op_hint.setStyleSheet(UI.HINT_STYLE)
        _op_hint.setWordWrap(True)
        al.addWidget(_op_hint)

        al.addStretch()

        tabs.insertTab(2, appearance_tab, tr("Appearance"))

        # ── Backup tab ────────────────────────────────────────────────────────
        backup_tab = QWidget()
        bl = QVBoxLayout(backup_tab)
        bl.setContentsMargins(16, 16, 16, 16)
        bl.setSpacing(12)

        def _newest_backup_label():
            gens = self.list_backups()
            return (tr("Last backup: {}").format(gens[0]["when"].strftime('%d.%m.%Y %H:%M'))
                    if gens else tr("No backup yet"))
        status_lbl = QLabel(_newest_backup_label())
        status_lbl.setStyleSheet(UI.HINT_STYLE)
        bl.addWidget(status_lbl)

        manual_row = QHBoxLayout()
        btn_backup = QPushButton(tr("Backup Now"))
        btn_backup.setStyleSheet(_btn_primary())
        def do_manual_backup():
            self._force_backup()                 # creates a new backup generation
            status_lbl.setText(_newest_backup_label())
        btn_backup.clicked.connect(do_manual_backup)

        btn_restore = QPushButton(tr("Restore from Backup…"))
        btn_restore.setStyleSheet(_btn_secondary())
        # Opens the backup picker so the user chooses WHICH generation to restore.
        btn_restore.clicked.connect(lambda: self.show_backups())
        manual_row.addWidget(btn_backup)
        manual_row.addWidget(btn_restore)
        manual_row.addStretch()
        bl.addLayout(manual_row)

        backup_hint = QLabel(tr(
            "Backups save copies of ALL your notes (active, archived and trash) in a "
            "backups folder on this computer. \"Backup Now\" and the auto-backup "
            "interval each add a new restore point (the 5 most recent are kept); the "
            "daily auto-backup keeps the latest one fresh. \"Restore from Backup…\" "
            "lets you pick which one to go back to (this overwrites your current notes)."))
        backup_hint.setWordWrap(True)
        backup_hint.setStyleSheet(UI.HINT_STYLE)
        bl.addWidget(backup_hint)

        bl.addSpacing(6)

        auto_label = QLabel(tr("Auto backup every"))
        auto_label.setStyleSheet(UI.LABEL_STYLE)
        bl.addWidget(auto_label)

        auto_row = QHBoxLayout()
        interval_combo = QComboBox()
        interval_combo.setStyleSheet(f"""
            QComboBox {{ border: 1px solid {UI.BORDER}; border-radius: 6px;
                padding: 5px 10px; font-size: 13px; color: {UI.TEXT};
                background: {UI.SURFACE}; }}
            QComboBox:hover {{ border-color: {UI.ACCENT}; }}
            QComboBox::drop-down {{ border: none; width: 22px; }}
        """)
        intervals = [
            (tr("15 minutes"), 15), (tr("30 minutes"), 30),
            (tr("1 hour"), 60),     (tr("2 hours"), 120),
            (tr("4 hours"), 240),   (tr("8 hours"), 480),
            (tr("12 hours"), 720),  (tr("24 hours"), 1440),
            ("Disabled", 0),
        ]
        for label, minutes in intervals:
            interval_combo.addItem(label, minutes)
            if minutes == self._backup_interval_minutes:
                interval_combo.setCurrentText(label)

        btn_save_interval = QPushButton(tr("Save"))
        btn_save_interval.setStyleSheet(_btn_primary())
        btn_save_interval.clicked.connect(
            lambda: self._set_backup_interval(interval_combo.currentData())
        )
        auto_row.addWidget(interval_combo)
        auto_row.addWidget(btn_save_interval)
        auto_row.addStretch()
        bl.addLayout(auto_row)

        # ── Export / Import separator ─────────────────────────────────────────
        sep_io = QWidget()
        sep_io.setFixedHeight(1)
        sep_io.setStyleSheet(f"background-color: {UI.BORDER};")
        bl.addSpacing(6)
        bl.addWidget(sep_io)
        bl.addSpacing(4)

        io_header = QLabel(tr("EXPORT / IMPORT"))
        io_header.setStyleSheet(UI.SECTION_STYLE)
        bl.addWidget(io_header)

        io_row = QHBoxLayout()
        btn_export = QPushButton(tr("Export to JSON…"))
        btn_export.setStyleSheet(_btn_secondary())
        btn_import = QPushButton(tr("Import from JSON…"))
        btn_import.setStyleSheet(_btn_secondary())
        btn_export.clicked.connect(lambda: self._export_notes(dlg))
        btn_import.clicked.connect(lambda: self._import_notes(dlg))
        io_row.addWidget(btn_export)
        io_row.addWidget(btn_import)
        io_row.addStretch()
        bl.addLayout(io_row)

        io_hint = QLabel(tr(
            "Export writes a portable JSON file of your ACTIVE notes (to move to "
            "another computer or re-import). Import always brings notes in as active. "
            "To export archived notes, use “Export All” in the Manager's Archive tab."))
        io_hint.setWordWrap(True)
        io_hint.setStyleSheet(UI.HINT_STYLE)
        bl.addWidget(io_hint)

        bl.addStretch()

        tabs.addTab(backup_tab, tr("Backup"))
        tabs.addTab(language_tab, tr("Language"))

        main_layout.addWidget(tabs)

        # ── Close button ──────────────────────────────────────────────────────
        sep2 = QWidget()
        sep2.setFixedHeight(1)
        sep2.setStyleSheet(f"background-color: {UI.BORDER};")
        main_layout.addWidget(sep2)

        btn_row = QHBoxLayout()
        restart_btn = QPushButton(tr("Restart now"))
        restart_btn.setStyleSheet(_btn_primary())
        restart_btn.setVisible(False)               # real visibility set at the end, once parented
        restart_btn.clicked.connect(self._apply_pending_and_restart)
        btn_close = QPushButton(tr("Close"))
        btn_close.setStyleSheet(_btn_secondary())
        btn_close.clicked.connect(dlg.accept)
        btn_row.addWidget(restart_btn)
        btn_row.addStretch()
        btn_row.addWidget(btn_close)
        main_layout.addLayout(btn_row)

        # Set restart visibility now that the button is parented into the shown
        # dialog — doing it at creation (pre-parent) gets undone when addWidget
        # reparents the widget (Qt hides a widget on reparent). Kept alive across
        # a live-theme rebuild by _pending_restart (scale/language pending).
        restart_btn.setVisible(self._pending_restart)

        tabs.setCurrentIndex(active_tab)
        dlg._tabs = tabs
        dlg._retheme = lambda: self._build_settings_content(dlg, dlg._tabs.currentIndex())

    # The cheat-sheet sets its own type sizes, deliberately larger than the app's
    # dense chrome: tabs freed the vertical room the single long column used to
    # eat. These are local on purpose — UI.LABEL_STYLE is shared by every dialog
    # and must not grow just because this window wanted bigger text.
    # The KEYCAPS sit just under the label: they are already a raised, padded box,
    # so they don't need extra size to read as keys — at 17px they shouted. 15px
    # (matching the label) is the settled middle, tuned on a real screen.
    _CHEAT_LABEL_PX  = 15
    _CHEAT_KEYCAP_PX = 15
    _CHEAT_HINT_PX   = 13

    def _keycap(self, text: str) -> QLabel:
        """A single raised keycap label (cheat-sheet style B)."""
        cap = QLabel(text)
        cap.setStyleSheet(
            f"background:{UI.SURFACE}; border:1px solid {UI.BORDER};"
            f"border-bottom:3px solid {UI.BORDER}; border-radius:6px;"
            f"padding:4px 9px; color:{UI.TEXT}; font-size:{self._CHEAT_KEYCAP_PX}px;")
        return cap

    def show_shortcuts(self):
        from . import shortcuts
        if self._raise_if_open(tr("Keyboard shortcuts")):
            return
        dlg = QDialog()
        dlg.setWindowTitle(tr("Keyboard shortcuts"))
        dlg.setMinimumWidth(520)   # wider: the bigger type needs the room
        dlg.setStyleSheet(f"QDialog {{ background: {UI.WINDOW_BG}; }}")
        outer = QVBoxLayout(dlg)
        outer.setContentsMargins(16, 16, 16, 16)

        # One tab per catalog section: stacking every section in a single column
        # made the window grow taller with each shortcut added. sections() stays
        # the source of truth — a new section there becomes a new tab here.
        tabs = QTabWidget()
        tabs.setStyleSheet(f"""
            QTabWidget::pane {{ border: 1px solid {UI.BORDER}; border-radius: 6px; }}
            QTabBar::tab {{ padding: 8px 16px; border-radius: 4px; font-size: 14px;
                color: {UI.TEXT_MUTED}; }}
            QTabBar::tab:selected {{ color: {UI.TEXT}; font-weight: 600; }}
        """)
        outer.addWidget(tabs)

        label_style = f"font-size: {self._CHEAT_LABEL_PX}px; color: {UI.TEXT};"
        hint_style  = f"font-size: {self._CHEAT_HINT_PX}px; color: {UI.TEXT_MUTED};"

        for title, rows in shortcuts.sections():
            page = QWidget()
            v = QVBoxLayout(page)
            v.setContentsMargins(16, 14, 16, 14)
            v.setSpacing(7)          # bigger type needs room to breathe
            note_text = shortcuts.SECTION_NOTES.get(title)
            if note_text:
                note = QLabel(tr(note_text))
                note.setStyleSheet(hint_style)
                note.setWordWrap(True)
                v.addWidget(note)
                v.addSpacing(4)
            for row in rows:
                line = QHBoxLayout()
                line.setContentsMargins(0, 0, 0, 0)
                lbl = QLabel(row["label"])
                lbl.setStyleSheet(label_style)
                line.addWidget(lbl)
                line.addStretch()
                for i, key in enumerate(row["keys"]):
                    if i:
                        plus = QLabel("+")
                        plus.setStyleSheet(hint_style)
                        line.addWidget(plus)
                    line.addWidget(self._keycap(key))
                v.addLayout(line)
                if row.get("hint"):
                    hint = QLabel("↳ " + tr(row["hint"]))
                    hint.setStyleSheet(hint_style + " padding-left: 2px;")
                    hint.setWordWrap(True)
                    v.addWidget(hint)
            # Push short tabs' rows to the top so the window doesn't resize as
            # the user moves between tabs of different lengths.
            v.addStretch()
            tabs.addTab(page, tr(title))

        self._show_window(dlg)

    def show_backups(self):
        if self._raise_if_open(tr("Backups")):
            return
        dlg = QDialog()
        dlg.setWindowTitle(tr("Backups"))
        dlg.setMinimumWidth(420)
        # + message boxes: the restore confirmation is parented here, so it
        # inherits this sheet's background and needs its ink named too.
        dlg.setStyleSheet(f"QDialog {{ background: {UI.WINDOW_BG}; }}"
                          + message_box_style())
        outer = QVBoxLayout(dlg)
        outer.setContentsMargins(20, 18, 20, 18)
        outer.setSpacing(10)

        head = QLabel(tr("Restore your notes from an earlier backup"))
        head.setStyleSheet(UI.SECTION_STYLE)
        outer.addWidget(head)
        hint = QLabel(tr("The 5 most recent backups. Restoring overwrites your current "
                         "notes and cannot be undone — press \"Backup Now\" first if you "
                         "want to keep them."))
        hint.setStyleSheet(UI.HINT_STYLE)
        hint.setWordWrap(True)
        outer.addWidget(hint)

        lst = QListWidget()
        outer.addWidget(lst)

        state = {"tags": []}

        def _refresh():
            lst.clear()
            gens = self.list_backups()
            state["tags"] = [g["tag"] for g in gens]
            if not gens:
                lst.addItem(tr("No backups yet."))
                return
            for i, g in enumerate(gens):
                lst.addItem(g["label"] + ("    " + tr("(latest)") if i == 0 else ""))

        _refresh()

        def _on_restore():
            row = lst.currentRow()
            if row < 0 or row >= len(state["tags"]):
                return
            tag = state["tags"][row]
            when = lst.currentItem().text().strip()
            confirm = QMessageBox(dlg)
            confirm.setWindowTitle(tr("Restore from Backup"))
            confirm.setIcon(QMessageBox.Icon.Warning)
            confirm.setText(tr("Replace your current notes with the backup from {}?\n\n"
                               "This overwrites your current notes and cannot be undone. "
                               "Use \"Backup Now\" first if you want to keep them.").format(when))
            confirm.setStandardButtons(
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            confirm.setDefaultButton(QMessageBox.StandardButton.No)
            if confirm.exec() != QMessageBox.StandardButton.Yes:
                return
            if self.restore_backup(tag):
                QMessageBox.information(dlg, tr("Restore complete"),
                    tr("Your notes were restored from the selected backup."))
                _refresh()
            else:
                QMessageBox.warning(dlg, tr("Restore failed"),
                    tr("That backup could not be restored."))

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_close = QPushButton(tr("Close"))
        btn_close.setStyleSheet(_btn_secondary())
        btn_close.clicked.connect(dlg.close)
        btn_restore = QPushButton(tr("Restore selected"))
        btn_restore.setStyleSheet(_btn_primary())
        btn_restore.clicked.connect(_on_restore)
        btn_row.addWidget(btn_close)
        btn_row.addWidget(btn_restore)
        outer.addLayout(btn_row)

        self._show_window(dlg)

    def show_about(self):
        if self._raise_if_open(tr("About Sticky Notes")):
            return
        dlg = QDialog()
        dlg.setWindowTitle(tr("About Sticky Notes"))
        dlg.setMinimumWidth(360)
        dlg.setStyleSheet(f"QDialog {{ background: {UI.WINDOW_BG}; }}")
        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(28, 24, 28, 20)

        dark = getattr(self, "_theme", "light") == "dark"
        icon_lbl = QLabel()
        icon_lbl.setPixmap(about_icon_pixmap(dark, UI.TEXT, 56))
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = QLabel("Sticky Notes")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(f"font-size: 20px; font-weight: 700; color: {UI.TEXT};")

        version = QLabel(tr("Version {}").format(APP_VERSION))
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        version.setStyleSheet(f"font-size: 12px; color: {UI.TEXT_MUTED};")

        body = QLabel(
            tr("A lightweight sticky notes application\nfor Ubuntu desktop.\n\nBuilt with Python & PyQt6")
        )
        body.setAlignment(Qt.AlignmentFlag.AlignCenter)
        body.setStyleSheet(f"font-size: 13px; color: {UI.TEXT_MUTED};")

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFixedHeight(1)
        line.setStyleSheet(f"background: {UI.BORDER}; border: none;")

        signature = QLabel(tr("Made by Nikola Javorina"))
        signature.setAlignment(Qt.AlignmentFlag.AlignCenter)
        signature.setStyleSheet(f"color: {UI.TEXT}; font-size: 13px; font-weight: 500;")

        donate = QPushButton()
        donate.setStyleSheet(_btn_primary(min_w=200)
                             + "QPushButton { font-size: 15px; padding: 10px 22px; }")
        donate.setCursor(Qt.CursorShape.PointingHandCursor)
        # Coffee SVG (in its own colours) on the donate button, text alongside.
        # When SVG rendering is unavailable, fall back to a ☕-prefixed text button
        # so the glyph is still conveyed.
        _coffee_px = 20
        _coffee = coffee_button_icon(_coffee_px)
        _coffee_label = tr("Buy me a coffee")
        if not _coffee.isNull():
            # Leading spaces give the icon a little gap from the text — QPushButton
            # has no QSS property for the icon-to-text spacing.
            donate.setText("  " + _coffee_label)
            donate.setIcon(_coffee)
            donate.setIconSize(QSize(_coffee_px, _coffee_px))
        else:
            donate.setText("☕  " + _coffee_label)
        donate.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(DONATE_URL)))

        github = QLabel(
            f'<a href="{GITHUB_URL}" style="color: {UI.ACCENT}; text-decoration: none;">'
            f'{tr("View on GitHub")}</a>'
        )
        github.setAlignment(Qt.AlignmentFlag.AlignCenter)
        github.setStyleSheet("font-size: 13px;")
        github.setOpenExternalLinks(True)
        # Let the link itself own the hand cursor (Qt shows it over the anchor
        # text only). A widget-wide setCursor would put the hand over the label's
        # empty padding too, implying dead space is clickable.
        github.setTextInteractionFlags(Qt.TextInteractionFlag.LinksAccessibleByMouse)

        ok = QPushButton(tr("OK"))
        ok.setStyleSheet(_btn_secondary(min_w=80))
        ok.clicked.connect(dlg.accept)

        layout.addWidget(icon_lbl)
        layout.addSpacing(10)
        layout.addWidget(title)
        layout.addSpacing(2)
        layout.addWidget(version)
        layout.addSpacing(14)
        layout.addWidget(body)
        layout.addSpacing(18)
        layout.addWidget(line)
        layout.addSpacing(16)
        layout.addWidget(signature)
        layout.addSpacing(14)
        donate_row = QHBoxLayout()
        donate_row.addStretch(); donate_row.addWidget(donate); donate_row.addStretch()
        layout.addLayout(donate_row)
        layout.addSpacing(8)
        layout.addWidget(github)
        layout.addSpacing(20)
        ok_row = QHBoxLayout()
        ok_row.addStretch(); ok_row.addWidget(ok); ok_row.addStretch()
        layout.addLayout(ok_row)

        # Deterministic open: pin the size to the built content, then centre on the
        # primary screen. show_about previously left both to the show-time sizeHint
        # and the WM's placement, so the window opened at a varying size and
        # position ("About opens differently each time") — the same root-cause class
        # as the old "Settings opens squished" fix (ea610e4). XWayland (forced xcb in
        # __main__) honours an explicit move, as it already does for notes/manager.
        # The body uses explicit "\n" (no word-wrap), so the sizeHint is stable
        # pre-/post-show and the centre computed here matches where it maps.
        dlg.resize(dlg.sizeHint())
        avail = self.primaryScreen().availableGeometry()
        sz = dlg.size()
        dlg.move(avail.left() + (avail.width()  - sz.width())  // 2,
                 avail.top()  + (avail.height() - sz.height()) // 2)
        self._show_window(dlg)

    # ── Persistence ───────────────────────────────────────────────────────────
    def _trim_memory(self):
        """Return unused memory to the OS after heavy operations like file dialogs.
        gc.collect() clears Python cyclic references; malloc_trim(0) returns
        freed heap pages back to the OS so htop/top show accurate RSS.
        """
        import gc
        from PyQt6.QtGui import QPixmapCache
        QPixmapCache.clear()   # drop Qt's internal pixmap cache
        gc.collect()
        try:
            import ctypes
            ctypes.cdll.LoadLibrary("libc.so.6").malloc_trim(0)
        except Exception:
            pass

    def quit_app(self):
        self._global_save_timer.stop()
        self._do_save()
        self._save_trash_notes()
        self._save_archived_notes()
        self.quit()
