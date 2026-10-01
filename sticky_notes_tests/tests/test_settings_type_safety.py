"""Krive vrijednosti u settings.json ne smiju sprijeciti pokretanje aplikacije.

Review prolaz 6, C-1. Sve brojcane postavke citale su se sirovo:
    self._note_opacity = data.get("note_opacity", self._note_opacity)
Rucno uredjen (ili iz starije verzije naslijedjen) string umjesto broja proso bi
kroz load bez rijeci, a puknuo bi tek na mjestu upotrebe — _bg_alpha radi
aritmetiku nad njim, pa NIJEDNA nota ne bi mogla nastati i aplikacija se ne bi
pokrenula. Podaci prezive, ali app je neupotrebljiv i uzrok je nevidljiv.

Presedan da se tip mijenja kroz verzije vec postoji: note_border je isao
bool -> str, zbog cega i postoji coerce_border_mode.
"""
import sys, os, json, tempfile, atexit, shutil
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
from sticky_notes.app import StickyNotesApp
from sticky_notes.config import SETTINGS_FILE

app = StickyNotesApp(sys.argv[:1])
app._snap_to_grid = app._snap_to_notes = app._snap_size = False
for e in list(app.notes.values()):
    e.hide(); e.deleteLater()
app.notes.clear()

# ── neispravni tipovi i vrijednosti izvan raspona ───────────────────────────
json.dump({
    "note_opacity": "80",        # string umjesto broja  -> rusio _bg_alpha
    "grid_size": None,           # null
    "ui_scale": 50,              # daleko izvan raspona 1.0-2.0
    "font_size": "velik",        # nebrojcani string
    "note_width": [500],         # lista
    "note_height": {"a": 1},     # dict
    "backup_interval": -5,       # negativan
}, open(SETTINGS_FILE, "w", encoding="utf-8"))
app._load_backup_settings()

check("opacity krivog tipa -> brojcana vrijednost",
      isinstance(app._note_opacity, (int, float)))
check("opacity unutar raspona kontrole (40-100)", 40 <= app._note_opacity <= 100)
check("grid_size null -> broj", isinstance(app._grid_size, int) and 5 <= app._grid_size <= 100)
check("ui_scale 50 clampan na 1.0-2.0", 1.0 <= app._ui_scale <= 2.0)

# donja granica: vrijednost ispod 100% (stari raspon dopuštao 0.7) migrira na 1.0
json.dump({"ui_scale": 0.7}, open(SETTINGS_FILE, "w", encoding="utf-8"))
app._load_backup_settings()
check("ui_scale 0.7 migrira na donju granicu 1.0", app._ui_scale == 1.0)
check("font_size nebrojcan -> broj u rasponu",
      isinstance(app._default_font_size, int) and 8 <= app._default_font_size <= 72)
check("note_width lista -> broj", isinstance(app._default_note_width, int))
check("note_height dict -> broj", isinstance(app._default_note_height, int))
check("backup_interval nije negativan", app._backup_interval_minutes >= 0)

# ── najvaznije: nota se moze napraviti i nacrtati ──────────────────────────
try:
    n = app.create_new_note()
    ok_note = n is not None
    alpha = n._bg_alpha()
except Exception as e:
    ok_note = False; alpha = None
    print(f"        iznimka: {type(e).__name__}: {e}")
check("nota se moze stvoriti unatoc pokvarenim postavkama", ok_note)
check("_bg_alpha vraca ispravnu alfu", isinstance(alpha, int) and 0 <= alpha <= 255)

# ── POZITIVNA POLOVICA: ispravne vrijednosti se NE diraju ─────────────────
json.dump({"note_opacity": 65, "grid_size": 25, "ui_scale": 1.25,
           "font_size": 15, "note_width": 480, "note_height": 320,
           "backup_interval": 60}, open(SETTINGS_FILE, "w", encoding="utf-8"))
app._load_backup_settings()
check("ispravan opacity prolazi netaknut", app._note_opacity == 65)
check("ispravan grid prolazi netaknut", app._grid_size == 25)
check("ispravan ui_scale prolazi netaknut", abs(app._ui_scale - 1.25) < 1e-9)
check("ispravan font_size prolazi netaknut", app._default_font_size == 15)
check("ispravne dimenzije prolaze netaknute",
      app._default_note_width == 480 and app._default_note_height == 320)
check("ispravan interval prolazi netaknut", app._backup_interval_minutes == 60)

print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
