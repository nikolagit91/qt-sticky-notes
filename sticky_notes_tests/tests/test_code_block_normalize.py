import sys, os, tempfile, atexit, shutil
_SB = tempfile.mkdtemp(prefix="sn_cbn_")
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
from sticky_notes.widgets import CODE_FONT_FAMILY
app = StickyNotesApp(sys.argv[:1])
note = StickyNote(app, "n", {"id": "n", "geometry": [0, 0, 300, 200]})
te = note.text_edit
c = te.textCursor(); c.insertText("x = 1"); te.toggle_code_block()
html = te.toHtml()
check("code background round-trips in HTML", "background" in html.lower())

# reload into a fresh note, then normalize with a new code colour
note2 = StickyNote(app, "m", {"id": "m", "geometry": [0, 0, 300, 200]})
te2 = note2.text_edit
te2.setHtml(html)
check("code block survives reload (has background)", te2._is_code_block(te2.document().begin()) is True)
te2.code_bg_color = QColor(255, 255, 255, 26)
te2.code_fg_color = QColor("#abcdef")
te2.normalize_code_blocks()
# The block keeps only a TRANSPARENT marker (the visible rounded box is painted
# in paintEvent from te.code_bg_color, not filled into the block).
mark = te2.document().begin().blockFormat().background()
check("normalize keeps a transparent marker (still detected as code)",
      mark.style() != Qt.BrushStyle.NoBrush and mark.color().alpha() == 0)
cc = te2.textCursor(); cc.movePosition(cc.MoveOperation.Start)
cc.setPosition(1, cc.MoveMode.KeepAnchor)
check("normalize re-applies monospace", CODE_FONT_FAMILY in cc.charFormat().fontFamilies())
check("normalize re-applies the light code foreground",
      cc.charFormat().foreground().color().name().lower() == "#abcdef")
print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
