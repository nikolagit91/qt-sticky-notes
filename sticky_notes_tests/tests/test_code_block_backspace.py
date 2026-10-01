import sys, os, tempfile, atexit, shutil
_SB = tempfile.mkdtemp(prefix="sn_cbbs_")
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
from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest

fails = []
def check(name, cond):
    print(f"  {'PASS' if cond else 'FAIL'}   {name}")
    if not cond: fails.append(name)

from sticky_notes.app import StickyNotesApp
from sticky_notes.note import StickyNote
app = StickyNotesApp(sys.argv[:1])

def bs(te):  QTest.keyClick(te, Qt.Key.Key_Backspace)
def is_code(te, n=0): return te._is_code_block(te.document().findBlockByNumber(n))

# ── The reported case: { } on an EMPTY first line, then Backspace (no typing).
#    Backspace would otherwise be a no-op; it must drop the code formatting.
note = StickyNote(app, "a", {"id": "a", "geometry": [0, 0, 300, 200]})
te = note.text_edit
te.toggle_code_block()
check("setup: empty first line is a code block", is_code(te, 0) is True)
bs(te)
check("Backspace on empty first-line code block reverts it to plain",
      is_code(te, 0) is False)
check("still a single block (nothing merged away)", te.document().blockCount() == 1)

# ── Regression: an empty code line BELOW another code line must still merge up
#    and stay code (Backspace removes the blank row, doesn't split the block).
note2 = StickyNote(app, "b", {"id": "b", "geometry": [0, 0, 300, 200]})
te2 = note2.text_edit
c = te2.textCursor(); c.insertText("code")
te2.toggle_code_block()                       # line 0 → code
c = te2.textCursor(); c.movePosition(c.MoveOperation.End); te2.setTextCursor(c)
QTest.keyClick(te2, Qt.Key.Key_Return)        # Enter continues the code block
check("setup: second line is an empty code line", is_code(te2, 1) is True)
bs(te2)                                        # at start of line 1 → merge up
check("Backspace on empty code line below code merges up (blocks=1)",
      te2.document().blockCount() == 1)
check("merged line stays a code block", is_code(te2, 0) is True)
check("merged text preserved", te2.document().toPlainText() == "code")

# ── The reported case: empty code line with EMPTY lines above must un-code IN
#    PLACE on the first Backspace (overlay gone at once) instead of "lifting" the
#    code block up row by row until the first line.
note4 = StickyNote(app, "d", {"id": "d", "geometry": [0, 0, 300, 200]})
te4 = note4.text_edit
c = te4.textCursor(); c.insertText("\n\n")     # 3 empty blocks: 0, 1, 2
c = te4.textCursor(); c.movePosition(c.MoveOperation.End); te4.setTextCursor(c)
te4.toggle_code_block()                        # code on block 2
check("setup: empty line 2 is a code block", is_code(te4, 2) is True)
bs(te4)
check("Backspace un-codes the empty line in place (block count unchanged)",
      te4.document().blockCount() == 3)
check("the empty code line is now plain (overlay gone)", is_code(te4, 2) is False)
check("the line above did NOT become code (no lifting)", is_code(te4, 1) is False)

# ── Regression: an empty code line with TEXT above still merges into that text
#    on Backspace (normal line-join; overlay gone because it adopts the plain
#    line's format).
note5 = StickyNote(app, "e", {"id": "e", "geometry": [0, 0, 300, 200]})
te5 = note5.text_edit
c = te5.textCursor(); c.insertText("a\nb\n")
c = te5.textCursor(); c.movePosition(c.MoveOperation.End); te5.setTextCursor(c)
te5.toggle_code_block()                        # code on empty line 2
bs(te5)
check("Backspace on empty code below text merges up (blocks=2)",
      te5.document().blockCount() == 2)
check("merged result is plain text", te5.document().toPlainText() == "a\nb")

# ── Regression: Backspace inside a non-empty code block still just deletes a
#    character (doesn't strip the code formatting).
note3 = StickyNote(app, "c", {"id": "c", "geometry": [0, 0, 300, 200]})
te3 = note3.text_edit
c = te3.textCursor(); c.insertText("hi")
te3.toggle_code_block()
bs(te3)                                        # caret at end → delete 'i'
check("Backspace in non-empty code deletes a char, stays code",
      is_code(te3, 0) is True and te3.document().toPlainText() == "h")

for n in (note, note2, note3, note4, note5):
    n.hide(); n.deleteLater()
print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
