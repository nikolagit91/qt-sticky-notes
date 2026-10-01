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

# ── polazno: fiksni light, atributi postoje ──────────────────────────────────
check("mode default light", app._theme_mode == "light")
check("efektivna default light", app._theme == "light")
check("override default None", app._theme_override is None)
check("default vremena 20:00-07:00",
      app._theme_dark_start == "20:00" and app._theme_dark_end == "07:00")

# ── _set_theme wrapper: fiksni modovi rade kao prije ─────────────────────────
app._set_theme("dark")
check("wrapper: _theme postane dark", app._theme == "dark")
check("wrapper: mod postane dark", app._theme_mode == "dark")
data = json.load(open(SETTINGS_FILE, encoding="utf-8"))
check("wrapper: na disku theme='dark'", data.get("theme") == "dark")

# ── prelazak u auto: efektivna slijedi raspored, disk kaze 'auto' ────────────
# Period se racuna RELATIVNO od stvarnog sata (sada-1h .. sada+2h) da je "sada"
# GARANTIRANO unutra — fiksni period tipa 00:00-23:59 ima jednominutnu rupu i
# test bi pokrenuti tocno u toj minuti lazno pao.
from datetime import datetime, timedelta
_now = datetime.now()
_start = (_now - timedelta(hours=1)).strftime("%H:%M")
_end   = (_now + timedelta(hours=2)).strftime("%H:%M")
app._theme_dark_start = _start; app._theme_dark_end = _end
app._set_theme_mode("auto")
check("auto: mod je auto", app._theme_mode == "auto")
check("auto: efektivna je dark (period pokriva sada)", app._theme == "dark")
check("auto: _theme NIJE 'auto'", app._theme in ("light", "dark"))
data = json.load(open(SETTINGS_FILE, encoding="utf-8"))
check("auto: disk kaze theme='auto'", data.get("theme") == "auto")
check("auto: vremena na disku", data.get("theme_dark_start") == _start
      and data.get("theme_dark_end") == _end)

# ── _apply_effective_theme ne dira mod ni disk-mod ───────────────────────────
app._apply_effective_theme("light")
check("apply_effective: efektivna light", app._theme == "light")
check("apply_effective: mod OSTAO auto", app._theme_mode == "auto")
data = json.load(open(SETTINGS_FILE, encoding="utf-8"))
check("apply_effective: disk i dalje 'auto'", data.get("theme") == "auto")

# ── povratak u fiksni mod brise override ─────────────────────────────────────
app._theme_override = "light"
app._set_theme_mode("dark")
check("fiksni mod: override obrisan", app._theme_override is None)
check("fiksni mod: efektivna dark", app._theme == "dark")

# ── load: kriva vremena padnu na default, kriv mod na light ──────────────────
data = json.load(open(SETTINGS_FILE, encoding="utf-8"))
data["theme"] = "banana"; data["theme_dark_start"] = 99; data["theme_dark_end"] = "26:00"
json.dump(data, open(SETTINGS_FILE, "w", encoding="utf-8"))
app._theme_dark_start = "20:00"; app._theme_dark_end = "07:00"   # poznato stanje
app._load_backup_settings()
check("load: kriv mod -> light", app._theme_mode == "light")
check("load: kriva vremena -> ostaju prethodna valjana",
      app._theme_dark_start == "20:00" and app._theme_dark_end == "07:00")
check("load: app zivi dalje (nema iznimke) i efektivna je valjana",
      app._theme in ("light", "dark"))

print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
