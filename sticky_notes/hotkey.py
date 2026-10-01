"""GNOME global shortcut registration via GSettings (gnome-settings-daemon).

On GNOME/Wayland the robust way to provide a global hotkey is to register a
custom keyboard shortcut at the desktop level that runs a command. We register
one pointing at the app launcher with ``--new-note``; the running instance then
creates the note over D-Bus (see ipc.py). Because the binding lives in the
compositor, it fires no matter which window is focused.

All access goes through Gio.Settings (the native GNOME settings API). Everything
is guarded: if PyGObject/Gio is missing, or the GNOME media-keys schema isn't
installed (a non-GNOME desktop), registration is silently skipped and the app
still runs — the user just binds a shortcut manually.
"""

import os
import shlex

from .config import DATA_DIR

# A stable name lets us find / update / remove *our* entry without disturbing
# any other custom shortcuts the user has created.
class Hotkey:
    """One registerable GNOME shortcut: a stable name (so we can find/update our
    own entry without disturbing the user's other shortcuts), the command-line
    arg the launcher forwards, and a default accelerator."""

    def __init__(self, name: str, arg: str, default_binding: str, migrate_from: str = None):
        self.name = name
        self.arg = arg
        self.default_binding = default_binding
        # A superseded binding to auto-upgrade on sync: when the LIVE registered
        # accelerator is exactly this value, treat it as a stale default the user
        # never really chose and re-register at default_binding instead of
        # adopting it. Used to move existing installs off the swallowed <Super>n.
        self.migrate_from = migrate_from

_MEDIA_KEYS_SCHEMA = "org.gnome.settings-daemon.plugins.media-keys"
_CUSTOM_SCHEMA     = "org.gnome.settings-daemon.plugins.media-keys.custom-keybinding"
_CUSTOM_PATH_BASE  = "/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/"
_LIST_KEY          = "custom-keybindings"

NEW_NOTE      = Hotkey("Sticky Notes — New Note",
                       "--new-note", "<Super><Alt>n", migrate_from="<Super>n")
                       # NOT a bare <Super>n: GNOME's overview grabs Super+<letter>
                       # (routes it to shell search), so a plain Super+N never reaches
                       # this custom binding. The two Shift combos below dodge the grab;
                       # new-note uses Alt. migrate_from moves existing installs that
                       # still have the old <Super>n registered onto the new default.
NEW_NOTE_CLIP = Hotkey("Sticky Notes — New Note from Clipboard",
                       "--new-note-from-clipboard", "<Super><Shift>n")
SEARCH        = Hotkey("Sticky Notes — Search Notes",
                       "--search", "<Super><Shift>f")
# NO "surface notes" hotkey. Bringing existing notes to the front from a global
# shortcut has been tried TWICE (Super+Shift+R in 2026-07-07, Super+Shift+S in
# 2026-07-18) and failed both times. Still not present — but see the caveat.
#
# ⚠️ THE OLD REASON WAS WRONG — MEASURED 2026-07-18. It used to read: "Mutter's
# focus-stealing prevention drops raise_()/activateWindow() on an EXISTING window
# when the call arrives from a background context". A standalone probe (a
# note-like xcb window raising ITSELF from a pure QTimer, no user interaction
# with it at all) settled it:
#
#   against a browser : the probe came to the front, and _NET_ACTIVE_WINDOW
#                       became the probe's own id  → the background raise WORKS
#   against Claude    : nothing moved, _NET_ACTIVE_WINDOW stayed 0x0
#
# The user confirmed both by eye. So the caller's context was never the problem.
# The real reason is the STACKING LAYER: the Claude desktop app keeps itself
# always-on-top, and raise_() only reorders a window WITHIN its own layer — so a
# normal-layer window can never rise past it, however it is invoked. Both earlier
# experiments were run against the one application that cannot be beaten.
#
# WHAT THIS MEANS IF THE FEATURE IS EVER RECONSIDERED: a global "surface notes"
# hotkey would work fine against ordinary applications, and would still NOT work
# against an always-on-top one. Beating those needs EWMH _NET_WM_STATE_ABOVE, and
# that road was explored and rejected in the same session — see the ABOVE-pulse
# post-mortem in PROJEKAT_HANDOFF.md (notes then never drop back down).
#
# Feature deliberately still absent — the user has not asked for it back.


def _gio():
    """Return the Gio module IF it imports AND the GNOME media-keys schemas are
    installed; otherwise None.

    Critically, ``Gio.Settings.new()`` on a missing schema *aborts the process*
    (it is a g_error, not a Python exception), so schema existence is verified
    via the schema source before any Settings object is constructed.
    """
    try:
        from gi.repository import Gio
    except Exception:
        return None
    try:
        src = Gio.SettingsSchemaSource.get_default()
        if src is None:
            return None
        if src.lookup(_MEDIA_KEYS_SCHEMA, True) is None:
            return None
        if src.lookup(_CUSTOM_SCHEMA, True) is None:
            return None
    except Exception:
        return None
    return Gio


def is_supported() -> bool:
    """True if a GNOME shortcut can be registered on this system."""
    return _gio() is not None


def command_for(hk: "Hotkey") -> str:
    """The command a shortcut runs to perform its action.

    Routes through the app's start.sh launcher (which cd's to the package parent
    and runs ``-m sticky_notes``), forwarding the hotkey's arg. A running
    instance handles it over D-Bus; if none is running, it cold-starts.
    """
    wrapper = os.path.join(DATA_DIR, "start.sh")
    return f"{shlex.quote(wrapper)} {hk.arg}"


def _find_our_path(Gio, media_keys, name) -> "str | None":
    for path in media_keys.get_strv(_LIST_KEY):
        try:
            kb = Gio.Settings.new_with_path(_CUSTOM_SCHEMA, path)
            if kb.get_string("name") == name:
                return path
        except Exception:
            continue
    return None


def _next_free_path(existing) -> str:
    i = 0
    while f"{_CUSTOM_PATH_BASE}custom{i}/" in existing:
        i += 1
    return f"{_CUSTOM_PATH_BASE}custom{i}/"


def get_state(hk: "Hotkey") -> "tuple[bool, str]":
    """Return ``(is_registered, binding)`` for the given shortcut.

    ``binding`` is the accelerator currently set — which the user may have
    changed via GNOME Settings — or ``''`` if not registered.
    """
    Gio = _gio()
    if Gio is None:
        return (False, "")
    try:
        media_keys = Gio.Settings.new(_MEDIA_KEYS_SCHEMA)
        path = _find_our_path(Gio, media_keys, hk.name)
        if path is None:
            return (False, "")
        kb = Gio.Settings.new_with_path(_CUSTOM_SCHEMA, path)
        return (True, kb.get_string("binding"))
    except Exception as e:
        print(f"[hotkey] read failed: {e}")
        return (False, "")


def command_is_current(hk: "Hotkey") -> bool:
    """True if the registered shortcut's command matches what we'd write now
    (``command_for``). A False means the stored command is stale — the app moved,
    or a headless/test run polluted the real dconf with a temp path — so the
    caller should re-register to self-heal (which preserves the user's binding).
    Returns True (no repair) when the entry is absent or gsettings is unavailable."""
    Gio = _gio()
    if Gio is None:
        return True
    try:
        media_keys = Gio.Settings.new(_MEDIA_KEYS_SCHEMA)
        path = _find_our_path(Gio, media_keys, hk.name)
        if path is None:
            return True
        kb = Gio.Settings.new_with_path(_CUSTOM_SCHEMA, path)
        return kb.get_string("command") == command_for(hk)
    except Exception:
        return True


def register(hk: "Hotkey", binding: str = None) -> bool:
    """Create or update the given custom shortcut. Returns True on success."""
    Gio = _gio()
    if Gio is None:
        return False
    if binding is None:
        binding = hk.default_binding
    try:
        media_keys = Gio.Settings.new(_MEDIA_KEYS_SCHEMA)
        existing = list(media_keys.get_strv(_LIST_KEY))
        path = _find_our_path(Gio, media_keys, hk.name)
        if path is None:
            path = _next_free_path(existing)
        kb = Gio.Settings.new_with_path(_CUSTOM_SCHEMA, path)
        kb.set_string("name", hk.name)
        kb.set_string("command", command_for(hk))
        kb.set_string("binding", binding)
        # Force gnome-settings-daemon's media-keys plugin to (re)load the binding.
        # Writing the per-binding sub-keys alone is often ignored for an entry that
        # ALREADY exists — the daemon only re-scans when the custom-keybindings
        # LIST changes. That is the classic "it only works after I delete and
        # re-add the same shortcut". So we always rewrite the list, removing then
        # re-adding our path, to guarantee a change signal (and thus a reload)
        # whether the entry is new or merely had its accelerator changed.
        without = [p for p in existing if p != path]
        media_keys.set_strv(_LIST_KEY, without)
        Gio.Settings.sync()
        media_keys.set_strv(_LIST_KEY, without + [path])
        Gio.Settings.sync()
        return True
    except Exception as e:
        print(f"[hotkey] register failed: {e}")
        return False


def unregister(hk: "Hotkey") -> bool:
    """Remove the given custom shortcut, leaving other shortcuts intact."""
    Gio = _gio()
    if Gio is None:
        return False
    try:
        media_keys = Gio.Settings.new(_MEDIA_KEYS_SCHEMA)
        path = _find_our_path(Gio, media_keys, hk.name)
        if path is None:
            return True
        existing = list(media_keys.get_strv(_LIST_KEY))
        if path in existing:
            existing.remove(path)
            media_keys.set_strv(_LIST_KEY, existing)
        try:
            kb = Gio.Settings.new_with_path(_CUSTOM_SCHEMA, path)
            for key in ("name", "command", "binding"):
                kb.reset(key)
        except Exception:
            pass
        Gio.Settings.sync()
        return True
    except Exception as e:
        print(f"[hotkey] unregister failed: {e}")
        return False


def accel_to_label(accel: str) -> str:
    """'<Super>n' -> 'Super+N' for display (best-effort, GTK accelerator names)."""
    if not accel:
        return "(none)"
    repl = {
        "<Super>": "Super+", "<Primary>": "Ctrl+", "<Control>": "Ctrl+",
        "<Ctrl>": "Ctrl+", "<Alt>": "Alt+", "<Shift>": "Shift+", "<Meta>": "Meta+",
    }
    s = accel
    for k, v in repl.items():
        s = s.replace(k, v)
    if s and s[-1].isalpha() and (len(s) == 1 or s[-2] == "+"):
        s = s[:-1] + s[-1].upper()
    return s
