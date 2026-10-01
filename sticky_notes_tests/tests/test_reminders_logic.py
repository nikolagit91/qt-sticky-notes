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
check("reminder u get_data", note.get_data()["reminder"] == t_future)
check("zvonce vidljivo dok reminder postoji", note.btn_bell.isVisibleTo(note) is True)

# ── buduci reminder se NE okida ──────────────────────────────────────────────
app._reminders._tick()
check("buduci: nista poslano", len(sent) == 0)
check("buduci: reminder ostaje", note._reminder == t_future)

# ── dospio reminder se okine TOCNO JEDNOM i potrosi se ───────────────────────
note.set_reminder(time.time() - 5)
app._reminders._tick()
check("dospio: notifikacija poslana", len(sent) == 1)
check("dospio: reminder POTROSEN (None)", note._reminder is None)
check("dospio: zvonce sakriveno", note.btn_bell.isVisibleTo(note) is False)
app._reminders._tick()
check("drugi tick: NEMA ponovnog okidanja", len(sent) == 1)

# ── dospio reminder OTKRIVA skrivenu notu ────────────────────────────────────
note.set_hidden(True)
# dokazi da je nota STVARNO skrivena prije okidanja, inace sljedeca provjera ne
# dokazuje nista (mogla bi proci i na kodu koji nikad ne postavi _hidden)
check("nota stvarno skrivena prije okidanja", note._hidden is True)
note.set_reminder(time.time() - 5)
app._reminders._tick()
check("okidanje skida hidden flag", note._hidden is False)

# ── snooze pomice ~10 min ────────────────────────────────────────────────────
before = time.time()
app._reminders._on_action(note, "snooze")
check("snooze postavlja novi reminder", note._reminder is not None)
check("snooze je ~+600 s", abs(note._reminder - (before + rem._SNOOZE_SECONDS)) < 5)
# Vrijednost se mora usporediti s onom PRIJE poziva. "is not None" je ovdje
# vec bilo istinito od snoozea iznad, pa je tvrdnja mjerila zateceno stanje i
# prolazila bi i da nepoznata akcija postavi neki drugi reminder (izmjereno).
_prev = note._reminder
app._reminders._on_action(note, "nesto")
check("nepoznata akcija ne dira reminder", note._reminder == _prev)

print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
