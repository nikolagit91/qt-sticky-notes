import sys, os, tempfile, atexit, shutil
_SB = tempfile.mkdtemp(prefix="sn_lind_")
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
from sticky_notes.widgets import LIST_INDENT_WIDTH, CHECK_LEFT_MARGIN
app = StickyNotesApp(sys.argv[:1])
note = StickyNote(app, "n", {"id": "n", "geometry": [0, 0, 300, 200]})
te = note.text_edit

check("bullet indent width reduced from Qt's 40", te.document().indentWidth() == LIST_INDENT_WIDTH)

# Bullet: offset is list level × indentWidth.
c = te.textCursor(); c.insertText("bullet")
c.createList(QTextListFormat.Style.ListDisc)
lst = te.textCursor().currentList()
check("bullet list offset uses the reduced width",
      lst.format().indent() * te.document().indentWidth() == LIST_INDENT_WIDTH)

# Checklist: base left margin so it isn't flush at the edge.
note2 = StickyNote(app, "m", {"id": "m", "geometry": [0, 0, 300, 200]})
te2 = note2.text_edit
cur = te2.textCursor(); cur.insertText("milk")
te2.toggle_checklist()
check("checklist line gets the base inset", te2.textCursor().blockFormat().leftMargin() == CHECK_LEFT_MARGIN)

# New checklist item (Enter) inherits the inset.
te2.keyPressEvent(QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Return, Qt.KeyboardModifier.NoModifier))
check("new checklist item keeps the inset", te2.textCursor().blockFormat().leftMargin() == CHECK_LEFT_MARGIN)

# Enter on the now-empty item exits to a plain line → inset cleared.
te2.keyPressEvent(QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Return, Qt.KeyboardModifier.NoModifier))
check("exiting the checklist clears the inset", te2.textCursor().blockFormat().leftMargin() == 0.0)

# Toggling a checklist back off also clears the inset.
cur2 = te2.textCursor(); cur2.insertText("eggs")
te2.toggle_checklist()
check("toggled-on again has the inset", te2.textCursor().blockFormat().leftMargin() == CHECK_LEFT_MARGIN)
te2.toggle_checklist()
check("toggled back off clears the inset", te2.textCursor().blockFormat().leftMargin() == 0.0)

note.hide(); note.deleteLater(); note2.hide(); note2.deleteLater()
print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
