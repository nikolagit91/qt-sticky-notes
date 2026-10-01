"""Regression: resizing a selected line must not bleed into the next block.

Mouse-selecting a whole visual line lands the caret at the START of the row
below, so the selection end sits in the next block. The size code used `end` as
the block-scaling bound and read the toolbar label from currentCharFormat() at
that end position — so the ▲ button climbed the label +2 while the text grew +1
(label 21 while the text was 17), and the empty row below got resized too.

Fix: iterate real characters per block (skip separators), bound by the last
selected character (end-1), and read the label from the FIRST selected char.
"""
import sys, os, tempfile, atexit, shutil

_SB = tempfile.mkdtemp(prefix="sn_flb_")
atexit.register(lambda: shutil.rmtree(_SB, ignore_errors=True))
os.environ["HOME"] = _SB
os.environ["XDG_CONFIG_HOME"] = os.path.join(_SB, ".config")
os.environ["XDG_DATA_HOME"]   = os.path.join(_SB, ".local", "share")
os.environ.setdefault("XDG_RUNTIME_DIR", _SB)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ.pop("DISPLAY", None); os.environ.pop("WAYLAND_DISPLAY", None)
os.makedirs(os.path.join(_SB, ".local", "share", "sticky_notes"), exist_ok=True)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtGui import QTextCursor
QMessageBox.information = staticmethod(lambda *a, **k: None)

fails = []
def check(name, cond):
    print(f"  {'PASS' if cond else 'FAIL'}   {name}")
    if not cond: fails.append(name)

from sticky_notes.app import StickyNotesApp
from sticky_notes.note import StickyNote
app = StickyNotesApp(sys.argv[:1])
note = StickyNote(app, "n", {"id": "n", "geometry": [100, 100, 400, 300]})
app.notes["n"] = note
te = note.text_edit
doc = te.document()

def build():
    te.clear()
    c = te.textCursor()
    c.insertText("red 1"); c.insertBlock(); c.insertBlock(); c.insertText("red 2")

def sizes(lo, hi):
    out = []
    for p in range(lo, hi):
        c = QTextCursor(doc); c.setPosition(p); c.setPosition(p+1, QTextCursor.MoveMode.KeepAnchor)
        out.append(round(c.charFormat().fontPointSize(), 1))
    return out

# Layout: "red 1"=0..4, sep=5, empty row=6, "red 2"=7..11
# Selecting the whole first line lands the caret at pos 6 (start of empty row).
build()
sel = te.textCursor(); sel.setPosition(0); sel.setPosition(6, QTextCursor.MoveMode.KeepAnchor)
te.setTextCursor(sel)
for _ in range(4):
    note._change_font_size(+1)          # 13 -> 17 over four presses

check("selected line reached 17pt uniformly", sizes(0, 5) == [17.0]*5)
check("label matches the text (17), not a phantom", note.font_size_label.text() == "17")

# Click the empty row below — it was never selected, must stay default.
c = te.textCursor(); c.setPosition(6); te.setTextCursor(c)
note._update_toolbar_state()
check("empty row below still shows default 13", note.font_size_label.text() == "13")
check("empty row char size untouched (13)", sizes(6, 7) == [13.0])

# Absolute popup path (_apply_font_size) must respect the same boundary.
build()
cap = te.textCursor(); cap.setPosition(0); cap.setPosition(6, QTextCursor.MoveMode.KeepAnchor)
note._apply_font_size(30, cap)
check("absolute resize set the line to 30", sizes(0, 5) == [30.0]*5)
c = te.textCursor(); c.setPosition(6); te.setTextCursor(c)
note._update_toolbar_state()
check("absolute resize left empty row at 13", note.font_size_label.text() == "13")

note.hide(); note.deleteLater()
print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
