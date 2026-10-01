"""Option 3: code blocks render as a distinctly DARK box with LIGHT monospace
text, regardless of note colour or theme (the "mockup look"). Guards:
  - note_ink gives an opaque, dark code_bg and a light code_fg with real contrast
  - toggling a code block stamps code_fg on the code text
  - un-coding clears that foreground so the text follows the note ink again
"""
import sys, os, tempfile, atexit, shutil
_SB = tempfile.mkdtemp(prefix="sn_cbd_")
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
from PyQt6.QtCore import Qt, QPoint

fails = []
def check(name, cond):
    print(f"  {'PASS' if cond else 'FAIL'}   {name}")
    if not cond: fails.append(name)

from sticky_notes.theme import note_ink, _rel_luminance, _code_box
from sticky_notes.app import StickyNotesApp
from sticky_notes.note import StickyNote

def contrast(a: QColor, b: QColor) -> float:
    la, lb = _rel_luminance(a), _rel_luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)

# ── theme layer ──────────────────────────────────────────────────────────────
# On every note colour the code box must be OPAQUE, READABLE with the light
# text, and clearly DISTINGUISHABLE from the note itself. The last one guards the
# regression where a fixed-dark box vanished into dark notes (both ~0.18).
for name, hexv in [("Blue light", "#E3F2FD"), ("Yellow light", "#fff59d"),
                   ("Green light", "#E8F5E9"), ("Charcoal dark", "#2b2b30"),
                   ("Slate dark", "#2c3542"), ("Teal dark", "#1f3638")]:
    note_c = QColor(hexv)
    ink = note_ink(note_c)
    bg, fg = ink.code_bg, ink.code_fg
    check(f"{name}: code_bg opaque", bg.alpha() == 255)
    check(f"{name}: code_fg is light", _rel_luminance(fg) > 0.55)
    check(f"{name}: code_fg/bg contrast >= 4.5", contrast(fg, bg) >= 4.5)
    check(f"{name}: box distinguishable from note",
          abs(bg.getHslF()[2] - note_c.getHslF()[2]) >= 0.10)

# A near-grey note must NOT get a saturated (e.g. blue) box; a deliberately
# tinted note must keep its colour. (#2b2b30 has a hair of blue but reads grey.)
check("near-grey note gets a neutral box", _code_box(QColor("#2b2b30")).getHslF()[1] < 0.12)
check("tinted dark note keeps a coloured box", _code_box(QColor("#2c3542")).getHslF()[1] >= 0.30)
# A pure-black note's box must stay clearly visible (lightness floor).
check("very dark note box stays visible (lightness floor)",
      _code_box(QColor("#000000")).getHslF()[2] >= 0.24)

# ── editor layer ─────────────────────────────────────────────────────────────
app = StickyNotesApp(sys.argv[:1])
note = StickyNote(app, "n", {"id": "n", "geometry": [0, 0, 300, 200], "color": "#E3F2FD"})
te = note.text_edit

c = te.textCursor(); c.insertText("git push origin main")
te.toggle_code_block()

cc = te.textCursor(); cc.movePosition(cc.MoveOperation.StartOfBlock)
cc.setPosition(cc.position() + 1, cc.MoveMode.KeepAnchor)
fg_hex = cc.charFormat().foreground().color().name().lower()
check("code text carries code_fg foreground",
      cc.charFormat().foreground().style() != Qt.BrushStyle.NoBrush and
      fg_hex == te.code_fg_color.name().lower())

# un-code: foreground must be cleared so the text follows the note ink again
te.toggle_code_block()
cc = te.textCursor(); cc.movePosition(cc.MoveOperation.StartOfBlock)
cc.setPosition(cc.position() + 1, cc.MoveMode.KeepAnchor)
check("un-coding clears the code foreground",
      cc.charFormat().foreground().style() == Qt.BrushStyle.NoBrush)

# ── box geometry: symmetric + copy button inside it (regressions from live test) ──
note2 = StickyNote(app, "g", {"id": "g", "geometry": [0, 0, 340, 240], "color": "#E3F2FD"})
te2 = note2.text_edit
g = te2.textCursor(); g.insertText("x = 1"); te2.toggle_code_block()
note2.resize(340, 240); note2.show(); app.processEvents()
box = te2._code_region_rect(0, 0)
left_gap = box.left()
right_gap = te2.viewport().width() - box.right()
check("code box has equal left/right breathing room", abs(left_gap - right_gap) <= 1.5)
te2._update_copy_btn(QPoint(int(box.left()) + 10, int(box.top()) + 8))
btn = te2._copy_btn
check("copy button sits inside the code box",
      btn.isVisible() and btn.x() >= int(box.left())
      and btn.x() + btn.width() <= int(box.right()) + 1
      and btn.y() >= int(box.top()) - 1)
note2.hide()

# An empty code line must already carry monospace metrics, so neither the line
# nor its box shrinks the instant the first character is typed.
note3 = StickyNote(app, "h", {"id": "h", "geometry": [0, 0, 320, 200], "color": "#E3F2FD"})
te3 = note3.text_edit
te3.toggle_code_block()
note3.show(); app.processEvents()
b0 = te3.document().findBlockByNumber(0)
h_empty = te3.cursorRect(QTextCursor(b0)).height()
te3.textCursor().insertText("x"); app.processEvents()
h_typed = te3.cursorRect(QTextCursor(b0)).height()
check("empty code line height matches typed (no shrink on first char)", h_empty == h_typed)
note3.hide()

# The code box follows the note's background opacity (so it isn't an opaque
# rectangle on a see-through note); inline code is a translucent tint too.
app._note_opacity = 50
note_op = StickyNote(app, "op", {"id": "op", "geometry": [0, 0, 300, 150], "color": "#E3F2FD"})
note_op._apply_opacity()
check("code box paint alpha follows note opacity",
      note_op.text_edit.paper_alpha == note_op._bg_alpha() and note_op.text_edit.paper_alpha < 255)
note_op.hide(); app._note_opacity = 100

# Inline code is now painted as a rounded, padded chip: the doc carries only a
# transparent char marker, and _inline_run_rects yields a rect to paint.
note_i = StickyNote(app, "ic", {"id": "ic", "geometry": [0, 0, 320, 120], "color": "#E3F2FD"})
te_i = note_i.text_edit
ci = te_i.textCursor(); ci.insertText("run "); te_i.setTextCursor(ci)
te_i.toggle_inline_code(); te_i.textCursor().insertText("cmd"); te_i.toggle_inline_code()
note_i.show(); app.processEvents()
check("inline code paints a chip rect", len(te_i._inline_run_rects()) >= 1)
pi = te_i.textCursor(); pi.setPosition(4); pi.setPosition(5, QTextCursor.MoveMode.KeepAnchor)
check("inline char carries a transparent marker (chip painted, not filled)",
      te_i._is_inline_code(pi.charFormat()) and pi.charFormat().background().color().alpha() == 0)
# Inline must NOT carry over to a new line (regression: it stayed active there).
from PyQt6.QtGui import QKeyEvent
from PyQt6.QtCore import QEvent
ce = te_i.textCursor(); ce.movePosition(ce.MoveOperation.End); te_i.setTextCursor(ce)
te_i.keyPressEvent(QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Return, Qt.KeyboardModifier.NoModifier))
te_i.textCursor().insertText("z")
lb = te_i.document().lastBlock()
pz = QTextCursor(te_i.document()); pz.setPosition(lb.position())
pz.setPosition(lb.position() + 1, QTextCursor.MoveMode.KeepAnchor)
check("inline does not carry over to a new line", not te_i._is_inline_code(pz.charFormat()))
note_i.hide()

# The box must sit an equal distance from the lines above and below it (a code
# line is centred between its neighbours; equal padding keeps the outer gaps
# symmetric). Regression: they were 1px vs 0px.
note4 = StickyNote(app, "s", {"id": "s", "geometry": [0, 0, 360, 320], "color": "#E3F2FD"})
te4 = note4.text_edit
cc = te4.textCursor(); cc.insertText("above line\n"); te4.setTextCursor(cc)
te4.toggle_code_block(); te4.textCursor().insertText("code")
cur = te4.textCursor(); cur.movePosition(QTextCursor.MoveOperation.EndOfBlock)
from PyQt6.QtGui import QTextBlockFormat, QTextCharFormat
pcf = QTextCharFormat(); pcf.setFontFamilies([te4.code_revert_family or te4.document().defaultFont().family()])
cur.insertBlock(QTextBlockFormat(), pcf); te4.setTextCursor(cur); te4._reflow_code_spacing()
te4.textCursor().insertText("below line")
note4.resize(360, 320); note4.show(); app.processEvents()
d4 = te4.document()
box4 = te4._code_region_rect(1, 1)
gap_above = box4.top() - te4.cursorRect(QTextCursor(d4.findBlockByNumber(0))).bottom()
gap_below = te4.cursorRect(QTextCursor(d4.findBlockByNumber(2))).top() - box4.bottom()
check("code box outer gaps are symmetric (above == below)", abs(gap_above - gap_below) < 0.6)
note4.hide()

# Enter to add a code line, then Backspace to delete it, must restore the code
# region's bottom margin — otherwise the line below is pulled up onto the box.
from PyQt6.QtGui import QKeyEvent
from PyQt6.QtCore import QEvent
def press(te, key):
    te.keyPressEvent(QKeyEvent(QEvent.Type.KeyPress, key, Qt.KeyboardModifier.NoModifier))
from PyQt6.QtGui import QTextBlockFormat as _BF, QTextCharFormat as _CF
note5 = StickyNote(app, "d", {"id": "d", "geometry": [0, 0, 360, 320], "color": "#E3F2FD"})
te5 = note5.text_edit
te5.toggle_code_block(); te5.textCursor().insertText("code")   # block 0 = code
# exit the block and type a line below it (block 1 = plain "below")
cur = te5.textCursor(); cur.movePosition(QTextCursor.MoveOperation.EndOfBlock)
pcf = _CF(); pcf.setFontFamilies([te5.code_revert_family or te5.document().defaultFont().family()])
cur.insertBlock(_BF(), pcf); te5.setTextCursor(cur); te5._reflow_code_spacing()
te5.textCursor().insertText("below"); app.processEvents()

def last_code_block(te):
    idx = None
    for i in range(te.document().blockCount()):
        if te._is_code_block(te.document().findBlockByNumber(i)):
            idx = i
    return idx

# back to the end of the code line, Enter (adds a code line), Backspace (deletes it)
c = QTextCursor(te5.document().findBlockByNumber(last_code_block(te5)))
c.movePosition(QTextCursor.MoveOperation.EndOfBlock); te5.setTextCursor(c)
press(te5, Qt.Key.Key_Return); app.processEvents()     # new empty code line becomes last
press(te5, Qt.Key.Key_Backspace); app.processEvents()  # delete it → deferred reflow fires
bm = te5.document().findBlockByNumber(last_code_block(te5)).blockFormat().bottomMargin()
check("bottom margin restored after Enter+Backspace on last code line", bm > 0)
note5.hide()

print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
