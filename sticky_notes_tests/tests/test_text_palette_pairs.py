"""Guard: the text-colour palette comes in (light-note, dark-note) PAIRS, like
link colours. The DOCUMENT always stores the light side (the "real" colour —
what is saved, copied, exported to ODT); on a dark note the DISPLAY shows the
dark twin, painted by a QSyntaxHighlighter, so the swap is never a document
edit (no undo step, nothing leaks to the clipboard / another note / ODT).

History (2026-11-13): user-picked colours never changed — on a dark note 10 of
16 swatches fell below 3:1 (black 1.5, purple 1.3), so text coloured by day was
unreadable after the auto theme switched at night; the last row (white +
pastels) was invisible on every light note. The first pairs fix (d9328d3)
rewrote the colours IN the document on each flip, which leaked: text copied
from a dark note pasted near-white into a light note / mail, ODT got #f5f5f5 on
white paper, and Ctrl+Z after the auto theme reverted the colours. Measured,
then replaced by display-only mapping (2026-11-15).
"""
import sys, os, tempfile, atexit, shutil, re, zipfile
_SB = tempfile.mkdtemp(prefix="sn_tpp_")
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
from PyQt6.QtWidgets import QMessageBox, QDialog, QPushButton
QMessageBox.information = staticmethod(lambda *a, **k: None)
from PyQt6.QtGui import QTextCursor, QColor, QTextCharFormat
from PyQt6.QtTest import QTest
from sticky_notes.app import StickyNotesApp
from sticky_notes.note import StickyNote
from sticky_notes import theme, export

PAIRS = getattr(theme, "TEXT_PALETTE", None)
check("theme defines TEXT_PALETTE (light, dark) pairs", PAIRS is not None)
if PAIRS is None:
    print(f"\n{len(fails)} FAIL"); sys.exit(1)
LIGHT = [l for l, _ in PAIRS]
DARK  = [d for _, d in PAIRS]
TWIN  = dict(PAIRS)
LIGHT_NOTE, DARK_NOTE = "#fff59d", "#2b2b30"

def ratio(a, b):
    la, lb = sorted((theme._rel_luminance(QColor(a)), theme._rel_luminance(QColor(b))), reverse=True)
    return (la + 0.05) / (lb + 0.05)

# ── the palette itself ────────────────────────────────────────────────────────
check("16 pairs", len(PAIRS) == 16)
check("light set has no duplicates", len(set(LIGHT)) == 16)
check("dark set has no duplicates", len(set(DARK)) == 16)
check("light and dark sets are disjoint (a colour's side is never ambiguous)",
      not set(LIGHT) & set(DARK))
check("the first 12 light colours are unchanged (existing text keeps its colour)",
      LIGHT[:12] == ["#000000", "#434343", "#666666", "#999999",
                     "#e53935", "#e67c13", "#f9a825", "#2e7d32",
                     "#1565c0", "#6a1b9a", "#ad1457", "#00838f"])
check("old white/pastels are now the dark-note last row",
      DARK[12:] == ["#ffffff", "#fce4ec", "#e8f5e9", "#e3f2fd"])
dark_notes = list(StickyNote.DARK_NOTE_COLORS.values())
light_notes = list(StickyNote.NOTE_COLORS.values())
for i, d in enumerate(DARK):
    need = 3.5 if i == 3 else 4.5          # index 3 = the deliberately subtle grey
    check(f"dark twin {d} readable on every dark note (≥{need})",
          min(ratio(d, n) for n in dark_notes) >= need)
for l in LIGHT[12:]:
    check(f"new light last-row {l} readable on every light note (≥4.5)",
          min(ratio(l, n) for n in light_notes) >= 4.5)

# ── app setup ─────────────────────────────────────────────────────────────────
app = StickyNotesApp(sys.argv[:1])
for e in list(app.notes.values()):
    e.hide(); e.deleteLater()
app.notes.clear()
n = app.create_new_note(); te = n.text_edit; doc = te.document()
n.show(); app.processEvents()

def set_base(note, hex_):
    note._qcolor_base = QColor(hex_); note._apply_ink(); app.processEvents()

def stored(p, d=None):
    """(name, alpha) of the colour the DOCUMENT stores for the char right of p."""
    d = d or doc
    c = QTextCursor(d); c.setPosition(p); c.setPosition(p + 1, QTextCursor.MoveMode.KeepAnchor)
    f = c.charFormat()
    if f.foreground().style() == Qt.BrushStyle.NoBrush:
        return None
    col = f.foreground().color()
    return col.name().lower(), col.alpha()

def shown(p, d=None):
    """(name, alpha) the editor DRAWS for the char right of p: a highlighter
    override from the block layout if there is one, else the stored colour."""
    d = d or doc
    blk = d.findBlock(p)
    rel = p - blk.position()
    for r in blk.layout().formats():
        if r.start <= rel < r.start + r.length and \
                r.format.foreground().style() != Qt.BrushStyle.NoBrush:
            col = r.format.foreground().color()
            return col.name().lower(), col.alpha()
    return stored(p, d)

def fresh(html, note=None):
    note = note or n
    note.text_edit.setCurrentCharFormat(QTextCharFormat())
    note.text_edit.setHtml(html); app.processEvents()

def palette_html(cols):
    return "".join(f'<p><span style="color:{c}">x</span></p>' for c in cols)

def per_block(fn, d=None):
    d = d or doc
    return [fn(d.findBlockByNumber(i).position(), d)[0] for i in range(d.blockCount())]

# ── the picker shows the set for the note's ink ───────────────────────────────
swatches = []
def _capture_exec(self):
    swatches.clear()
    for b in self.findChildren(QPushButton):
        m = re.search(r"background-color:\s*(#[0-9a-fA-F]{6})", b.styleSheet())
        if m:
            swatches.append(m.group(1).lower())
    return QDialog.DialogCode.Rejected
_real_exec = QDialog.exec
QDialog.exec = _capture_exec
set_base(n, LIGHT_NOTE); n._open_text_color_picker()
check("picker on a light note shows the light set", swatches == LIGHT)
set_base(n, DARK_NOTE); n._open_text_color_picker()
check("picker on a dark note shows the dark set", swatches == DARK)
marked = []
def _capture_marked(self):
    marked.clear()
    for b in self.findChildren(QPushButton):
        css = b.styleSheet().split("QPushButton:hover")[0]
        m = re.search(r"background-color:\s*(#[0-9a-fA-F]{6})", css)
        if m and "2px solid" in css:
            marked.append(m.group(1).lower())
    return QDialog.DialogCode.Rejected
QDialog.exec = _capture_marked
fresh(f'<p><span style="color:{LIGHT[12]}">x</span></p>')
c = te.textCursor(); c.setPosition(1); te.setTextCursor(c); app.processEvents()
n._open_text_color_picker()
check("dark note, text in the white pair: the picker marks the WHITE swatch (what you see)",
      marked == ["#ffffff"])
fresh(f'<p><span style="color:#1565c0">plavo</span></p>')
c = te.textCursor(); c.setPosition(2); te.setTextCursor(c); app.processEvents()
n._open_text_color_picker()
check("dark note, blue text: the picker marks the dark blue twin", marked == [TWIN["#1565c0"]])
QDialog.exec = _real_exec

# ── a flip changes the DISPLAY, never the document ────────────────────────────
set_base(n, LIGHT_NOTE); fresh(palette_html(LIGHT))
doc.clearUndoRedoStacks()
set_base(n, DARK_NOTE)
check("light→dark: the document still stores the light colours", per_block(stored) == LIGHT)
check("light→dark: the editor DRAWS every dark twin", per_block(shown) == DARK)
check("light→dark: the flip is not an undo step", not doc.isUndoAvailable())
set_base(n, LIGHT_NOTE)
check("dark→light: no override left, drawn = stored = light", per_block(shown) == LIGHT)
set_base(n, "#3b2a31"); set_base(n, DARK_NOTE)
check("dark→dark (Wine→Charcoal): still the dark twins", per_block(shown) == DARK)

# ── picking a swatch on a dark note stores the real (light) colour ───────────
set_base(n, DARK_NOTE); fresh("<p>abc</p>")
c = te.textCursor(); c.setPosition(0); c.setPosition(3, QTextCursor.MoveMode.KeepAnchor); te.setTextCursor(c)
n._apply_text_color(TWIN["#e53935"])          # the swatch the dark picker shows
check("dark note, pick the (dark) red swatch: stored as the real red", stored(0)[0] == "#e53935")
check("…and drawn as the dark red twin", shown(0)[0] == TWIN["#e53935"])

# ── typing with a picked colour, then a flip ──────────────────────────────────
set_base(n, LIGHT_NOTE); fresh("<p>abc</p>")
c = te.textCursor(); c.movePosition(QTextCursor.MoveOperation.End); te.setTextCursor(c)
n._apply_text_color("#1565c0"); set_base(n, DARK_NOTE)
te.setFocus(); QTest.keyClicks(te, "X"); app.processEvents()
check("typed after a flip: drawn in the dark blue twin (readable)", shown(3)[0] == TWIN["#1565c0"])

# ── copy from a dark note: the clipboard carries the real colours ─────────────
set_base(n, LIGHT_NOTE); fresh('<p><span style="color:#000000">crno</span></p>')
set_base(n, DARK_NOTE)        # written on a light note, then the theme flipped
c = te.textCursor(); c.select(QTextCursor.SelectionType.Document); te.setTextCursor(c)
md = te.createMimeDataFromSelection()
check("copy from a dark note: clipboard HTML has the real black, not near-white",
      "#000000" in md.html().lower() and TWIN["#000000"] not in md.html().lower())
m = app.create_new_note(); m.show(); set_base(m, LIGHT_NOTE)
m.text_edit.setFocus(); m.text_edit.insertFromMimeData(md); app.processEvents()
check("…pasted into a light note it is black (readable)",
      shown(0, m.text_edit.document())[0] == "#000000")

# ── pasting a dark-side colour stores its real (light) colour ─────────────────
set_base(m, DARK_NOTE); fresh("<p></p>", m)
md2 = QMimeData(); md2.setHtml(f'<span style="color:{TWIN["#1565c0"]}">plavo</span>'); md2.setText("plavo")
m.text_edit.insertFromMimeData(md2); app.processEvents()
md_doc = m.text_edit.document()
check("paste of a dark-side colour (e.g. copied by the old build): stored as the real colour",
      stored(0, md_doc)[0] == "#1565c0")
check("…drawn as its dark twin on this dark note", shown(0, md_doc)[0] == TWIN["#1565c0"])

# ── load: dark-side colours saved by the old build are made real, no undo ─────
html = palette_html(DARK) + '<p><a href="https://example.com">link</a></p>'
ld = StickyNote(app, data={"content": html, "content_type": "html", "color": DARK_NOTE})
ld.show(); app.processEvents()
ld_doc = ld.text_edit.document()
check("load: dark-side colours become the real light colours in the document",
      [stored(ld_doc.findBlockByNumber(i).position(), ld_doc)[0] for i in range(16)] == LIGHT)
check("load: drawn as the dark twins", [shown(ld_doc.findBlockByNumber(i).position(), ld_doc)[0]
                                        for i in range(16)] == DARK)
check("load leaves NO undo step (Ctrl+Z after opening did turn links Qt-blue)",
      not ld_doc.isUndoAvailable())
lt = StickyNote(app, data={"content": '<p><span style="color:#ffffff">bijelo</span></p>',
                           "content_type": "html", "color": LIGHT_NOTE})
app.processEvents()
check("old white text on a light note becomes the readable light twin",
      stored(0, lt.text_edit.document())[0] == LIGHT[12])

# ── exports ───────────────────────────────────────────────────────────────────
set_base(n, LIGHT_NOTE)
fresh('<p><span style="color:#000000">crno</span> <span style="color:#1565c0">plavo</span></p>')
set_base(n, DARK_NOTE)
p = os.path.join(_SB, "x.odt"); export.to_odt(doc, p)
odt = zipfile.ZipFile(p).read("content.xml").decode().lower()
check("ODT from a dark note (white paper): the real colours",
      "#000000" in odt and "#1565c0" in odt and TWIN["#000000"] not in odt)
clone_hook = getattr(export, "_display_palette", None)
check("export has a helper that maps a clone to the dark display", callable(clone_hook))
if callable(clone_hook):
    clone = doc.clone(); clone_hook(clone, True)
    check("PDF clone of a dark note: dark twins (the page is dark)",
          stored(0, clone)[0] == TWIN["#000000"] and stored(5, clone)[0] == TWIN["#1565c0"])
    check("…the live note's document is untouched", stored(0)[0] == "#000000")
    calls = []
    orig = export._display_palette
    export._display_palette = lambda d, dark: (calls.append(dark), orig(d, dark))
    export.to_pdf(doc, os.path.join(_SB, "x.pdf"), DARK_NOTE)
    export.to_pdf(doc, os.path.join(_SB, "y.pdf"), LIGHT_NOTE)
    export._display_palette = orig
    check("to_pdf maps the palette for a dark page only", calls == [True, False])

# ── non-palette colours and links are left alone ──────────────────────────────
set_base(n, LIGHT_NOTE)
fresh('<p><span style="color:#123456">vlastita</span> '
      '<a href="https://example.com">example.com</a></p>')
set_base(n, LIGHT_NOTE)
set_base(n, DARK_NOTE)
check("a colour outside the palette is not touched", shown(0)[0] == "#123456")
check("a link keeps its own (link) colour, not a palette twin",
      shown(len("vlastita "))[0] == theme.link_color("web", True))

# ── a done (faded) checklist item keeps its fade in the display ───────────────
set_base(n, LIGHT_NOTE)
te.setCurrentCharFormat(QTextCharFormat()); te.setPlainText("gotovo")
c = te.textCursor(); c.setPosition(0); te.setTextCursor(c); te.toggle_checklist()
c = te.textCursor(); c.setPosition(2); c.setPosition(len("☐ gotovo"), QTextCursor.MoveMode.KeepAnchor)
te.setTextCursor(c); n._apply_text_color("#e53935")
te.toggle_checkbox(0); app.processEvents()
set_base(n, DARK_NOTE)
check("done red item on a dark note: stored real red, faded",
      stored(3)[0] == "#e53935" and stored(3)[1] < 255)
check("…drawn as the dark red twin with the same fade",
      shown(3) == (TWIN["#e53935"], stored(3)[1]))

print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
