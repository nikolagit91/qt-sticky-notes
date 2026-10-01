"""Otkljucavanje note ne smije otvoriti toolbar koji nitko nije trazio.

Dva buga s istim korijenom (_refresh_lock_ui je vracao traku bezuvjetno):
  1) clean mode, chrome skriven: Ctrl+L lock pa unlock spustio bi traku ispod
     skrivenog headera, gdje visi dok se ne odradi pun hover ciklus.
  2) bilo koji mod: ako je korisnik RUCNO sakrio traku, lock+unlock bi je
     uskrsnuo unatoc _toolbar_pref=False.

Pravilo je sad isto kao u _reveal_chrome: traka se vraca samo ako je chrome
prikazan I korisnik je zeli.
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

app = StickyNotesApp(sys.argv[:1])
app._snap_to_grid = app._snap_to_notes = app._snap_size = False
for e in list(app.notes.values()):
    e.hide(); e.deleteLater()
app.notes.clear()

# ── 1) CLEAN MODE, chrome skriven — prijavljeni bug ──────────────────────────
app._clean_mode = True
n = app.create_new_note()          # __init__ primijeni clean mode iz app-a
check("clean mode: nota krece sa skrivenim chromeom",
      n._chrome_revealed is False and n._toolbar_visible is False)

n.toggle_lock()                    # Ctrl+L — zakljucaj
check("lock ne otvara nista dok je chrome skriven", n._toolbar_visible is False)

n.toggle_lock()                    # Ctrl+L — otkljucaj
check("unlock NE spusta toolbar dok je chrome skriven", n._toolbar_visible is False)
check("unlock ne otkriva chrome sam od sebe", n._chrome_revealed is False)
check("korisnikova preferenca trake netaknuta", n._toolbar_pref is True)

# ── 1b) CLEAN MODE, chrome OTKRIVEN — pozitivna polovica ─────────────────────
n._reveal_chrome()
check("reveal otvara chrome i traku",
      n._chrome_revealed is True and n._toolbar_visible is True)
n.toggle_lock()
check("lock na otkrivenom chromeu SAKRIJE traku (locked=nema sto formatirati)",
      n._toolbar_visible is False)
n.toggle_lock()
check("unlock na otkrivenom chromeu VRACA traku", n._toolbar_visible is True)

# ── 2) BEZ clean modea, korisnik rucno sakrio traku ──────────────────────────
app._clean_mode = False
n2 = app.create_new_note()
check("obicna nota: traka vidljiva i zeljena",
      n2._toolbar_visible is True and n2._toolbar_pref is True)

n2._toggle_toolbar()               # rucni klik na dugme za traku
check("rucno skrivanje spusta i preferencu",
      n2._toolbar_visible is False and n2._toolbar_pref is False)

n2.toggle_lock(); n2.toggle_lock()
check("lock+unlock NE uskrsava rucno sakrivenu traku", n2._toolbar_visible is False)
check("preferenca i dalje False", n2._toolbar_pref is False)

# ── 2b) BEZ clean modea, normalan slucaj — pozitivna polovica ────────────────
n3 = app.create_new_note()
check("treca nota: traka vidljiva", n3._toolbar_visible is True)
n3.toggle_lock()
check("lock sakriva traku", n3._toolbar_visible is False)
n3.toggle_lock()
check("unlock vraca traku (korisnik je zeli)", n3._toolbar_visible is True)

print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
