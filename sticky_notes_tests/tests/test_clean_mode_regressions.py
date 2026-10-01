import sys, os, tempfile, atexit, shutil
_SB = tempfile.mkdtemp(prefix="sn_cleanreg_")
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

# ── Bug 1: toggling the toolbar OFF while in clean mode must persist across a
# hide/reveal cycle (the manual toggle updates the remembered preference). ──
note = StickyNote(app, "n", {"id": "n", "geometry": [0, 0, 300, 200]})
note._set_clean_mode(True)
note._reveal_chrome()
check("bug1: toolbar visible after reveal", note._toolbar_visible is True)
note._toggle_toolbar()                     # user clicks the toggle → hide toolbar
check("bug1: manual toggle hides toolbar", note._toolbar_visible is False)
note._hide_chrome()
note._reveal_chrome()                      # next hover reveal
check("bug1: toolbar STAYS hidden after reveal (pref remembered)",
      note._toolbar_visible is False)
note.hide(); note.deleteLater()

# ── Bug 2: while the header holds keyboard focus (user is arrow-moving the
# note), _maybe_hide must NOT collapse the chrome and steal that focus. ──
note2 = StickyNote(app, "m", {"id": "m", "geometry": [0, 0, 300, 200]})
note2._set_clean_mode(True)
note2._reveal_chrome()
note2.header.hasFocus = lambda: True        # simulate arrow-move focus
note2._maybe_hide()
check("bug2: chrome stays revealed while header has keyboard focus",
      note2._chrome_revealed is True)
note2.header.hasFocus = lambda: False       # focus left the header
note2._maybe_hide()
check("bug2: chrome hides once the header loses focus",
      note2._chrome_revealed is False)
note2.hide(); note2.deleteLater()

# ── Bug 3: reveal must clear stale :hover left on toolbar buttons by the
# animation. Can't exercise real hover offscreen, so verify the reset helper
# actually drops WA_UnderMouse on every toolbar button. ──
from PyQt6.QtWidgets import QPushButton
from PyQt6.QtCore import Qt
note3 = StickyNote(app, "h", {"id": "h", "geometry": [0, 0, 300, 200]})
btns = note3.toolbar.findChildren(QPushButton)
for b in btns:
    b.setAttribute(Qt.WidgetAttribute.WA_UnderMouse, True)   # fake stuck hover
note3._clear_toolbar_hover()
check("bug3: _clear_toolbar_hover drops WA_UnderMouse on all toolbar buttons",
      bool(btns) and all(not b.testAttribute(Qt.WidgetAttribute.WA_UnderMouse) for b in btns))
note3.hide(); note3.deleteLater()

# ── Bug 2b: clicking the body / clicking away must hide the chrome without
# needing a stray mouse move (hide used to fire only on Leave/MouseMove). ──
from PyQt6.QtCore import QEvent
note4 = StickyNote(app, "b2", {"id": "b2", "geometry": [0, 0, 300, 200]})
note4._set_clean_mode(True)
note4._reveal_chrome()
# A press in the note body arms the hide; the debounced check then collapses it.
note4.eventFilter(note4.text_edit, QEvent(QEvent.Type.MouseButtonPress))
check("bug2b: body click arms the hide debounce", note4._hide_debounce.isActive())
note4._maybe_hide()
check("bug2b: chrome hides on a body click (no mouse move needed)",
      note4._chrome_revealed is False)

note4._reveal_chrome()
# Clicking away deactivates the note window → chrome must collapse too.
note4.eventFilter(note4, QEvent(QEvent.Type.WindowDeactivate))
check("bug2b: window deactivate arms the hide debounce", note4._hide_debounce.isActive())
note4._maybe_hide()
check("bug2b: chrome hides when the note is deactivated (clicked away)",
      note4._chrome_revealed is False)
note4.hide(); note4.deleteLater()

print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
