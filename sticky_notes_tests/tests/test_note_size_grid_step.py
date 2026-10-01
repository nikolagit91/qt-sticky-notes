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

from PyQt6.QtWidgets import QMessageBox, QSpinBox, QCheckBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
QMessageBox.warning     = staticmethod(lambda *a, **k: None)
QMessageBox.exec        = lambda self, *a, **k: QMessageBox.StandardButton.Ok

from sticky_notes.app import StickyNotesApp
app = StickyNotesApp(sys.argv[:1])
app._snap_to_grid = app._snap_to_notes = False
for e in list(app.notes.values()):
    e.hide(); e.deleteLater()
app.notes.clear()

# poznato polazno stanje: snap size ON, grid 20, default 440x300 (oba visekratnici 20)
app._snap_size = True
app._grid_size = 20
app._default_note_width = 440
app._default_note_height = 300

app.show_settings()
dlg = [w for w in app.topLevelWidgets() if w.isVisible() and w.findChildren(QSpinBox)][-1]
spins = dlg.findChildren(QSpinBox)
width_spin  = [s for s in spins if s.minimum() == 240 and s.maximum() == 1200][0]
height_spin = [s for s in spins if s.minimum() == 168 and s.maximum() == 1000][0]
grid_spin   = [s for s in spins if s.minimum() == 5   and s.maximum() == 100][0]
snap_chk    = [c for c in dlg.findChildren(QCheckBox) if "Snap size" in c.text()][0]

# ── snap ON, grid 20: korak = grid, vrijednosti visekratnici ─────────────────
check("snap ON: width korak = grid (20)", width_spin.singleStep() == 20)
check("snap ON: height korak = grid (20)", height_spin.singleStep() == 20)
check("snap ON: width je visekratnik grida", width_spin.value() % 20 == 0)
check("snap ON: height je visekratnik grida", height_spin.value() % 20 == 0)

# ── strelica GORE dodaje tocno grid (ostaje visekratnik) ─────────────────────
before = width_spin.value()
width_spin.stepBy(1)
check("strelica gore doda grid (440 -> 460)", width_spin.value() == before + 20)
check("nakon strelice i dalje visekratnik", width_spin.value() % 20 == 0)
width_spin.stepBy(-1)   # vrati

# ── promjena grida na 30: korak prati, vrijednost se PRE-snapa ────────────────
grid_spin.setValue(30)
check("grid 30: width korak = 30", width_spin.singleStep() == 30)
check("grid 30: width re-snapan na visekratnik 30 (440 -> 450)", width_spin.value() == 450)
check("grid 30: height ostao visekratnik 30 (300)", height_spin.value() % 30 == 0)

# ── snap OFF: korak natrag na 1 (slobodno) ───────────────────────────────────
snap_chk.setChecked(False)
check("snap OFF: width korak = 1", width_spin.singleStep() == 1)
check("snap OFF: height korak = 1", height_spin.singleStep() == 1)
# pozitivna polovica: sad se MOZE dobiti ne-visekratnik
width_spin.setValue(455)
width_spin.stepBy(1)
check("snap OFF: strelica doda 1 (455 -> 456, ne-visekratnik dozvoljen)",
      width_spin.value() == 456)

# ── snap natrag ON: korak opet grid, vrijednost se snapa ─────────────────────
snap_chk.setChecked(True)
check("snap ON opet: korak = grid (30)", width_spin.singleStep() == 30)
check("snap ON opet: 456 snapan na najblizi visekratnik 30 (450)",
      width_spin.value() == 450)

print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
