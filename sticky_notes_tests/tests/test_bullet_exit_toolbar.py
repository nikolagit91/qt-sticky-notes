import sys, os, tempfile, atexit, shutil
_SB = tempfile.mkdtemp(prefix="sn_bullet_")
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

from sticky_notes.app import StickyNotesApp
from sticky_notes.note import StickyNote
app = StickyNotesApp(sys.argv[:1])
note = StickyNote(app, "n", {"id": "n", "geometry": [0, 0, 300, 200]})

# Build a bullet list, then land the caret on a trailing EMPTY bullet item.
# (createList on a still-empty document segfaults the offscreen platform, so
# start with a line of text.)
te = note.text_edit
cur = te.textCursor()
cur.insertText("hello")
cur.createList(QTextListFormat.Style.ListDisc)
cur.movePosition(cur.MoveOperation.End)
cur.insertBlock()               # new, empty item in the same list
te.setTextCursor(cur)
note._update_toolbar_state()
check("bullet button highlighted while in the list", note.btn_bullet.isChecked() is True)
check("caret is in an empty bullet item", te.textCursor().currentList() is not None
      and te.textCursor().block().text() == "")

# Enter on the empty bullet exits the list; the button must un-highlight at once
# even though the caret position is unchanged.
te.keyPressEvent(QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Return,
                           Qt.KeyboardModifier.NoModifier))
check("Enter exited the list", te.textCursor().currentList() is None)
check("bullet button un-highlights immediately on exit (bug)",
      note.btn_bullet.isChecked() is False)

note.hide(); note.deleteLater()
print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
