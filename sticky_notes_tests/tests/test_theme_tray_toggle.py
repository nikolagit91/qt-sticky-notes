import sys, os, json, time, tempfile, atexit, shutil
_SB = tempfile.mkdtemp(prefix="sn_test_")
atexit.register(lambda: shutil.rmtree(_SB, ignore_errors=True))
os.environ["HOME"] = _SB
os.environ["XDG_CONFIG_HOME"] = os.path.join(_SB, ".config")
os.environ["XDG_DATA_HOME"]   = os.path.join(_SB, ".local", "share")
os.environ.setdefault("XDG_RUNTIME_DIR", _SB)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ.pop("DISPLAY", None); os.environ.pop("WAYLAND_DISPLAY", None)
os.makedirs(os.path.join(_SB, ".local", "share", "sticky_notes"), exist_ok=True)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

fails = []
def check(name, cond):
    print(f"  {'PASS' if cond else 'FAIL'}   {name}")
    if not cond: fails.append(name)

from PyQt6.QtWidgets import QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
QMessageBox.warning     = staticmethod(lambda *a, **k: None)
QMessageBox.exec        = lambda self, *a, **k: QMessageBox.StandardButton.Ok

from sticky_notes.app import StickyNotesApp
app = StickyNotesApp(sys.argv[:1])
app._snap_to_grid = app._snap_to_notes = app._snap_size = False
for e in list(app.notes.values()):
    e.hide(); e.deleteLater()
app.notes.clear()

from sticky_notes.config import SETTINGS_FILE

# ── fiksni mod: toggle mijenja MOD (kao oduvijek) ────────────────────────────
app._set_theme_mode("light")
app._toggle_theme()
check("fiksni: light -> dark", app._theme == "dark" and app._theme_mode == "dark")
data = json.load(open(SETTINGS_FILE, encoding="utf-8"))
check("fiksni: disk prati mod", data.get("theme") == "dark")

# ── auto mod: toggle = override, mod i disk netaknuti ────────────────────────
# period relativno od stvarnog sata -> "sada" je garantirano u tamnom periodu
from datetime import datetime, timedelta
_now = datetime.now()
app._theme_dark_start = (_now - timedelta(hours=1)).strftime("%H:%M")
app._theme_dark_end   = (_now + timedelta(hours=2)).strftime("%H:%M")
app._set_theme_mode("auto")
check("auto polaz: efektivna dark", app._theme == "dark")
app._toggle_theme()
check("auto: efektivna preskocila na light", app._theme == "light")
check("auto: override postavljen", app._theme_override == "light")
check("auto: mod OSTAO auto", app._theme_mode == "auto")
data = json.load(open(SETTINGS_FILE, encoding="utf-8"))
check("auto: disk OSTAO 'auto'", data.get("theme") == "auto")

# ── drugi toggle vraca natrag (override na suprotno) ─────────────────────────
app._toggle_theme()
check("auto: drugi toggle vrati dark", app._theme == "dark"
      and app._theme_override == "dark" and app._theme_mode == "auto")

print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
