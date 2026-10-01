"""Linkovi: vidljivo odrediste + odbijanje shema koje nemaju sto traziti.

Review prolaz 7, S-2. Zalijepljen HTML s weba moze nositi <a href> ciji se
tekst proizvoljno razlikuje od odredista, a _open_url je predavao BILO STO
xdg-openu bez provjere. Nista u sucelju nije pokazivalo kamo link zapravo vodi.

Dvije mjere:
  1) hover nad linkom pokazuje pravi href (korisnik moze prosuditi)
  2) _open_url pusta samo sheme koje u biljeznici imaju smisla, i odbija
     .desktop datoteke koje xdg-open na GNOME-u IZVRSAVA
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

from sticky_notes import widgets

# ── 1) dopustene sheme se otvaraju ─────────────────────────────────────────
pokrenuto = []
widgets.subprocess.Popen = lambda cmd, **k: pokrenuto.append(cmd)

for dopusten in ("http://example.com", "https://example.com/a?b=1",
                 "file:///home/korisnik/dokument.pdf", "mailto:netko@example.com"):
    pokrenuto.clear()
    widgets._open_url(dopusten)
    check(f"otvara {dopusten.split(':')[0]}:", len(pokrenuto) == 1)

pokrenuto.clear()
widgets._open_url("file:///home/korisnik/Mapa")
check("otvara obicnu lokalnu mapu/datoteku", len(pokrenuto) == 1)

# ── 2) opasne sheme se NE otvaraju ────────────────────────────────────────
for odbijen in ("javascript:alert(1)", "data:text/html;base64,PHNjcmlwdD4=",
                "vbscript:msgbox", "ftp://negdje/x"):
    pokrenuto.clear()
    widgets._open_url(odbijen)
    check(f"odbija {odbijen.split(':')[0]}:", len(pokrenuto) == 0)

# ── 3) .desktop se odbija (xdg-open ga na GNOME-u IZVRSAVA) ───────────────
for izvrsni in ("file:///tmp/zlo.desktop", "file:///home/k/Downloads/x.DESKTOP"):
    pokrenuto.clear()
    widgets._open_url(izvrsni)
    check(f"odbija izvrsni {izvrsni.rsplit('.', 1)[1]}", len(pokrenuto) == 0)

# ── 4) hover pokazuje PRAVI href ──────────────────────────────────────────
from PyQt6.QtWidgets import QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from PyQt6.QtCore import QMimeData, QPoint, Qt, QPointF, QEvent
from PyQt6.QtGui import QMouseEvent
from sticky_notes.app import StickyNotesApp

app = StickyNotesApp(sys.argv[:1])
app._snap_to_grid = app._snap_to_notes = app._snap_size = False
for e in list(app.notes.values()):
    e.hide(); e.deleteLater()
app.notes.clear()
n = app.create_new_note(); te = n.text_edit
te.resize(400, 200)

md = QMimeData()
md.setHtml('<a href="http://pravo-odrediste.example/x">izgleda kao banka.hr</a>')
md.setText("izgleda kao banka.hr")
te.insertFromMimeData(md)

# hover nad prvim znakom linka (gornji lijevi kut teksta)
ev = QMouseEvent(QEvent.Type.MouseMove, QPointF(14.0, 14.0), Qt.MouseButton.NoButton,
                 Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier)
te.mouseMoveEvent(ev)
tip = te.viewport().toolTip()
check("hover nad linkom pokazuje pravi href",
      "pravo-odrediste.example" in tip)

# hover izvan linka cisti tooltip (pozitivna polovica)
ev2 = QMouseEvent(QEvent.Type.MouseMove, QPointF(390.0, 190.0), Qt.MouseButton.NoButton,
                  Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier)
te.mouseMoveEvent(ev2)
check("izvan linka nema tooltipa", te.viewport().toolTip() == "")

print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
