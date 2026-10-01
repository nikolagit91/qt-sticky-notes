"""Promjena prozirnosti ne smije prolaziti kroz puni _apply_ink (review P-1).

Slajder "Background opacity" salje valueChanged na SVAKI korak vucenja, a
_apply_note_opacity je za svaku notu radio pun _apply_color -> _apply_ink:
~15 setStyleSheet poziva plus tri prolaska znak-po-znak kroz cijeli dokument.
Izmjereno na 50 nota: 139 ms po koraku, tj. slajder koji se ne da vuci.

Prozirnost mijenja SAMO alfu. Ink set se bira po luminanciji koja alfu ignorira
(_rel_luminance), a sva ink polja su konstante — pa bi sve to racunalo iste
vrijednosti. Mijenjaju se jedino tri izvedene boje: header, border, grip.

Ovaj test cuva EKVIVALENCIJU: brzi put mora dati identicno stanje kao puni.
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

n = app.create_new_note()
n.text_edit.setPlainText("tekst note\nkupiti mlijeko")

app._note_opacity = 100
n._apply_color()
alfa_prije = n._qcolor_base.alpha()
qss_prije  = n.btn_bold.styleSheet()
edit_prije = n.text_edit.styleSheet()
check("na 100% je nota potpuno neprozirna", alfa_prije == 255)

# ── brzi put: promijeni prozirnost ────────────────────────────────────────
app._note_opacity = 50
app._apply_note_opacity()

check("alfa ispune prati postavku", n._qcolor_base.alpha() == round(50 * 255 / 100))
check("header nosi novu alfu", n._qcolor_header.alpha() == n._qcolor_base.alpha())
check("border nosi novu alfu", n._qcolor_border.alpha() == n._qcolor_base.alpha())
check("grip nosi novu alfu", n._qcolor_grip.alpha() == n._qcolor_base.alpha())

# Stilovi se NE smiju mijenjati — dokaz da ih nije trebalo ni racunati
check("stil toolbar gumba nepromijenjen", n.btn_bold.styleSheet() == qss_prije)
check("stil text edita nepromijenjen", n.text_edit.styleSheet() == edit_prije)

# ── EKVIVALENCIJA: brzi put == puni put ──────────────────────────────────
brzi = (n._qcolor_base.rgba(), n._qcolor_header.rgba(),
        n._qcolor_border.rgba(), n._qcolor_grip.rgba())
n._apply_color()                       # puni put nad istom postavkom
puni = (n._qcolor_base.rgba(), n._qcolor_header.rgba(),
        n._qcolor_border.rgba(), n._qcolor_grip.rgba())
check("brzi put daje IDENTICNE boje kao puni put", brzi == puni)

# ── i dalje radi na tamnoj noti (ink se bira po luminanciji, ne alfi) ────
n._set_color("#2b2b30")
app._note_opacity = 70
app._apply_note_opacity()
brzi_d = (n._qcolor_base.rgba(), n._qcolor_header.rgba(),
          n._qcolor_border.rgba(), n._qcolor_grip.rgba())
n._apply_color()
puni_d = (n._qcolor_base.rgba(), n._qcolor_header.rgba(),
          n._qcolor_border.rgba(), n._qcolor_grip.rgba())
check("ekvivalencija vrijedi i na tamnoj noti", brzi_d == puni_d)

# ── povratak na 100% vraca neprozirnost ─────────────────────────────────
app._note_opacity = 100
app._apply_note_opacity()
check("povratak na 100% vraca punu neprozirnost", n._qcolor_base.alpha() == 255)

print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
