import sys, os, tempfile, atexit, shutil
_SB = tempfile.mkdtemp(prefix="sn_icp_")
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
from PyQt6.QtCore import Qt, QMimeData, QPoint
from PyQt6.QtGui import QTextCursor

fails = []
def check(name, cond):
    print(f"  {'PASS' if cond else 'FAIL'}   {name}")
    if not cond: fails.append(name)

from sticky_notes.app import StickyNotesApp
from sticky_notes.note import StickyNote
from sticky_notes.widgets import CODE_FONT_FAMILY
app = StickyNotesApp(sys.argv[:1])

def char_at(te, pos):
    c = QTextCursor(te.document()); c.setPosition(pos)
    c.setPosition(pos + 1, QTextCursor.MoveMode.KeepAnchor)
    return c.charFormat()
def paste(te, text):
    md = QMimeData(); md.setText(text); te.insertFromMimeData(md)

# ── Paste inside an inline-code span keeps the pasted text inline (mono + char
#    background) instead of splitting the span with clean text.
note = StickyNote(app, "a", {"id": "a", "geometry": [0, 0, 300, 200]})
te = note.text_edit
c = te.textCursor(); c.insertText("code")
c = te.textCursor(); c.select(QTextCursor.SelectionType.Document); te.setTextCursor(c)
te.toggle_inline_code()                       # "code" → inline
c = te.textCursor(); c.movePosition(c.MoveOperation.End); te.setTextCursor(c)  # caret after span
paste(te, "XY")
check("text is inserted", te.document().toPlainText() == "codeXY")
f = char_at(te, 4)                            # first pasted char 'X'
check("pasted char is monospace", CODE_FONT_FAMILY in (f.fontFamilies() or []))
check("pasted char keeps the inline-code background",
      f.background().style() != Qt.BrushStyle.NoBrush)

# ── The pasted run must carry the SAME transparent marker as typed/toggled
#    inline code — the visible chip is painted in paintEvent. A real tinted
#    background made Qt paint it natively UNDER the painted chip → the pasted
#    part came out darker than the rest of the span (double tint).
check("pasted char carries the transparent inline marker (alpha 0)",
      f.background().color().alpha() == 0)

def chip_pixels(note, positions):
    """Rendered chip colour above the glyphs at each char position. Grabbed from
    the whole NOTE: the editor viewport is see-through, so grabbing it alone
    returns transparent pixels instead of what is on screen."""
    te = note.text_edit
    te.viewport().update(); app.processEvents()
    img = note.grab().toImage()
    rect = te._inline_run_rects()[0]
    out = []
    for pos in positions:
        c = QTextCursor(te.document()); c.setPosition(pos)
        pt = te.viewport().mapTo(note, QPoint(te.cursorRect(c).x() + 3, int(rect.top()) + 2))
        out.append(img.pixelColor(pt.x(), pt.y()).name())
    return out

def html_paste(te, text):
    """Like copying from a web page: rich HTML plus the plain-text flavour."""
    md = QMimeData(); md.setHtml(f"<span style='color:#202124'>{text}</span>"); md.setText(text)
    te.insertFromMimeData(md)

for label, do_paste in (("plain-text paste", paste), ("web (HTML) paste", html_paste)):
    n3 = StickyNote(app, label, {"id": label, "geometry": [0, 0, 360, 200], "color": "#fff59d"})
    n3.show(); app.processEvents()
    t3 = n3.text_edit
    c = t3.textCursor(); c.insertText("inline")
    c = t3.textCursor(); c.select(QTextCursor.SelectionType.Document); t3.setTextCursor(c)
    t3.toggle_inline_code()
    c = t3.textCursor(); c.setPosition(3); t3.setTextCursor(c)    # caret INSIDE the span: "inl|ine"
    do_paste(t3, "PASTED")
    check(f"{label}: text lands inside the span", t3.document().toPlainText() == "inlPASTEDine")
    before, pasted, after = chip_pixels(n3, (1, 5, 10))
    check(f"{label}: chip under pasted text matches the original part ({pasted} vs {before})",
          pasted == before)
    check(f"{label}: chip after the paste matches too ({after} vs {before})", after == before)
    n3.hide(); n3.deleteLater()

# ── Regression: pasting on a PLAIN line stays clean (not forced inline).
note2 = StickyNote(app, "b", {"id": "b", "geometry": [0, 0, 300, 200]})
te2 = note2.text_edit
c = te2.textCursor(); c.insertText("hi ")
c = te2.textCursor(); c.movePosition(c.MoveOperation.End); te2.setTextCursor(c)
paste(te2, "there")
f2 = char_at(te2, 3)                           # first pasted char 't'
check("paste on a plain line has no inline background",
      f2.background().style() == Qt.BrushStyle.NoBrush)
check("paste on a plain line is not monospace",
      CODE_FONT_FAMILY not in (f2.fontFamilies() or []))

note.hide(); note.deleteLater(); note2.hide(); note2.deleteLater()
print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
