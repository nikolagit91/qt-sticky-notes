"""Guard: the toolbar's text-colour "A" shows the text colour AT THE CARET (or the
selection's first char), like every other toolbar control (B/I/U/S, size,
family) — and text with no colour of its own shows the note's ink, so the "A"
is never black-on-dark. The colour picker marks that same colour.

Before (2026-10-15): the "A" showed only the LAST PICKED colour, starting at
#000000 on every note (black on a dark note), never followed the caret, and
the picker marked the last pick rather than the text you were in.
Links don't count as a text colour (their colour marks the link; the picker
never recolours them).
"""
import sys, os, tempfile, atexit, shutil, re
_SB = tempfile.mkdtemp(prefix="sn_tcb_")
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

from PyQt6.QtWidgets import QMessageBox, QDialog, QPushButton
QMessageBox.information = staticmethod(lambda *a, **k: None)
from PyQt6.QtGui import QTextCursor, QColor, QTextCharFormat
from PyQt6.QtTest import QTest
from sticky_notes.app import StickyNotesApp
from sticky_notes.theme import note_ink

app = StickyNotesApp(sys.argv[:1])
for e in list(app.notes.values()):
    e.hide(); e.deleteLater()
app.notes.clear()
n = app.create_new_note(); te = n.text_edit; doc = te.document()
n.show(); app.processEvents()
BLUE, RED = "#1565c0", "#e53935"

def glyph():
    return re.search(r"color:\s*(#[0-9a-fA-F]{6})", n.btn_text_color.styleSheet()).group(1).lower()

def ink():
    return note_ink(n._qcolor_base, auto=getattr(app, "_auto_contrast", True)).text.lower()

def set_base(hex_):
    n._qcolor_base = QColor(hex_); n._apply_ink()

def caret(p):
    c = te.textCursor(); c.setPosition(p); te.setTextCursor(c); app.processEvents()

def fresh(html):
    te.setCurrentCharFormat(QTextCharFormat())
    te.setHtml(html); app.processEvents()

# ── starting state follows the note's ink, light and dark ────────────────────
set_base("#fff59d"); fresh("<p>obicno</p>"); caret(3)
check("light note, default text: 'A' shows the note ink", glyph() == ink())
set_base("#2b2b2b")
check("dark note, default text: 'A' shows the (light) ink, not black",
      glyph() == ink() and glyph() != "#000000")
set_base("#fff59d")

# ── follows the caret / selection ────────────────────────────────────────────
fresh(f'<p>crno <span style="color:{BLUE}">plavo</span> crno</p>')
caret(8)
check("caret in blue text: 'A' is blue", glyph() == BLUE)
caret(2)
check("caret back in default text: 'A' is the ink again", glyph() == ink())
c = te.textCursor(); c.setPosition(6); c.setPosition(10, QTextCursor.MoveMode.KeepAnchor)
te.setTextCursor(c); app.processEvents()
check("selection starting in blue: 'A' is blue", glyph() == BLUE)

# ── picking a colour shows it at once ────────────────────────────────────────
fresh("<p>obicno</p>"); caret(6)
n._apply_text_color(RED)
check("pick red, no selection: 'A' red immediately (typing format)", glyph() == RED)
QTest.keyClicks(te, "x"); app.processEvents()
check("…and still red after typing in it", glyph() == RED)
fresh("<p>obicno</p>")
c = te.textCursor(); c.setPosition(0); c.setPosition(6, QTextCursor.MoveMode.KeepAnchor)
te.setTextCursor(c); n._apply_text_color(RED)
check("pick red on a selection: 'A' red", glyph() == RED)

# ── selection starting in a CHECKED row: the row keeps its colour, so must "A" ─
te.setCurrentCharFormat(QTextCharFormat())
te.setPlainText("gotovo\nostalo")
for bn in (0, 1):
    c = te.textCursor(); c.setPosition(doc.findBlockByNumber(bn).position())
    te.setTextCursor(c); te.toggle_checklist()
te.toggle_checkbox(doc.findBlockByNumber(0).position())
done = QTextCursor(doc); done.setPosition(3); done.setPosition(4, QTextCursor.MoveMode.KeepAnchor)
done_colour = done.charFormat().foreground().color().name()
c = te.textCursor(); c.setPosition(2); c.setPosition(doc.characterCount() - 1, QTextCursor.MoveMode.KeepAnchor)
te.setTextCursor(c); n._apply_text_color(RED)
check("pick red with selection starting in a checked row: 'A' shows that row's "
      "real (kept) colour, not red", glyph() == done_colour and done_colour != RED)

# ── links don't count as a text colour ───────────────────────────────────────
fresh('<p>vidi <a href="https://example.com">example.com</a></p>')
caret(len("vidi example.com"))
check("caret right after a link: 'A' shows the ink, not link blue", glyph() == ink())

# ── note colour / theme change re-reads the caret's colour ────────────────────
fresh("<p>obicno</p>"); caret(3)
set_base("#2b2b2b")
check("ink flip with caret in default text: 'A' follows the new ink", glyph() == ink())
set_base("#fff59d")
fresh(f'<p><span style="color:{BLUE}">plavo</span></p>'); caret(3)
set_base("#2b2b2b")
check("ink flip with caret in blue text: 'A' stays blue", glyph() == BLUE)
set_base("#fff59d")

# ── the picker marks the caret's colour ──────────────────────────────────────
shown = []
def _capture_exec(self):
    for b in self.findChildren(QPushButton):
        m = re.search(r"background-color:\s*(#[0-9a-fA-F]{6})", b.styleSheet())
        if m and "2px solid" in b.styleSheet().split("QPushButton:hover")[0]:
            shown.append(m.group(1).lower())
    return QDialog.DialogCode.Rejected
QDialog.exec = _capture_exec
fresh(f'<p>crno <span style="color:{BLUE}">plavo</span></p>'); caret(8)
n._open_text_color_picker()
check("picker marks the caret's colour (blue)", shown == [BLUE])

print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
