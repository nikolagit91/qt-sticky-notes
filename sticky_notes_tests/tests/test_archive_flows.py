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

from sticky_notes.config import ARCHIVE_FILE, TRASH_FILE

def fcount(path):
    try:
        return len(json.load(open(path, encoding="utf-8")))
    except Exception:
        return -1

n = app.create_new_note()
n.text_edit.setPlainText("arhivska proba")
nid = n.note_id

# ── archive: makne widget, doda dict, PERSISTIRA na disk ─────────────────────
check("archive_note vraca True", app.archive_note(nid) is True)
check("nota vise NIJE aktivna", nid not in app.notes)
check("dict u archived_notes s ocuvanim id-jem", app.archived_notes[0]["id"] == nid)
check("archived.json na disku ima 1 zapis", fcount(ARCHIVE_FILE) == 1)

# ── unarchive: obnovi widget, ocisti hidden, makne iz arhive ─────────────────
data = dict(app.archived_notes[0]); data["hidden"] = True    # i skrivena se vraca vidljiva
app.archived_notes[0] = data
check("unarchive vraca True", app.unarchive_note(data) is True)
check("nota OPET aktivna, isti id", nid in app.notes)
check("sadrzaj prezivio round-trip", "arhivska proba" in app.notes[nid].text_edit.toPlainText())
check("hidden ocisten pri povratku", app.notes[nid]._hidden is False)
check("archive prazna (memorija i disk)", len(app.archived_notes) == 0 and fcount(ARCHIVE_FILE) == 0)

# ── archive -> trash direktno ────────────────────────────────────────────────
app.archive_note(nid)
d = app.archived_notes[0]
app.archive_to_trash(d)
check("archive_to_trash: maknuto iz arhive", len(app.archived_notes) == 0)
# Trash ovdje ima tocno jednu stavku, pa ovo NE tvrdi nista o redoslijedu —
# samo da je bas ta nota zavrsila u njemu. Redoslijed pokriva test_limits.py.
check("archive_to_trash: bas ta nota je u trashu", app.trash_notes[0]["id"] == nid)
check("trash persistiran", fcount(TRASH_FILE) == 1)

# ── delete_from_trash / empty_trash ──────────────────────────────────────────
other = app.create_new_note(); app.move_note_to_trash(other.note_id)
check("dva u trashu", len(app.trash_notes) == 2)
app.delete_from_trash({"id": nid})
check("delete_from_trash makne tocno taj", [t["id"] for t in app.trash_notes] == [other.note_id])
# Pozitivna polovica (nedostaje u briefu — dodano jer "empty_trash prazni... disk"
# ispod bi prosao trivijalno i na kodu koji nikad nista ne zapise): dokazi da
# TRASH_FILE stvarno ima 1 zapis NEPOSREDNO PRIJE nego sto ga empty_trash isprazni.
check("trash.json na disku ima 1 zapis prije praznjenja", fcount(TRASH_FILE) == 1)
app.empty_trash()
check("empty_trash prazni memoriju I disk", len(app.trash_notes) == 0 and fcount(TRASH_FILE) == 0)

print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
