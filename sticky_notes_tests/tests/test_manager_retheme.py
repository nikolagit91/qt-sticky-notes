"""The Manager rebuilds its content in the SAME widget on a live theme change:
top-level never recreated, active tab + search text preserved, root style
follows the new palette."""
import sys, os, tempfile, atexit, shutil
_SB = tempfile.mkdtemp(prefix="sn_mgrretheme_")
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
app._theme = "light"; theme.apply_theme("light")
app.create_new_note(content="one")

app.show_manager()
mgr = app._manager
check("manager has a retheme method", callable(getattr(mgr, "retheme", None)))

mgr.tabs.setCurrentIndex(2)          # Trash tab
mgr._search.setText("hello")

theme.apply_theme("dark")            # simulate the palette swap _apply_theme_live does
mgr.retheme()
app.processEvents()

check("active tab preserved", mgr.tabs.currentIndex() == 2)
check("search text preserved", mgr._search.text() == "hello")
check("root style follows the dark window bg", theme.UI.WINDOW_BG in mgr.styleSheet())
check("manager singleton unchanged", app._manager is mgr)

theme.apply_theme("light")
print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
