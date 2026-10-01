"""_toolbar_pref smije zapisati SAMO korisnikov izbor (review prolaz 2, S-1).

_set_clean_mode(True) je hvatao pref iz trenutne vidljivosti trake — a ta je
mogla biti spustena PRISILNO (lockom ili prethodnim clean modeom), ne izborom.
Posljedica: pref trajno padne na False i _reveal_chrome vise nikad ne vrati
traku toj noti.

Tri reproducirana slucaja:
  E) zakljucana nota se UCITA dok je clean mode ukljucen
  F) nota se zakljuca, PA se ukljuci clean mode
  A) _set_clean_mode(True) pozvan dvaput zaredom
"""
import sys, os, tempfile, atexit, shutil
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
from sticky_notes.app import StickyNotesApp
from sticky_notes.note import StickyNote

app = StickyNotesApp(sys.argv[:1])
app._snap_to_grid = app._snap_to_notes = app._snap_size = False
for e in list(app.notes.values()):
    e.hide(); e.deleteLater()
app.notes.clear()

# ── E) ucitavanje ZAKLJUCANE note dok je clean mode ON ───────────────────────
app._clean_mode = True
nE = StickyNote(app, "e1", {"id": "e1", "content": "<p>x</p>", "content_type": "html",
                            "locked": True, "geometry": [10, 10, 300, 200]})
app.notes["e1"] = nE
check("E: ucitana zakljucana nota cuva pref=True (lock ga nije pregazio)",
      nE._toolbar_pref is True)
nE.toggle_lock()
nE._reveal_chrome()
check("E: nakon otkljucavanja i hovera traka SE VRACA", nE._toolbar_visible is True)

# ── F) lock, pa ukljucen clean mode ─────────────────────────────────────────
app._clean_mode = False
nF = app.create_new_note()
nF.toggle_lock()                       # lock prisilno spusti traku
check("F: lock spusta traku ali NE dira pref",
      nF._toolbar_visible is False and nF._toolbar_pref is True)
app._clean_mode = True
app._apply_clean_mode()
check("F: ukljucenje clean modea ne gazi pref", nF._toolbar_pref is True)
nF.toggle_lock()
nF._reveal_chrome()
check("F: nakon otkljucavanja i hovera traka SE VRACA", nF._toolbar_visible is True)

# ── A) _set_clean_mode(True) dvaput ─────────────────────────────────────────
app._clean_mode = True
nA = app.create_new_note()
pref1 = nA._toolbar_pref
nA._set_clean_mode(True)
check("A: drugi _set_clean_mode(True) ne mijenja pref", nA._toolbar_pref == pref1)
nA._reveal_chrome()
check("A: traka se i dalje vraca na hover", nA._toolbar_visible is True)

# ── POZITIVNA POLOVICA: korisnikov RUCNI izbor se i dalje postuje ───────────
app._clean_mode = False
nP = app.create_new_note()
nP._toggle_toolbar()                   # rucno sakrio traku
check("P: rucno skrivanje spusta pref", nP._toolbar_pref is False)
app._clean_mode = True
app._apply_clean_mode()
nP._reveal_chrome()
check("P: hover NE vraca traku koju je korisnik sklonio",
      nP._toolbar_visible is False)
nP._toggle_toolbar()                   # rucno je vratio
check("P: rucni povratak dize i pref", nP._toolbar_pref is True)
nP._hide_chrome(); nP._reveal_chrome()
check("P: sada je hover VRACA", nP._toolbar_visible is True)

print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
