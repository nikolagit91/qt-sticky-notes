import sys, os, tempfile, atexit, shutil
_SB = tempfile.mkdtemp(prefix="sn_copybtn_")
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
from PyQt6.QtGui import QTextListFormat, QKeyEvent
from PyQt6.QtCore import Qt, QEvent

fails = []
def check(name, cond):
    print(f"  {'PASS' if cond else 'FAIL'}   {name}")
    if not cond: fails.append(name)

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QTextCursor
from sticky_notes.app import StickyNotesApp
from sticky_notes.note import StickyNote
app = StickyNotesApp(sys.argv[:1])
note = StickyNote(app, "n", {"id": "n", "geometry": [0, 0, 300, 200]})
te = note.text_edit
c = te.textCursor(); c.insertText("a\nb\nc")
sel = te.textCursor(); sel.select(QTextCursor.SelectionType.Document); te.setTextCursor(sel)
te.toggle_code_block()   # all three lines code

# arm the copy region as the hover logic would, then copy
te._copy_region = te.code_region_at(te.document().begin())
te._copy_current_region()
check("clipboard holds the whole code region", QApplication.clipboard().text() == "a\nb\nc")
check("copy button exists after a copy", te._copy_btn is not None)
check("copy button flashes a check mark right after copying",
      te._copy_btn.text() == "✓")
print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
