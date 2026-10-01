"""The chrome theme persists through settings.json like every other preference:
default "light", saved under key "theme", loaded back on _load_backup_settings."""
import sys, os, tempfile, atexit, shutil, json

_SB = tempfile.mkdtemp(prefix="sn_themeset_")
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
from sticky_notes.config import SETTINGS_FILE

fails = []
def check(name, cond):
    print(f"  {'PASS' if cond else 'FAIL'}   {name}")
    if not cond: fails.append(name)

app = StickyNotesApp(sys.argv[:1])
check("default theme is light", app._theme == "light")

# Kljuc "theme" na disku od auto-teme nosi MOD (light/dark/auto), pa round-trip
# ide kroz javni put — izravno pisanje privatnog _theme vise se ne persistira.
app._set_theme("dark")
with open(SETTINGS_FILE, encoding="utf-8") as f:
    check("theme persisted to settings.json", json.load(f).get("theme") == "dark")

# fresh load reads it back
app._theme = "light"; app._theme_mode = "light"
app._load_backup_settings()
check("theme loaded back as dark", app._theme == "dark" and app._theme_mode == "dark")

print("FAILS:", fails)
sys.exit(1 if fails else 0)
