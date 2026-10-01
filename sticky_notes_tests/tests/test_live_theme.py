"""Theme changes apply live (no restart): the palette swaps and open notes
re-ink in place. Chrome-window and tray specifics are covered in their own
tests; here we lock the core: _apply_theme_live swaps UI.* and flips a note's
effective colour."""
import sys, os, tempfile, atexit, shutil
_SB = tempfile.mkdtemp(prefix="sn_livetheme_")
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

from sticky_notes import theme
from sticky_notes.app import StickyNotesApp

app = StickyNotesApp(sys.argv[:1])
for e in list(app.notes.values()):
    e.hide(); e.deleteLater()
app.notes.clear()

check("_pending_restart defaults False", app._pending_restart is False)

# a note with both colour slots set: light=yellow, dark=charcoal
app._theme = "light"; theme.apply_theme("light")
n = app.create_new_note(content="x", color="#fff59d", color_dark="#2b2b30")
n.resize(300, 220); n.show(); app.processEvents()
check("starts on the light slot", n._qcolor_base.name() == "#fff59d")

# switch to dark LIVE
app._set_theme("dark")
app.processEvents()
check("app theme is dark", app._theme == "dark")
check("palette swapped to dark (UI.WINDOW_BG)", theme.UI.WINDOW_BG == theme.DARK_UI["WINDOW_BG"])
check("note flipped to its dark slot live", n._qcolor_base.name() == "#2b2b30")

# and back to light
app._set_theme("light")
app.processEvents()
check("note flipped back to the light slot", n._qcolor_base.name() == "#fff59d")
check("palette back to light", theme.UI.WINDOW_BG == theme.LIGHT_UI["WINDOW_BG"])

# selecting the same theme is a no-op (no exception, stays put)
app._set_theme("light")
check("re-selecting the current theme is a no-op", app._theme == "light")

print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
