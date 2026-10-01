"""Settings persistence extracted from app.py (review #3 A3).

Loads/saves the app's preferences (settings.json) and manages the backup
interval. Mixin: StickyNotesApp inherits it, so each method still operates on
`self` (the app). Neutral deps only (config), no import cycle.
"""
import os
import json

from .config import SETTINGS_FILE
from .theme import coerce_border_mode
from .theme_schedule import coerce_hhmm


def _num(value, fallback, lo, hi, cast=int):
    """Coerce a persisted numeric setting into something usable.

    settings.json is a plain file users do edit by hand, and a value's type can
    change between app versions — note_border went bool -> str, which is exactly
    why coerce_border_mode exists. Every numeric setting used to be read raw, so
    a string, a null or a list landed straight in app state and only blew up
    later, at the point of use. The worst case was note_opacity: it reached
    _bg_alpha's arithmetic, so EVERY note failed to build and the app would not
    start at all — with the cause invisible to anyone launching from the dock.

    Clamping to the same range the Settings control offers also means a value
    edited far out of range can still be dialled back from inside the app."""
    try:
        v = cast(value)
    except (TypeError, ValueError):
        return fallback
    return max(lo, min(hi, v))


class SettingsMixin:

    def _load_backup_settings(self):
        if not os.path.exists(SETTINGS_FILE):
            return   # first run — no settings file yet, use defaults silently
        try:
            with open(SETTINGS_FILE, encoding="utf-8") as f:
                data = json.load(f)
                # Numeric settings go through _num: ranges mirror the Settings
                # controls (spin boxes / sliders), so a hand-edited or
                # version-drifted value can never make the UI unusable.
                self._set_backup_interval(
                    _num(data.get("backup_interval", 0), 0, 0, 1440), save=False)
                self._default_font_family = data.get("font_family", self._default_font_family)
                self._default_font_size   = _num(data.get("font_size", self._default_font_size),
                                                 self._default_font_size, 8, 72)
                self._autostart_enabled   = data.get("autostart",   self._autostart_enabled)
                self._ui_scale            = _num(data.get("ui_scale", self._ui_scale),
                                                 self._ui_scale, 1.0, 2.0, float)
                self._hotkey_enabled      = data.get("hotkey_enabled", self._hotkey_enabled)
                self._hotkey_binding      = data.get("hotkey_binding", self._hotkey_binding)
                self._hotkey_clip_enabled = data.get("hotkey_clip_enabled", self._hotkey_clip_enabled)
                self._hotkey_clip_binding = data.get("hotkey_clip_binding", self._hotkey_clip_binding)
                self._hotkey_search_enabled = data.get("hotkey_search_enabled", self._hotkey_search_enabled)
                self._hotkey_search_binding = data.get("hotkey_search_binding", self._hotkey_search_binding)
                self._language            = data.get("language", self._language)
                self._snap_to_grid        = data.get("snap_to_grid", self._snap_to_grid)
                self._snap_to_notes       = data.get("snap_to_notes", self._snap_to_notes)
                self._snap_size           = data.get("snap_size", self._snap_size)
                self._grid_size           = _num(data.get("grid_size", self._grid_size),
                                                 self._grid_size, 5, 100)
                self._tray_scroll_enabled = data.get("tray_scroll_enabled", self._tray_scroll_enabled)
                self._default_note_width  = _num(data.get("note_width", self._default_note_width),
                                                 self._default_note_width, 240, 1200)
                self._default_note_height = _num(data.get("note_height", self._default_note_height),
                                                 self._default_note_height, 168, 1000)
                self._note_opacity        = _num(data.get("note_opacity", self._note_opacity),
                                                 self._note_opacity, 40, 100)
                self._auto_contrast       = data.get("auto_contrast", self._auto_contrast)
                self._clean_mode          = data.get("clean_mode", self._clean_mode)
                self._code_blocks         = data.get("code_blocks", self._code_blocks)
                self._note_border         = coerce_border_mode(data.get("note_border", self._note_border))
                _mode = data.get("theme", self._theme_mode)
                self._theme_mode = _mode if _mode in ("light", "dark", "auto") else "light"
                self._theme_dark_start = coerce_hhmm(
                    data.get("theme_dark_start", self._theme_dark_start), self._theme_dark_start)
                self._theme_dark_end = coerce_hhmm(
                    data.get("theme_dark_end", self._theme_dark_end), self._theme_dark_end)
                if self._theme_mode != "auto":
                    self._theme = self._theme_mode
                # auto: _theme (efektivna) ostaje kakvu je izracunao early blok /
                # zivi scheduler — load NE smije pregaziti raspored.
        except Exception as e:
            print(f"[load settings] error: {e}")

    def _set_backup_interval(self, minutes: int, save: bool = True):
        self._backup_interval_minutes = minutes
        self._backup_timer.stop()
        if minutes > 0:
            self._backup_timer.start(minutes * 60 * 1000)
        if save:
            self._save_backup_settings()

    def _save_backup_settings(self):
        os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
        try:
            existing = {}
            try:
                with open(SETTINGS_FILE, encoding="utf-8") as f:
                    existing = json.load(f)
                if not isinstance(existing, dict):
                    existing = {}
            except Exception:
                pass
            existing["backup_interval"] = self._backup_interval_minutes
            existing["font_family"] = self._default_font_family
            existing["font_size"]   = self._default_font_size
            existing["autostart"]   = self._autostart_enabled
            existing["ui_scale"]    = self._ui_scale
            existing["hotkey_enabled"] = self._hotkey_enabled
            existing["hotkey_binding"] = self._hotkey_binding
            existing["hotkey_clip_enabled"] = self._hotkey_clip_enabled
            existing["hotkey_clip_binding"] = self._hotkey_clip_binding
            existing["hotkey_search_enabled"] = self._hotkey_search_enabled
            existing["hotkey_search_binding"] = self._hotkey_search_binding
            existing["language"] = self._language
            existing["snap_to_grid"]  = self._snap_to_grid
            existing["snap_to_notes"] = self._snap_to_notes
            existing["snap_size"]     = self._snap_size
            existing["grid_size"]     = self._grid_size
            existing["tray_scroll_enabled"] = self._tray_scroll_enabled
            existing["note_width"]    = self._default_note_width
            existing["note_height"]   = self._default_note_height
            existing["note_opacity"]  = self._note_opacity
            existing["auto_contrast"] = self._auto_contrast
            existing["clean_mode"]    = self._clean_mode
            existing["code_blocks"]   = self._code_blocks
            existing["note_border"]   = self._note_border
            existing["theme"]            = self._theme_mode
            existing["theme_dark_start"] = self._theme_dark_start
            existing["theme_dark_end"]   = self._theme_dark_end
            # Atomic write: a crash mid-write must not truncate settings.json
            # (which would silently reset every preference on next launch).
            tmp = SETTINGS_FILE + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(existing, f, indent=2)
            os.replace(tmp, SETTINGS_FILE)
        except Exception as e:
            print(f"[settings] save error: {e}")

