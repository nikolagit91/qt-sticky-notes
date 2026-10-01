"""Plain text typed next to links must survive a save/reload as PLAIN text.

Reported symptom: a bullet item typed between two links came back UNDERLINED
after restarting the app. The note is persisted as HTML and rebuilt with
setHtml, so anything the caret picked up from a neighbouring link (anchor,
underline, colour) gets baked in and re-applied on load. This guards the
round-trip: the typed text stays un-underlined, un-anchored and in the note's
default ink, while the links keep theirs."""
import sys, os, tempfile, atexit, shutil
_SB = tempfile.mkdtemp(prefix="sn_linkrt_")
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
from sticky_notes.note import StickyNote
from sticky_notes.widgets import _LINK_COLOR_WEB

app = StickyNotesApp(sys.argv[:1])
for e in list(app.notes.values()):
    e.hide(); e.deleteLater()
app.notes.clear()
n = app.create_new_note(); te = n.text_edit
n.resize(420, 300); n.show(); app.processEvents()

def key(k):
    te.keyPressEvent(QKeyEvent(QEvent.Type.KeyPress, k, Qt.KeyboardModifier.NoModifier))
    app.processEvents()

def paste_link():
    md = QMimeData(); md.setText("http://example.com")
    te.insertFromMimeData(md); app.processEvents()

def type_text(s):
    for ch in s:
        te.keyPressEvent(QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_A,
                                   Qt.KeyboardModifier.NoModifier, ch))
    app.processEvents()

# bullet list: link / plain text / link  — the reported layout
te.clear(); app.processEvents()
n._fmt_bullet(QTextListFormat.Style.ListDisc); app.processEvents()
paste_link()
key(Qt.Key.Key_Return)
type_text("plain middle")
key(Qt.Key.Key_Return)
paste_link()
app.processEvents()

check("middle row typed as expected",
      te.document().findBlockByNumber(1).text() == "plain middle")

# round-trip exactly as the app persists it: get_data() -> a fresh note
data = n.get_data()
reloaded = StickyNote(app, data.get("id"), data)
rte = reloaded.text_edit
mid = rte.document().findBlockByNumber(1)
check("reloaded middle row text intact", mid.text() == "plain middle")

def char_fmt(block, i):
    c = QTextCursor(block.document())
    c.setPosition(block.position() + i)
    c.setPosition(block.position() + i + 1, QTextCursor.MoveMode.KeepAnchor)
    return c.charFormat()

bad_underline = [i for i in range(len(mid.text())) if char_fmt(mid, i).fontUnderline()]
bad_anchor    = [i for i in range(len(mid.text())) if char_fmt(mid, i).isAnchor()]
bad_colour    = [i for i in range(len(mid.text()))
                 if char_fmt(mid, i).foreground().color().name() == _LINK_COLOR_WEB]
check("no character of the middle row is underlined after reload", bad_underline == [])
check("no character of the middle row is a link after reload", bad_anchor == [])
check("no character of the middle row is link-coloured after reload", bad_colour == [])

# the links themselves must still be links after the round-trip
first = rte.document().findBlockByNumber(0)
check("the link above is still a link after reload", char_fmt(first, 1).isAnchor())
check("the link above keeps its colour after reload",
      char_fmt(first, 1).foreground().color().name() == _LINK_COLOR_WEB)

reloaded.hide(); reloaded.deleteLater()
print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
