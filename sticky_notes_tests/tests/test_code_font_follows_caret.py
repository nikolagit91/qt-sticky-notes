import sys, os, tempfile, atexit, shutil
_SB = tempfile.mkdtemp(prefix="sn_cffc_")
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
from PyQt6.QtGui import QTextCursor
from PyQt6.QtTest import QTest

fails = []
def check(name, cond):
    print(f"  {'PASS' if cond else 'FAIL'}   {name}")
    if not cond: fails.append(name)

from sticky_notes.app import StickyNotesApp
from sticky_notes.note import StickyNote
from sticky_notes.widgets import CODE_FONT_FAMILY
app = StickyNotesApp(sys.argv[:1])

def typing_fam(te): return te.currentCharFormat().fontFamilies() or []
def char_fam(te, pos):
    c = QTextCursor(te.document()); c.setPosition(pos)
    c.setPosition(pos + 1, QTextCursor.MoveMode.KeepAnchor)
    return c.charFormat().fontFamilies() or []
def is_mono(fams): return CODE_FONT_FAMILY in fams

# NOTE: the actual "bleed" (wrong font carried across a boundary) does NOT
# reproduce on the offscreen platform — Qt derives the caret format correctly
# there. These tests therefore GUARD the invariant and, above all, prove the fix
# doesn't break selections or inline code. Real verification is done live.

# ── Invariant: typing font matches the caret's block as it moves in/out of code.
note = StickyNote(app, "a", {"id": "a", "geometry": [0, 0, 300, 200]})
te = note.text_edit
c = te.textCursor(); c.insertText("abc\nx=1")
# make line 1 a code block
c = te.textCursor(); c.movePosition(c.MoveOperation.End)
c.movePosition(c.MoveOperation.StartOfBlock, c.MoveMode.KeepAnchor); te.setTextCursor(c)
te.toggle_code_block()
c = te.textCursor(); c.movePosition(c.MoveOperation.Start); te.setTextCursor(c)
check("on plain line the typing font is the note font", not is_mono(typing_fam(te)))
QTest.keyClick(te, Qt.Key.Key_Down)
check("moving down into a code block makes typing monospace", is_mono(typing_fam(te)))
QTest.keyClick(te, Qt.Key.Key_Up)
check("moving back up to a plain line restores the note font",
      not is_mono(typing_fam(te)))

# ── Inline code preserved: caret inside an inline-code span (on an otherwise
#    plain line) must keep typing monospace, not get forced to the note font.
note2 = StickyNote(app, "b", {"id": "b", "geometry": [0, 0, 300, 200]})
te2 = note2.text_edit
c = te2.textCursor(); c.insertText("ab")
c = te2.textCursor(); c.setPosition(0); c.setPosition(1, c.MoveMode.KeepAnchor)
te2.setTextCursor(c); te2.toggle_inline_code()          # char 0 → inline code
c = te2.textCursor(); c.setPosition(1); te2.setTextCursor(c)   # caret after inline char
check("caret in an inline-code span keeps typing monospace",
      is_mono(typing_fam(te2)))
c = te2.textCursor(); c.movePosition(c.MoveOperation.End); te2.setTextCursor(c)
check("caret after plain text uses the note font", not is_mono(typing_fam(te2)))

# ── Selection safety: a live selection spanning plain + code must NOT be
#    reformatted when the caret moves (the handler must bail on a selection).
note3 = StickyNote(app, "c", {"id": "c", "geometry": [0, 0, 300, 200]})
te3 = note3.text_edit
c = te3.textCursor(); c.insertText("ab\ncd")
c = te3.textCursor(); c.movePosition(c.MoveOperation.End)
c.movePosition(c.MoveOperation.StartOfBlock, c.MoveMode.KeepAnchor); te3.setTextCursor(c)
te3.toggle_code_block()                                 # line 1 "cd" → code
plain_before = char_fam(te3, 0)                         # 'a' on the plain line
# select from start of the plain line through the end of the code line
c = te3.textCursor(); c.setPosition(0)
c.setPosition(te3.document().characterCount() - 1, c.MoveMode.KeepAnchor)
te3.setTextCursor(c)                                    # fires cursorPositionChanged
check("selection spanning plain+code: plain part keeps its font (not reformatted)",
      char_fam(te3, 0) == plain_before and not is_mono(char_fam(te3, 0)))
check("selection spanning plain+code: code part stays monospace",
      is_mono(char_fam(te3, 3)))                        # 'c' on the code line

for n in (note, note2, note3):
    n.hide(); n.deleteLater()
print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
