"""Guard: restart-only settings (UI scale, language) are STAGED, not applied live.
Changing them in Settings updates only a pending value + shows the restart button;
it must NOT mutate the applied value, must NOT save, and must NOT change the active
language. Restart commits (applies + saves); closing and reopening discards.
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

from PyQt6.QtWidgets import QMessageBox, QDialog, QPushButton, QComboBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from sticky_notes.app import StickyNotesApp
from sticky_notes import i18n
from sticky_notes.config import SETTINGS_FILE

app = StickyNotesApp(sys.argv[:1])
for e in list(app.notes.values()):
    e.hide(); e.deleteLater()
app.notes.clear()
app._ui_scale = 1.0
app._language = "en"; i18n.set_language("en")

def settings_dlg():
    return next(w for w in app._open_windows
                if isinstance(w, QDialog) and w.windowTitle() == "Settings" and w.isVisible())

# ── open Settings, bump scale with the "+" button ────────────────────────────
app.show_settings()
dlg = settings_dlg()
plus = next(b for b in dlg.findChildren(QPushButton) if b.text() == "+")
plus.click()   # change_scale(+0.1)

check("scale staged (pending = 1.1)", abs((app._pending_ui_scale or 0) - 1.1) < 1e-9)
check("applied scale unchanged (1.0)", app._ui_scale == 1.0)
check("restart pending flag set", app._pending_restart is True)

# ── change language via the combo ────────────────────────────────────────────
combo = next(c for c in dlg.findChildren(QComboBox)
             if any(c.itemData(i) == "hr" for i in range(c.count())))
hr_idx = next(i for i in range(combo.count()) if combo.itemData(i) == "hr")
combo.setCurrentIndex(hr_idx)

check("language staged (pending = hr)", app._pending_language == "hr")
check("applied language unchanged (en)", app._language == "en")
check("active tr() language NOT switched", i18n.get_language() == "en")

# ── settings.json on disk must NOT carry the staged values ───────────────────
saved = json.load(open(SETTINGS_FILE)) if os.path.exists(SETTINGS_FILE) else {}
check("disk scale not written (still 1.0/absent)", saved.get("ui_scale", 1.0) == 1.0)
check("disk language not written (still en/absent)", saved.get("language", "en") == "en")

# ── close without restart → reopen discards the staged change ────────────────
dlg.accept()
app.show_settings()
check("reopen: pending scale discarded", app._pending_ui_scale is None)
check("reopen: pending language discarded", app._pending_language is None)
check("reopen: restart flag cleared", app._pending_restart is False)
settings_dlg().accept()

# ── Restart commits (apply + save); stub restart() to avoid relaunch ─────────
app.restart = lambda **k: None
app.show_settings()
dlg = settings_dlg()
next(b for b in dlg.findChildren(QPushButton) if b.text() == "+").click()   # scale → 1.1
combo = next(c for c in dlg.findChildren(QComboBox)
             if any(c.itemData(i) == "hr" for i in range(c.count())))
combo.setCurrentIndex(next(i for i in range(combo.count()) if combo.itemData(i) == "hr"))
app._apply_pending_and_restart()

check("restart commits scale (1.1)", abs(app._ui_scale - 1.1) < 1e-9)
check("restart commits language (hr)", app._language == "hr" and i18n.get_language() == "hr")
saved = json.load(open(SETTINGS_FILE))
check("restart saved scale to disk", abs(saved.get("ui_scale", 0) - 1.1) < 1e-9)
check("restart saved language to disk", saved.get("language") == "hr")

print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
