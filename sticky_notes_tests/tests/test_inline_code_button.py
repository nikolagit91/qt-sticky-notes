import sys, os, tempfile, atexit, shutil
_SB = tempfile.mkdtemp(prefix="sn_inlinebtn_")
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

from PyQt6.QtGui import QTextCursor
from sticky_notes.app import StickyNotesApp
from sticky_notes.note import StickyNote
app = StickyNotesApp(sys.argv[:1]); app._auto_contrast = True
note = StickyNote(app, "n", {"id": "n", "geometry": [0, 0, 300, 200], "color": "#fff8b8"})
te = note.text_edit
check("note has an inline-code button", hasattr(note, "btn_inline_code"))

c = te.textCursor(); c.insertText("abcdef")
sel = te.textCursor(); sel.setPosition(1); sel.setPosition(4, QTextCursor.MoveMode.KeepAnchor)
te.setTextCursor(sel)
note._toggle_inline_code()
# caret inside the span → button checked
mid = te.textCursor(); mid.setPosition(2); te.setTextCursor(mid)
note._update_toolbar_state()
check("inline button checked when caret is in an inline span", note.btn_inline_code.isChecked() is True)
# Inline code is now a SUBTLE translucent tint that shares the code block's hue.
check("inline_bg is a translucent tint (not opaque, not empty)",
      0 < te.inline_bg_color.alpha() < 255)
before = te.inline_bg_color.name()

note.color = "#000000"; note._apply_color()
check("inline_bg follows the note colour (recolours)", te.inline_bg_color.name() != before)
# The span itself carries only a TRANSPARENT marker (the visible chip is painted
# from inline_bg_color, not filled into the char) — but stays detected as inline.
p = te.textCursor(); p.setPosition(2); p.setPosition(3, QTextCursor.MoveMode.KeepAnchor)
check("inline span keeps a transparent marker (still detected)",
      te._is_inline_code(p.charFormat()) and p.charFormat().background().color().alpha() == 0)
print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
