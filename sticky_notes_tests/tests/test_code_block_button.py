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

fails = []
def check(name, cond):
    print(f"  {'PASS' if cond else 'FAIL'}   {name}")
    if not cond: fails.append(name)

from PyQt6.QtGui import QColor
from PyQt6.QtCore import Qt
from sticky_notes.app import StickyNotesApp
from sticky_notes.note import StickyNote
from sticky_notes.theme import note_ink, _rel_luminance
app = StickyNotesApp(sys.argv[:1]); app._auto_contrast = True
note = StickyNote(app, "n", {"id": "n", "geometry": [0, 0, 300, 200], "color": "#fff8b8"})
te = note.text_edit

check("note has a code button", hasattr(note, "btn_code"))
c = te.textCursor(); c.insertText("code")
note._toggle_code_block()
note._update_toolbar_state()
check("code button checked when caret in a code block", note.btn_code.isChecked() is True)
check("code_bg_color is an opaque dark box on the light note",
      te.code_bg_color.alpha() == 255 and _rel_luminance(te.code_bg_color) < 0.20)

# switch to a black note → the box recolours (a darker version of the new hue)
note.color = "#000000"; note._apply_color()
check("code_bg_color follows the new note colour",
      te.code_bg_color.name().lower() == note_ink(QColor("#000000")).code_bg.name().lower())
# the block itself now carries only a TRANSPARENT marker — the visible box is
# painted in paintEvent, not filled by Qt — but it's still detected as code.
mark = te.document().begin().blockFormat().background()
check("existing code block keeps a transparent marker (still detected)",
      mark.style() != Qt.BrushStyle.NoBrush and mark.color().alpha() == 0)

note._toggle_code_block(); note._update_toolbar_state()
check("code button unchecks after revert", note.btn_code.isChecked() is False)
print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
