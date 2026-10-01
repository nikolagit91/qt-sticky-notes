"""Toolbar size/family must reflect the character AT the cursor, even in a note
that mixes font sizes. Regression: clicking a word of a different size than the
toolbar showed didn't update the size box (Qt's currentCharFormat quirk)."""
import sys, os, tempfile, atexit, shutil

_SB = tempfile.mkdtemp(prefix="sn_fs_")
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
from PyQt6.QtGui import QTextCharFormat, QTextCursor
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
te.clear()
cur = te.textCursor()
big = QTextCharFormat(); big.setFontPointSize(28); big.setFontFamilies(["Ubuntu"])
cur.insertText("BIG", big)                 # positions 0..3
small = QTextCharFormat(); small.setFontPointSize(9); small.setFontFamilies(["DejaVu Sans"])
cur.insertText("small", small)             # positions 3..8

def size_at(pos):
    c = te.textCursor(); c.setPosition(pos); te.setTextCursor(c)
    note._update_toolbar_state()
    return note.font_size_label.text()

def family_at(pos):
    c = te.textCursor(); c.setPosition(pos); te.setTextCursor(c)
    note._update_toolbar_state()
    return note.btn_font_family.text()

check("cursor inside BIG (pos 2) → size 28", size_at(2) == "28")
check("cursor inside small (pos 6) → size 9", size_at(6) == "9")
check("cursor right after BIG (pos 3) → size 28 (left char)", size_at(3) == "28")
check("cursor at end (pos 8) → size 9", size_at(8) == "9")
check("family reflects BIG (Ubuntu)", family_at(2).startswith("Ubuntu"))
check("family reflects small (DejaVu)", family_at(6).startswith("DejaVu"))

note.hide(); note.deleteLater()
print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
