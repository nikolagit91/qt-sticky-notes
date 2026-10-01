"""Deleting a note must NOT re-raise the others (move_note_to_trash /
archive_note dropped the reraise_others machinery)."""
import sys, os, tempfile, atexit, shutil, time, inspect

_SB = tempfile.mkdtemp(prefix="sn_ts_")
atexit.register(lambda: shutil.rmtree(_SB, ignore_errors=True))
os.environ["HOME"] = _SB
os.environ["XDG_CONFIG_HOME"] = os.path.join(_SB, ".config")
os.environ["XDG_DATA_HOME"]   = os.path.join(_SB, ".local", "share")
os.environ.setdefault("XDG_RUNTIME_DIR", _SB)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ.pop("DISPLAY", None); os.environ.pop("WAYLAND_DISPLAY", None)
os.makedirs(os.path.join(_SB, ".local", "share", "sticky_notes"), exist_ok=True)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)

fails = []
def check(name, cond):
    print(f"  {'PASS' if cond else 'FAIL'}   {name}")
    if not cond: fails.append(name)

from sticky_notes.app import StickyNotesApp
from sticky_notes.note import StickyNote
app = StickyNotesApp(sys.argv[:1])
app._snap_to_grid = app._snap_to_notes = app._snap_size = False

def pump(ms=60):
    end = time.monotonic() + ms / 1000.0
    while time.monotonic() < end:
        QApplication.processEvents(); time.sleep(0.005)

# ── deleting a note does NOT re-raise the others ────────────────────────────
raised = []
app._bring_to_front = lambda w: raised.append(w)
n1 = StickyNote(app, "n1", {"id": "n1", "geometry": [10, 10, 200, 150]})
n2 = StickyNote(app, "n2", {"id": "n2", "geometry": [30, 30, 200, 150]})
app.notes["n1"] = n1; app.notes["n2"] = n2
raised.clear()
app.move_note_to_trash("n1")
pump()
check("delete: remaining note NOT re-raised", n2 not in raised)
check("delete: no reraise_others param on move_note_to_trash",
      "reraise_others" not in inspect.signature(app.move_note_to_trash).parameters)
check("delete: no reraise_others param on archive_note",
      "reraise_others" not in inspect.signature(app.archive_note).parameters)
n2.hide(); n2.deleteLater()

print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
