"""Hovering a link shows the hand cursor immediately.

We set the viewport cursor ourselves, but QTextEdit's own mouse-move handler
also manages it — an editable QTextEdit doesn't carry LinksAccessibleByMouse, so
super() put the I-beam back over links. Setting our cursor BEFORE super() meant
Qt overwrote it and the hand only appeared once its logic caught up (the visible
delay). Ours must be applied last."""
import sys, os, tempfile, atexit, shutil
_SB = tempfile.mkdtemp(prefix="sn_linkcur_")
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
from PyQt6.QtCore import Qt, QEvent, QMimeData, QPointF
from PyQt6.QtGui import QMouseEvent, QTextCursor
QMessageBox.information = staticmethod(lambda *a, **k: None)

fails = []
def check(name, cond):
    print(f"  {'PASS' if cond else 'FAIL'}   {name}")
    if not cond: fails.append(name)

from sticky_notes.app import StickyNotesApp

app = StickyNotesApp(sys.argv[:1])
for e in list(app.notes.values()):
    e.hide(); e.deleteLater()
app.notes.clear()
n = app.create_new_note(); te = n.text_edit
n.resize(420, 260); n.show(); app.processEvents()

md = QMimeData(); md.setText("http://example.com")
te.insertFromMimeData(md); app.processEvents()

def move_to(pt):
    te.mouseMoveEvent(QMouseEvent(QEvent.Type.MouseMove, QPointF(pt),
                                  Qt.MouseButton.NoButton, Qt.MouseButton.NoButton,
                                  Qt.KeyboardModifier.NoModifier))
    app.processEvents()

# a point in the middle of the link text
c = QTextCursor(te.document()); c.setPosition(3)
r = te.cursorRect(c)
link_pt = r.center()
check("the probe point really is over the link", te.anchorAt(link_pt) != "")

move_to(link_pt)
check("hovering a link leaves the HAND cursor set (not overwritten by super())",
      te.viewport().cursor().shape() == Qt.CursorShape.PointingHandCursor)

# a point well past the end of the text → plain I-beam
move_to(te.viewport().rect().bottomRight() - r.center() / 4)
check("off the link the cursor is the I-beam",
      te.viewport().cursor().shape() == Qt.CursorShape.IBeamCursor)

print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
