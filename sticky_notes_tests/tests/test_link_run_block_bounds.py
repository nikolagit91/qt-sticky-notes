"""Deleting a link must never eat the paragraph separator.

_link_run walked raw document positions, so at the start of a block it stepped
onto the PREVIOUS block's paragraph separator (whose char format still carries
the link's href) and swallowed it. Deleting that run merged the line into the
one above — destroying the list item, so the bullet vanished. Only a link on the
very first block was safe (position 0 can't step back).

A link never spans paragraphs, so the run is clamped to its own block.
"""
import sys, os, tempfile, atexit, shutil
_SB = tempfile.mkdtemp(prefix="sn_linkrun_")
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

app = StickyNotesApp(sys.argv[:1])
for e in list(app.notes.values()):
    e.hide(); e.deleteLater()
app.notes.clear()
n = app.create_new_note(); te = n.text_edit
n.resize(420, 300); n.show(); app.processEvents()

def key(k):
    te.keyPressEvent(QKeyEvent(QEvent.Type.KeyPress, k, Qt.KeyboardModifier.NoModifier))
    app.processEvents()

def rows():
    d = te.document()
    return [(d.findBlockByNumber(i).text(),
             QTextCursor(d.findBlockByNumber(i)).currentList() is not None)
            for i in range(d.blockCount())]

def build_list_with_link_on(item_idx, html=True):
    """3 bullet items; the link sits on item_idx."""
    te.clear(); app.processEvents()
    n._fmt_bullet(QTextListFormat.Style.ListDisc); app.processEvents()
    for i in range(3):
        if i:
            key(Qt.Key.Key_Return)
        if i == item_idx:
            md = QMimeData()
            if html:
                md.setHtml('<a href="http://example.com">example.com</a>')
                md.setText("example.com")
            else:
                md.setText("http://example.com")
            te.insertFromMimeData(md)
        else:
            te.textCursor().insertText(f"item{i}")
        app.processEvents()

def backspace_at_end_of(item_idx):
    b = te.document().findBlockByNumber(item_idx)
    c = te.textCursor(); c.setPosition(b.position() + len(b.text()))
    te.setTextCursor(c)
    key(Qt.Key.Key_Backspace)

# ── the run must stay inside its own block, wherever the link sits ──────────
for idx in (0, 1, 2):
    build_list_with_link_on(idx)
    b = te.document().findBlockByNumber(idx)
    c = te.textCursor(); c.setPosition(b.position() + len(b.text()))
    run = te._link_run(c.position() - 1)
    check(f"item{idx}: run starts at/after the block start",
          run is not None and run[0] >= b.position())
    check(f"item{idx}: run ends at/before the block end",
          run is not None and run[1] <= b.position() + len(b.text()))

# ── deleting the link keeps the row AND its bullet, at every position ───────
for idx in (0, 1, 2):
    build_list_with_link_on(idx)
    before = len(rows())
    backspace_at_end_of(idx)
    after = rows()
    check(f"item{idx}: the row still exists after deleting the link",
          len(after) == before)
    check(f"item{idx}: the row is now empty", after[idx][0] == "")
    check(f"item{idx}: the row keeps its bullet", after[idx][1] is True)
    check(f"item{idx}: neighbouring items untouched",
          all(after[j][0] == f"item{j}" for j in (0, 1, 2) if j != idx))

# ── same for a plain-text URL link ─────────────────────────────────────────
build_list_with_link_on(1, html=False)
before = len(rows())
backspace_at_end_of(1)
after = rows()
check("plain-url link on item1: row survives with its bullet",
      len(after) == before and after[1][1] is True and after[1][0] == "")

print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
