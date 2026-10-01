import sys, os, tempfile, atexit, shutil
_SB = tempfile.mkdtemp(prefix="sn_ckcon_")
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
from PyQt6.QtGui import QColor, QTextCursor

fails = []
def check(name, cond):
    print(f"  {'PASS' if cond else 'FAIL'}   {name}")
    if not cond: fails.append(name)

from sticky_notes.app import StickyNotesApp
from sticky_notes.note import StickyNote
from sticky_notes.theme import note_ink, LIGHT_INK, DARK_INK
app = StickyNotesApp(sys.argv[:1])
app._auto_contrast = True

note = StickyNote(app, "n", {"id": "n", "geometry": [0, 0, 300, 200], "color": "#fff8b8"})
te = note.text_edit
c = te.textCursor(); c.insertText("milk"); te.toggle_checklist()

def box_fg():
    b = te.document().begin().position()
    cc = QTextCursor(te.document()); cc.setPosition(b); cc.setPosition(b + 1, QTextCursor.MoveMode.KeepAnchor)
    return cc.charFormat().foreground().color().name().lower()

check("light note: checkbox uses dark ink (visible)", box_fg() == DARK_INK.text.lower())

# Switch to a black note → the box must flip to the light ink so it stays visible.
note.color = "#000000"; note._apply_color()
check("checkbox_text_color follows the note ink", te.checkbox_text_color.lower() == LIGHT_INK.text.lower())
check("black note: checkbox recoloured to light ink (was invisible)", box_fg() == LIGHT_INK.text.lower())

# And back to a light note.
note.color = "#fff8b8"; note._apply_color()
check("back to light: checkbox dark again", box_fg() == DARK_INK.text.lower())

note.hide(); note.deleteLater()
print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
