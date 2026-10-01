"""In dark mode the colour picker offers the dark note palette and the dark tray
icon renders; in light mode the pastels are offered. Existing notes are never
recoloured — only the picker's swatch set and the new-note default change."""
import sys, os, tempfile, atexit, shutil

_SB = tempfile.mkdtemp(prefix="sn_darkpal_")
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
from sticky_notes.icons import create_tray_icon

fails = []
def check(name, cond):
    print(f"  {'PASS' if cond else 'FAIL'}   {name}")
    if not cond: fails.append(name)

app = StickyNotesApp(sys.argv[:1])
app._snap_to_grid = app._snap_to_notes = app._snap_size = False

# light mode → picker offers the pastels
app._theme = "light"; th.apply_theme("light")
n = app.create_new_note()
check("light picker uses pastels", n._note_palette() is StickyNote.NOTE_COLORS)
check("light default note colour", app._default_note_color() == "#fff59d")

# dark mode → picker offers the dark set, and every dark swatch is actually dark
app._theme = "dark"; th.apply_theme("dark")
pal = n._note_palette()
check("dark picker uses dark set", pal is StickyNote.DARK_NOTE_COLORS)
check("dark default note colour", app._default_note_color() == "#2b2b30")
check("dark default is one of the dark swatches", "#2b2b30" in pal.values())
from PyQt6.QtGui import QColor
all_dark = all(th._rel_luminance(QColor(c)) < th.LIGHT_INK_THRESHOLD for c in pal.values())
check("every dark swatch flips to light ink (auto-contrast)", all_dark)

# an explicit colour is stored in the light slot (kept across theme switches)
n2 = app.create_new_note(color="#E3F2FD")
check("explicit colour stored in light slot", n2._color_light == "#E3F2FD")

# both icon variants render to a non-null pixmap
check("light tray icon renders", not create_tray_icon(dark=False).pixmap(64, 64).isNull())
check("dark tray icon renders",  not create_tray_icon(dark=True).pixmap(64, 64).isNull())

print("FAILS:", fails)
sys.exit(1 if fails else 0)
