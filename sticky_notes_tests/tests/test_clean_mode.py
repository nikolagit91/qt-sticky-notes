import sys, os, tempfile, atexit, shutil
_SB = tempfile.mkdtemp(prefix="sn_clean_")
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
from PyQt6.QtCore import QEvent
QMessageBox.information = staticmethod(lambda *a, **k: None)

fails = []
def check(name, cond):
    print(f"  {'PASS' if cond else 'FAIL'}   {name}")
    if not cond: fails.append(name)

from sticky_notes.app import StickyNotesApp
from sticky_notes.note import StickyNote
app = StickyNotesApp(sys.argv[:1])
note = StickyNote(app, "n", {"id": "n", "geometry": [0, 0, 300, 200]})

check("defaults to clean mode off", note._clean_mode is False)
check("chrome starts revealed", note._chrome_revealed is True)

note._set_clean_mode(True)
check("enabling clean mode sets the flag", note._clean_mode is True)
check("enabling collapses the chrome (not revealed)", note._chrome_revealed is False)
check("header animation targets 0", note._header_anim.endValue() == 0)
check("toolbar is collapsed with the header", note._toolbar_visible is False)
check("resize grip is NOT hidden by clean mode", not note._grip.isHidden())

# Hover logic: a Leave arms the hide debounce; an Enter cancels it.
note.eventFilter(note, QEvent(QEvent.Type.Leave))
check("Leave arms the hide debounce", note._hide_debounce.isActive())
note.eventFilter(note, QEvent(QEvent.Type.Enter))
check("Enter cancels the hide debounce", not note._hide_debounce.isActive())

note._reveal_chrome()
check("reveal marks chrome revealed", note._chrome_revealed is True)
check("reveal animates the header open (to 38)", note._header_anim.endValue() == 38)

note._hide_chrome()
check("hide marks chrome hidden", note._chrome_revealed is False)
check("hide animates the header shut (to 0)", note._header_anim.endValue() == 0)

# _maybe_hide must still hide when the NOTE itself is the active window (only a
# child dialog of the note should defer the hide).
from PyQt6.QtWidgets import QApplication
note._reveal_chrome()
_orig_aw = QApplication.activeWindow
QApplication.activeWindow = staticmethod(lambda: note)
note._maybe_hide()
QApplication.activeWindow = _orig_aw
check("_maybe_hide hides when the note itself is active", note._chrome_revealed is False)

note._set_clean_mode(False)
check("disabling clean mode clears the flag", note._clean_mode is False)
check("disabling reveals the chrome", note._chrome_revealed is True)
note.eventFilter(note, QEvent(QEvent.Type.Leave))
check("Leave ignored when clean mode is off", not note._hide_debounce.isActive())

note.hide(); note.deleteLater()

# Global setting drives every open note.
check("app defaults clean mode off", app._clean_mode is False)
n1 = StickyNote(app, "a", {"id": "a", "geometry": [0, 0, 300, 200]}); app.notes["a"] = n1
n2 = StickyNote(app, "b", {"id": "b", "geometry": [0, 0, 300, 200]}); app.notes["b"] = n2
app._clean_mode = True
app._apply_clean_mode()
check("_apply_clean_mode collapses all notes",
      n1._chrome_revealed is False and n2._chrome_revealed is False)
app._clean_mode = False
app._apply_clean_mode()
check("_apply_clean_mode restores all notes",
      n1._chrome_revealed is True and n2._chrome_revealed is True)
n1.hide(); n1.deleteLater(); n2.hide(); n2.deleteLater()

print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
