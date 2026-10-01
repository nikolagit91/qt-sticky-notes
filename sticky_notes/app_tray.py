"""System-tray setup extracted from app.py (review #3 A3).

Builds the tray indicator (AyatanaAppIndicator3 on GNOME, else QSystemTrayIcon)
and its menu, and handles tray clicks. Mixin: StickyNotesApp inherits it, so
each method still operates on `self` (the app). gi/Gtk/AppIndicator are imported
lazily inside the methods (only on GNOME); module-level deps are neutral
(config/icons/i18n/PyQt6), so there is no import cycle.
"""
import os

from PyQt6.QtWidgets import QSystemTrayIcon, QMenu
from PyQt6.QtCore import QTimer

from .config import DATA_DIR
from .icons import create_tray_icon
from .i18n import tr
from .theme import menu_style


class TrayMixin:

    def _build_tray(self):
        # Try AyatanaAppIndicator first — fixes GNOME spinner bug
        try:
            import gi
            gi.require_version('AyatanaAppIndicator3', '0.1')
            from gi.repository import AyatanaAppIndicator3, GLib
            self._build_tray_ayatana(AyatanaAppIndicator3, GLib)
        except Exception:
            self._build_tray_qt()

    def _build_tray_ayatana(self, AyatanaAppIndicator3, GLib):
        _dark = getattr(self, "_theme", "light") == "dark"
        # Save icon as PNG for ayatana
        icon_path = os.path.join(DATA_DIR, "tray_icon_dark.png" if _dark else "tray_icon.png")
        create_tray_icon(dark=_dark).pixmap(64, 64).save(icon_path)

        self._indicator = AyatanaAppIndicator3.Indicator.new(
            "sticky-notes",
            icon_path,
            AyatanaAppIndicator3.IndicatorCategory.APPLICATION_STATUS
        )
        self._indicator.set_status(AyatanaAppIndicator3.IndicatorStatus.ACTIVE)

        # Build GTK menu
        import gi
        gi.require_version('Gtk', '3.0')
        from gi.repository import Gtk

        # NOTE: the Ayatana menu is exported over DBusMenu and RENDERED BY
        # gnome-shell (the AppIndicator extension), not by our process — so its
        # colours follow the shell theme and can't be themed from the app (same
        # category as the WM titlebar). Only the tray *icon* (our PNG) is ours.
        gtk_menu = Gtk.Menu()

        entries = [
            (tr("New Note"),      lambda *a: QTimer.singleShot(0, self.create_new_note)),
            (tr("Show All"),      lambda *a: QTimer.singleShot(0, self.show_all_notes)),
            (tr("Hide All"),      lambda *a: QTimer.singleShot(0, self.hide_all_notes)),
            (tr("Lock All"),      lambda *a: QTimer.singleShot(0, self.lock_all_notes)),
            (tr("Unlock All"),    lambda *a: QTimer.singleShot(0, self.unlock_all_notes)),
            (tr("Search Notes…"), lambda *a: QTimer.singleShot(0, self.show_search)),
            None,
            (tr("Notes Manager"), lambda *a: QTimer.singleShot(0, self.show_manager)),
            (tr("Settings"),      lambda *a: QTimer.singleShot(0, self.show_settings)),
            (tr("Toggle theme"), lambda *a: QTimer.singleShot(0, self._toggle_theme)),
            (tr("Keyboard shortcuts…"), lambda *a: QTimer.singleShot(0, self.show_shortcuts)),
            (tr("About"),         lambda *a: QTimer.singleShot(0, self.show_about)),
            None,
            (tr("Quit"),          lambda *a: QTimer.singleShot(0, self.quit_app)),
        ]

        for entry in entries:
            if entry is None:
                item = Gtk.SeparatorMenuItem()
            else:
                label, slot = entry
                item = Gtk.MenuItem(label=label)
                item.connect("activate", slot)
            item.show()
            gtk_menu.append(item)

        self._indicator.set_menu(gtk_menu)

        # Scroll UP on the tray icon brings visible (non-pinned) notes to the
        # front — a quick "surface my notes" gesture. Scroll DOWN intentionally
        # does nothing: reliably dropping notes *behind* a window is a Mutter
        # dead end, so the user drops them by clicking their work window.
        try:
            self._indicator.connect("scroll-event", self._on_tray_scroll)
        except Exception:
            pass

    def _on_tray_scroll(self, indicator, delta, direction):
        try:
            from gi.repository import Gdk
            up = direction == Gdk.ScrollDirection.UP
        except Exception:
            up = False
        if up and getattr(self, "_tray_scroll_enabled", True):
            QTimer.singleShot(0, self.raise_visible_notes)

    def _update_tray_icon(self, dark: bool):
        """Refresh the tray icon for the current theme. Best-effort and guarded:
        the Ayatana path can't be exercised headless, and a failure here must
        never break a theme switch."""
        try:
            if getattr(self, "_indicator", None) is not None:
                path = os.path.join(DATA_DIR, "tray_icon_dark.png" if dark else "tray_icon.png")
                create_tray_icon(dark=dark).pixmap(64, 64).save(path)
                self._indicator.set_icon_full(path, "Sticky Notes")
            elif getattr(self, "tray", None) is not None:
                self.tray.setIcon(create_tray_icon(dark=dark))
        except Exception:
            pass

    def _build_tray_qt(self):
        """Fallback to QSystemTrayIcon if ayatana not available."""
        self.tray = QSystemTrayIcon(
            create_tray_icon(dark=getattr(self, "_theme", "light") == "dark"), self)
        self.tray.setToolTip("Sticky Notes")

        menu = QMenu()
        menu.setStyleSheet(menu_style())

        entries = [
            (tr("New Note"),       lambda: self.create_new_note()),
            (tr("Show All"),       self.show_all_notes),
            (tr("Hide All"),       self.hide_all_notes),
            (tr("Lock All"),       self.lock_all_notes),
            (tr("Unlock All"),     self.unlock_all_notes),
            (tr("Search Notes…"),  self.show_search),
            None,
            (tr("Notes Manager"),  self.show_manager),
            (tr("Settings"),       self.show_settings),
            (tr("Toggle theme"),   lambda: self._set_theme("light" if self._theme == "dark" else "dark")),
            (tr("Keyboard shortcuts…"), self.show_shortcuts),
            (tr("About"),          self.show_about),
            None,
            (tr("Quit"),           self.quit_app),
        ]

        for entry in entries:
            if entry is None:
                menu.addSeparator()
            else:
                label, slot = entry
                menu.addAction(label).triggered.connect(slot)

        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._on_tray_click)
        self.tray.show()

    def _on_tray_click(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            if any(n.isVisible() for n in self.notes.values()):
                self.hide_all_notes()
            else:
                self.show_all_notes()

    # ── Note management ───────────────────────────────────────────────────────
