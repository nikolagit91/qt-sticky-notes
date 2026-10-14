"""After the tray scroll-up raises the visible notes:
  * CLICKING one of them drops the others to the bottom of the stack;
  * LEAVING the app (clicking another app) drops ALL of them, the one you were
    editing included — so every raised note ends on the "desktop layer".

Spiked on the user's GNOME (2026-10-13), measured by eye + focus logs:
  * QWidget.lower() is honoured only while our app is ACTIVE; once the user has
    gone to another app it is ignored (the note they had used stayed above the
    window behind). EWMH _NET_RESTACK_WINDOW (pager source) is honoured in both
    cases → every drop goes through x11.restack_below, lower() only as fallback.
  * NOT solvable here: minimizing the front app makes GNOME hand focus to the
    most-recently-used window — the note — and raise it again.

The trigger for "the user picked a note" is a real MOUSE PRESS (the raise itself
activates every note in turn). The app-wide event filter lives only for one
raise session, which ends when the app goes inactive (debounced: focus moving
between our own notes can blip it inactive).

Window stacking itself is not observable offscreen; this guards the logic:
who gets dropped, when, through which call, and that the session ends."""
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

import time
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

A = app.create_new_note(); B = app.create_new_note(); C = app.create_new_note()
D = app.create_new_note(); E = app.create_new_note()
D._pinned = True                       # pinned: never raised, never dropped
E._hidden = True                       # hidden: never raised, never dropped
app._bring_to_front = lambda n: None   # WM stacking isn't observable offscreen

# ── _drop_note: EWMH restack first, lower() only when X11 is unavailable ──────
restacked, lowered = [], []
real_restack = x11.restack_below
for n in (A, B, C, D, E):
    n.lower = (lambda n=n: lowered.append(n))
x11.restack_below = lambda wid: (restacked.append(wid), True)[1]
app._drop_note(A)
check("drop uses EWMH restack_below with the note's window id",
      restacked == [int(A.winId())] and lowered == [])
restacked.clear()
x11.restack_below = lambda wid: False          # off X11 → fallback
app._drop_note(A)
check("drop falls back to lower() when X11 restack is unavailable", lowered == [A])
x11.restack_below = real_restack
lowered.clear()

# From here on, spy on the drop itself.
dropped = []
app._drop_note = lambda n: dropped.append(n)

def press(widget):
    ev = QMouseEvent(QEvent.Type.MouseButtonPress, QPointF(5, 5), QPointF(5, 5),
                     Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton,
                     Qt.KeyboardModifier.NoModifier)
    app.sendEvent(widget, ev)
    app.processEvents()

def leave_app():
    """User clicked another app: the app goes inactive and STAYS inactive."""
    real_state = app.applicationState
    app.applicationState = lambda: Qt.ApplicationState.ApplicationInactive
    app._on_app_state_changed(Qt.ApplicationState.ApplicationInactive)
    t0 = time.time()
    while time.time() - t0 < 0.6:
        app.processEvents(); time.sleep(0.02)
    app.applicationState = real_state

def blip_inactive():
    """Focus moving between our own notes: inactive for an instant only."""
    app._on_app_state_changed(Qt.ApplicationState.ApplicationInactive)   # state is still Active
    t0 = time.time()
    while time.time() - t0 < 0.6:
        app.processEvents(); time.sleep(0.02)

# ── click inside a raised note (the text area, a CHILD widget) drops the others
app.raise_visible_notes()
press(B.text_edit.viewport())
check(f"clicking B drops the other raised notes, once each ({len(dropped)} drops)",
      set(dropped) == {A, C} and len(dropped) == 2)
check("the clicked note is NOT dropped at the click", B not in dropped)
check("pinned and hidden notes are untouched", D not in dropped and E not in dropped)

# ── picking another raised note within the same session drops the rest again
dropped.clear()
press(A.text_edit.viewport())
check("clicking A next drops the others (B, C)", set(dropped) == {B, C})

# ── leaving the app drops ALL raised notes, incl. the one being edited
dropped.clear()
leave_app()
check("leaving the app drops every raised note, the edited one included",
      set(dropped) == {A, B, C})
check("pinned and hidden notes are never dropped", D not in dropped and E not in dropped)

# ── the session is over: a later click drops nothing
dropped.clear()
press(C.text_edit.viewport())
check("after leaving, the session is over (a click drops nothing)", dropped == [])

# ── without a tray raise, clicking a note never drops anything
press(A.text_edit.viewport())
check("without a tray raise, clicking a note drops nothing", dropped == [])

# ── raise, then go straight to another app (no note clicked) → all dropped
app.raise_visible_notes()
leave_app()
check("raise then leave without clicking a note → all raised notes dropped",
      set(dropped) == {A, B, C})
dropped.clear()

# ── a TRANSIENT inactive blip must neither drop nor end the session
app.raise_visible_notes()
blip_inactive()
check("transient inactive blip drops nothing", dropped == [])
press(A.text_edit.viewport())
check("…and keeps the session (a click still drops the others)", set(dropped) == {B, C})
leave_app()
dropped.clear()

# ── the app-wide event filter only lives for a session
check("event filter removed once the session ends", app._tray_filter_on is False)

print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
