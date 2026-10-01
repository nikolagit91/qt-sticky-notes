import sys, os, tempfile, atexit, shutil
_SB = tempfile.mkdtemp(prefix="sn_icn_")
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

from PyQt6.QtGui import QColor, QTextCursor
from sticky_notes.app import StickyNotesApp
from sticky_notes.note import StickyNote

app = StickyNotesApp(sys.argv[:1])
note = StickyNote(app, "n", {"id": "n", "geometry": [0, 0, 300, 200]})
te = note.text_edit
c = te.textCursor(); c.insertText("x main y")
sel = te.textCursor(); sel.setPosition(2); sel.setPosition(6, QTextCursor.MoveMode.KeepAnchor)
te.setTextCursor(sel); te.toggle_inline_code()
# round-trip, then normalize to a new colour
html = te.toHtml()
te2 = StickyNote(app, "m", {"id": "m", "geometry": [0,0,300,200]}).text_edit
te2.setHtml(html)
te2.inline_bg_color = QColor(255, 255, 255, 26)
te2.normalize_inline_code()
p = te2.textCursor(); p.setPosition(3); p.setPosition(4, QTextCursor.MoveMode.KeepAnchor)
bg = p.charFormat().background().color()
# normalize keeps only a TRANSPARENT marker (the visible chip is painted from
# inline_bg_color); the run survives reload and stays detected as inline.
check("normalize keeps a transparent inline marker (still detected)",
      te2._is_inline_code(p.charFormat()) and bg.alpha() == 0)
# a plain char keeps no background
q = te2.textCursor(); q.setPosition(0); q.setPosition(1, QTextCursor.MoveMode.KeepAnchor)
check("plain char untouched by normalize", te2._is_inline_code(q.charFormat()) is False)
print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
