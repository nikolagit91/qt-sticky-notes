import sys, os, tempfile, atexit, shutil
_SB = tempfile.mkdtemp(prefix="sn_cbml_")
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

# Three lines; select all three, then toggle → every line becomes a code block.
c = te.textCursor(); c.insertText("a = 1\nb = 2\nc = 3")
c.movePosition(c.MoveOperation.Start)
c.movePosition(c.MoveOperation.End, c.MoveMode.KeepAnchor)
te.setTextCursor(c)
te.toggle_code_block()

def all_blocks():
    d = te.document()
    return [d.findBlockByNumber(i) for i in range(d.blockCount())]

check("all selected lines became code blocks",
      all(te._is_code_block(b) for b in all_blocks()))

# Toggle again over the same selection → all revert to plain.
c = te.textCursor(); c.movePosition(c.MoveOperation.Start)
c.movePosition(c.MoveOperation.End, c.MoveMode.KeepAnchor)
te.setTextCursor(c)
te.toggle_code_block()
check("toggling the selection again reverts every line",
      not any(te._is_code_block(b) for b in all_blocks()))

note.hide(); note.deleteLater()
print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
