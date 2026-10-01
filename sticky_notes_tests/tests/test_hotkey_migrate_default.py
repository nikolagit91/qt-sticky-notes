"""Existing installs move off the swallowed <Super>n onto the new default.

_sync_hotkey normally ADOPTS the live gsettings binding ("respect a binding
changed elsewhere"). But bare <Super>n was our own broken default (GNOME's
overview eats it), never a real user choice — so when the live accelerator is
EXACTLY that old value, sync must re-register at the new default instead of
adopting it, and persist so the hint/settings agree. Any other accelerator is a
genuine user choice and must be left alone.

hotkey.get_state/register/command_is_current are monkeypatched, so this touches
no real dconf.
"""
import sys, os, tempfile, atexit, shutil
_SB = tempfile.mkdtemp(prefix="sn_hkmig_")
atexit.register(lambda: shutil.rmtree(_SB, ignore_errors=True))
os.environ["HOME"] = _SB
os.environ["XDG_CONFIG_HOME"] = os.path.join(_SB, ".config")
os.environ["XDG_DATA_HOME"]   = os.path.join(_SB, ".local", "share")
os.environ.setdefault("XDG_RUNTIME_DIR", _SB)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ.pop("DISPLAY", None); os.environ.pop("WAYLAND_DISPLAY", None)
os.makedirs(os.path.join(_SB, ".local", "share", "sticky_notes"), exist_ok=True)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)

fails = []
def check(name, cond):
    print(f"  {'PASS' if cond else 'FAIL'}   {name}")
    if not cond: fails.append(name)

from sticky_notes import hotkey
from sticky_notes.app import StickyNotesApp

app = StickyNotesApp(sys.argv[:1])

# ── Harness: record register() calls, stub the gsettings reads ───────────────
registered = []            # list of (name, binding)
hotkey.register = lambda hk, binding=None: (registered.append((hk.name, binding)) or True)
hotkey.command_is_current = lambda hk: True   # so the ONLY re-register is migration

# ── Case 1: the old broken default is live → migrate to the new default ──────
hotkey.get_state = lambda hk: (True, "<Super>n")
app._hotkey_binding = "<Super>n"
registered.clear()
app._sync_hotkey(hotkey.NEW_NOTE, True, "_hotkey_binding")

check("registered exactly once (the upgrade)", len(registered) == 1)
check("re-registered at the NEW default <Super><Alt>n",
      registered == [(hotkey.NEW_NOTE.name, "<Super><Alt>n")])
check("stored binding updated to the new default",
      app._hotkey_binding == "<Super><Alt>n")

# ── Case 2: a real user binding is live → adopt it, do NOT migrate ───────────
hotkey.get_state = lambda hk: (True, "<Super><Shift>k")
app._hotkey_binding = "<Super>n"     # stale stored value; live one must win
registered.clear()
app._sync_hotkey(hotkey.NEW_NOTE, True, "_hotkey_binding")

check("a genuine user binding is NOT re-registered", registered == [])
check("a genuine user binding is adopted, not overwritten",
      app._hotkey_binding == "<Super><Shift>k")

print("ALL PASS" if not fails else f"FAILS: {fails}")
sys.exit(1 if fails else 0)
