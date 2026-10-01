import sys, os, tempfile, atexit, shutil
_SB = tempfile.mkdtemp(prefix="sn_cbtc_")
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
from PyQt6.QtGui import QTextCursor

fails = []
def check(name, cond):
    print(f"  {'PASS' if cond else 'FAIL'}   {name}")
    if not cond: fails.append(name)

from sticky_notes.app import StickyNotesApp
from sticky_notes.note import StickyNote
app = StickyNotesApp(sys.argv[:1])
note = StickyNote(app, "n", {"id": "n", "geometry": [0, 0, 300, 200]})
te = note.text_edit
c = te.textCursor(); c.insertText("line0\nline1\nline2")

# Triple-click selects a line INCLUDING its trailing newline, so the selection
# ends at the start of the next block. Toggling must code only the clicked line.
d = te.document()
b0, b1 = d.findBlockByNumber(0), d.findBlockByNumber(1)
sel = QTextCursor(d)
sel.setPosition(b0.position())
sel.setPosition(b1.position(), QTextCursor.MoveMode.KeepAnchor)
te.setTextCursor(sel)
te.toggle_code_block()

check("triple-clicked line is a code block", te._is_code_block(d.findBlockByNumber(0)) is True)
check("the line BELOW is NOT pulled into the code block",
      te._is_code_block(d.findBlockByNumber(1)) is False)
check("unrelated line stays plain", te._is_code_block(d.findBlockByNumber(2)) is False)

# A genuine multi-line selection still codes every line it truly spans.
c2 = te.textCursor()
c2.setPosition(d.findBlockByNumber(1).position())
c2.setPosition(d.findBlockByNumber(2).position() + 2, QTextCursor.MoveMode.KeepAnchor)
te.setTextCursor(c2)
te.toggle_code_block()
check("real multi-line selection codes both spanned lines",
      te._is_code_block(d.findBlockByNumber(1)) and te._is_code_block(d.findBlockByNumber(2)))

note.hide(); note.deleteLater()
print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
