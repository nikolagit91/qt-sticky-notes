"""_set_theme applies the chrome palette and persists the choice. It does NOT
close/reopen any window (reopening dropped the dock icon under always-on-top);
already-open windows update on restart via the shared Restart button. It is a
no-op when the requested theme already matches."""
import sys, os, tempfile, atexit, shutil, json

_SB = tempfile.mkdtemp(prefix="sn_themetoggle_")
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
from sticky_notes.config import SETTINGS_FILE

fails = []
def check(name, cond):
    print(f"  {'PASS' if cond else 'FAIL'}   {name}")
    if not cond: fails.append(name)

app = StickyNotesApp(sys.argv[:1])
# _set_theme must NOT reopen/close windows (that dropped the dock icon).
calls = {"show_settings": 0, "closed": 0}
app.show_settings = lambda *a, **k: calls.__setitem__("show_settings", calls["show_settings"] + 1)

app._theme = "light"; th.apply_theme("light")
app._set_theme("dark")
check("_set_theme sets _theme", app._theme == "dark")
check("_set_theme applies palette", th.current_theme() == "dark")
with open(SETTINGS_FILE, encoding="utf-8") as f:
    check("_set_theme persisted", json.load(f).get("theme") == "dark")
check("_set_theme did NOT reopen settings", calls["show_settings"] == 0)

# idempotent: same theme is a no-op
before = th.current_theme()
app._set_theme("dark")
check("no-op when theme unchanged", app._theme == "dark" and th.current_theme() == before)

print("FAILS:", fails)
sys.exit(1 if fails else 0)
