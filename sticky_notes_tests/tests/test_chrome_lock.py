"""Double-clicking a note's header locks its chrome open (clean mode only).

Clean mode auto-hides the header/toolbar and reveals them when the pointer
dwells on the top edge. While editing heavily that means travelling to the top
edge over and over, so a double-click on the revealed header pins the chrome
open FOR THAT NOTE; double-clicking again hands it back to auto-hide.

Deliberately NOT persisted: it is a temporary editing convenience, so a restart
returns the note to clean mode and notes.json is unchanged.
"""
import sys, os, tempfile, atexit, shutil
_SB = tempfile.mkdtemp(prefix="sn_chromelock_")
atexit.register(lambda: shutil.rmtree(_SB, ignore_errors=True))
os.environ["HOME"] = _SB
os.environ["XDG_CONFIG_HOME"] = os.path.join(_SB, ".config")
os.environ["XDG_DATA_HOME"]   = os.path.join(_SB, ".local", "share")
os.environ.setdefault("XDG_RUNTIME_DIR", _SB)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ.pop("DISPLAY", None); os.environ.pop("WAYLAND_DISPLAY", None)
os.makedirs(os.path.join(_SB, ".local", "share", "sticky_notes"), exist_ok=True)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

fails = []
def check(name, cond):
    print(f"  {'PASS' if cond else 'FAIL'}   {name}")
    if not cond: fails.append(name)

from PyQt6.QtCore import Qt, QEvent, QPointF
from PyQt6.QtGui import QMouseEvent

from sticky_notes.app import StickyNotesApp
app = StickyNotesApp(sys.argv[:1])
app._snap_to_grid = app._snap_to_notes = app._snap_size = False
for e in list(app.notes.values()):
    e.hide(); e.deleteLater()
app.notes.clear()

from PyQt6.QtWidgets import QApplication

def dbl(widget):
    """Send the FULL event sequence Qt delivers for a double-click — press,
    release, dbl-click, release — not just the dbl-click. The press handler
    early-returns on a locked note, so only the full sequence reproduces how the
    gesture behaves there."""
    def ev(t):
        return QMouseEvent(t, QPointF(20.0, 10.0), Qt.MouseButton.LeftButton,
                           Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    for t in (QEvent.Type.MouseButtonPress, QEvent.Type.MouseButtonRelease,
              QEvent.Type.MouseButtonDblClick, QEvent.Type.MouseButtonRelease):
        QApplication.sendEvent(widget, ev(t))

# ── clean mode ON: the double-click pins the chrome open ─────────────────────
app._clean_mode = True
note = app.create_new_note(content="editing a lot")
note._set_clean_mode(True)
check("clean mode starts with the chrome hidden", note._chrome_revealed is False)
check("clean mode is armed on the note", note._clean_mode is True)

# The header must actually handle the gesture — QFrame's default is a no-op, and
# a no-op would let several checks below pass for the wrong reason. (Comparing
# bound methods is useless here: PyQt hands back a fresh wrapper each access, so
# `is not QFrame.mouseDoubleClickEvent` is always True. Check the override.)
from sticky_notes.widgets import NoteHeader
check("the header overrides mouseDoubleClickEvent",
      "mouseDoubleClickEvent" in NoteHeader.__dict__)

note._reveal_chrome()          # the user hovers the top edge first — header shows
dbl(note.header)
check("double-click disarms auto-hide (locks it open)", note._clean_mode is False)
check("chrome is open after the lock", note._chrome_revealed is True)

# Locked means the hover filter is gone, so dropping into the body can't hide it.
note._maybe_hide()
check("locked chrome survives a hide check", note._chrome_revealed is True)

# ── double-click again → back to auto-hide ───────────────────────────────────
# Establish the locked state explicitly so this group tests only the gesture.
note._set_clean_mode(False)
assert note._clean_mode is False and note._chrome_revealed is True
dbl(note.header)
check("second double-click re-arms auto-hide", note._clean_mode is True)
check("second double-click hides the chrome again", note._chrome_revealed is False)

# ── the lock is per note ─────────────────────────────────────────────────────
other = app.create_new_note(content="untouched")
other._set_clean_mode(True)
note._set_clean_mode(True); note._reveal_chrome()
dbl(note.header)
check("locking one note actually locked it", note._clean_mode is False)
check("locking one note leaves the other in clean mode", other._clean_mode is True)
check("the other note's chrome stays hidden", other._chrome_revealed is False)

# ── not persisted ────────────────────────────────────────────────────────────
data = note.get_data()
check("the lock is not serialised", not any("lock" in k and "chrome" in k for k in data))

# ── clean mode OFF: the gesture is a no-op (nothing to disable) ──────────────
app._clean_mode = False
plain = app.create_new_note(content="no clean mode")
plain._set_clean_mode(False)
before = plain._chrome_revealed
dbl(plain.header)
check("no-op when clean mode is off (chrome unchanged)",
      plain._chrome_revealed == before is True)
check("no-op when clean mode is off (stays disarmed)", plain._clean_mode is False)

# ── a locked note is handed back by the global setting ───────────────────────
app._clean_mode = True
note._set_clean_mode(False)          # pretend it is locked open
app._apply_clean_mode()              # user toggles the setting in Settings
check("the global setting reclaims a locked note", note._clean_mode is True)

# ── the gesture is discoverable ──────────────────────────────────────────────
# A mouse gesture with no trace in the UI is one nobody finds, and the
# cheat-sheet only covers keys — so the auto-hide setting has to mention it.
from PyQt6.QtWidgets import QLabel
app.show_settings()
dlg = next(w for w in app.topLevelWidgets()
           if isinstance(w, type(app._open_windows[-1])) and w.windowTitle() == "Settings")
hints = " ".join(l.text() for l in dlg.findChildren(QLabel))
check("Settings explains the double-click lock under auto-hide",
      "double-click" in hints.lower())
check("...and says it keeps the controls open",
      "double-click" in hints.lower() and "open" in hints.lower())
dlg.close()

# ── the gesture keeps working after the note is LOCKED (read-only) ────────────
# Regression: the double-click was blocked on a locked note, so once you pinned
# the chrome open and then locked the note you could no longer toggle it — and
# couldn't easily reach the unlock button. Read-only content is orthogonal to
# whether the header is pinned.
app._clean_mode = True
ln = app.create_new_note(content="lock me")
ln._set_clean_mode(True)
ln._reveal_chrome()
dbl(ln.header)
check("locked-note setup: chrome pinned open before locking", ln._clean_mode is False)
ln.toggle_lock(True)
check("note is read-only locked", ln.locked is True)

before = (ln._clean_mode, ln._chrome_revealed)
dbl(ln.header)
check("double-click still responds on a locked note",
      (ln._clean_mode, ln._chrome_revealed) != before)
check("double-click on a locked note re-arms auto-hide", ln._clean_mode is True)

# Pinning a locked note open shows only the HEADER — a read-only note has
# nothing to format, so the toolbar must stay collapsed.
ln._reveal_chrome()
dbl(ln.header)
check("locked note pins the header open again", ln._chrome_revealed is True)
check("a locked note never shows its toolbar", ln._toolbar_visible is False)

print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
