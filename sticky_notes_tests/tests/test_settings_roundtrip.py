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

# Ne-defaultne vrijednosti za SVAKI kljuc koji _save_backup_settings zapisuje.
NONDEFAULT = {
    "_backup_interval_minutes": 30,
    "_default_font_family": "Serif",
    "_default_font_size": 17,
    "_autostart_enabled": False,
    "_ui_scale": 1.3,
    "_hotkey_enabled": False,
    "_hotkey_binding": "<Super>k",
    "_hotkey_clip_enabled": False,
    "_hotkey_clip_binding": "<Super><Shift>k",
    "_hotkey_search_enabled": False,
    "_hotkey_search_binding": "<Super><Shift>j",
    "_language": "hr",
    # True, a NE False kako je plan pisao: app-blok iz boilerplatea gasi oba
    # snapa odmah nakon gradnje, pa bi False ovdje bio JEDNAK zatecenom stanju i
    # round-trip za ta dva kljuca ne bi mjerio nista. (Default u kodu jest True.)
    "_snap_to_grid": True,
    "_snap_to_notes": True,
    "_snap_size": True,
    "_grid_size": 35,
    "_tray_scroll_enabled": False,
    "_default_note_width": 500,
    "_default_note_height": 350,
    "_note_opacity": 80,
    "_auto_contrast": False,
    "_clean_mode": True,
    "_code_blocks": True,
    "_note_border": "auto",
    "_theme_mode": "auto",
    "_theme_dark_start": "21:30",
    "_theme_dark_end": "06:15",
}
defaults = {k: getattr(app, k) for k in NONDEFAULT}
check("test koristi ne-defaultne vrijednosti za SVE kljuceve",
      all(NONDEFAULT[k] != defaults[k] for k in NONDEFAULT))

for k, v in NONDEFAULT.items():
    setattr(app, k, v)
app._save_backup_settings()

# vrati na defaulte pa ucitaj s diska — sve se mora vratiti na NONDEFAULT
for k, v in defaults.items():
    setattr(app, k, v)
app._load_backup_settings()
for k, v in NONDEFAULT.items():
    check(f"round-trip {k}", getattr(app, k) == v)

# ── save cuva TUDJE kljuceve u settings.json (append, ne prepis) ─────────────
raw = json.load(open(SETTINGS_FILE, encoding="utf-8"))
raw["buduci_nepoznati_kljuc"] = 42
json.dump(raw, open(SETTINGS_FILE, "w", encoding="utf-8"))
# dokazi da je kljuc STVARNO u datoteci PRIJE save-a, inace sljedeca provjera
# ne dokazuje nista (mogla bi proci i da save prepise citavu datoteku)
raw_before = json.load(open(SETTINGS_FILE, encoding="utf-8"))
check("nepoznati kljuc doista upisan prije save", raw_before.get("buduci_nepoznati_kljuc") == 42)
app._save_backup_settings()
raw2 = json.load(open(SETTINGS_FILE, encoding="utf-8"))
check("nepoznati kljuc prezivi save", raw2.get("buduci_nepoznati_kljuc") == 42)

# ── stari bool note_border migrira ───────────────────────────────────────────
raw2["note_border"] = True
json.dump(raw2, open(SETTINGS_FILE, "w", encoding="utf-8"))
app._load_backup_settings()
check("note_border bool True -> 'always'", app._note_border == "always")

# ── pokvaren settings.json ne rusi load ──────────────────────────────────────
# _note_border mora biti NE-DEFAULTNA vrijednost prije ovog poziva: default je
# "off", pa bi provjera "ostane off" trivijalno prosla i na kodu koji pri
# iznimci tiho resetira sve na defaulte (a ne samo na kodu koji doista ne
# dira stanje). "always" nije default, pa provjera stvarno razlikuje "load
# nista nije dirao" od "load je resetirao na default".
open(SETTINGS_FILE, "w").write("{ovo nije json")
app._note_border = "always"
app._load_backup_settings()                    # ne smije baciti iznimku
check("pokvaren settings.json: load prezivi, vrijednost ostane", app._note_border == "always")

print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
