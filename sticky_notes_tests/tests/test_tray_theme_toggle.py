"""The tray menu exposes a 'Toggle theme' action that flips light<->dark through
_set_theme (→ live apply).

Offscreen uses the Ayatana (GTK) backend, whose menu isn't inspectable from Qt,
so we build the Qt menu explicitly (`_build_tray_qt` — same entries list) and
assert on it."""
import sys, os, tempfile, atexit, shutil
_SB = tempfile.mkdtemp(prefix="sn_traytheme_")
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
from sticky_notes.i18n import tr

app = StickyNotesApp(sys.argv[:1])
app._theme = "light"

# Build the Qt tray menu explicitly (same entries as the Ayatana path).
app._build_tray_qt()
menu = app.tray.contextMenu()
labels = [a.text() for a in menu.actions()]
check("tray menu has a Toggle theme item", tr("Toggle theme") in labels)

act = next((a for a in menu.actions() if a.text() == tr("Toggle theme")), None)
check("the toggle item exists", act is not None)
act.trigger()
check("triggering it switches light -> dark", app._theme == "dark")
act.trigger()
check("triggering again switches dark -> light", app._theme == "light")

print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
