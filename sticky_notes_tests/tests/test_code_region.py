import sys, os, tempfile, atexit, shutil
_SB = tempfile.mkdtemp(prefix="sn_coderegion_")
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
from PyQt6.QtGui import QTextListFormat, QKeyEvent
from PyQt6.QtCore import Qt, QEvent

fails = []
def check(name, cond):
    print(f"  {'PASS' if cond else 'FAIL'}   {name}")
    if not cond: fails.append(name)

from PyQt6.QtGui import QTextCursor
from sticky_notes.app import StickyNotesApp
from sticky_notes.note import StickyNote
app = StickyNotesApp(sys.argv[:1])
note = StickyNote(app, "n", {"id": "n", "geometry": [0, 0, 300, 200]})
te = note.text_edit
c = te.textCursor(); c.insertText("plain\nc1\nc2\nc3\ntail")
d = te.document()
# make blocks 1..3 code
sel = te.textCursor()
sel.setPosition(d.findBlockByNumber(1).position())
sel.setPosition(d.findBlockByNumber(3).position() + 2, QTextCursor.MoveMode.KeepAnchor)
te.setTextCursor(sel); te.toggle_code_block()

first, last = te.code_region_at(d.findBlockByNumber(2))
check("region spans the whole contiguous code run", (first, last) == (1, 3))
check("region text joins the code lines", te.code_region_text(first, last) == "c1\nc2\nc3")
# a single isolated code block is its own region
te2 = StickyNote(app, "m", {"id": "m", "geometry": [0,0,300,200]}).text_edit
te2.textCursor().insertText("only")
te2.toggle_code_block()
f2, l2 = te2.code_region_at(te2.document().begin())
check("single code line is its own region", (f2, l2) == (0, 0))

# A code block on the FIRST row must not overhang the viewport top — Qt ignores
# a first block's top margin, so the PAD_Y overhang would clip the rounded top
# into square corners. The painted box top must stay >= 0.
n3 = StickyNote(app, "top", {"id": "top", "geometry": [0, 0, 320, 220]})
te3 = n3.text_edit
te3.textCursor().insertText("num1 = input('x')\nnum2 = input('y')")
selall = te3.textCursor(); selall.movePosition(QTextCursor.MoveOperation.Start)
selall.movePosition(QTextCursor.MoveOperation.End, QTextCursor.MoveMode.KeepAnchor)
te3.setTextCursor(selall); te3.toggle_code_block()
n3.resize(320, 220); n3.show(); app.processEvents()
fa, la = te3.code_region_at(te3.document().begin())
check("first-row code box top not clipped above viewport (rounded top corners)",
      te3._code_region_rect(fa, la).top() >= 0)
n3.hide(); n3.deleteLater()
print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
