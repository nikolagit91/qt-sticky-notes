"""Clicking away from a note must RELEASE its focus, not just hide the caret.

Bug (second half): once a note's editor had been focused by a click, Qt kept
that focus inside the window. Clicking elsewhere only DEACTIVATED the window
(caret hidden), so every later WM re-activation (another app closing, focus
returning) restored the caret — "the cursor keeps coming back after I clicked
away". changeEvent now clears the focused child when the note stops being the
active window, so re-activation has nothing to restore.

The handler is unit-tested directly (offscreen can't drive real WM activation):
isActiveWindow / focusWidget are stubbed so we can assert exactly when the child
is cleared.
"""
import sys, os, tempfile, atexit, shutil
_SB = tempfile.mkdtemp(prefix="sn_deact_")
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
from PyQt6.QtCore import QEvent
QMessageBox.information = staticmethod(lambda *a, **k: None)

fails = []
def check(name, cond):
    print(f"  {'PASS' if cond else 'FAIL'}   {name}")
    if not cond: fails.append(name)

from sticky_notes.app import StickyNotesApp
from sticky_notes.note import StickyNote

app = StickyNotesApp(sys.argv[:1])
note = StickyNote(app, "deact-1", {"id": "deact-1", "content": "hi"})

cleared = {"n": 0}
class FakeFocus:
    def clearFocus(self): cleared["n"] += 1
note.focusWidget = lambda: FakeFocus()   # a child currently holds focus

def activation_change():
    note.changeEvent(QEvent(QEvent.Type.ActivationChange))

# Deactivated → the focused child is released.
note.isActiveWindow = lambda: False
activation_change()
check("deactivation releases the focused child", cleared["n"] == 1)

# Activated → nothing is cleared (you may be about to type).
note.isActiveWindow = lambda: True
activation_change()
check("activation does NOT clear focus", cleared["n"] == 1)

# A non-activation change (e.g. window state) is ignored even when inactive.
note.isActiveWindow = lambda: False
note.changeEvent(QEvent(QEvent.Type.WindowStateChange))
check("non-activation change is ignored", cleared["n"] == 1)

# No focused child → no crash, nothing to clear.
note.focusWidget = lambda: None
activation_change()
check("no focused child → no-op (no crash)", cleared["n"] == 1)

print("ALL PASS" if not fails else f"FAILS: {fails}")
sys.exit(1 if fails else 0)
