"""Guard: deleting an UNCHECKED parent row (a generic deletion, not the checked
whole-row gesture) still promotes its orphaned children back to the margin. This
is handled by a deferred pass triggered on net text removal (contentsChange),
covering deletion paths other than _delete_whole_line.
"""
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

fails = []
def check(name, cond):
    print(f"  {'PASS' if cond else 'FAIL'}   {name}")
    if not cond: fails.append(name)

from PyQt6.QtWidgets import QMessageBox, QApplication
QMessageBox.information = staticmethod(lambda *a, **k: None)
from PyQt6.QtGui import QTextCursor
from PyQt6.QtTest import QTest
from sticky_notes.app import StickyNotesApp

app = StickyNotesApp(sys.argv[:1])
for e in list(app.notes.values()):
    e.hide(); e.deleteLater()
app.notes.clear()
note = app.create_new_note()
te = note.text_edit
doc = te.document()

def indent(bn):
    return QTextCursor(doc.findBlockByNumber(bn)).blockFormat().indent()
def body(bn):
    return doc.findBlockByNumber(bn).text()[2:]

# unchecked tree: parent(0) / child1(1) / child2(1) / grand(2) / after(0)
te.setPlainText("parent\nchild1\nchild2\ngrand\nafter")
for bn in range(5):
    b = doc.findBlockByNumber(bn); c = te.textCursor(); c.setPosition(b.position()); te.setTextCursor(c)
    te.toggle_checklist()
te._change_indent(doc.findBlockByNumber(1), +1)   # child1 → 1
te._change_indent(doc.findBlockByNumber(2), +1)   # child2 → 1
te._change_indent(doc.findBlockByNumber(3), +1)   # grand → 1
te._change_indent(doc.findBlockByNumber(3), +1)   # grand → 2
check("setup: none checked, children indented", indent(1) == 1 and indent(3) == 2)

# delete the (unchecked) parent line generically: remove "☐ parent\n"
c = te.textCursor()
c.setPosition(doc.findBlockByNumber(0).position())
c.setPosition(doc.findBlockByNumber(1).position(), QTextCursor.MoveMode.KeepAnchor)
c.removeSelectedText()
# the deferred promote fires on the event loop (QTimer.singleShot) — pump it
QTest.qWait(50)

check("parent gone; first line is child1", body(0) == "child1")
check("child1 promoted to indent 0", indent(0) == 0)
check("child2 promoted to indent 0", indent(1) == 0)
check("grand kept relative nesting (indent 1)", indent(2) == 1)
check("grand's parent is child2", te._parent_of(2) == 1)
check("after untouched", body(3) == "after" and indent(3) == 0)

print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
