import sys, os, tempfile, atexit, shutil
_SB = tempfile.mkdtemp(prefix="sn_ics_")
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

def ctrl_m(te): QTest.keyClick(te, Qt.Key.Key_M, Qt.KeyboardModifier.ControlModifier)
def char_fmt(te, pos):
    c = QTextCursor(te.document()); c.setPosition(pos)
    c.setPosition(pos + 1, QTextCursor.MoveMode.KeepAnchor)
    return c.charFormat()

# ── Ctrl+M toggles inline code on the selection (feature enabled).
app._code_blocks = True
note = StickyNote(app, "a", {"id": "a", "geometry": [0, 0, 300, 200]})
te = note.text_edit
c = te.textCursor(); c.insertText("word")
c = te.textCursor(); c.select(QTextCursor.SelectionType.Document); te.setTextCursor(c)
ctrl_m(te)
f = char_fmt(te, 0)
check("Ctrl+M makes the selection inline code (monospace + bg)",
      CODE_FONT_FAMILY in (f.fontFamilies() or [])
      and f.background().style() != Qt.BrushStyle.NoBrush)
# toggling again removes it
c = te.textCursor(); c.select(QTextCursor.SelectionType.Document); te.setTextCursor(c)
ctrl_m(te)
f = char_fmt(te, 0)
check("Ctrl+M again removes inline code",
      f.background().style() == Qt.BrushStyle.NoBrush)

# ── Ctrl+M is a no-op when the code-blocks feature is disabled.
app._code_blocks = False
note2 = StickyNote(app, "b", {"id": "b", "geometry": [0, 0, 300, 200]})
te2 = note2.text_edit
c = te2.textCursor(); c.insertText("word")
c = te2.textCursor(); c.select(QTextCursor.SelectionType.Document); te2.setTextCursor(c)
ctrl_m(te2)
f2 = char_fmt(te2, 0)
check("Ctrl+M does nothing when the feature is off",
      f2.background().style() == Qt.BrushStyle.NoBrush
      and CODE_FONT_FAMILY not in (f2.fontFamilies() or []))

note.hide(); note.deleteLater(); note2.hide(); note2.deleteLater()
print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
