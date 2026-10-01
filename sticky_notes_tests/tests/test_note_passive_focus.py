"""A restored note must not grab the keyboard when its window is activated.

Bug: on login (and whenever another app closes and the WM activates a note),
Qt auto-assigned focus to the note's editor because QTextEdit ships with
WheelFocus (includes TabFocus) — so a blinking caret appeared on whichever note
the WM made active, without any user interaction.

Root-cause fix: no child of a note carries the TabFocus bit, so nothing is a
target for Qt's activate-time auto-focus. The editor is ClickFocus (edit by
clicking) and the chrome buttons are NoFocus (still mouse-operable). Focus — and
the caret — then land only via an explicit click or setFocus().

This guards the invariant offscreen; the actual "no caret at login" is verified
on real GNOME (see docs/RUCNA_GNOME_CHECKLISTA.md).
"""
import sys, os, tempfile, atexit, shutil
_SB = tempfile.mkdtemp(prefix="sn_passive_")
atexit.register(lambda: shutil.rmtree(_SB, ignore_errors=True))
os.environ["HOME"] = _SB
os.environ["XDG_CONFIG_HOME"] = os.path.join(_SB, ".config")
os.environ["XDG_DATA_HOME"]   = os.path.join(_SB, ".local", "share")
os.environ.setdefault("XDG_RUNTIME_DIR", _SB)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ.pop("DISPLAY", None); os.environ.pop("WAYLAND_DISPLAY", None)
os.makedirs(os.path.join(_SB, ".local", "share", "sticky_notes"), exist_ok=True)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import QMessageBox, QAbstractButton
from PyQt6.QtCore import Qt
QMessageBox.information = staticmethod(lambda *a, **k: None)

fails = []
def check(name, cond):
    print(f"  {'PASS' if cond else 'FAIL'}   {name}")
    if not cond: fails.append(name)

from sticky_notes.app import StickyNotesApp
from sticky_notes.note import StickyNote

app = StickyNotesApp(sys.argv[:1])

# A note as restored from disk (the login path builds notes exactly like this,
# NOT via create_new_note).
note = StickyNote(app, "passive-1", {"id": "passive-1", "content": "hello"})

TAB = Qt.FocusPolicy.TabFocus

# 1) The editor must not be tab/auto-focusable, but must still accept clicks.
te_pol = note.text_edit.focusPolicy()
check("editor is NOT TabFocus-capable (no activate-time caret)",
      not (int(te_pol) & int(TAB)))
check("editor still accepts click focus (edit by clicking)",
      bool(int(te_pol) & int(Qt.FocusPolicy.ClickFocus)))

# 2) NO child of the note may carry TabFocus — that is what Qt picks as the
#    auto-focus target on window activation. Empty set = nothing to auto-focus.
tabbable = [type(w).__name__ for w in note.findChildren(object)
            if hasattr(w, "focusPolicy") and callable(getattr(w, "focusPolicy"))
            and int(w.focusPolicy()) & int(TAB)]
check("no note child is TabFocus-capable (nothing auto-focuses on activation)",
      tabbable == [])

# 3) The chrome buttons must still exist and be clickable (NoFocus, not removed).
buttons = note.findChildren(QAbstractButton)
check("note still has its chrome buttons (not removed, just NoFocus)",
      len(buttons) > 0 and all(b.focusPolicy() == Qt.FocusPolicy.NoFocus for b in buttons))

if tabbable:
    print("   still tabbable:", tabbable)
print("ALL PASS" if not fails else f"FAILS: {fails}")
sys.exit(1 if fails else 0)
