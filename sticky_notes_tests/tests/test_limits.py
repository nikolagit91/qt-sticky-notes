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

import sticky_notes.app as appmod
import sticky_notes.app_storage as stmod

# Male vrijednosti da test bude brz; patch na modulima koji su ih importali.
appmod.ACTIVE_LIMIT = 3
appmod.TRASH_LIMIT = 2
appmod.ARCHIVE_LIMIT = 1
stmod.ACTIVE_LIMIT = 3

# ── Active hard-stop ─────────────────────────────────────────────────────────
n1 = app.create_new_note(); n2 = app.create_new_note(); n3 = app.create_new_note()
check("tri note stanu", len(app.notes) == 3)
n4 = app.create_new_note()
check("cetvrta ODBIJENA (vraca None)", n4 is None)
check("broj nota nepromijenjen", len(app.notes) == 3)

# ── Trash FIFO: najstarija ispada preko capa ─────────────────────────────────
id1, id2, id3 = n1.note_id, n2.note_id, n3.note_id
app.move_note_to_trash(id1)
app.move_note_to_trash(id2)
app.move_note_to_trash(id3)
check("trash drzi tocno TRASH_LIMIT", len(app.trash_notes) == 2)
tids = [d["id"] for d in app.trash_notes]
check("najnovija je prva", tids[0] == id3)
check("najstarija (id1) EVICTANA, novije prezivjele", id1 not in tids and id2 in tids)

# ── restore odbijen na punom Active ──────────────────────────────────────────
a1 = app.create_new_note(); a2 = app.create_new_note(); a3 = app.create_new_note()
check("active opet pun", len(app.notes) == 3)
check("restore_from_trash na punom Active vraca False", app.restore_from_trash(app.trash_notes[0]) is False)
check("trash NEOKRNJEN nakon odbijenog restorea", len(app.trash_notes) == 2)

# ── Archive hard-stop ────────────────────────────────────────────────────────
check("prva arhiva prolazi", app.archive_note(a1.note_id) is True)
check("archived lista ima 1", len(app.archived_notes) == 1)
check("druga arhiva ODBIJENA (limit 1)", app.archive_note(a2.note_id) is False)
check("odbijena nota OSTALA aktivna", a2.note_id in app.notes)

# ── unarchive odbijen na punom Active ────────────────────────────────────────
extra = app.create_new_note()          # popuni treci slot natrag
check("active pun prije unarchive", len(app.notes) == 3)
check("unarchive na punom Active vraca False", app.unarchive_note(app.archived_notes[0]) is False)
check("archive NEOKRNJEN", len(app.archived_notes) == 1)

# ── Pozitivna polovica (nedostaje u briefu — dodano jer negativne tvrdnje iznad
#    prolaze i na kodu koji restore/unarchive uvijek odbija): isti pozivi moraju
#    USPJETI kad Active NIJE pun. Prvo oslobodi jedan Active slot pa dokazi da
#    restore_from_trash stvarno vraca notu i skida je iz trasha. ───────────────
app.move_note_to_trash(extra.note_id)
check("active ima mjesta nakon trashanja extra note", len(app.notes) == 2)
restore_target = app.trash_notes[0]      # najnovije trashano == extra
restore_id = restore_target["id"]
check("restore_from_trash na NEPUNOM Active vraca True (pozitivna polovica)",
      app.restore_from_trash(restore_target) is True)
check("active naraso natrag na 3", len(app.notes) == 3)
check("restorirana nota je u Active", restore_id in app.notes)
check("restorirana nota SKINUTA s trasha",
      restore_id not in [d["id"] for d in app.trash_notes])

# Isto za unarchive_note: oslobodi slot pa dokazi da uspije kad Active NIJE pun.
app.move_note_to_trash(a2.note_id)
check("active ima mjesta nakon trashanja a2", len(app.notes) == 2)
unarchive_target = app.archived_notes[0]  # jos uvijek a1 (jedino sto je ikad arhivirano)
unarchive_id = unarchive_target["id"]
check("unarchive_note na NEPUNOM Active vraca True (pozitivna polovica)",
      app.unarchive_note(unarchive_target) is True)
check("active naraso natrag na 3", len(app.notes) == 3)
check("unarchivirana nota je u Active", unarchive_id in app.notes)
check("archive lista ISPRAZNJENA", len(app.archived_notes) == 0)

print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
