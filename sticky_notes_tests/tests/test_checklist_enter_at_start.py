import sys, os, tempfile, atexit, shutil
_SB = tempfile.mkdtemp(prefix="sn_ckstart_")
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
from PyQt6.QtGui import QKeyEvent
from PyQt6.QtCore import Qt, QEvent

fails = []
def check(name, cond):
    print(f"  {'PASS' if cond else 'FAIL'}   {name}")
    if not cond: fails.append(name)

from sticky_notes.app import StickyNotesApp
from sticky_notes.note import StickyNote
from sticky_notes.widgets import CHECK_EMPTY, CHECK_DONE
app = StickyNotesApp(sys.argv[:1])
note = StickyNote(app, "n", {"id": "n", "geometry": [0, 0, 300, 200]})
te = note.text_edit

def lines():
    d = te.document()
    return [d.findBlockByNumber(i).text() for i in range(d.blockCount())]
def boxes(t):
    return t.count(CHECK_EMPTY) + t.count(CHECK_DONE)

# Checklist "☐ milk"; put the caret at the very start (before the box) and Enter.
c = te.textCursor(); c.insertText("milk"); te.toggle_checklist()
c = te.textCursor(); c.setPosition(te.textCursor().block().position()); te.setTextCursor(c)
te.keyPressEvent(QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Return, Qt.KeyboardModifier.NoModifier))

ls = lines()
check("no line ends up with two checkboxes", all(boxes(t) <= 1 for t in ls))
check("the 'milk' item keeps a single box below", any("milk" in t and boxes(t) == 1 for t in ls))
check("the line above is a PLAIN empty line (no box)", ls[0] == "")
check("the checklist row was pushed down one place", "milk" in ls[1] and boxes(ls[1]) == 1)

note.hide(); note.deleteLater()
print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
