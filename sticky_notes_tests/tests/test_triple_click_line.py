import sys, os, tempfile, atexit, shutil
_SB = tempfile.mkdtemp(prefix="sn_tcl_")
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
d = te.document()
b0, b1 = d.findBlockByNumber(0), d.findBlockByNumber(1)

# select_block_text selects the line's TEXT only — no trailing separator, so the
# caret stays on the clicked line (not the next one).
te.select_block_text(b0)
sel = te.textCursor()
check("selection starts at the line start", sel.selectionStart() == b0.position())
check("selection ends at the end of the line's text (excludes the newline)",
      sel.selectionEnd() == b0.position() + len("line0"))
check("selection does NOT reach the next block", sel.selectionEnd() < b1.position())
check("the whole line text is selected", sel.selectedText() == "line0")

# Empty block: no crash, empty selection at the block start.
c2 = te.textCursor(); c2.movePosition(c2.MoveOperation.End); c2.insertText("\n")
empty = d.findBlockByNumber(d.blockCount() - 1)
te.select_block_text(empty)
check("empty line select is a no-op selection at its start",
      te.textCursor().position() == empty.position())

# Toggling code after a line-text select codes only that line (root-cause fix).
te.select_block_text(b0)
te.toggle_code_block()
check("code toggle after line-select codes only that line",
      te._is_code_block(d.findBlockByNumber(0)) and not te._is_code_block(d.findBlockByNumber(1)))

note.hide(); note.deleteLater()
print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
