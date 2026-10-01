"""Guard: turning a line into a checklist item (toggle_checklist) re-establishes
the parent invariant. Adding a parent row above already-checked children must
auto-check the new parent (all its descendants are done); stripping a box must
likewise keep parents consistent.
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
from sticky_notes.app import StickyNotesApp
from sticky_notes.widgets import CHECK_EMPTY, CHECK_DONE

app = StickyNotesApp(sys.argv[:1])
for e in list(app.notes.values()):
    e.hide(); e.deleteLater()
app.notes.clear()
note = app.create_new_note()
te = note.text_edit
doc = te.document()
def g(bn):
    return doc.findBlockByNumber(bn).text()[:1]

# two checked, indented children; "newparent" above is still plain text
te.setPlainText("newparent\nchild1\nchild2")
for bn in (1, 2):
    b = doc.findBlockByNumber(bn); c = te.textCursor(); c.setPosition(b.position()); te.setTextCursor(c)
    te.toggle_checklist()
    te._change_indent(doc.findBlockByNumber(bn), +1)
    te.toggle_checkbox(doc.findBlockByNumber(bn).position())
check("setup: both children checked", g(1) == CHECK_DONE and g(2) == CHECK_DONE)

# turn the line above into a checklist item → it becomes the parent
c = te.textCursor(); c.setPosition(doc.findBlockByNumber(0).position()); te.setTextCursor(c)
te.toggle_checklist()
check("new parent above all-checked children auto-checks", g(0) == CHECK_DONE)
check("children stay checked", g(1) == CHECK_DONE and g(2) == CHECK_DONE)

print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
