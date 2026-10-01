import sys, os, tempfile, atexit, shutil
_SB = tempfile.mkdtemp(prefix="sn_excl_")
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
from PyQt6.QtGui import QTextCursor

fails = []
def check(name, cond):
    print(f"  {'PASS' if cond else 'FAIL'}   {name}")
    if not cond: fails.append(name)

from sticky_notes.app import StickyNotesApp
from sticky_notes.note import StickyNote
app = StickyNotesApp(sys.argv[:1])
note = StickyNote(app, "n", {"id": "n", "geometry": [0, 0, 300, 200]})
te = note.text_edit

# The invariant the whole feature rests on: a BLOCK code line carries a BLOCK
# background, its characters carry NO char background — so inline detection and
# inline recolour must never touch block code.
c = te.textCursor(); c.insertText("print(1)"); te.toggle_code_block()
blk = te.document().begin()
def char_is_inline(i):
    cc = te.textCursor(); cc.setPosition(blk.position() + i)
    cc.setPosition(blk.position() + i + 1, QTextCursor.MoveMode.KeepAnchor)
    return te._is_inline_code(cc.charFormat())

check("block-code chars are NOT inline (no char background)",
      not any(char_is_inline(i) for i in range(len("print(1)"))))

# normalize_inline_code must leave block-code characters untouched...
te.normalize_inline_code()
check("normalize_inline_code leaves block-code chars untouched",
      not any(char_is_inline(i) for i in range(len("print(1)"))))
# ...and the block is still a code block afterwards.
check("block stays a code block after inline normalize",
      te._is_code_block(te.document().begin()) is True)

note.hide(); note.deleteLater()
print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
