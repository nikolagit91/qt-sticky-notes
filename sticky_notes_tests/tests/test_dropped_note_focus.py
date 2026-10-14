"""A note dropped to the bottom is made UNFOCUSABLE until the user picks it again.

Why (measured on the user's GNOME, 2026-10-14, three probe runs, by eye + focus
logs): minimizing the front app makes GNOME hand focus to the most-recently-used
window — a dropped note — and RAISE it, undoing the drop. Clearing only
WM_HINTS.input stopped the focus but GNOME still raised the note; clearing
input AND removing WM_TAKE_FOCUS from WM_PROTOCOLS made GNOME skip it (all
notes stayed at the bottom), and restoring both on a click let the user type.

Guards: a drop makes the note unfocusable; a mouse press on it, any
_bring_to_front and a firing reminder make it focusable again BEFORE activating
it; off X11 nothing is marked; the press listener only lives while needed."""
import sys, os, tempfile, atexit, shutil
_SB = tempfile.mkdtemp(prefix="sn_test_")
atexit.register(lambda: shutil.rmtree(_SB, ignore_errors=True))
os.environ["HOME"] = _SB
os.environ["XDG_CONFIG_HOME"] = os.path.join(_SB, ".config")
os.environ["XDG_DATA_HOME"]   = os.path.join(_SB, ".local", "share")
os.environ.setdefault("XDG_RUNTIME_DIR", _SB)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ.pop("DISPLAY", None); os.environ.pop("WAYLAND_DISPLAY", None)
os.makedirs(os.path.join(_SB, ".local", "share", "sticky_notes"), exist_ok=True)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtCore import Qt, QEvent, QPointF
from PyQt6.QtGui import QMouseEvent

fails = []
def check(name, cond):
    print(f"  {'PASS' if cond else 'FAIL'}   {name}")
    if not cond: fails.append(name)

from sticky_notes import x11
from sticky_notes.app import StickyNotesApp
app = StickyNotesApp(sys.argv[:1])
app._snap_to_grid = app._snap_to_notes = app._snap_size = False
for e in list(app.notes.values()):
    e.hide(); e.deleteLater()
app.notes.clear()

A = app.create_new_note(); B = app.create_new_note()

# Pretend X11 works: record every call, in order, per window id.
calls = []
x11.restack_below = lambda wid: (calls.append(("restack", wid)), True)[1]
x11.set_focusable = lambda wid, on: (calls.append(("focusable", wid, on)), True)[1]
activated = []
for n in (A, B):
    n.activateWindow = (lambda n=n: (calls.append(("activate", int(n.winId()))), activated.append(n)))

def press(widget):
    ev = QMouseEvent(QEvent.Type.MouseButtonPress, QPointF(5, 5), QPointF(5, 5),
                     Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton,
                     Qt.KeyboardModifier.NoModifier)
    app.sendEvent(widget, ev)
    app.processEvents()

wa, wb = int(A.winId()), int(B.winId())

# ── drop → bottom of the stack AND unfocusable
app._drop_note(A)
check("drop restacks the note to the bottom", ("restack", wa) in calls)
check("drop makes the note unfocusable", ("focusable", wa, False) in calls)
check("the note remembers it is unfocusable", A._unfocusable is True)
check("press listener is on while a note is unfocusable", app._tray_filter_on is True)

# ── a mouse press on the dropped note makes it focusable, THEN activates it
calls.clear()
press(A.text_edit.viewport())
check("press on a dropped note restores focusability", ("focusable", wa, True) in calls)
check("…before activating it",
      ("activate", wa) in calls and calls.index(("focusable", wa, True)) < calls.index(("activate", wa)))
check("flag cleared after the press", A._unfocusable is False)
check("press listener removed once nothing needs it", app._tray_filter_on is False)

# ── a press on a note that was never dropped does not touch it
calls.clear()
press(B.text_edit.viewport())
check("press on a normal note changes nothing", calls == [])

# ── _bring_to_front (tray raise, Show All, search, Manager) restores first
app._drop_note(B)
calls.clear()
app._bring_to_front(B)
check("_bring_to_front makes a dropped note focusable before activating",
      ("focusable", wb, True) in calls and ("activate", wb) in calls
      and calls.index(("focusable", wb, True)) < calls.index(("activate", wb)))
check("…and clears its flag", B._unfocusable is False)

# ── a firing reminder surfaces the note: focusable first
x11.set_above = lambda wid, on: True
app._drop_note(A)
calls.clear()
A._surface_for_reminder()
check("reminder makes a dropped note focusable before activating",
      ("focusable", wa, True) in calls and ("activate", wa) in calls
      and calls.index(("focusable", wa, True)) < calls.index(("activate", wa)))

# ── off X11: the drop falls back to lower() and nothing is marked unfocusable
x11.restack_below = lambda wid: False
x11.set_focusable = lambda wid, on: False
lowered = []
A.lower = lambda: lowered.append(A)
app._drop_note(A)
check("off X11 the drop falls back to lower()", lowered == [A])
check("off X11 the note is NOT marked unfocusable", A._unfocusable is False)

print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
