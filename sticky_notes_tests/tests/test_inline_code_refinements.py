import sys, os, tempfile, atexit, shutil
_SB = tempfile.mkdtemp(prefix="sn_inref_")
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

fails = []
def check(name, cond):
    print(f"  {'PASS' if cond else 'FAIL'}   {name}")
    if not cond: fails.append(name)

from sticky_notes.app import StickyNotesApp
from sticky_notes.note import StickyNote
from sticky_notes.theme import note_ink
from PyQt6.QtGui import QColor
app = StickyNotesApp(sys.argv[:1]); app._auto_contrast = True

# #1: no-selection inline toggle updates the button immediately (both ways).
note = StickyNote(app, "n", {"id": "n", "geometry": [0, 0, 300, 200]})
note._toggle_inline_code()
check("inline button checked after turning inline mode on", note.btn_inline_code.isChecked() is True)
note._toggle_inline_code()
check("inline button UN-checks immediately after turning it off",
      note.btn_inline_code.isChecked() is False)

# #2: inline code stays a subtle TRANSLUCENT overlay (a few chars read fine with
# the note's own ink), unlike the block which is now an opaque dark box.
note2 = StickyNote(app, "m", {"id": "m", "geometry": [0, 0, 300, 200], "color": "#000000"})
code_bg = note_ink(QColor("#000000"), auto=True).code_bg
check("dark note: block box is opaque (not an overlay)", code_bg.alpha() == 255)
check("dark note: inline overlay stays translucent",
      0 < note2.text_edit.inline_bg_color.alpha() < 255)
check("dark note: inline is a neutral light (white) tint",
      note2.text_edit.inline_bg_color.red() == 255)

# #3: a WRAPPING inline-code run gets a full chip on EVERY visual line — the
# earlier segments must NOT collapse. cursorRect(seg_end) at a soft-wrap boundary
# resolves to the NEXT line's start (far left), which used to shrink every chip
# but the last to ~0 width.
note3 = StickyNote(app, "w", {"id": "w", "geometry": [0, 0, 300, 220]})
te3 = note3.text_edit
long = "Testiram inline kod i kako ce funkcionisati kada pocnem ispisivati pune redove."
te3.textCursor().insertText(long)
sel = te3.textCursor(); sel.movePosition(sel.MoveOperation.Start)
sel.movePosition(sel.MoveOperation.End, sel.MoveMode.KeepAnchor)
te3.setTextCursor(sel); te3.toggle_inline_code()
note3.resize(300, 220); note3.show(); app.processEvents()
rects = te3._inline_run_rects()
check("wrapping inline run occupies multiple visual lines", len(rects) >= 2)
check("no inline chip segment collapses (all have real width)",
      all(r.width() > 20 for r in rects))
check("each chip sits on a distinct visual line",
      len({round(r.top()) for r in rects}) == len(rects))
note3.hide(); note3.deleteLater()

# Inline-chip padding is UNIFORM: every chip edge sits exactly CODE_INLINE_PAD_X
# past the edge glyph's INK. Measured against the EXACT layout position
# (QTextLine.cursorToX, fractional) — NOT cursorRect(), which is an integer rect:
# the chip used to be built from that truncated caret while glyphs are drawn at
# fractional x (GNOME slight hinting), so the SAME letter 'd' showed ~1px of
# padding in one chip and ~0 in another. A cursorRect-based chip is off by the
# truncation (0.3-0.5px here), so the tight tolerance below catches a regression.
# (The pixel difference itself only shows on the real xcb renderer; offscreen
# draws glyphs snapped, so the guard pins the geometry instead.)
from PyQt6.QtGui import QTextCursor as _TC, QFontMetricsF as _FM
from sticky_notes.widgets import CODE_INLINE_PAD_X as _PADX

def exact_x(te, pos):
    doc = te.document(); blk = doc.findBlock(pos); lay = blk.layout()
    ln = lay.lineForTextPosition(pos - blk.position())
    return lay.position().x() + ln.cursorToX(pos - blk.position())[0] - te.horizontalScrollBar().value()

def ink_pads(te, s, e):
    """(left_pad, right_pad): the chip's distance past the first/last glyph INK,
    with the ink taken from the exact (fractional) layout position."""
    doc = te.document()
    f = _TC(doc); f.setPosition(s); f.setPosition(s + 1, _TC.MoveMode.KeepAnchor)
    fm = _FM(f.charFormat().font())
    x0, x1 = exact_x(te, s), exact_x(te, e)
    cy = te._caret_rect(s).center().y()
    chip = next(r for r in te._inline_run_rects()
                if r.top() <= cy <= r.bottom() and r.left() <= x0 + 3 and r.right() >= x1 - 3)
    c0, c1 = doc.characterAt(s), doc.characterAt(e - 1)
    ink_left = x0 + (0.0 if c0.isspace() else fm.leftBearing(c0))
    ink_right = x1 - (0.0 if c1.isspace() else fm.rightBearing(c1))
    return (ink_left - chip.left(), chip.right() - ink_right)

# (a) The user's exact case: the SAME last letter 'd', once at a block end, once
# before a space, must get the SAME right padding.
nd = StickyNote(app, "p", {"id": "p", "geometry": [0, 0, 380, 220]})
ted = nd.text_edit
ted.toggle_inline_code(); ted.textCursor().insertText("aaa kod")        # 'd' at block end
e_end = ted.textCursor().position()
c = ted.textCursor(); c.movePosition(c.MoveOperation.End); c.insertBlock(); ted.setTextCursor(c)
ted.toggle_inline_code(); ted.textCursor().insertText("bbb kod xxx")     # 'd' before a space
full = ted.toPlainText(); base = full.rindex("bbb"); ps = full.index("kod", base)
c = ted.textCursor(); c.setPosition(ps); c.setPosition(ps + 3, _TC.MoveMode.KeepAnchor)
ted.setTextCursor(c); ted.toggle_inline_code()
nd.resize(380, 220); nd.show(); app.processEvents()
rp_blockend = ink_pads(ted, e_end - 3, e_end)[1]
rp_space = ink_pads(ted, ps, ps + 3)[1]
check("same letter 'd' gets equal right padding at block end vs before a space",
      abs(rp_blockend - rp_space) <= 0.05)
check("that padding equals CODE_INLINE_PAD_X", abs(rp_blockend - _PADX) <= 0.05)

# (b) Padding is symmetric (left == right) and == CODE_INLINE_PAD_X for runs whose
# edge glyphs have DIFFERENT bearings — 'Ctrl + M' (line start), 'inline' (i/e),
# 'wow' (w overhangs its cell). If it tracked the advance box these would differ.
nb = StickyNote(app, "s", {"id": "s", "geometry": [0, 0, 380, 240]})
teb = nb.text_edit
for i, word in enumerate(["Ctrl + M", "inline", "wow"]):
    c = teb.textCursor(); c.movePosition(c.MoveOperation.End)
    if i: c.insertBlock()
    teb.setTextCursor(c)
    teb.toggle_inline_code(); s0 = teb.textCursor().position(); teb.textCursor().insertText(word)
    e0 = teb.textCursor().position()
    teb.toggle_inline_code(); teb.textCursor().insertText(" x")
    nb.resize(380, 240); nb.show(); app.processEvents()
    lp, rp = ink_pads(teb, s0, e0)
    check(f"'{word}': left padding == CODE_INLINE_PAD_X", abs(lp - _PADX) <= 0.05)
    check(f"'{word}': right padding == CODE_INLINE_PAD_X", abs(rp - _PADX) <= 0.05)
# (c) A SPACE typed in inline mode is part of the chip right away. Qt reports a
# space's rightBearing as ~its whole advance (no ink), which used to end the chip
# BEFORE the trailing space — it looked un-chipped until the next letter.
nt = StickyNote(app, "t", {"id": "t", "geometry": [0, 0, 340, 160]})
tet = nt.text_edit
tet.toggle_inline_code(); tet.textCursor().insertText("kod ")
nt.resize(340, 160); nt.show(); app.processEvents()
chip_t = tet._inline_run_rects()[0]
check("trailing space typed inline is covered by the chip",
      chip_t.right() >= exact_x(tet, 4) + _PADX - 0.05)
nt.hide(); nt.deleteLater()
nd.hide(); nd.deleteLater(); nb.hide(); nb.deleteLater()

note.hide(); note.deleteLater(); note2.hide(); note2.deleteLater()
print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
