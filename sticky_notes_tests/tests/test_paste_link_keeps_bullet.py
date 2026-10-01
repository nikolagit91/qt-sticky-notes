"""Pasting rich text (a browser-copied link) into a bullet keeps the bullet.

Qt's HTML insert brings its own block format, which REPLACES the current one —
so pasting a link copied from a browser into a bullet line knocked that line out
of its QTextList and the bullet vanished *at paste time*. (A file/folder drop
goes through the hasUrls path and was never affected.)"""
import sys, os, tempfile, atexit, shutil
_SB = tempfile.mkdtemp(prefix="sn_pastebullet_")
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
from PyQt6.QtCore import Qt, QEvent, QMimeData, QUrl
from PyQt6.QtGui import QKeyEvent, QTextCursor, QTextListFormat
QMessageBox.information = staticmethod(lambda *a, **k: None)

fails = []
def check(name, cond):
    print(f"  {'PASS' if cond else 'FAIL'}   {name}")
    if not cond: fails.append(name)

from sticky_notes.app import StickyNotesApp

app = StickyNotesApp(sys.argv[:1])
for e in list(app.notes.values()):
    e.hide(); e.deleteLater()
app.notes.clear()
n = app.create_new_note(); te = n.text_edit
n.resize(420, 260); n.show(); app.processEvents()

def first_block_in_list():
    b = te.document().findBlockByNumber(0)
    return QTextCursor(b).currentList() is not None

def fresh_bullet():
    te.clear(); app.processEvents()
    n._fmt_bullet(QTextListFormat.Style.ListDisc); app.processEvents()

def backspace_at_end_of_first_block():
    b0 = te.document().findBlockByNumber(0)
    c = te.textCursor(); c.setPosition(b0.position() + len(b0.text()))
    te.setTextCursor(c)
    te.keyPressEvent(QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Backspace,
                               Qt.KeyboardModifier.NoModifier))
    app.processEvents()

# ── the reported case: browser-copied link (text/html) ──────────────────────
fresh_bullet()
md = QMimeData()
md.setHtml('<a href="http://example.com">example.com</a>')
md.setText("example.com")
te.insertFromMimeData(md); app.processEvents()
check("html paste keeps the line in the bullet list", first_block_in_list())
check("html paste actually inserted the link text",
      "example.com" in te.document().findBlockByNumber(0).text())

# and deleting that link must still leave the bullet
backspace_at_end_of_first_block()
check("deleting the pasted link leaves the bullet", first_block_in_list())
check("the line is empty after deleting the link",
      te.document().findBlockByNumber(0).text() == "")

# ── file/folder drop (hasUrls path) — was already fine, keep it that way ────
fresh_bullet()
md2 = QMimeData(); md2.setUrls([QUrl.fromLocalFile("/home")])
te.insertFromMimeData(md2); app.processEvents()
check("file-url drop keeps the bullet", first_block_in_list())
backspace_at_end_of_first_block()
check("deleting a file link leaves the bullet", first_block_in_list())

# ── plain-text URL paste (linkify path) — also unaffected ──────────────────
fresh_bullet()
md3 = QMimeData(); md3.setText("http://example.com")
te.insertFromMimeData(md3); app.processEvents()
check("plain url paste keeps the bullet", first_block_in_list())

# ── rich paste OUTSIDE a list must not invent a list ───────────────────────
te.clear(); app.processEvents()
md4 = QMimeData(); md4.setHtml('<a href="http://x.com">x</a>'); md4.setText("x")
te.insertFromMimeData(md4); app.processEvents()
check("rich paste outside a list doesn't create one", not first_block_in_list())

print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
