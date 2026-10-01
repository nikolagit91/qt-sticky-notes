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

import uuid
from PyQt6.QtWidgets import QFileDialog, QMessageBox

EXPORT = os.path.join(_SB, "izvoz.json")
QFileDialog.getSaveFileName = staticmethod(lambda *a, **k: (EXPORT, ""))
QFileDialog.getOpenFileName = staticmethod(lambda *a, **k: (EXPORT, ""))

# ── export: fajl nastane i sadrzi note ───────────────────────────────────────
n1 = app.create_new_note(); n1.text_edit.setPlainText("prva")
n2 = app.create_new_note(); n2.text_edit.setPlainText("druga")
app._export_notes(None)
data = json.load(open(EXPORT, encoding="utf-8"))
check("export: JSON lista s 2 note", isinstance(data, list) and len(data) == 2)
check("export: content_type=html i sadrzaj unutra",
      all(d["content_type"] == "html" for d in data) and any("prva" in d["content"] for d in data))
orig_ids = {d["id"] for d in data}

# ── import: svjezi UUID-i, hidden ocisten, geometrija na ekranu ──────────────
data[0]["hidden"] = True
data[0]["geometry"] = [99999, 99999, 300, 200]        # daleko van ekrana
json.dump(data, open(EXPORT, "w", encoding="utf-8"))
before = len(app.notes)
app._import_notes(None)
check("import: broj nota narastao za 2", len(app.notes) == before + 2)
new_ids = set(app.notes.keys()) - {n1.note_id, n2.note_id}
# Skup MORA prvo biti nenula: bez svjezeg UUID-a uvezena stavka prepise
# postojeci unos umjesto da doda novi, new_ids ostane prazan i presjek nize
# prolazi trivijalno (prazan skup se ne sijece ni s cim).
check("import: nastala su tocno 2 NOVA id-ja", len(new_ids) == 2)
check("import: SVJEZI UUID-i (nema kolizije s izvornima)", not (new_ids & orig_ids))
imported = [app.notes[i] for i in new_ids]
check("import: hidden ocisten (note vidljive)", all(not n._hidden for n in imported))
scr = app.primaryScreen().availableGeometry()
check("import: geometrija clampana na ekran",
      all(scr.left() <= n.x() <= scr.right() and scr.top() <= n.y() <= scr.bottom()
          for n in imported))

# ── import: pokvaren fajl ne unosi nista ─────────────────────────────────────
open(EXPORT, "w").write('{"nije": "lista"}')
before = len(app.notes)
app._import_notes(None)
check("import pokvarenog: nista dodano", len(app.notes) == before)
open(EXPORT, "w").write('[{"bez_contenta": 1}]')
app._import_notes(None)
check("import bez 'content' polja: odbijen cijeli fajl", len(app.notes) == before)

# ── import preko kapaciteta: No preskace, Yes uzima koliko stane ─────────────
import sticky_notes.app_storage as stmod
import sticky_notes.app as appmod
appmod.ACTIVE_LIMIT = stmod.ACTIVE_LIMIT = len(app.notes) + 1   # mjesta za tocno 1
json.dump([{"content": "<p>a</p>"}, {"content": "<p>b</p>"}],
          open(EXPORT, "w", encoding="utf-8"))
QMessageBox.exec = lambda self, *a, **k: QMessageBox.StandardButton.No
before = len(app.notes)
app._import_notes(None)
check("preko kapaciteta + No: nista uvezeno", len(app.notes) == before)
QMessageBox.exec = lambda self, *a, **k: QMessageBox.StandardButton.Yes
app._import_notes(None)
check("preko kapaciteta + Yes: uveden tocno 1 (koliko stane)", len(app.notes) == before + 1)

print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
