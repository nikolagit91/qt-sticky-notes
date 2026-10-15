"""Typing after a link must not inherit the link's colour.

The caret sitting just after a link carries that link's char format. The
link-edit guard already strips the anchor/href/underline before an insert, but
it left the FOREGROUND colour, so a new line (Enter) — or text typed right after
a link — came out in link blue/violet/amber. Clearing the foreground lets the
text fall back to the note's default ink (which follows auto-contrast)."""
import sys, os, tempfile, atexit, shutil
_SB = tempfile.mkdtemp(prefix="sn_linkbleed_")
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
from PyQt6.QtCore import Qt, QEvent, QMimeData
from PyQt6.QtGui import QKeyEvent, QTextCursor, QTextListFormat
QMessageBox.information = staticmethod(lambda *a, **k: None)

fails = []
def check(name, cond):
    print(f"  {'PASS' if cond else 'FAIL'}   {name}")
    if not cond: fails.append(name)

from sticky_notes.app import StickyNotesApp
from sticky_notes.widgets import _LINK_COLOR_WEB

app = StickyNotesApp(sys.argv[:1])
for e in list(app.notes.values()):
    e.hide(); e.deleteLater()
app.notes.clear()
n = app.create_new_note(); te = n.text_edit; n.show(); app.processEvents()

def paste_link():
    md = QMimeData(); md.setText("http://example.com")
    te.insertFromMimeData(md); app.processEvents()

def caret_to_end():
    c = te.textCursor(); c.movePosition(QTextCursor.MoveOperation.EndOfBlock)
    te.setTextCursor(c)

def key(k):
    te.keyPressEvent(QKeyEvent(QEvent.Type.KeyPress, k, Qt.KeyboardModifier.NoModifier))
    app.processEvents()

# ── Enter right after a link → the new line must not type in link colour ─────
te.clear(); paste_link(); caret_to_end()
f = te.currentCharFormat()
check("caret right after a link does carry the link format (precondition)",
      f.isAnchor() and f.foreground().color().name() == _LINK_COLOR_WEB)

key(Qt.Key.Key_Return)
f = te.currentCharFormat()
check("after Enter the anchor is cleared", not f.isAnchor())
check("after Enter the underline is cleared", not f.fontUnderline())
check("after Enter the LINK COLOUR is gone",
      f.foreground().color().name() != _LINK_COLOR_WEB)

# ── same inside a bullet list (the user's report) ────────────────────────────
te.clear(); app.processEvents()
n._fmt_bullet(QTextListFormat.Style.ListDisc)
paste_link(); caret_to_end()
key(Qt.Key.Key_Return)
f = te.currentCharFormat()
check("bullet list: new item doesn't inherit the link colour",
      f.foreground().color().name() != _LINK_COLOR_WEB)
check("bullet list: still in the list after Enter",
      te.textCursor().currentList() is not None)

# ── typing a printable char straight after a link ───────────────────────────
te.clear(); paste_link(); caret_to_end()
te.keyPressEvent(QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_A,
                           Qt.KeyboardModifier.NoModifier, "a"))
app.processEvents()
f = te.currentCharFormat()
check("typing right after a link doesn't come out link-coloured",
      f.foreground().color().name() != _LINK_COLOR_WEB)

# ── a colour the USER picks right after a link is kept (2026-10-15) ──────────
# Only a recognised LINK colour may be cleared; clearing every foreground also
# threw away a colour just picked from the toolbar (it lands in the same
# anchor-carrying typing format), so the text came out in the note's ink.
te.clear(); paste_link(); caret_to_end()
n._apply_text_color("#c62828")
te.keyPressEvent(QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_A,
                           Qt.KeyboardModifier.NoModifier, "a"))
app.processEvents()
c = QTextCursor(te.document()); c.movePosition(QTextCursor.MoveOperation.End)
f = c.charFormat()
check("colour picked right after a link: typed text uses it",
      f.foreground().color().name() == "#c62828")
check("colour picked right after a link: typed text is not a link", not f.isAnchor())

te.clear(); paste_link(); caret_to_end()
n._apply_text_color("#c62828")
key(Qt.Key.Key_Return)
f = te.currentCharFormat()
check("colour picked right after a link: survives Enter to a new line",
      f.foreground().color().name() == "#c62828" and not f.isAnchor())

# ── the link itself keeps its colour ────────────────────────────────────────
te.clear(); paste_link(); caret_to_end()
te.keyPressEvent(QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_A,
                           Qt.KeyboardModifier.NoModifier, "a"))
doc = te.document()
c = QTextCursor(doc); c.setPosition(1)
check("the link text itself is still link-coloured",
      c.charFormat().foreground().color().name() == _LINK_COLOR_WEB)

print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
