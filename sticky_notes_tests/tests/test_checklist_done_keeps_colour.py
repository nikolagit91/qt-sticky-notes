"""Guard: ticking a checklist item keeps the text's OWN colour (only faded), and
unticking restores it at full strength — also after a save/reload, for mixed
colours in one item, through the parent cascade, and across a theme flip.

Bug (2026-10-15): ticking painted the whole item a fixed grey (#9aa0a6),
unticking painted it the note ink — a red item came back black. Qt keeps no
other place for the original colour in the saved HTML (a custom format
property is dropped by toHtml — measured), but an rgba colour round-trips
exactly, so "done" = same RGB, reduced alpha. Legacy grey items (made before
this) still untick to the ink.
"""
import sys, os, tempfile, atexit, shutil
_SB = tempfile.mkdtemp(prefix="sn_dk_")
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
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QTextCursor, QColor, QTextCharFormat
from sticky_notes.app import StickyNotesApp
from sticky_notes.widgets import CHECK_DONE, CHECK_EMPTY
from sticky_notes.theme import note_ink

app = StickyNotesApp(sys.argv[:1])
for e in list(app.notes.values()):
    e.hide(); e.deleteLater()
app.notes.clear()
n = app.create_new_note(); te = n.text_edit; doc = te.document()
RED, BLUE = "#e53935", "#1565c0"

def ink():
    return note_ink(n._qcolor_base, auto=getattr(app, "_auto_contrast", True)).text

def set_base(hex_):
    n._qcolor_base = QColor(hex_); n._apply_ink()

def fg(bn, off):
    """(rgb hex, alpha, struck) of the char at offset `off` of row bn; a char
    with no colour of its own reads as the ink at full alpha."""
    b = doc.findBlockByNumber(bn)
    c = QTextCursor(doc); c.setPosition(b.position() + off)
    c.setPosition(b.position() + off + 1, QTextCursor.MoveMode.KeepAnchor)
    f = c.charFormat()
    if f.foreground().style() == Qt.BrushStyle.NoBrush:
        return (ink(), 255, f.fontStrikeOut())
    col = f.foreground().color()
    return (col.name(), col.alpha(), f.fontStrikeOut())

def colour_text(bn, a, b, hex_):
    blk = doc.findBlockByNumber(bn)
    c = QTextCursor(doc); c.setPosition(blk.position() + a)
    c.setPosition(blk.position() + b, QTextCursor.MoveMode.KeepAnchor)
    f = QTextCharFormat(); f.setForeground(QColor(hex_)); c.mergeCharFormat(f)

def setup(texts=("crveno",), indents=()):
    set_base("#fff59d")
    te.setCurrentCharFormat(QTextCharFormat())
    te.setPlainText("\n".join(texts))
    for bn in range(len(texts)):
        c = te.textCursor(); c.setPosition(doc.findBlockByNumber(bn).position())
        te.setTextCursor(c); te.toggle_checklist()
    for bn, lvl in indents:
        c = QTextCursor(doc); c.setPosition(doc.findBlockByNumber(bn).position())
        bf = c.blockFormat(); bf.setIndent(lvl); c.setBlockFormat(bf)

def tick(bn):
    te.toggle_checkbox(doc.findBlockByNumber(bn).position())

# ── red item: faded while done, full red again after unticking ───────────────
setup(); colour_text(0, 2, 8, RED)
tick(0)
rgb, a, st = fg(0, 3)
check("ticked red item: still red (RGB kept)", rgb == RED)
check("ticked red item: faded (alpha < 255)", a < 255)
check("ticked red item: struck", st)
tick(0)
check("unticked red item: full red again (the reported bug)", fg(0, 3) == (RED, 255, False))

# ── two colours in one item ───────────────────────────────────────────────────
setup(("crvenoplavo",)); colour_text(0, 2, 8, RED); colour_text(0, 8, 13, BLUE)
tick(0); tick(0)
check("mixed item: red part restored", fg(0, 3) == (RED, 255, False))
check("mixed item: blue part restored", fg(0, 10) == (BLUE, 255, False))

# ── default-ink item ─────────────────────────────────────────────────────────
setup(("obicno",))
tick(0)
rgb, a, _ = fg(0, 3)
check("ticked default item: faded ink", rgb == ink() and a < 255)
tick(0)
check("unticked default item: ink at full strength", fg(0, 3)[:2] == (ink(), 255))

# ── survives save/reload (the note is stored as HTML) ────────────────────────
setup(); colour_text(0, 2, 8, RED); tick(0)
html = te.toHtml()
te.setCurrentCharFormat(QTextCharFormat()); te.setHtml(html)
check("(reload) item still ticked", doc.firstBlock().text().startswith(CHECK_DONE))
tick(0)
check("after reload, unticking restores full red", fg(0, 3) == (RED, 255, False))

# ── parent cascade: ticking the parent ticks + restores the child's colour ────
setup(("roditelj", "dijete"), indents=((1, 1),)); colour_text(1, 2, 8, RED)
tick(0)
check("cascade: child ticked with its red faded",
      doc.findBlockByNumber(1).text().startswith(CHECK_DONE)
      and fg(1, 3)[0] == RED and fg(1, 3)[1] < 255)
tick(0)
check("cascade: unticking the parent restores the child's full red",
      fg(1, 3) == (RED, 255, False))

# ── theme flip while done: faded ink follows the ink; red stays red ──────────
setup(("obicno", "crveno")); colour_text(1, 2, 8, RED)
tick(0); tick(1)
light_alpha = fg(1, 3)[1]
set_base("#2b2b2b")
check("dark flip: done default item fades the NEW ink", fg(0, 3)[0] == ink() and fg(0, 3)[1] < 255)
check("dark flip: done red item stays red, faded", fg(1, 3)[0] == RED and fg(1, 3)[1] < 255)
check("dark flip: done text a bit stronger on a dark note (readability)",
      fg(1, 3)[1] > light_alpha)
tick(1)
check("dark flip then untick: full red", fg(1, 3) == (RED, 255, False))

# ── removing the checklist (toolbar ☑) keeps the text's colour too ────────────
def strip_checklist():
    c = te.textCursor(); c.setPosition(doc.firstBlock().position() + 3); te.setTextCursor(c)
    te.toggle_checklist()
setup(); colour_text(0, 2, 8, RED)
strip_checklist()
check("strip checklist from an unticked red item: text stays red",
      doc.firstBlock().text() == "crveno" and fg(0, 1) == (RED, 255, False))
setup(); colour_text(0, 2, 8, RED); tick(0)
strip_checklist()
check("strip checklist from a TICKED red item: full red, not struck",
      doc.firstBlock().text() == "crveno" and fg(0, 1) == (RED, 255, False))

# ── ODT export: ODF has no alpha → the faded colour is pre-blended on white ──
import zipfile, re
from sticky_notes import export
setup(); colour_text(0, 2, 8, RED); tick(0)
a = fg(0, 3)[1] / 255.0
r, g, b_ = QColor(RED).red(), QColor(RED).green(), QColor(RED).blue()
want = QColor(round(r * a + 255 * (1 - a)), round(g * a + 255 * (1 - a)),
              round(b_ * a + 255 * (1 - a))).name()
odt = os.path.join(_SB, "done.odt")
export.to_odt(doc, odt)
odt_colours = set(re.findall(r'fo:color="(#[0-9a-fA-F]{6})"',
                             zipfile.ZipFile(odt).read("content.xml").decode()))
check("ODT: done red exported faded (blended on white), not full red",
      want in odt_colours and RED not in odt_colours)
check("ODT export leaves the note itself untouched (still faded red)",
      fg(0, 3)[0] == RED and fg(0, 3)[1] < 255)

# ── legacy grey done item (saved before this change) unticks to the ink ──────
set_base("#fff59d")
te.setCurrentCharFormat(QTextCharFormat())
te.setHtml(f'<p><a href="x-sticky-check" style="color:{ink()};text-decoration:none">{CHECK_DONE}</a>'
           f'<span style="color:{ink()}"> </span>'
           f'<span style="color:#9aa0a6;text-decoration:line-through">staro</span></p>')
tick(0)
check("legacy grey item unticks to the ink at full strength",
      doc.firstBlock().text().startswith(CHECK_EMPTY) and fg(0, 3)[:2] == (ink(), 255))

print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
