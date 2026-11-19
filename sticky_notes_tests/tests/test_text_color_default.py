"""Guard: the text-colour picker has a "Default colour" entry that takes the
colour OFF the text, so it follows the note's ink again (light↔dark flip,
auto theme) — the same state as text that was never coloured.

Before (2026-11-13): the picker's black (#000000) was the only way "back", but
the note's default ink is #333333 on a light note (#f0f0f0 on a dark one), so
"black" text visibly differed from default text, never flipped with the note,
and the picker marked nothing on default text. There was no way to un-colour.
"""
import sys, os, tempfile, atexit, shutil, re
_SB = tempfile.mkdtemp(prefix="sn_tcd_")
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
RED, LIGHT, DARK = "#e53935", "#fff59d", "#2b2b2b"

def ink():
    return note_ink(n._qcolor_base, auto=getattr(app, "_auto_contrast", True)).text.lower()

def glyph():
    return re.search(r"color:\s*(#[0-9a-fA-F]{6})", n.btn_text_color.styleSheet()).group(1).lower()

def set_base(hex_):
    n._qcolor_base = QColor(hex_); n._apply_ink()

def fresh(html):
    te.setCurrentCharFormat(QTextCharFormat())
    te.setHtml(html); app.processEvents()

def select(a, b):
    c = te.textCursor(); c.setPosition(a); c.setPosition(b, QTextCursor.MoveMode.KeepAnchor)
    te.setTextCursor(c); app.processEvents()

def caret(p):
    c = te.textCursor(); c.setPosition(p); te.setTextCursor(c); app.processEvents()

def fg_at(p):
    """Foreground of the char right after position p: None = no colour of its own."""
    c = QTextCursor(doc); c.setPosition(p); c.setPosition(p + 1, QTextCursor.MoveMode.KeepAnchor)
    f = c.charFormat()
    if f.foreground().style() == Qt.BrushStyle.NoBrush:
        return None
    return f.foreground().color().name().lower()

def has_default_action():
    return callable(getattr(n, "_apply_default_text_color", None))

set_base(LIGHT)

# ── the picker offers "Default colour" and marks it on uncoloured text ────────
captured = {}
def _capture_exec(self):
    btn = self.findChild(QPushButton, "default_text_color")
    captured["btn"] = btn is not None
    captured["marked"] = bool(btn) and "2px solid" in btn.styleSheet().split("QPushButton:hover")[0]
    marked = []
    for b in self.findChildren(QPushButton):
        m = re.search(r"background-color:\s*(#[0-9a-fA-F]{6})", b.styleSheet())
        if m and "2px solid" in b.styleSheet().split("QPushButton:hover")[0]:
            marked.append(m.group(1).lower())
    captured["swatches_marked"] = marked
    captured["has_black"] = any(
        re.search(r"background-color:\s*#000000", b.styleSheet()) for b in self.findChildren(QPushButton))
    return QDialog.DialogCode.Rejected
_real_exec = QDialog.exec
QDialog.exec = _capture_exec

fresh("<p>obicno</p>"); caret(3)
n._open_text_color_picker()
check("picker has a 'Default colour' button", captured.get("btn"))
check("on uncoloured text the picker marks 'Default colour'", captured.get("marked"))
check("…and no colour swatch", captured.get("swatches_marked") == [])
check("black stays a real #000000 swatch", captured.get("has_black"))

fresh('<p><span style="color:#000000">crno</span></p>'); caret(2)
n._open_text_color_picker()
check("on black text the picker marks black, not 'Default colour'",
      captured.get("swatches_marked") == ["#000000"] and not captured.get("marked"))
# A checklist item made with Enter carries the ink EXPLICITLY (_plain_format) —
# it is still default text, so the picker must mark "Default colour".
te.setCurrentCharFormat(QTextCharFormat()); te.setPlainText("")
te.setFocus(); QTest.keyClicks(te, "prva"); te.toggle_checklist()
c = te.textCursor(); c.movePosition(QTextCursor.MoveOperation.End); te.setTextCursor(c)
QTest.keyClick(te, Qt.Key.Key_Return); QTest.keyClicks(te, "druga"); app.processEvents()
n._open_text_color_picker()
check("Enter-made checklist item (explicit ink): picker marks 'Default colour'",
      captured.get("marked") and captured.get("swatches_marked") == [])
QDialog.exec = _real_exec

check("note has a 'default text colour' action", has_default_action())
if not has_default_action():
    print(f"\n{len(fails)} FAIL"); sys.exit(1)

# ── selection: the colour comes off, the text follows the ink ─────────────────
fresh(f'<p><span style="color:{RED}">crveno</span> ostalo</p>')
select(0, 6)
n._apply_default_text_color()
check("selection: coloured chars lose their own colour",
      all(fg_at(i) is None for i in range(6)))
check("'A' shows the ink after Default", glyph() == ink())
set_base(DARK)
check("after a flip to a dark note the text still has no colour (follows light ink)",
      all(fg_at(i) is None for i in range(6)) and glyph() == ink() and ink() != "#333333")
set_base(LIGHT)

# ── one undo step brings the colour back ──────────────────────────────────────
te.undo(); app.processEvents()
check("one undo restores the red", all(fg_at(i) == RED for i in range(6)))

# ── no selection: typing after Default is uncoloured ──────────────────────────
fresh("<p>abc</p>"); caret(3)
n._apply_text_color(RED)
n._apply_default_text_color()
QTest.keyClicks(te, "x"); app.processEvents()
check("no selection: text typed after Default has no colour", fg_at(3) is None)

# ── links keep their link colour ──────────────────────────────────────────────
fresh(f'<p><span style="color:{RED}">vidi </span><a href="https://example.com">example.com</a></p>')
link_before = fg_at(6)
select(0, len("vidi example.com"))
n._apply_default_text_color()
check("link inside the selection keeps its link colour",
      link_before is not None and fg_at(6) == link_before)
check("text before the link lost its red", fg_at(0) is None)

# ── code block: Default means the code text colour, not the dark note ink ─────
fresh("<p>kod</p>"); caret(1)
te.toggle_code_block(); app.processEvents()
code_fg = te.code_fg_color.name().lower()
select(0, 3); n._apply_text_color(RED)
check("(setup) code text turned red", fg_at(0) == RED)
select(0, 3); n._apply_default_text_color()
check("Default inside a code block restores the code text colour",
      all(fg_at(i) == code_fg for i in range(3)))

# ── a checked (locked) checklist row is left alone ───────────────────────────
te.setCurrentCharFormat(QTextCharFormat())
te.setPlainText("gotovo\nostalo")
for bn in (0, 1):
    caret(doc.findBlockByNumber(bn).position()); te.toggle_checklist()
te.toggle_checkbox(doc.findBlockByNumber(0).position())
done_pos = doc.findBlockByNumber(0).position() + 3
done_before = fg_at(done_pos)
select(0, doc.characterCount() - 1)
n._apply_default_text_color()
check("checked row keeps its (faded) colour", fg_at(done_pos) == done_before and done_before)

print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
