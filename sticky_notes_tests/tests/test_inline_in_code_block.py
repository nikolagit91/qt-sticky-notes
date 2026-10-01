"""Inline code INSIDE a code block must stay visible. The inline chip used one
colour everywhere (inline_bg) — a translucent tint tuned for the note PAPER. On a
light note that's a dark tint, so on the dark code box it nearly vanished
(chip↔box contrast 1.13-1.31); on a dark note it's a light tint that lifted the
box under the light code text (text contrast 2.4-3.5, unreadable). A chip inside
a code block now uses ink.code_inline_bg, derived from the box itself.
Guards:
  - theme: on every built-in note colour (+ extremes, auto on and off) the chip
    is visible on the box (>= 1.65) and the code text on it stays readable (>= 4.5)
  - editor: the PAINTED chip inside a code block differs from the box in pixels
"""
import sys, os, tempfile, atexit, shutil
_SB = tempfile.mkdtemp(prefix="sn_icb_")
atexit.register(lambda: shutil.rmtree(_SB, ignore_errors=True))
os.environ["HOME"] = _SB
os.environ["XDG_CONFIG_HOME"] = os.path.join(_SB, ".config")
os.environ["XDG_DATA_HOME"]   = os.path.join(_SB, ".local", "share")
os.environ.setdefault("XDG_RUNTIME_DIR", _SB)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ.pop("DISPLAY", None); os.environ.pop("WAYLAND_DISPLAY", None)
os.makedirs(os.path.join(_SB, ".local", "share", "sticky_notes"), exist_ok=True)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from PyQt6.QtGui import QColor, QTextCursor

fails = []
def check(name, cond):
    print(f"  {'PASS' if cond else 'FAIL'}   {name}")
    if not cond: fails.append(name)

from sticky_notes.theme import note_ink, _rel_luminance
from sticky_notes.app import StickyNotesApp
from sticky_notes.note import StickyNote

def over(fg, bg):
    a = fg.alpha() / 255
    return QColor(round(fg.red() * a + bg.red() * (1 - a)),
                  round(fg.green() * a + bg.green() * (1 - a)),
                  round(fg.blue() * a + bg.blue() * (1 - a)))
def contrast(a, b):
    la, lb = _rel_luminance(a), _rel_luminance(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)

# ── theme layer ──────────────────────────────────────────────────────────────
colours = dict(StickyNote.NOTE_COLORS)
colours.update(StickyNote.DARK_NOTE_COLORS)
colours.update({"white": "#ffffff", "black": "#000000", "grey": "#808080", "red": "#e53935"})
for auto in (True, False):
    for name, hx in colours.items():
        ink = note_ink(QColor(hx), auto=auto)
        cib = getattr(ink, "code_inline_bg", None)
        if cib is None:
            check(f"{name} auto={auto}: ink has code_inline_bg", False); continue
        chip = over(cib, ink.code_bg)
        check(f"{name} auto={auto}: chip visible on code box (>=1.65, got {contrast(chip, ink.code_bg):.2f})",
              contrast(chip, ink.code_bg) >= 1.65)
        check(f"{name} auto={auto}: code text readable on chip (>=4.5, got {contrast(ink.code_fg, chip):.2f})",
              contrast(ink.code_fg, chip) >= 4.5)

# ── editor layer: the painted pixels ─────────────────────────────────────────
app = StickyNotesApp(sys.argv[:1])
def chip_vs_box(colour):
    note = StickyNote(app, colour, {"id": colour, "geometry": [0, 0, 320, 200], "color": colour})
    te = note.text_edit
    te.textCursor().insertText("x" + " " * 6 + "y")
    te.toggle_code_block()
    blk = te.document().begin()
    c = te.textCursor(); c.setPosition(blk.position() + 1)
    c.setPosition(blk.position() + 7, QTextCursor.MoveMode.KeepAnchor)
    te.setTextCursor(c); te.toggle_inline_code()           # inline run of spaces: no ink
    c = te.textCursor(); c.clearSelection(); c.movePosition(QTextCursor.MoveOperation.End)
    te.setTextCursor(c)
    note.resize(320, 200); note.show(); app.processEvents()
    img = te.viewport().grab().toImage()
    chip = te._inline_run_rects()[0]
    box = te._code_region_rect(0, 0)
    cy = int(chip.center().y())
    p_chip = img.pixelColor(int(chip.center().x()), cy)
    p_box = img.pixelColor(int(box.right()) - 8, cy)       # inside the box, right of the text
    note.hide(); note.deleteLater()
    return contrast(p_chip, p_box)
for colour in ("#fff59d", "#E3F2FD", "#2b2b30", "#273630"):
    r = chip_vs_box(colour)
    check(f"note {colour}: painted chip stands out from the code box (>=1.5, got {r:.2f})", r >= 1.5)

# ── export layer: the PDF clone gets the same colours ─────────────────────────
# (drawContents doesn't run paintEvent, so the markers are made opaque on a clone;
# inline inside a code block used to be skipped entirely there.)
from sticky_notes.export import _restore_code_fills
en = StickyNote(app, "ex", {"id": "ex", "geometry": [0, 0, 320, 200], "color": "#fff59d"})
ete = en.text_edit
ete.textCursor().insertText("plain cmd here")
c = ete.textCursor(); c.setPosition(6); c.setPosition(9, QTextCursor.MoveMode.KeepAnchor)
ete.setTextCursor(c); ete.toggle_inline_code()                       # inline on paper
c = ete.textCursor(); c.movePosition(QTextCursor.MoveOperation.End); c.insertBlock()
ete.setTextCursor(c); ete.textCursor().insertText("run git now"); ete.toggle_code_block()
blk1 = ete.document().lastBlock()
c = ete.textCursor(); c.setPosition(blk1.position() + 4); c.setPosition(blk1.position() + 7, QTextCursor.MoveMode.KeepAnchor)
ete.setTextCursor(c); ete.toggle_inline_code()                       # inline inside the block
ink = note_ink(QColor("#fff59d"))
doc = ete.document().clone(); _restore_code_fills(doc, ink)
def bg_at(pos):
    cc = QTextCursor(doc); cc.setPosition(pos); cc.setPosition(pos + 1, QTextCursor.MoveMode.KeepAnchor)
    return cc.charFormat().background().color()
check("export: inline inside a code block gets code_inline_bg",
      bg_at(doc.lastBlock().position() + 5).rgba() == ink.code_inline_bg.rgba())
check("export: inline on the paper keeps inline_bg",
      bg_at(7).rgba() == ink.inline_bg.rgba())
en.hide(); en.deleteLater()

print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
