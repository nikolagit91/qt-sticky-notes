"""Chrome colours route through the UI palette: menu_style() follows the theme,
and the Settings dialog built under the dark theme carries dark chrome (not the
old hardcoded light surface/window colours) in its stylesheets."""
import sys, os, tempfile, atexit, shutil

_SB = tempfile.mkdtemp(prefix="sn_chromedark_")
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

fails = []
def check(name, cond):
    print(f"  {'PASS' if cond else 'FAIL'}   {name}")
    if not cond: fails.append(name)

# menu_style follows the palette
th.apply_theme("dark")
ms_dark = th.menu_style()
check("menu_style uses dark SURFACE", th.DARK_UI["SURFACE"] in ms_dark)
# White is allowed only as the selected-item text on the accent; the menu
# BACKGROUND must never be the light surface in dark mode.
check("menu_style background is not hardcoded white",
      "background: #ffffff" not in ms_dark.lower() and f"background: {th.LIGHT_UI['SURFACE']}" not in ms_dark.lower())
th.apply_theme("light")
check("menu_style uses light SURFACE", th.LIGHT_UI["SURFACE"] in th.menu_style())

# Settings dialog builds cleanly under dark theme and its stylesheets carry dark chrome.
from sticky_notes.app import StickyNotesApp
app = StickyNotesApp(sys.argv[:1])
app._theme = "dark"; th.apply_theme("dark")
app.show_settings()
ss = "".join(w.styleSheet() for w in app._open_windows)
# collect child widget stylesheets too (labels/inputs set their own)
from PyQt6.QtWidgets import QWidget
for w in app._open_windows:
    for child in w.findChildren(QWidget):
        ss += child.styleSheet()
check("settings chrome references dark bg or surface",
      th.DARK_UI["WINDOW_BG"] in ss or th.DARK_UI["SURFACE"] in ss)
check("settings chrome carries dark text colour", th.DARK_UI["TEXT"] in ss)
check("no stray light window-bg literal in dark settings", th.LIGHT_UI["WINDOW_BG"] not in ss)
for w in list(app._open_windows):
    w.close()

print("FAILS:", fails)
sys.exit(1 if fails else 0)
