"""A new note seeds its light slot (default yellow) and leaves the dark slot
unset (so it shows the dark default #2b2b30 in dark mode). Copying a note
preserves BOTH slots."""
import sys, os, tempfile, atexit, shutil

_SB = tempfile.mkdtemp(prefix="sn_nnc_")
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
import sticky_notes.theme as th
from sticky_notes.app import StickyNotesApp

fails = []
def check(name, cond):
    print(f"  {'PASS' if cond else 'FAIL'}   {name}")
    if not cond: fails.append(name)

app = StickyNotesApp(sys.argv[:1])
app._snap_to_grid = app._snap_to_notes = app._snap_size = False

# new note in light mode: light slot yellow, dark slot unset (→ #2b2b30 in dark)
app._theme = "light"; th.apply_theme("light")
n = app.create_new_note()
check("new light note: light slot yellow", n._color_light == "#fff59d")
check("new light note: dark slot unset", n._color_dark == "")
check("new light note shows yellow", n.color == "#fff59d")

# same note, viewed in dark, shows the dark default
app._theme = "dark"; th.apply_theme("dark")
check("unset dark slot → #2b2b30 effective", n._effective_color() == "#2b2b30")

# new note created in dark shows #2b2b30, still keeps a yellow light slot
n2 = app.create_new_note()
check("new dark note shows #2b2b30", n2.color == "#2b2b30")
check("new dark note keeps yellow light slot", n2._color_light == "#fff59d")

# copying a note preserves BOTH slots
n2._color_light = "#FCE4EC"; n2._color_dark = "#322a3f"
copy = app.create_new_note(color=n2._color_light, color_dark=n2._color_dark)
check("copy keeps light slot", copy._color_light == "#FCE4EC")
check("copy keeps dark slot", copy._color_dark == "#322a3f")

print("FAILS:", fails)
sys.exit(1 if fails else 0)
