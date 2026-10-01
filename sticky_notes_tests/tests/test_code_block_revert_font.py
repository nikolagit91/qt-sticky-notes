import sys, os, tempfile, atexit, shutil
_SB = tempfile.mkdtemp(prefix="sn_cbrf_")
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
app = StickyNotesApp(sys.argv[:1])
note = StickyNote(app, "n", {"id": "n", "geometry": [0, 0, 300, 200]})
te = note.text_edit

# The note carries its chosen family for code-block reverts.
check("note keeps text_edit.code_revert_family in sync",
      te.code_revert_family == note._current_font_family)

# Pick a distinctive note font, then code + un-code a line: it must revert to the
# NOTE's family, not the app default.
note._apply_font_family("Deja Vu Serif")
check("_apply_font_family updates code_revert_family", te.code_revert_family == "Deja Vu Serif")

c = te.textCursor(); c.insertText("some code")
te.toggle_code_block()      # → monospace
te.toggle_code_block()      # → revert
cc = te.textCursor(); cc.movePosition(cc.MoveOperation.StartOfBlock)
cc.setPosition(cc.position() + 1, cc.MoveMode.KeepAnchor)
fams = cc.charFormat().fontFamilies() or []
check("un-coded text reverts to the note's family (not app default)",
      "Deja Vu Serif" in fams)

note.hide(); note.deleteLater()
print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
