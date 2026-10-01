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

from sticky_notes.app import StickyNotesApp
from sticky_notes import app_storage as st
app = StickyNotesApp(sys.argv[:1])
app._snap_to_grid = app._snap_to_notes = app._snap_size = False
for e in list(app.notes.values()):
    e.hide(); e.deleteLater()
app.notes.clear()

def set_gen_mtime(tag, epoch):
    for prefix, _s in st._BACKUP_MEMBERS:
        p = os.path.join(st.BACKUP_DIR, f"{prefix}-{tag}.bak")
        if os.path.exists(p):
            os.utime(p, (epoch, epoch))

def notes_count(path):
    try:
        return len(json.load(open(path, encoding="utf-8")))
    except Exception:
        return -1

def write_notes_json():
    json.dump([n.get_data() for n in app.notes.values()],
              open(st.DATA_FILE, "w", encoding="utf-8"), ensure_ascii=False)

A = app.create_new_note(); B = app.create_new_note()
write_notes_json()                                    # notes.json = 2 notes

# ── Section 1: new generation, rotation keeps 5, filenames are .bak ────────────
shutil.rmtree(st.BACKUP_DIR, ignore_errors=True)
base = time.time() - 10000
for i in range(7):
    app._new_backup_generation(tag=f"g{i}")
    set_gen_mtime(f"g{i}", base + i)                  # increasing mtime → g6 newest
gens = app.list_backups()
check("keeps only 5 (MAX_BACKUP_GENERATIONS)", len(gens) == 5)
check("newest-first by mtime", [g["tag"] for g in gens] == ["g6", "g5", "g4", "g3", "g2"])
check("oldest two pruned", not any(g["tag"] in ("g0", "g1") for g in gens))
check("files use .bak extension", gens[0]["files"]["notes"].endswith("notes-g6.bak"))
check("in the backups/ folder", os.path.dirname(gens[0]["files"]["notes"]).endswith("/backups"))
check("every generation has all three members (empty if absent)",
      set(gens[0]["files"].keys()) == {"notes", "archived", "closed"})
check("an absent source is backed up as an empty list",
      notes_count(gens[0]["files"]["archived"]) == 0)

# ── Section 2: daily auto REFRESHES the newest (no new gen), only after 24h ────
shutil.rmtree(st.BACKUP_DIR, ignore_errors=True)
app._new_backup_generation(tag="d1")                  # snapshot of 2-note state
set_gen_mtime("d1", time.time())                      # fresh
app._maybe_backup()
check("maybe_backup skips while newest < 24h", len(app.list_backups()) == 1)

C = app.create_new_note()                             # in-memory now 3 notes
write_notes_json()                                    # notes.json = 3 notes (no _do_save → no auto)
set_gen_mtime("d1", time.time() - 2 * 86400)          # make newest stale
app._maybe_backup()
gens = app.list_backups()
check("daily refresh does NOT add a generation", len(gens) == 1)
check("daily refresh updates the newest to current state (3 notes)",
      notes_count(gens[0]["files"]["notes"]) == 3)

# ── Section 3: interval / "Backup Now" (_force_backup) creates a NEW generation ─
shutil.rmtree(st.BACKUP_DIR, ignore_errors=True)
app._new_backup_generation(tag="x1"); set_gen_mtime("x1", time.time() - 100)
before = len(app.list_backups())
app._force_backup()                                   # new generation
check("_force_backup adds a new generation", len(app.list_backups()) == before + 1)

# ── Section 4: restore REPLACES current with the chosen generation ─────────────
shutil.rmtree(st.BACKUP_DIR, ignore_errors=True)
write_notes_json()                                    # notes.json = current (3 notes)
app._new_backup_generation(tag="good")
n_good = len(app.notes)
victim_id = next(iter(app.notes))
v = app.notes.pop(victim_id); v.hide(); v.deleteLater()
write_notes_json()                                    # notes.json = 2 notes
check("state mutated", len(app.notes) == n_good - 1)
check("restore returns True", app.restore_backup("good") is True)
check("restore REPLACED back to the good count", len(app.notes) == n_good)
check("restore of unknown tag returns False", app.restore_backup("nope") is False)

# ── Section 5: corruption CASCADE — newest bad → fall to older valid ───────────
shutil.rmtree(st.BACKUP_DIR, ignore_errors=True)
write_notes_json()
cur = len(app.notes)
app._new_backup_generation(tag="older"); set_gen_mtime("older", time.time() - 1000)   # valid
app._new_backup_generation(tag="newer"); set_gen_mtime("newer", time.time() - 10)     # will corrupt
open(st.DATA_FILE, "w").write("{ broken")                                             # corrupt live file
open(os.path.join(st.BACKUP_DIR, "notes-newer.bak"), "w").write("broken too")         # corrupt newest bak
app._storage_alerts = []
data, ok = app._read_json_list(st.DATA_FILE, "notes")
check("cascade: reports recovery (ok False)", ok is False)
check("cascade: recovered from the older VALID backup", len(data) == cur)
check("cascade: queued a user alert", len(app._storage_alerts) >= 1)

# corrupt the older one too → all backups exhausted → empty
open(st.DATA_FILE, "w").write("still broken")
open(os.path.join(st.BACKUP_DIR, "notes-older.bak"), "w").write("broken as well")
data2, ok2 = app._read_json_list(st.DATA_FILE, "notes")
check("cascade exhausted → empty list, ok False", data2 == [] and ok2 is False)

# ── Section 6: one-time migration of a legacy <file>.bak into the folder ───────
shutil.rmtree(st.BACKUP_DIR, ignore_errors=True)
json.dump([{"id": "1", "content": "legacy"}], open(st.DATA_FILE + ".bak", "w", encoding="utf-8"))
app._migrate_old_bak()
gens = app.list_backups()
check("migrate: legacy .bak folded into a FULL generation (all three)",
      len(gens) == 1 and set(gens[0]["files"].keys()) == {"notes", "archived", "closed"})
check("migrate: legacy notes.json.bak removed", not os.path.exists(st.DATA_FILE + ".bak"))
app._migrate_old_bak()
check("migrate is idempotent (no-op second time)", len(app.list_backups()) == 1)

print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
