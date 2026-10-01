import sys, os, tempfile, atexit, shutil
_SB = tempfile.mkdtemp(prefix="sn_eru_")
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
from sticky_notes.widgets import CODE_FONT_FAMILY
app = StickyNotesApp(sys.argv[:1])

def select_all_delete(te):
    c = te.textCursor(); c.select(QTextCursor.SelectionType.Document)
    te.setTextCursor(c)
    te.textCursor().removeSelectedText()

# ── #3: Ctrl+A + Delete from a CODE BLOCK must leave a clean PLAIN note, not a
#        lingering monospace code block. (The "toggle {} on an empty line then
#        type" flow, covered by test_code_block_empty, must still keep the code
#        block — that's the intentional exception.)
note = StickyNote(app, "a", {"id": "a", "geometry": [0, 0, 300, 200]})
te = note.text_edit
c = te.textCursor(); c.insertText("hello")
te.toggle_code_block()                       # hello -> code block (monospace)
check("setup: line is a code block", te._is_code_block(te.document().begin()) is True)
select_all_delete(te)
check("#3 delete-all from code leaves a PLAIN block (no lingering code bg)",
      te._is_code_block(te.document().begin()) is False)
fams = te.currentCharFormat().fontFamilies() or []
check("#3 typing format is not monospace after delete-all",
      CODE_FONT_FAMILY not in fams)

# ── #4: undo after Ctrl+A + Delete must bring the text back (the empty-doc
#        format reset must not shadow the delete on the undo stack).
te.undo()
check("#4 undo restores the deleted code text", te.document().toPlainText() == "hello")

# ── #4 (plain text variant): same for a non-code note.
note2 = StickyNote(app, "b", {"id": "b", "geometry": [0, 0, 300, 200]})
te2 = note2.text_edit
c = te2.textCursor(); c.insertText("world")
select_all_delete(te2)
check("plain note stays plain after delete-all",
      te2._is_code_block(te2.document().begin()) is False)
te2.undo()
check("#4 undo restores deleted plain text", te2.document().toPlainText() == "world")

# ── The "{ } on an empty line, then type" flow is preserved (the one-shot flag
#    is consumed at once), yet deleting that code afterwards still cleans up.
note3 = StickyNote(app, "c", {"id": "c", "geometry": [0, 0, 300, 200]})
te3 = note3.text_edit
te3.toggle_code_block()                       # { } on empty doc → keep as code
check("toggle { } on empty keeps a code block",
      te3._is_code_block(te3.document().begin()) is True)
check("empty-code flag is consumed immediately", te3._pending_empty_code is False)
c = te3.textCursor(); c.insertText("x = 1")
select_all_delete(te3)
check("deleting the typed code then cleans to a plain block",
      te3._is_code_block(te3.document().begin()) is False)

note.hide(); note.deleteLater(); note2.hide(); note2.deleteLater()
note3.hide(); note3.deleteLater()
print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
