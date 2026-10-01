"""The new-note default must NOT be a bare Super+<letter>.

GNOME's overview grabs Super+<letter> (routing it to shell search), so a plain
<Super>n never reaches our low-priority custom keybinding — confirmed on Fedora,
where Super+N failed while the two Super+Shift combos worked. The default is
<Super><Alt>n instead. This is declared in TWO places that must agree:
hotkey.NEW_NOTE.default_binding and StickyNotesApp._hotkey_binding (the value
actually registered). Guard both, and guard the "no bare Super+letter" rule so a
future edit can't silently reintroduce the swallowed combo.
"""
import sys, os, tempfile, atexit, shutil, re
_SB = tempfile.mkdtemp(prefix="sn_hkdef_")
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

EXPECTED = "<Super><Alt>n"
check("hotkey.NEW_NOTE default is <Super><Alt>n",
      hotkey.NEW_NOTE.default_binding == EXPECTED)
check("app._hotkey_binding default matches the Hotkey default",
      app._hotkey_binding == hotkey.NEW_NOTE.default_binding)

# The rule that motivates the value: never a bare Super + single letter, which
# GNOME's overview swallows. Accept it only if it carries Alt or Ctrl too.
bare_super_letter = re.fullmatch(r"<Super>[a-z]", app._hotkey_binding) is not None
check("new-note default is NOT a bare Super+<letter> (overview would eat it)",
      not bare_super_letter)

print("ALL PASS" if not fails else f"FAILS: {fails}")
sys.exit(1 if fails else 0)
