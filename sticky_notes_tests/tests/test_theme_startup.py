"""A new note's starting colour follows the active chrome theme (dark theme →
dark note fill, which auto-contrast then makes readable). Explicit colours still
win. apply_theme is imported into app and used at startup."""
import sys, os, tempfile, atexit, shutil

_SB = tempfile.mkdtemp(prefix="sn_themestart_")
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

from sticky_notes.app import StickyNotesApp

fails = []
def check(name, cond):
    print(f"  {'PASS' if cond else 'FAIL'}   {name}")
    if not cond: fails.append(name)

app = StickyNotesApp(sys.argv[:1])
app._snap_to_grid = app._snap_to_notes = app._snap_size = False

# default note colour follows theme
app._theme = "light"
check("light default note colour", app._default_note_color() == "#fff59d")
app._theme = "dark"
check("dark default note colour", app._default_note_color() == "#2b2b30")

# a new note with no explicit colour picks up the theme default
n = app.create_new_note()
check("new note uses dark default", n is not None and n.color == "#2b2b30")

# explicit `color` now sets the LIGHT slot (shown in light mode)
app._theme = "light"
n2 = app.create_new_note(color="#E3F2FD")
check("explicit colour sets light slot", n2.color == "#E3F2FD" and n2._color_light == "#E3F2FD")

print("FAILS:", fails)
sys.exit(1 if fails else 0)
