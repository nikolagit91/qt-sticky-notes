import sys, os, tempfile, atexit, shutil
_SB = tempfile.mkdtemp(prefix="sn_ffp_")
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

# A note built with a chosen font family must SERIALIZE that family — the
# empty-note cleanup in _on_text_changed must not run during construction and
# clobber it (via _update_toolbar_state writing the caret font back into
# _current_font_family). This regressed once; golden caught it, this locks it.
note = StickyNote(app, "a", {
    "id": "a", "content": "<p>hello</p>", "content_type": "html",
    "geometry": [0, 0, 300, 200], "font_family": "Serif", "font_size": 15,
})
check("chosen font family survives construction",
      note.get_data()["font_family"] == "Serif")

# And emptying the note AFTER init (the real cleanup path) must not clobber the
# family either — the cleanup runs, but it stamps the note's OWN family.
c = note.text_edit.textCursor()
c.select(QTextCursor.SelectionType.Document); note.text_edit.setTextCursor(c)
note.text_edit.textCursor().removeSelectedText()
check("emptying the note keeps the chosen family",
      note.get_data()["font_family"] == "Serif")

note.hide(); note.deleteLater()
print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
