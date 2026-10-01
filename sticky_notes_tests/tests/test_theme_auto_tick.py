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

from datetime import datetime
from sticky_notes.config import SETTINGS_FILE

sched = app._theme_scheduler
check("scheduler postoji i zicaniran je", sched is not None)

def at(h, m):
    """Namjesti injektirani sat na h:m."""
    sched._now = lambda: datetime(2026, 7, 20, h, m)

app._theme_dark_start = "20:00"; app._theme_dark_end = "07:00"

# ── fiksni mod: tick je no-op (negativna) ALI auto tick mijenja (pozitivna) ──
app._set_theme_mode("light")
at(23, 0); sched._tick()
check("fiksni mod: tick ne dira temu", app._theme == "light")
app._set_theme_mode("auto")
at(23, 0); sched._tick()
check("auto mod: isti tick prebaci na dark", app._theme == "dark")

# ── dan -> light ─────────────────────────────────────────────────────────────
at(12, 0); sched._tick()
check("tick u 12:00 vrati light", app._theme == "light")

# ── override prezivi tickove unutar istog perioda ────────────────────────────
app._theme_override = "dark"          # korisnik rucno prebacio usred dana
app._apply_effective_theme("dark")
at(13, 0); sched._tick()
check("override drzi temu dark u 13:00", app._theme == "dark")
check("override jos aktivan", app._theme_override == "dark")

# ── granica cisti override i raspored preuzima ───────────────────────────────
at(20, 30); sched._tick()             # verdikt se mijenja light->dark = granica
check("granica: override ociscen", app._theme_override is None)
check("granica: tema po rasporedu (dark)", app._theme == "dark")
at(7, 30); sched._tick()              # dark->light granica
check("iduca granica: light po rasporedu", app._theme == "light")

# ── tick NE prepisuje mod na disku ───────────────────────────────────────────
data = json.load(open(SETTINGS_FILE, encoding="utf-8"))
check("disk i nakon tickova kaze 'auto'", data.get("theme") == "auto")

# ── izlazak iz auto moda resetira zapamceni verdikt ──────────────────────────
app._set_theme_mode("light")
at(23, 0); sched._tick()
check("po izlasku iz auto: tick opet no-op", app._theme == "light")
check("interni verdikt zaboravljen", sched._last_verdict is None)

print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
