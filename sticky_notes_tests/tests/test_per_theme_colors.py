"""A note carries a light and a dark colour slot; the shown (effective) colour
follows the app theme, _set_color writes only the active slot, and both slots
round-trip through serialization. Legacy records keep their colour as light."""
import sys, os, tempfile, atexit, shutil

_SB = tempfile.mkdtemp(prefix="sn_ptc_")
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
from sticky_notes.note import StickyNote

fails = []
def check(name, cond):
    print(f"  {'PASS' if cond else 'FAIL'}   {name}")
    if not cond: fails.append(name)

app = StickyNotesApp(sys.argv[:1])
app._snap_to_grid = app._snap_to_notes = app._snap_size = False

def make(color="#fff59d", color_dark=""):
    return StickyNote(app, data={"content": "", "color": color, "color_dark": color_dark,
                                 "geometry": [0, 0, 300, 200]})

# effective colour follows the theme
app._theme = "light"; th.apply_theme("light")
n = make("#E3F2FD", "#2c3542")
check("light shows light slot", n._effective_color() == "#E3F2FD" and n.color == "#E3F2FD")
app._theme = "dark"; th.apply_theme("dark")
n2 = make("#E3F2FD", "#2c3542")
check("dark shows dark slot", n2._effective_color() == "#2c3542")
# empty dark slot → dark default
n3 = make("#E3F2FD", "")
check("empty dark slot → #2b2b30", n3._effective_color() == "#2b2b30")

# _set_color writes the current theme's slot only
app._theme = "dark"; th.apply_theme("dark")
n4 = make("#E3F2FD", "#111213")
n4._set_color("#33373d")
check("set in dark writes dark slot", n4._color_dark == "#33373d")
check("set in dark leaves light slot", n4._color_light == "#E3F2FD")
app._theme = "light"; th.apply_theme("light")
n4._set_color("#FCE4EC")
check("set in light writes light slot", n4._color_light == "#FCE4EC")
check("set in light leaves dark slot", n4._color_dark == "#33373d")

# serialization carries both slots; reload is faithful
data = n4.get_data()
check("get_data serializes light slot as color", data["color"] == "#FCE4EC")
check("get_data serializes dark slot", data["color_dark"] == "#33373d")
n5 = StickyNote(app, data=data)
check("reload keeps light slot", n5._color_light == "#FCE4EC")
check("reload keeps dark slot", n5._color_dark == "#33373d")

# migration: legacy record (no color_dark) → light kept, dark unset
n6 = StickyNote(app, data={"content": "", "color": "#FFF3E0", "geometry": [0, 0, 300, 200]})
check("legacy: light slot = stored colour", n6._color_light == "#FFF3E0")
check("legacy: dark slot empty", n6._color_dark == "")

print("FAILS:", fails)
sys.exit(1 if fails else 0)
