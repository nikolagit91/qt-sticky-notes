import sys, os, tempfile, atexit, shutil
_SB = tempfile.mkdtemp(prefix="sn_cbe_")
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
app = StickyNotesApp(sys.argv[:1])
note = StickyNote(app, "n", {"id": "n", "geometry": [0, 0, 300, 200]})
te = note.text_edit

# Toggle { } on an EMPTY line (the "click, then type" flow) — must stick even
# though the empty-doc cleanup in _on_text_changed fires.
te.toggle_code_block()
check("toggling an empty line creates a code block", te._is_code_block(te.document().begin()) is True)

# Typing into that fresh code block keeps it a code block and is monospace.
c = te.textCursor(); c.insertText("x = 1")
check("typing keeps the code block", te._is_code_block(te.document().begin()) is True)
check("typed text is monospace", CODE_FONT_FAMILY in te.textCursor().charFormat().fontFamilies())

# Emptying a normal (non-code) note still gets cleaned to a plain block.
note2 = StickyNote(app, "m", {"id": "m", "geometry": [0, 0, 300, 200]})
te2 = note2.text_edit
c = te2.textCursor(); c.insertText("hello"); c.select(c.SelectionType.Document); c.removeSelectedText()
check("emptied plain note stays plain (cleanup preserved)",
      te2._is_code_block(te2.document().begin()) is False)

note.hide(); note.deleteLater(); note2.hide(); note2.deleteLater()
print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
