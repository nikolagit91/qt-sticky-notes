"""Guard: a colour the user picks for checklist text survives a note-colour /
theme change, and picking a colour never leaks into NEW checklist items.

Root cause (2026-10-15): _apply_text_color also wrote the picked colour into
text_edit.checkbox_text_color — which _apply_ink treats as the note's DEFAULT
checklist ink. recolor_checklist(old_default → new_ink) recolours every
checklist char matching the old default, so after picking red, the user's red
counted as "default" and was reset to the ink on the next note-colour or theme
change (also the scheduled dark-theme switch). And new items (Enter) got red
boxes/text. Default-coloured checklist text must still follow the ink.
"""
import sys, os, tempfile, atexit, shutil
_SB = tempfile.mkdtemp(prefix="sn_cc_")
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
from sticky_notes.theme import note_ink

app = StickyNotesApp(sys.argv[:1])
for e in list(app.notes.values()):
    e.hide(); e.deleteLater()
app.notes.clear()
n = app.create_new_note(); te = n.text_edit; doc = te.document()
RED = "#e53935"

def colour_at(bn, off):
    b = doc.findBlockByNumber(bn)
    c = QTextCursor(doc); c.setPosition(b.position() + off)
    c.setPosition(b.position() + off + 1, QTextCursor.MoveMode.KeepAnchor)
    f = c.charFormat()
    if f.foreground().style() == Qt.BrushStyle.NoBrush:
        return ink()          # no own colour → drawn in the editor's ink (QSS)
    return f.foreground().color().name()

def ink():
    return note_ink(n._qcolor_base, auto=getattr(app, "_auto_contrast", True)).text

def set_base(hex_):
    n._qcolor_base = QColor(hex_); n._apply_ink()

def setup():
    """Two checklist rows; row 0's text coloured red by the user."""
    set_base("#fff59d")
    # setPlainText inherits the current typing format — after a red pick the
    # whole fresh text would come out red. Reset it.
    te.setCurrentCharFormat(QTextCharFormat())
    te.setPlainText("crveno\nobicno")
    for bn in (0, 1):
        c = te.textCursor(); c.setPosition(doc.findBlockByNumber(bn).position())
        te.setTextCursor(c); te.toggle_checklist()
    b = doc.findBlockByNumber(0)
    c = te.textCursor(); c.setPosition(b.position() + 2)
    c.setPosition(b.position() + len(b.text()), QTextCursor.MoveMode.KeepAnchor)
    te.setTextCursor(c)
    n._apply_text_color(RED)

setup()
check("(setup) row 0 text is the user's red", colour_at(0, 3) == RED)

# ── new item after picking a colour: note ink, not the picked colour ──────────
c = te.textCursor(); c.setPosition(doc.findBlockByNumber(1).position() + len("☐ obicno"))
te.setTextCursor(c); te._handle_checklist_enter()
check("new checklist item's box is in the note ink, not the picked colour",
      colour_at(2, 0) == ink())

# ── light → light note colour: user's red survives ───────────────────────────
setup(); set_base("#E3F2FD")
check("note colour change (light→light): user's red checklist text kept",
      colour_at(0, 3) == RED)

# ── light → dark (ink flips): red kept, default text follows the ink ─────────
setup(); set_base("#2b2b2b")
check("ink flip to dark: user's red checklist text kept", colour_at(0, 3) == RED)
check("ink flip to dark: default checklist text follows the new ink",
      colour_at(1, 3) == ink() and ink() != note_ink(QColor("#fff59d")).text)
check("ink flip to dark: boxes follow the new ink", colour_at(1, 0) == ink())
set_base("#fff59d")
check("and back to light: red still kept", colour_at(0, 3) == RED)

print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
