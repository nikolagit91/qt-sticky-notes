"""Guard: the checklist parent-consistency invariant ("a parent is checked iff
all its descendants are checked") must hold after STRUCTURAL edits too — adding a
line (Enter), deleting a line, indenting/outdenting (Tab/Shift+Tab), and
reordering (Alt+arrow / drag) — not only after clicking a box (toggle_checkbox).

Before the fix the invariant was re-established only in toggle_checkbox, so
adding an item under a checked parent left the parent checked with an unchecked
child, deleting the last unchecked child left the parent unchecked though all
remaining children were done, etc. This is the "nested items + parent get
finicky" bug.
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
from sticky_notes.widgets import CHECK_EMPTY, CHECK_DONE

app = StickyNotesApp(sys.argv[:1])
for e in list(app.notes.values()):
    e.hide(); e.deleteLater()
app.notes.clear()
note = app.create_new_note()
te = note.text_edit
doc = te.document()

def build():
    """parent / child1 / child2 (indented) / separator / solo."""
    te.setPlainText("parent\nchild1\nchild2\nsep\nsolo")
    for bn in (0, 1, 2, 4):
        b = doc.findBlockByNumber(bn)
        c = te.textCursor(); c.setPosition(b.position()); te.setTextCursor(c)
        te.toggle_checklist()
    for bn in (1, 2):
        te._change_indent(doc.findBlockByNumber(bn), +1)

def g(bn):
    return te.document().findBlockByNumber(bn).text()[:1]

def invariant_broken():
    """Block numbers whose parent-state disagrees with 'all descendants done'."""
    bad = []
    for bn in range(te.document().blockCount()):
        kids = te._descendants(bn)
        if te._check_indent(bn) is not None and kids:
            if (g(bn) == CHECK_DONE) != all(g(k) == CHECK_DONE for k in kids):
                bad.append(bn)
    return bad

# ── 1) Enter under a checked parent → parent reverts to unchecked ─────────────
build()
te.toggle_checkbox(doc.findBlockByNumber(0).position())     # check parent (cascade)
b2 = doc.findBlockByNumber(2)
c = te.textCursor(); c.setPosition(b2.position())
c.movePosition(QTextCursor.MoveOperation.EndOfBlock); te.setTextCursor(c)
te._handle_checklist_enter()
te.textCursor().insertText("new child")
check("Enter-add: invariant holds", invariant_broken() == [])
check("Enter-add: parent reverts to unchecked", g(0) == CHECK_EMPTY)
check("Enter-add: the new item is unchecked", g(3) == CHECK_EMPTY)

# ── 2) Delete the last unchecked child → parent becomes checked ───────────────
build()
te.toggle_checkbox(doc.findBlockByNumber(1).position())     # check child1 only
te._delete_whole_line(doc.findBlockByNumber(2))            # remove unchecked child2
check("delete: invariant holds", invariant_broken() == [])
check("delete: parent now checked (only child left is done)", g(0) == CHECK_DONE)

# ── 3) Tab-indent an unchecked line under a checked parent → parent unchecks ──
build()
te.toggle_checkbox(doc.findBlockByNumber(0).position())     # parent + kids all done
# turn the solo item into a child of the parent: move it up against the subtree,
# then indent it. Simpler: append a new checklist sibling right after child2.
b2 = doc.findBlockByNumber(2)
c = te.textCursor(); c.setPosition(b2.position())
c.movePosition(QTextCursor.MoveOperation.EndOfBlock); te.setTextCursor(c)
te._handle_checklist_enter()                                # new item at child indent
te.textCursor().insertText("extra")
# it is already a child (same indent); outdent then re-indent to exercise _change_indent
te._change_indent(te.textCursor().block(), -1)             # becomes sibling of parent
check("outdent: invariant holds", invariant_broken() == [])
te._change_indent(te.textCursor().block(), +1)             # back under the parent
check("indent: invariant holds", invariant_broken() == [])
check("indent: parent unchecked (a child is undone)", g(0) == CHECK_EMPTY)

# ── 4) Reorder must not leave a broken invariant ─────────────────────────────
build()
te.toggle_checkbox(doc.findBlockByNumber(1).position())     # check child1 only (parent EMPTY)
te.move_block(1, 2, keep_cursor=True)                      # swap child1/child2 order
check("reorder: invariant holds", invariant_broken() == [])

print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
