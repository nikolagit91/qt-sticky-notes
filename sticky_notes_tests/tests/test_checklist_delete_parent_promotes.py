"""Guard: deleting a checklist PARENT row (the whole-row delete gesture —
Backspace/Delete on the item, via _delete_whole_line) promotes its descendants
one indent level, so they take the parent's place instead of being left visually
indented under nothing. Deeper nesting is preserved (shift the whole subtree left
by one), whether the deleted parent is top-level or mid-level.
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

from PyQt6.QtWidgets import QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from PyQt6.QtGui import QTextCursor
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
def text(bn):
    return doc.findBlockByNumber(bn).text()[2:]   # strip "☐ "/"☑ "

# ── top-level parent: parent(0) / child1(1) / child2(1) / grand(2) / after(0) ─
te.setPlainText("parent\nchild1\nchild2\ngrand\nafter")
for bn in range(5):
    b = doc.findBlockByNumber(bn); c = te.textCursor(); c.setPosition(b.position()); te.setTextCursor(c)
    te.toggle_checklist()
for bn, lvl in ((1, 1), (2, 1), (3, 2)):
    te._change_indent(doc.findBlockByNumber(bn), +1)   # child1,child2 → 1
te._change_indent(doc.findBlockByNumber(3), +1)         # grand → 2 (total)

te._delete_whole_line(doc.findBlockByNumber(0))         # delete the parent
# expected: child1(0) child2(0) grand(1) after(0)
check("top parent gone; first line is child1", text(0) == "child1")
check("child1 promoted to indent 0", indent(0) == 0)
check("child2 promoted to indent 0", indent(1) == 0)
check("grand kept relative nesting (indent 1)", indent(2) == 1)
check("grand's parent is child2", te._parent_of(2) == 1)
check("after untouched (indent 0)", text(3) == "after" and indent(3) == 0)

# ── mid-level parent: A(0) / B(1) / C(2) / D(2) — delete B (indent 1) ─────────
te.setPlainText("A\nB\nC\nD")
for bn in range(4):
    b = doc.findBlockByNumber(bn); c = te.textCursor(); c.setPosition(b.position()); te.setTextCursor(c)
    te.toggle_checklist()
te._change_indent(doc.findBlockByNumber(1), +1)   # B → 1
te._change_indent(doc.findBlockByNumber(2), +1)   # C → 1
te._change_indent(doc.findBlockByNumber(2), +1)   # C → 2
te._change_indent(doc.findBlockByNumber(3), +1)   # D → 1
te._change_indent(doc.findBlockByNumber(3), +1)   # D → 2

te._delete_whole_line(doc.findBlockByNumber(1))   # delete mid-level parent B
# expected: A(0) / C(1) / D(1)  — C,D promoted from 2 to 1, under A
check("mid parent B gone; C follows A", text(1) == "C")
check("C promoted from 2 to 1", indent(1) == 1)
check("D promoted from 2 to 1", indent(2) == 1)
check("C's parent is A", te._parent_of(1) == 0)

print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
