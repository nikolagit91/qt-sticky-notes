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

from PyQt6.QtWidgets import QComboBox, QTimeEdit
from sticky_notes.i18n import tr, set_language

# ── otvori Settings i nadji kontrole ─────────────────────────────────────────
app.show_settings()
dlg = None; combo = None
for w in app.topLevelWidgets():
    if w.isVisible():
        combos = [c for c in w.findChildren(QComboBox) if c.findData("auto") >= 0]
        if combos:
            dlg = w; combo = combos[0]; break
check("Settings otvoren i theme combo ima stavku 'auto'", dlg is not None)

if dlg is not None:
    times = dlg.findChildren(QTimeEdit)
    check("dva QTimeEdit polja postoje", len(times) >= 2)
    # sched_box je roditelj polja vremena; isHidden() odrazava tocno nas
    # setVisible poziv (za razliku od isVisibleTo, koji offscreen laze jer
    # Appearance sekcija sjedi na neaktivnom tabu — to bi bilo lazno zeleno).
    sched_box = times[0].parent()
    check("u fiksnom modu red vremena SKRIVEN", sched_box.isHidden() is True)
    # prebaci combo na Auto -> red se pokaze, mod se promijeni
    combo.setCurrentIndex(combo.findData("auto"))
    check("combo na auto -> mod auto", app._theme_mode == "auto")
    check("red vremena sada VIDLJIV (pozitivna polovica)", sched_box.isHidden() is False)
    # natrag na fiksni -> red se opet sakrije (druga pozitivna/negativna polovica)
    combo.setCurrentIndex(combo.findData("light"))
    check("povratak na light -> red opet skriven", sched_box.isHidden() is True)

# ── i18n: novi stringovi prevedeni ───────────────────────────────────────────
set_language("hr")
check("hr: Auto", tr("Auto") == "Automatski")
check("hr: Dark from", tr("Dark from") == "Tamna od")
check("hr: until", tr("until") == "do")
set_language("en")

print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
