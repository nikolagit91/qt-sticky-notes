"""Guard: a theme / light↔dark flip leaves NOTHING in the undo history — the
first Ctrl+Z after the auto theme undoes the user's own last edit.

Before (2026-11-19, measured): a flip WROTE the dark variants into the
document — recolor_links (link colours), recolor_checklist (box + checklist
ink, done fade), and normalize_code_blocks rewrote every code block even when
nothing changed (4 steps on a mere Yellow→Blue change). After the auto theme the
first Ctrl+Z did nothing visible, the 2nd turned links dark blue on the dark
note, the 3rd made the boxes dark; only the 4th undid the user's typing.

Now the document stores the light-note look (link light colour, ink #333333,
done fade 120) and the editor's highlighter DRAWS the dark-note look.
"""
import sys, os, tempfile, atexit, shutil, zipfile
_SB = tempfile.mkdtemp(prefix="sn_tfu_")
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

from PyQt6.QtCore import Qt, QMimeData
from PyQt6.QtWidgets import QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from PyQt6.QtGui import QTextCursor, QColor, QTextCharFormat
from PyQt6.QtTest import QTest
from sticky_notes.app import StickyNotesApp
from sticky_notes.note import StickyNote
from sticky_notes import theme, export
from sticky_notes.widgets import CHECK_DONE

app = StickyNotesApp(sys.argv[:1])
for e in list(app.notes.values()):
    e.hide(); e.deleteLater()
app.notes.clear()
LIGHT_NOTE, DARK_NOTE = "#fff59d", "#2b2b30"
WEB_L, WEB_D = theme.LINK_COLORS["web"]
INK_L, INK_D = theme.DARK_INK.text, theme.LIGHT_INK.text     # light-note / dark-note ink

def stored(doc, p):
    c = QTextCursor(doc); c.setPosition(p); c.setPosition(p + 1, QTextCursor.MoveMode.KeepAnchor)
    f = c.charFormat()
    if f.foreground().style() == Qt.BrushStyle.NoBrush:
        return None
    col = f.foreground().color()
    return col.name().lower(), col.alpha()

def shown(doc, p):
    blk = doc.findBlock(p); rel = p - blk.position()
    for r in blk.layout().formats():
        if r.start <= rel < r.start + r.length and \
                r.format.foreground().style() != Qt.BrushStyle.NoBrush:
            col = r.format.foreground().color()
            return col.name().lower(), col.alpha()
    return stored(doc, p)

def recolour(note, hex_):
    note.color = hex_; note._apply_color(); app.processEvents()

# A note like a user's: a link, an unticked + a ticked checklist item, a code
# block, inline code, a palette colour. Built with the app's own actions.
# Loaded like at app start (setHtml only happens at load; the link arrives in
# Qt's #0000ff and load makes it the stored light-note link colour).
n = StickyNote(app, data={"content":
    '<p><a href="https://example.com">link</a> i <span style="color:#1565c0">plavo</span></p>'
    '<p>prva</p><p>druga</p><p>kod</p><p>ima inline ovdje</p>',
    "content_type": "html", "color": LIGHT_NOTE})
n.show(); app.processEvents()
te = n.text_edit; doc = te.document()
for bn in (1, 2):
    c = te.textCursor(); c.setPosition(doc.findBlockByNumber(bn).position()); te.setTextCursor(c)
    te.toggle_checklist()
te.toggle_checkbox(doc.findBlockByNumber(2).position())
c = te.textCursor(); c.setPosition(doc.findBlockByNumber(3).position() + 1); te.setTextCursor(c)
te.toggle_code_block()
b4 = doc.findBlockByNumber(4).position()
c = te.textCursor(); c.setPosition(b4 + 4); c.setPosition(b4 + 10, QTextCursor.MoveMode.KeepAnchor)
te.setTextCursor(c); te.toggle_inline_code(); app.processEvents()

# positions read at use time — typing in row 1 shifts the rows below
def box1(): return doc.findBlockByNumber(1).position()
def box2(): return doc.findBlockByNumber(2).position()
def done_text(): return box2() + 3

# ── the user types, then the theme flips ──────────────────────────────────────
te.setFocus()
c = te.textCursor(); c.setPosition(box1() + len(doc.findBlockByNumber(1).text())); te.setTextCursor(c)
QTest.keyClicks(te, " X"); app.processEvents()
doc.clearUndoRedoStacks()
QTest.keyClicks(te, "Y"); app.processEvents()        # one user edit on the stack
steps_before = doc.availableUndoSteps()
recolour(n, DARK_NOTE)
check(f"light→dark adds NO undo steps (before {steps_before}, after {doc.availableUndoSteps()})",
      doc.availableUndoSteps() == steps_before)

# ── what is drawn on the dark note ────────────────────────────────────────────
check("link drawn in the dark-note link colour", shown(doc, 0)[0] == WEB_D)
check("unticked box drawn in the dark-note ink", shown(doc, box1())[0] == INK_D)
check("ticked box drawn in the dark-note ink", shown(doc, box2())[0] == INK_D)
check("done item text drawn in the dark-note ink, dark-note fade",
      shown(doc, done_text()) == (INK_D, 165))
check("palette colour drawn as its dark twin", shown(doc, 8)[0] == theme.palette_display("#1565c0", True))

# ── what is stored: the light-note look, unchanged by the flip ────────────────
check("link stored in the light-note link colour", stored(doc, 0)[0] == WEB_L)
check("box stored in the light-note ink", stored(doc, box1())[0] == INK_L)
check("done item stored with the light-note fade", stored(doc, done_text()) == (INK_L, 120))

# ── the first Ctrl+Z undoes the user's typing, nothing else ───────────────────
te.undo(); app.processEvents()
check("1st Ctrl+Z after the flip removes the user's 'Y'",
      doc.findBlockByNumber(1).text().endswith(" X"))
check("…and the link / box still LOOK right", shown(doc, 0)[0] == WEB_D and shown(doc, box1())[0] == INK_D)

# ── a light→light colour change touches nothing either ────────────────────────
recolour(n, LIGHT_NOTE)
doc.clearUndoRedoStacks()
recolour(n, "#E3F2FD")
check("light→light (Yellow→Blue) adds no undo steps (code blocks rewrote 4 before)",
      doc.availableUndoSteps() == 0)
recolour(n, DARK_NOTE); recolour(n, LIGHT_NOTE)
check("dark→light: nothing drawn over the stored look",
      shown(doc, 0)[0] == WEB_L and shown(doc, box1())[0] == INK_L and shown(doc, done_text()) == (INK_L, 120))

# ── new content created ON a dark note is stored in the light-note look ───────
recolour(n, DARK_NOTE)
te.setCurrentCharFormat(QTextCharFormat()); te.setPlainText("nova")
c = te.textCursor(); c.setPosition(0); te.setTextCursor(c); te.toggle_checklist()
te.toggle_checkbox(0); app.processEvents()
check("box made on a dark note: stored light ink, drawn dark ink",
      stored(doc, 0)[0] == INK_L and shown(doc, 0)[0] == INK_D)
check("item ticked on a dark note: stored fade 120, drawn 165",
      stored(doc, 3)[1] == 120 and shown(doc, 3)[1] == 165)
te.setCurrentCharFormat(QTextCharFormat()); te.setPlainText("")
md = QMimeData()
md.setText("https://example.com"); te.insertFromMimeData(md); app.processEvents()
check("link pasted on a dark note: stored light link colour, drawn dark",
      stored(doc, 0)[0] == WEB_L and shown(doc, 0)[0] == WEB_D)

# ── load: a note saved by the old build on a dark note is made canonical ──────
old = (f'<p><a href="https://example.com" style="color:{WEB_D}">link</a></p>'
       f'<p><a href="x-sticky-check" style="color:{INK_D}">☑</a>'
       f'<span style="color:{INK_D}"> </span>'
       f'<span style="color:rgba(240,240,240,0.647); text-decoration:line-through">gotovo</span></p>')
ld = StickyNote(app, data={"content": old, "content_type": "html", "color": DARK_NOTE})
ld.show(); app.processEvents(); ldoc = ld.text_edit.document()
lb = ldoc.findBlockByNumber(1).position()
check("load: dark link colour stored as the light one", stored(ldoc, 0)[0] == WEB_L)
check("load: dark checklist ink stored as the light ink", stored(ldoc, lb)[0] == INK_L)
check("load: done fade stored as 120", stored(ldoc, lb + 3) == (INK_L, 120))
check("load: drawn as the dark-note look", shown(ldoc, 0)[0] == WEB_D and shown(ldoc, lb + 3) == (INK_D, 165))
check("load leaves no undo step", not ldoc.isUndoAvailable())

# ── exports ───────────────────────────────────────────────────────────────────
recolour(n, DARK_NOTE)
te.setCurrentCharFormat(QTextCharFormat()); te.setPlainText("stavka")
c = te.textCursor(); c.setPosition(0); te.setTextCursor(c); te.toggle_checklist(); app.processEvents()
p = os.path.join(_SB, "c.odt"); export.to_odt(doc, p)
xml = zipfile.ZipFile(p).read("content.xml").decode().lower()
check("ODT of a dark note (white paper): checklist in the light-note ink, not near-white",
      INK_L in xml and INK_D not in xml)
clone = doc.clone(); export._display_palette(clone, True)
check("PDF clone of a dark note: the box drawn in the dark-note ink", stored(clone, 0)[0] == INK_D)

print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
