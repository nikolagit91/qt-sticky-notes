"""List markers must survive text formatting and editing.

Two classes of bug this locks down:
1. Bullet lists: applying a code block across a multi-line selection stamped the
   BLOCK char format (stored at the paragraph separator inside the selection)
   with monospace, so Qt drew that item's bullet in monospace → the marker
   shifted out of line with its siblings.
2. Checklists: the box is a real character at the start of the line, so a
   triple-click selection included it and code/inline formatting shrank it, and
   Backspace ate it even on a line that still had text.
"""
import sys, os, tempfile, atexit, shutil

_SB = tempfile.mkdtemp(prefix="sn_marker_")
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
from PyQt6.QtGui import QTextCursor, QTextListFormat, QKeyEvent
from PyQt6.QtCore import Qt, QEvent

from sticky_notes.app import StickyNotesApp
from sticky_notes.widgets import CHECK_EMPTY, CHECK_DONE

fails = []
def check(name, cond):
    print(f"  {'PASS' if cond else 'FAIL'}   {name}")
    if not cond: fails.append(name)

app = StickyNotesApp(sys.argv[:1])
app._snap_to_grid = app._snap_to_notes = app._snap_size = False

MONO = "Monospace"

def fresh(text=""):
    """A brand-new note per scenario — a shared one leaks the monospace typing
    format from an earlier case and makes 'unchanged' assertions pass falsely."""
    n = app.create_new_note()
    n.text_edit.setPlainText(text)
    return n.text_edit, n.text_edit.document()

def backspace(te):
    te.keyPressEvent(QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Backspace,
                               Qt.KeyboardModifier.NoModifier))

def delete_key(te):
    te.keyPressEvent(QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Delete,
                               Qt.KeyboardModifier.NoModifier))

def char_font(doc, pos):
    """Font families of the single character at `pos`."""
    p = QTextCursor(doc); p.setPosition(pos)
    p.setPosition(pos + 1, QTextCursor.MoveMode.KeepAnchor)
    return p.charFormat().fontFamilies() or []

def box_is_mono(doc, block):
    """True if the box glyph got restyled to the code font."""
    return MONO in char_font(doc, block.position())

# ── 1. Bullet marker keeps the note font when code is applied across items ────
te, doc = fresh("one\ntwo\nthree")
c = QTextCursor(doc); c.movePosition(QTextCursor.MoveOperation.Start)
c.movePosition(QTextCursor.MoveOperation.End, QTextCursor.MoveMode.KeepAnchor)
te.setTextCursor(c)
lf = QTextListFormat(); lf.setStyle(QTextListFormat.Style.ListDisc); c.createList(lf)
sel = QTextCursor(doc)
sel.setPosition(doc.findBlockByNumber(0).position())
sel.setPosition(doc.findBlockByNumber(1).position() + 3, QTextCursor.MoveMode.KeepAnchor)
te.setTextCursor(sel)
te.toggle_code_block()
fams1 = doc.findBlockByNumber(1).charFormat().fontFamilies() or []
check("bullet: 2nd item's block char format not monospaced (marker stays aligned)",
      MONO not in fams1)

# ── 2. Triple-click on a checklist line selects only the TEXT ─────────────────
te, doc = fresh("milk")
te.toggle_checklist()
b = doc.findBlockByNumber(0)
te.select_block_text(b)
cur = te.textCursor()
sel_text = doc.toPlainText()[cur.selectionStart():cur.selectionEnd()]
check("checklist: select_block_text excludes the box glyph", sel_text == "milk")

# ── 3. Inline code over a triple-click selection leaves the box untouched ─────
te, doc = fresh("milk")
te.toggle_checklist()
b = doc.findBlockByNumber(0)
te.select_block_text(b)
te.toggle_inline_code()
check("checklist: inline code does not restyle the box", not box_is_mono(doc, b))

# ── 3b. A MANUAL selection dragged over the box still must not restyle it ────
te, doc = fresh("milk")
te.toggle_checklist()
b = doc.findBlockByNumber(0)
c = te.textCursor()
c.setPosition(b.position())                                  # start ON the box
c.setPosition(b.position() + b.length() - 1, QTextCursor.MoveMode.KeepAnchor)
te.setTextCursor(c)
te.toggle_inline_code()
check("checklist: inline code over a manual selection spares the box",
      not box_is_mono(doc, b))
check("checklist: ...but the text still got inline code",
      MONO in char_font(doc, b.position() + 2))

# ── 4. Code block on a checklist line leaves the box untouched ────────────────
te, doc = fresh("eggs")
te.toggle_checklist()
b = doc.findBlockByNumber(0)
te.select_block_text(b)
te.toggle_code_block()
check("checklist: code block does not restyle the box", not box_is_mono(doc, b))

# ── 5. Backspace next to the marker on a line WITH text keeps the WHOLE prefix ─
te, doc = fresh("bread")
te.toggle_checklist()
b = doc.findBlockByNumber(0)
c = te.textCursor(); c.setPosition(b.position() + 2)   # right after "☐ "
te.setTextCursor(c)
backspace(te)
check("checklist: Backspace at text start keeps the full '☐ ' prefix",
      doc.findBlockByNumber(0).text().startswith(CHECK_EMPTY + " "))
check("checklist: ...and keeps the text", "bread" in doc.findBlockByNumber(0).text())

# ── 6. Backspace on an EMPTY checklist line drops the box → plain line ────────
te, doc = fresh("")
te.toggle_checklist()
c = te.textCursor(); c.movePosition(QTextCursor.MoveOperation.EndOfBlock)
te.setTextCursor(c)
backspace(te)
check("checklist: Backspace on an empty item drops the box",
      doc.findBlockByNumber(0).text()[:1] not in (CHECK_EMPTY, CHECK_DONE))

# ── 6b. Delete (forward) from IN FRONT of the box must not eat it ────────────
te, doc = fresh("bread")
te.toggle_checklist()
b = doc.findBlockByNumber(0)
c = te.textCursor(); c.setPosition(b.position())          # caret in front of the box
te.setTextCursor(c)
delete_key(te)
check("checklist: Delete in front of the box keeps the '☐ ' prefix",
      doc.findBlockByNumber(0).text().startswith(CHECK_EMPTY + " "))
check("checklist: ...and keeps the text", "bread" in doc.findBlockByNumber(0).text())

# ── 6c. Delete between box and space must not eat the space ──────────────────
te, doc = fresh("bread")
te.toggle_checklist()
b = doc.findBlockByNumber(0)
c = te.textCursor(); c.setPosition(b.position() + 1)
te.setTextCursor(c)
delete_key(te)
check("checklist: Delete between box and space keeps the prefix",
      doc.findBlockByNumber(0).text().startswith(CHECK_EMPTY + " "))

# ── 6d. Delete AT the text start still edits text normally (not over-protected) ─
te, doc = fresh("bread")
te.toggle_checklist()
b = doc.findBlockByNumber(0)
c = te.textCursor(); c.setPosition(b.position() + 2)
te.setTextCursor(c)
delete_key(te)
check("checklist: Delete at text start still deletes a text char",
      doc.findBlockByNumber(0).text() == CHECK_EMPTY + " read")

# ── 6e. Delete on an EMPTY item still drops the box (no lost convenience) ────
te, doc = fresh("")
te.toggle_checklist()
b = doc.findBlockByNumber(0)
c = te.textCursor(); c.setPosition(b.position())
te.setTextCursor(c)
delete_key(te)
check("checklist: Delete on an empty item drops the box",
      doc.findBlockByNumber(0).text()[:1] not in (CHECK_EMPTY, CHECK_DONE))

# ── 7. Backspace on a CHECKED item still removes the whole row (kept feature) ─
te, doc = fresh("done thing")
te.toggle_checklist()
te.toggle_checkbox(doc.findBlockByNumber(0).position())
check("checklist: item is now checked", doc.findBlockByNumber(0).text()[:1] == CHECK_DONE)
c = te.textCursor(); c.movePosition(QTextCursor.MoveOperation.EndOfBlock)
te.setTextCursor(c)
backspace(te)
check("checklist: Backspace on a checked item still deletes the whole row",
      "done thing" not in doc.toPlainText())

print("FAILS:", fails)
sys.exit(1 if fails else 0)
