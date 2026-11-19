"""Guard: text with NO colour of its own is exported in the note's INK, as on
screen — not Qt's default black.

Before (2026-11-19, user report with PDFs): on screen such text follows the
editor's QSS (`color: <ink>`), but export works on a CLONED document, which has
no stylesheet. PDF drew it with doc.drawContents → the default palette's black,
so on a dark note's dark page it was black on near-black (the user's own pick
of black, drawn as its light twin, stayed readable — the opposite of what you'd
expect). ODT wrote it with no colour → black, so default (#333333 on screen) and
picked black (#000000) looked the same.
"""
import sys, os, tempfile, atexit, shutil, subprocess, zipfile, re
_SB = tempfile.mkdtemp(prefix="sn_edi_")
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

from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtWidgets import QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from PyQt6.QtGui import QColor, QTextCharFormat, QImage, QPainter, QFont
from sticky_notes.app import StickyNotesApp
from sticky_notes.theme import note_ink
from sticky_notes import export

app = StickyNotesApp(sys.argv[:1])
for e in list(app.notes.values()):
    e.hide(); e.deleteLater()
app.notes.clear()
n = app.create_new_note(); te = n.text_edit; doc = te.document()
n.show(); app.processEvents()
DARK, LIGHT = "#2b2b30", "#fff59d"

def fill(html):
    te.setCurrentCharFormat(QTextCharFormat())
    te.setHtml(html); app.processEvents()

def most_opaque_ink(img, x0, x1, y0, y1, bg):
    """The glyph pixel farthest from the page colour inside the box."""
    bgc = QColor(bg); best, far = None, -1
    for y in range(y0, y1):
        for x in range(x0, x1):
            c = img.pixelColor(x, y)
            d = abs(c.red() - bgc.red()) + abs(c.green() - bgc.green()) + abs(c.blue() - bgc.blue())
            if d > far:
                far, best = d, c
    return best

# ── the PDF text painter uses the note ink for uncoloured text ────────────────
helper = getattr(export, "_draw_text", None)
check("export has a text painter that takes the ink (_draw_text)", callable(helper))
if callable(helper):
    for page, label in ((DARK, "dark"), (LIGHT, "light")):
        fill('<p>MMMMMMMM</p>')
        clone = doc.clone(); clone.setDefaultFont(QFont("DejaVu Sans", 20))
        clone.setTextWidth(400)
        img = QImage(420, 80, QImage.Format.Format_RGB32); img.fill(QColor(page))
        p = QPainter(img)
        helper(clone, p, QRectF(0, 0, 420, 80), note_ink(QColor(page)).text)
        p.end()
        got = most_opaque_ink(img, 0, 300, 0, 60, page)
        want = QColor(note_ink(QColor(page)).text)
        check(f"{label} page: uncoloured text drawn in the note ink {want.name()} (got {got.name()})",
              abs(got.red() - want.red()) <= 12 and abs(got.green() - want.green()) <= 12)

# ── end to end: a real PDF of a dark note (when poppler is installed) ─────────
if shutil.which("pdftoppm"):
    fill('<p>MMMMMMMM</p>')
    pdf = os.path.join(_SB, "d.pdf")
    export.to_pdf(doc, pdf, DARK)
    subprocess.run(["pdftoppm", "-r", "60", "-png", "-singlefile", pdf, os.path.join(_SB, "d")], check=True)
    img = QImage(os.path.join(_SB, "d.png"))
    got = most_opaque_ink(img, 0, img.width() // 2, 0, img.height() // 6, DARK)
    check(f"real PDF of a dark note: uncoloured text is LIGHT (got {got.name()})", got.lightness() > 180)
else:
    print("  (pdftoppm not installed — end-to-end PDF check skipped)")

# ── ODT (always white paper): uncoloured text in the light-note ink ───────────
fill('<p>zadano <span style="color:#000000">crno</span></p>')
odt = os.path.join(_SB, "x.odt"); export.to_odt(doc, odt)
xml = zipfile.ZipFile(odt).read("content.xml").decode().lower()
light_ink = note_ink(QColor(LIGHT)).text.lower()
check(f"ODT: uncoloured text carries the light-note ink {light_ink}", light_ink in xml)
check("ODT: picked black stays black", "#000000" in xml)
fill('<p>vidi <a href="https://example.com">example.com</a></p>')
n._apply_ink()
export.to_odt(doc, odt)
xml = zipfile.ZipFile(odt).read("content.xml").decode().lower()
check("ODT: a link keeps its link colour (not the ink)", "#1a73e8" in xml)
check("ODT: the live note is untouched (uncoloured text still has no colour)",
      doc.begin().begin().fragment().charFormat().foreground().style() == Qt.BrushStyle.NoBrush)

print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
