"""Guard: a reminder on an ARCHIVED note (user decision 2026-11-21).

Before: the scheduler only looks at active notes, so an archived note's reminder
waited silently and, if its time had passed, FIRED the moment the note was
restored from the archive — a stale alarm for something put away on purpose.
Agreed behaviour:
- while archived, the reminder never fires;
- restored BEFORE its time → kept, fires normally;
- restored AFTER its time → dropped (never fires, bell hidden, saved as None);
- an ACTIVE note whose time passed while the app was closed still fires
  (different case — nothing was put away).
Same rule for a note restored from the TRASH (user, same day).
"""
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

import sticky_notes.reminders as rem

# Utisaj zvuk i presretni notifikacije (bez daemona; brojimo pozive).
rem._play_alarm_sound = lambda: None
sent = []
app._reminders._notifier.send = lambda *a, **k: sent.append(a) or None

note = app.create_new_note()
note.text_edit.setPlainText("nazovi zubara")

# ── set_reminder: persist + bell ─────────────────────────────────────────────
t_future = time.time() + 3600
note.set_reminder(t_future)

def archived(text, when):
    n = app.create_new_note(); n.text_edit.setPlainText(text); n.set_reminder(when)
    nid = n.note_id
    check(f"{text}: archived", app.archive_note(nid))
    return nid, next(d for d in app.archived_notes if d["id"] == nid)

# ── while archived: never fires ──────────────────────────────────────────────
nid, data = archived("istekao u arhivi", time.time() - 60)
k = len(sent); app._reminders._tick()
check("archived + past: nothing fired", len(sent) == k)
check("archived: the reminder is kept in the archive data", data.get("reminder") is not None)

# ── restored AFTER its time → dropped, never fires ───────────────────────────
check("restored (past)", app.unarchive_note(data))
n = app.notes[nid]
check("restored after its time: reminder dropped", n._reminder is None)
check("restored after its time: no bell", n.btn_bell.isVisibleTo(n) is False)
app._do_save()                            # what the restore itself left (before any tick)
saved = {d["id"]: d for d in json.load(open(os.path.join(_SB, ".local", "share", "sticky_notes", "notes.json")))}
check("restored after its time: saved without a reminder", saved[nid].get("reminder") is None)
k = len(sent); app._reminders._tick()
check("restored after its time: does NOT fire", len(sent) == k)

# ── restored BEFORE its time → kept, fires when due ──────────────────────────
future = time.time() + 3600
nid2, data2 = archived("buduci u arhivi", future)
check("restored (future)", app.unarchive_note(data2))
n2 = app.notes[nid2]
check("restored before its time: reminder kept", n2._reminder == future)
n2.set_reminder(time.time() - 1)          # its time comes
k = len(sent); app._reminders._tick()
check("restored before its time: fires when due", len(sent) == k + 1)

# ── TRASH: same rule ─────────────────────────────────────────────────────────
def trashed(text, when):
    t = app.create_new_note(); t.text_edit.setPlainText(text); t.set_reminder(when)
    tid = t.note_id; app.move_note_to_trash(tid)
    return tid, next(d for d in app.trash_notes if d["id"] == tid)

tid, tdata = trashed("istekao u smecu", time.time() - 60)
k = len(sent); app._reminders._tick()
check("trash + past: nothing fired", len(sent) == k)
check("restored from trash (past)", app.restore_from_trash(tdata))
t = app.notes[tid]
check("trash, restored after its time: reminder dropped", t._reminder is None)
check("trash, restored after its time: no bell", t.btn_bell.isVisibleTo(t) is False)
k = len(sent); app._reminders._tick()
check("trash, restored after its time: does NOT fire", len(sent) == k)

future = time.time() + 3600
tid2, tdata2 = trashed("buduci u smecu", future)
check("restored from trash (future)", app.restore_from_trash(tdata2))
check("trash, restored before its time: reminder kept", app.notes[tid2]._reminder == future)

# ── an ACTIVE note past due (app was closed) still fires ─────────────────────
n3 = app.create_new_note(); n3.text_edit.setPlainText("aktivna"); n3.set_reminder(time.time() - 60)
k = len(sent); app._reminders._tick()
check("active + past: still fires", len(sent) == k + 1)

print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
