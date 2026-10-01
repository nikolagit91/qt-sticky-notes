"""x11 pozivi: redoslijed, argumenti, i kada se NE pozivaju (review prolaz 5).

Offscreen ne moze dokazati slaganje prozora, ali moze dokazati LOGIKU poziva.
Kljucna invarijanta koju ovaj test cuva:

  set_skip_taskbar pise _NET_WM_STATE u REPLACE modu -> brise _NET_WM_STATE_ABOVE,
  tj. tiho odpina notu. Zato _apply_pin_above MORA doci nakon njega u svakom
  putu. Ako netko ikad zamijeni redoslijed, ovaj test pada.
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
from PyQt6.QtCore import QEventLoop, QTimer
from sticky_notes.app import StickyNotesApp
from sticky_notes import x11

app = StickyNotesApp(sys.argv[:1])
app._snap_to_grid = app._snap_to_notes = app._snap_size = False
for e in list(app.notes.values()):
    e.hide(); e.deleteLater()
app.notes.clear()

log = []
x11.detach_window_group = lambda w: log.append("detach") or True
x11.set_skip_taskbar    = lambda w: log.append("skip_taskbar") or True
x11.set_above           = lambda w, e: log.append(("set_above", e)) or True

def pump(ms=120):
    loop = QEventLoop(); QTimer.singleShot(ms, loop.quit); loop.exec()

n = app.create_new_note()
pump()          # pusti odgodjene pozive iz kreiranja da se isprazne

# ── redoslijed: skip_taskbar uvijek prije set_above ─────────────────────────
log.clear()
n._reassert_window_state(spontaneous=False)
pump()
triplets = [log[i:i+3] for i in range(0, len(log) - 2, 3)]
check("re-assert radi u trojkama (detach, skip_taskbar, set_above)",
      len(triplets) >= 2 and all(
          t[0] == "detach" and t[1] == "skip_taskbar"
          and isinstance(t[2], tuple) and t[2][0] == "set_above" for t in triplets))
skip_i = [i for i, e in enumerate(log) if e == "skip_taskbar"]
abv_i  = [i for i, e in enumerate(log) if isinstance(e, tuple)]
check("SVAKI skip_taskbar ima set_above poslije sebe (pin se obnavlja)",
      all(any(a > s for a in abv_i) for s in skip_i))

# ── spontani show (promjena workspacea) ne radi nista ───────────────────────
log.clear()
n._reassert_window_state(spontaneous=True)
pump()
check("spontani show ne poziva nijednu x11 operaciju", len(log) == 0)
# pozitivna polovica: nespontani JE poziva
log.clear()
n._reassert_window_state(spontaneous=False)
pump()
check("nespontani show ih poziva (pozitivna polovica)", len(log) > 0)

# ── pin salje ispravan argument ─────────────────────────────────────────────
log.clear(); n._toggle_pin(); pump()
check("pin salje set_above(True)",
      ("set_above", True) in [e for e in log if isinstance(e, tuple)])
log.clear(); n._toggle_pin(); pump()
check("unpin salje set_above(False)",
      ("set_above", False) in [e for e in log if isinstance(e, tuple)])

# ── podsjetnik: pinana nota ZADRZI ABOVE, nepinana ga spusti ────────────────
n._pinned = True
log.clear(); n._surface_for_reminder(); pump(1700)
check("podsjetnik na PINANOJ noti ne skida ABOVE",
      ("set_above", False) not in [e for e in log if isinstance(e, tuple)])
n._pinned = False
log.clear(); n._surface_for_reminder(); pump(1700)
check("podsjetnik na nepinanoj noti spusti ABOVE (pozitivna polovica)",
      ("set_above", False) in [e for e in log if isinstance(e, tuple)])

# ── raise_visible_notes filtrira skrivene i pinane ─────────────────────────
for e in list(app.notes.values()):
    e.hide(); e.deleteLater()
app.notes.clear()
vid = app.create_new_note()
skr = app.create_new_note(); skr.set_hidden(True)
pin = app.create_new_note(); pin._pinned = True
dignute = []
app._bring_to_front = lambda w: dignute.append(w)
app.raise_visible_notes()
check("raise dize vidljivu nepinanu", vid in dignute)
check("raise preskace skrivenu", skr not in dignute)
check("raise preskace pinanu", pin not in dignute)

print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
