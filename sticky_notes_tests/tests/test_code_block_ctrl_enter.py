import sys, os, tempfile, atexit, shutil
_SB = tempfile.mkdtemp(prefix="sn_cbce_")
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
from sticky_notes.widgets import CODE_FONT_FAMILY
app = StickyNotesApp(sys.argv[:1])

def is_code(te, n): return te._is_code_block(te.document().findBlockByNumber(n))
def typing_fam(te): return te.currentCharFormat().fontFamilies() or []

# Ctrl+Enter inside a code block exits it: a fresh PLAIN line after the current
# one, in the note font, leaving the code above intact.
note = StickyNote(app, "a", {"id": "a", "geometry": [0, 0, 300, 200]})
te = note.text_edit
c = te.textCursor(); c.insertText("x=1")
te.toggle_code_block()
check("setup: line 0 is a code block", is_code(te, 0) is True)
QTest.keyClick(te, Qt.Key.Key_Return, Qt.KeyboardModifier.ControlModifier)
check("Ctrl+Enter adds a new line below (2 blocks)", te.document().blockCount() == 2)
check("the code line above is untouched", is_code(te, 0) is True and
      te.document().findBlockByNumber(0).text() == "x=1")
check("the new line is NOT a code block", is_code(te, 1) is False)
check("caret is on the new line", te.textCursor().blockNumber() == 1)
check("typing on the new line uses the note font (not monospace)",
      CODE_FONT_FAMILY not in typing_fam(te))

# Plain Enter still continues the code block (regression).
note2 = StickyNote(app, "b", {"id": "b", "geometry": [0, 0, 300, 200]})
te2 = note2.text_edit
c = te2.textCursor(); c.insertText("y=2")
te2.toggle_code_block()
QTest.keyClick(te2, Qt.Key.Key_Return)          # plain Enter
check("plain Enter still continues the code block", is_code(te2, 1) is True)

# Ctrl+Enter from a MIDDLE line exits below the WHOLE block (no mid-block split).
from PyQt6.QtGui import QTextCursor
note3 = StickyNote(app, "c", {"id": "c", "geometry": [0, 0, 300, 220]})
te3 = note3.text_edit
c = te3.textCursor(); c.insertText("a=1"); te3.toggle_code_block()
QTest.keyClick(te3, Qt.Key.Key_Return); te3.textCursor().insertText("b=2")
QTest.keyClick(te3, Qt.Key.Key_Return); te3.textCursor().insertText("c=3")   # 3 code lines
mid = QTextCursor(te3.document().findBlockByNumber(1))
mid.movePosition(QTextCursor.MoveOperation.EndOfBlock); te3.setTextCursor(mid)
QTest.keyClick(te3, Qt.Key.Key_Return, Qt.KeyboardModifier.ControlModifier)
check("Ctrl+Enter mid-block does NOT split: first 3 lines stay code",
      is_code(te3, 0) and is_code(te3, 1) and is_code(te3, 2) and not is_code(te3, 3))
check("Ctrl+Enter mid-block: plain line added at the end (4 blocks)",
      te3.document().blockCount() == 4)

note.hide(); note.deleteLater(); note2.hide(); note2.deleteLater(); note3.hide(); note3.deleteLater()
print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
