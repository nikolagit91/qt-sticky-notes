"""Guard: colour / underline / "Default colour" on a selection that covers
checklist boxes leave the BOX alone — it stays the neutral note-ink glyph
(_box_format), exactly like links are skipped.

Before (2026-11-13): merge_format_preserving_links skipped links via
_href_right, which on purpose reports the box as a plain char (for EDITING) —
so selecting a checklist and picking red turned the unticked boxes red (and U
underlined them). Ticking a row re-made its box in the ink, and every reload
(normalize_checkboxes) did too, so the boxes ended up inconsistent.
"""
import sys, os, tempfile, atexit, shutil
_SB = tempfile.mkdtemp(prefix="sn_cbf_")
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

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from PyQt6.QtGui import QTextCursor, QColor, QTextCharFormat
from sticky_notes.app import StickyNotesApp

app = StickyNotesApp(sys.argv[:1])
for e in list(app.notes.values()):
    e.hide(); e.deleteLater()
app.notes.clear()
n = app.create_new_note(); te = n.text_edit; doc = te.document()
n.show(); app.processEvents()
RED = "#e53935"

def fmt_at(p):
    c = QTextCursor(doc); c.setPosition(p); c.setPosition(p + 1, QTextCursor.MoveMode.KeepAnchor)
    return c.charFormat()

def fg_at(p):
    f = fmt_at(p)
    if f.foreground().style() == Qt.BrushStyle.NoBrush:
        return None
    return f.foreground().color().name().lower()

def boxes():
    return [doc.findBlockByNumber(i).position() for i in range(doc.blockCount())]

def checklist():
    te.setCurrentCharFormat(QTextCharFormat())
    te.setPlainText("jedan\ndva")
    for bn in (0, 1):
        c = te.textCursor(); c.setPosition(doc.findBlockByNumber(bn).position())
        te.setTextCursor(c); te.toggle_checklist()
    app.processEvents()

def select_all():
    c = te.textCursor(); c.setPosition(0)
    c.setPosition(doc.characterCount() - 1, QTextCursor.MoveMode.KeepAnchor)
    te.setTextCursor(c); app.processEvents()

ink = te.checkbox_text_color.lower()

# ── colour ────────────────────────────────────────────────────────────────────
checklist(); select_all(); n._apply_text_color(RED)
check("select checklist + red: boxes keep the note ink",
      all(fg_at(p) == ink for p in boxes()))
check("…and the item text IS red", fg_at(boxes()[0] + 2) == RED and fg_at(boxes()[1] + 2) == RED)

# ── underline ─────────────────────────────────────────────────────────────────
checklist(); select_all(); n._fmt_underline()
check("select checklist + U: boxes not underlined",
      not any(fmt_at(p).fontUnderline() for p in boxes()))
check("…and the item text IS underlined", fmt_at(boxes()[0] + 2).fontUnderline())
select_all(); n._fmt_underline()
check("second U turns it OFF (boxes don't count in 'all underlined?')",
      not fmt_at(boxes()[0] + 2).fontUnderline() and not fmt_at(boxes()[1] + 2).fontUnderline())

# ── "Default colour" ──────────────────────────────────────────────────────────
checklist(); select_all(); n._apply_text_color(RED)
select_all(); n._apply_default_text_color()
check("Default colour: boxes keep their own ink colour (not stripped)",
      all(fg_at(p) == ink for p in boxes()))
check("…and the item text lost its red", fg_at(boxes()[0] + 2) != RED)

# ── boxes still toggle and still follow an ink flip ───────────────────────────
checklist(); select_all(); n._apply_text_color(RED)
n._qcolor_base = QColor("#2b2b2b"); n._apply_ink(); app.processEvents()
# The box is stored in the light-note ink; the dark note DRAWS the dark-note ink
# (2026-11-19 — a flip no longer writes into the document).
from sticky_notes.theme import LIGHT_INK
def drawn_at(p):
    blk = doc.findBlock(p); rel = p - blk.position()
    for r in blk.layout().formats():
        if r.start <= rel < r.start + r.length and \
                r.format.foreground().style() != Qt.BrushStyle.NoBrush:
            return r.format.foreground().color().name().lower()
    return fg_at(p)
dark_ink = LIGHT_INK.text.lower()
check("after a flip to a dark note boxes are DRAWN in the new ink (red never reached them)",
      dark_ink != ink and all(drawn_at(p) == dark_ink for p in boxes())
      and all(fg_at(p) == ink for p in boxes()))
n._qcolor_base = QColor("#fff59d"); n._apply_ink(); app.processEvents()

# ── a real link in the selection is still skipped ────────────────────────────
te.setCurrentCharFormat(QTextCharFormat())
te.setHtml('<p>vidi <a href="https://example.com">example.com</a></p>'); app.processEvents()
link_before = fg_at(6)
select_all(); n._apply_text_color(RED)
check("link still keeps its colour", link_before and fg_at(6) == link_before)

print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
