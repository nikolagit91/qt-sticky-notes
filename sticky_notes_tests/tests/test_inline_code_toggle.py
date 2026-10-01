import sys, os, tempfile, atexit, shutil
_SB = tempfile.mkdtemp(prefix="sn_inline_code_")
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

from sticky_notes.app import StickyNotesApp
from sticky_notes.note import StickyNote
from sticky_notes.widgets import CODE_FONT_FAMILY
from PyQt6.QtGui import QTextCursor
from PyQt6.QtCore import Qt
app = StickyNotesApp(sys.argv[:1])
note = StickyNote(app, "n", {"id": "n", "geometry": [0, 0, 300, 200]})
te = note.text_edit

c = te.textCursor(); c.insertText("call main() now")
# select "main()" (positions 5..11) and toggle inline
sel = te.textCursor(); sel.setPosition(5); sel.setPosition(11, QTextCursor.MoveMode.KeepAnchor)
te.setTextCursor(sel); te.toggle_inline_code()
probe = te.textCursor(); probe.setPosition(6); probe.setPosition(7, QTextCursor.MoveMode.KeepAnchor)
check("inline span has a char background", te._is_inline_code(probe.charFormat()) is True)
check("inline span is monospace", CODE_FONT_FAMILY in (probe.charFormat().fontFamilies() or []))
# outside the span stays plain
out = te.textCursor(); out.setPosition(0); out.setPosition(1, QTextCursor.MoveMode.KeepAnchor)
check("text outside is not inline", te._is_inline_code(out.charFormat()) is False)
# toggle again reverts the span
sel2 = te.textCursor(); sel2.setPosition(5); sel2.setPosition(11, QTextCursor.MoveMode.KeepAnchor)
te.setTextCursor(sel2); te.toggle_inline_code()
probe2 = te.textCursor(); probe2.setPosition(6); probe2.setPosition(7, QTextCursor.MoveMode.KeepAnchor)
check("toggling again clears the inline background", te._is_inline_code(probe2.charFormat()) is False)
# no selection → inline mode for typing
te2 = StickyNote(app, "m", {"id": "m", "geometry": [0,0,300,200]}).text_edit
te2.toggle_inline_code()
check("no-selection toggle makes the typing format inline", te2._is_inline_code(te2.currentCharFormat()) is True)
print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
