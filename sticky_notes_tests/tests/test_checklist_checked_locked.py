"""Guard: a CHECKED (☑) checklist row is locked. Its text can't be typed into,
pasted into, cut, IME-composed into, dropped into or dragged out of; any delete
that reaches it removes the WHOLE row (never leaves a bare "☑ " box or a partial
"☑ mli"). Structure stays free: Enter at the end adds a fresh item, Enter at the
start pushes the row down, Tab/Alt+↑↓ still work, a click on the box unchecks it.

Bug this guards (2026-10-14): typing into a checked row was allowed, but a single
Backspace anywhere in it deleted the whole row; selecting the row's text and
pressing Backspace emptied it and left a lone checked box.
"""
import sys, os, tempfile, atexit, shutil
_SB = tempfile.mkdtemp(prefix="sn_test_")
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

from PyQt6.QtWidgets import QMessageBox, QApplication, QMenu, QTextEdit
QMessageBox.information = staticmethod(lambda *a, **k: None)
from PyQt6.QtCore import Qt, QMimeData, QPointF, QPoint
from PyQt6.QtGui import (QTextCursor, QInputMethodEvent, QDropEvent, QMouseEvent,
                         QContextMenuEvent)
from PyQt6.QtTest import QTest
from sticky_notes.app import StickyNotesApp
from sticky_notes.widgets import CHECK_EMPTY, CHECK_DONE

app = StickyNotesApp(sys.argv[:1])
for e in list(app.notes.values()):
    e.hide(); e.deleteLater()
app.notes.clear()
note = app.create_new_note()
te = note.text_edit
doc = te.document()
note.show(); te.setFocus()

E, D = CHECK_EMPTY, CHECK_DONE
START = [f"{E} prvi", f"{D} mlijeko", f"{E} treci"]

def lines():
    return [doc.findBlockByNumber(i).text() for i in range(doc.blockCount())]

def setup(texts=("prvi", "mlijeko", "treci"), tick=(1,)):
    """Checklist rows from `texts`, rows in `tick` checked."""
    te.setPlainText("\n".join(texts))
    for bn in range(len(texts)):
        c = te.textCursor(); c.setPosition(doc.findBlockByNumber(bn).position())
        te.setTextCursor(c); te.toggle_checklist()
    for bn in tick:
        te.toggle_checkbox(doc.findBlockByNumber(bn).position())

def pos(bn, off):
    return doc.findBlockByNumber(bn).position() + off

def caret(p):
    c = te.textCursor(); c.setPosition(p); te.setTextCursor(c)

def select(a, b):
    c = te.textCursor(); c.setPosition(a); c.setPosition(b, QTextCursor.MoveMode.KeepAnchor)
    te.setTextCursor(c)

def key(k, mods=Qt.KeyboardModifier.NoModifier):
    QTest.keyClick(te, k, mods)

def no_partial_done():
    """No checked row survives in a damaged form (bare box or cut text)."""
    return all(not (t.startswith(D) and t != f"{D} mlijeko") for t in lines())

# ── typing ───────────────────────────────────────────────────────────────────
setup(); caret(pos(1, 5)); QTest.keyClicks(te, "XY")
check("typing in the middle of a checked row changes nothing", lines() == START)
setup(); caret(pos(1, len("☑ mlijeko"))); QTest.keyClicks(te, "XY")
check("typing at the end of a checked row changes nothing", lines() == START)
setup(); caret(pos(1, 0)); QTest.keyClicks(te, "XY")
check("typing before the box of a checked row changes nothing", lines() == START)
setup(); select(pos(1, 2), pos(1, 9)); QTest.keyClicks(te, "Z")
check("typing over a selection inside a checked row changes nothing", lines() == START)
setup(); select(pos(0, 3), pos(1, 5)); QTest.keyClicks(te, "Z")
check("typing over a selection reaching into a checked row changes nothing", lines() == START)
setup(); caret(pos(0, 6)); QTest.keyClicks(te, "!")
check("typing in an UNCHECKED row still works", lines()[0] == f"{E} prvi!")

# ── IME commit (e.g. č/ć via IBus) ─────────────────────────────────────────────
setup(); caret(pos(1, 5))
ev = QInputMethodEvent(); ev.setCommitString("č")
QApplication.sendEvent(te, ev)
check("IME commit into a checked row changes nothing", lines() == START)
setup(); caret(pos(0, 6))
ev = QInputMethodEvent(); ev.setCommitString("č")
QApplication.sendEvent(te, ev)
check("IME commit into an unchecked row still works", lines()[0] == f"{E} prvič")

# ── Backspace / Delete without a selection: whole row, anywhere ───────────────
for name, k in (("Backspace", Qt.Key.Key_Backspace), ("Delete", Qt.Key.Key_Delete)):
    for where, off in (("middle", 5), ("end", 9), ("after box", 2)):
        setup(); caret(pos(1, off)); key(k)
        check(f"{name} at {where} of a checked row deletes the whole row",
              lines() == [START[0], START[2]])
setup(); caret(pos(1, 5)); key(Qt.Key.Key_Backspace, Qt.KeyboardModifier.ControlModifier)
check("Ctrl+Backspace in a checked row deletes the whole row", lines() == [START[0], START[2]])

# ── the reported bug: select the row's text, Backspace ─────────────────────────
for name, k in (("Backspace", Qt.Key.Key_Backspace), ("Delete", Qt.Key.Key_Delete)):
    setup(); select(pos(1, 2), pos(1, 9)); key(k)
    check(f"select checked row's text + {name} → whole row gone (no bare box)",
          lines() == [START[0], START[2]])
    setup(); select(pos(1, 4), pos(1, 6)); key(k)
    check(f"select part of a checked row + {name} → whole row gone",
          lines() == [START[0], START[2]])

# ── multi-line selections partly covering a checked row ───────────────────────
setup(); select(pos(0, 4), pos(1, 5)); key(Qt.Key.Key_Backspace)
check("selection from row above into a checked row: checked row removed whole",
      lines() == [f"{E} pr", START[2]])
setup(); select(pos(1, 5), pos(2, 4)); key(Qt.Key.Key_Backspace)
check("selection from a checked row into the row below: no damaged ☑ left",
      no_partial_done() and f"{D} mlijeko" not in lines())
setup(); select(pos(0, 0), pos(2, len(START[2]))); key(Qt.Key.Key_Backspace)
check("select-all + Backspace still empties the note", "".join(lines()) == "")
# selection touching a checked row only at its boundary must not merge into it
setup(); select(pos(0, 4), pos(1, 0)); key(Qt.Key.Key_Backspace)
check("selection ending at a checked row's start: row above trimmed, checked row intact",
      lines() == [f"{E} pr", START[1], START[2]])
setup(); select(pos(1, 9), pos(2, 4)); key(Qt.Key.Key_Backspace)
check("selection starting at a checked row's end: checked row intact, nothing merged",
      lines()[1] == START[1] and len(lines()) == 3)

# ── merging into a checked row from a neighbour ───────────────────────────────
te.setPlainText("plain\nmlijeko\nplain2")
c = te.textCursor(); c.setPosition(doc.findBlockByNumber(1).position()); te.setTextCursor(c)
te.toggle_checklist(); te.toggle_checkbox(doc.findBlockByNumber(1).position())
base = lines()
caret(pos(2, 0)); key(Qt.Key.Key_Backspace)
check("Backspace at the start of a line below a checked row doesn't merge into it",
      lines() == base)
caret(pos(0, 5)); key(Qt.Key.Key_Delete)
check("Delete at the end of a line above a checked row doesn't merge it up",
      lines() == base)
te.setPlainText("\nmlijeko\n")
c = te.textCursor(); c.setPosition(doc.findBlockByNumber(1).position()); te.setTextCursor(c)
te.toggle_checklist(); te.toggle_checkbox(doc.findBlockByNumber(1).position())
indent_before = doc.findBlockByNumber(1).blockFormat().leftMargin()
caret(pos(2, 0)); key(Qt.Key.Key_Backspace)
check("Backspace on an EMPTY line below a checked row removes the empty line",
      lines() == ["", f"{D} mlijeko"])
caret(pos(0, 0)); key(Qt.Key.Key_Delete)
check("Delete on an EMPTY line above a checked row removes the empty line",
      lines() == [f"{D} mlijeko"]
      and doc.findBlockByNumber(0).blockFormat().leftMargin() == indent_before)

# ── Enter ─────────────────────────────────────────────────────────────────────
setup(); caret(pos(1, 9)); key(Qt.Key.Key_Return)
check("Enter at the end of a checked row adds a fresh unchecked item below",
      lines() == [START[0], START[1], f"{E} ", START[2]])
setup(); caret(pos(1, 5)); key(Qt.Key.Key_Return)
check("Enter in the middle of a checked row does nothing", lines() == START)
setup(); caret(pos(1, 0)); key(Qt.Key.Key_Return)
check("Enter at the start of a checked row pushes it down intact",
      lines() == [START[0], "", START[1], START[2]])
setup(); caret(pos(1, 5)); key(Qt.Key.Key_Return, Qt.KeyboardModifier.ShiftModifier)
check("Shift+Enter in a checked row does nothing", lines() == START)

# ── structure stays free ──────────────────────────────────────────────────────
setup(); caret(pos(1, 5)); key(Qt.Key.Key_Tab)
check("Tab still indents a checked row (text untouched)",
      doc.findBlockByNumber(1).blockFormat().indent() == 1 and lines()[1] == START[1])
setup(); caret(pos(1, 5)); key(Qt.Key.Key_Up, Qt.KeyboardModifier.AltModifier)
check("Alt+↑ still moves a checked row", lines() == [START[1], START[0], START[2]])
setup(); te.toggle_checkbox(pos(1, 0))
caret(pos(1, 9)); QTest.keyClicks(te, "X")
check("after unchecking, the row is editable again", lines()[1] == f"{E} mlijekoX")

# ── paste (Ctrl+V, Ctrl+Shift+V, insertFromMimeData) ──────────────────────────
QApplication.clipboard().setText("PASTE")
setup(); caret(pos(1, 5)); key(Qt.Key.Key_V, Qt.KeyboardModifier.ControlModifier)
check("Ctrl+V into a checked row changes nothing", lines() == START)
setup(); caret(pos(1, 5))
key(Qt.Key.Key_V, Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier)
check("Ctrl+Shift+V into a checked row changes nothing", lines() == START)
setup(); select(pos(1, 2), pos(1, 9)); te.paste()
check("paste over a checked row's text changes nothing", lines() == START)
setup(); caret(pos(0, 6)); te.paste()
check("paste into an unchecked row still works", lines()[0] == f"{E} prviPASTE")

# ── cut ───────────────────────────────────────────────────────────────────────
setup(); select(pos(1, 2), pos(1, 9)); key(Qt.Key.Key_X, Qt.KeyboardModifier.ControlModifier)
check("Ctrl+X on a checked row's text changes nothing", lines() == START)
setup(); select(pos(1, 2), pos(1, 9)); key(Qt.Key.Key_Delete, Qt.KeyboardModifier.ShiftModifier)
check("Shift+Delete (cut) on a checked row's text changes nothing", lines() == START)
setup(); select(pos(1, 2), pos(1, 9)); key(Qt.Key.Key_C, Qt.KeyboardModifier.ControlModifier)
check("Ctrl+C still copies a checked row's text",
      QApplication.clipboard().text() == "mlijeko" and lines() == START)

# ── context menu: editing actions disabled on a checked row ───────────────────
_menu_state = {}
_orig_exec = QMenu.exec
def _fake_exec(self, *a, **k):
    for act in self.actions():
        if act.objectName():
            _menu_state[act.objectName()] = act.isEnabled()
    return None
QMenu.exec = _fake_exec
setup(); select(pos(1, 2), pos(1, 9))
QApplication.sendEvent(te.viewport(), QContextMenuEvent(QContextMenuEvent.Reason.Mouse, QPoint(5, 5), QPoint(5, 5)))
check("context menu on a checked row: Cut disabled", _menu_state.get("edit-cut") is False)
check("context menu on a checked row: Paste disabled", _menu_state.get("edit-paste") is False)
check("context menu on a checked row: Delete disabled", _menu_state.get("edit-delete") is False)
check("context menu on a checked row: Copy still enabled", _menu_state.get("edit-copy") is True)
_menu_state.clear()
setup(); select(pos(0, 2), pos(0, 6))
QApplication.sendEvent(te.viewport(), QContextMenuEvent(QContextMenuEvent.Reason.Mouse, QPoint(5, 5), QPoint(5, 5)))
check("context menu on an unchecked row: Cut enabled", _menu_state.get("edit-cut") is True)
QMenu.exec = _orig_exec

# ── drop into a checked row ───────────────────────────────────────────────────
from PyQt6.QtGui import QDragEnterEvent, QDragMoveEvent
mime = QMimeData(); mime.setText("DROP")
def drop_at(p):
    """A full drag sequence (enter → move → drop) onto document position p, the
    way Qt delivers a real one. Returns whether the move was accepted."""
    c = QTextCursor(doc); c.setPosition(p); pt = te.cursorRect(c).center()
    args = (Qt.DropAction.CopyAction, mime, Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier)
    QApplication.sendEvent(te.viewport(), QDragEnterEvent(pt, *args))
    mv = QDragMoveEvent(pt, *args)
    QApplication.sendEvent(te.viewport(), mv)
    QApplication.sendEvent(te.viewport(), QDropEvent(QPointF(pt), *args))
    return mv.isAccepted()
setup(); accepted = drop_at(pos(1, 5))
check("dropping text into a checked row changes nothing", lines() == START)
check("drag-hover over a checked row is refused (no-drop cursor)", accepted is False)
setup(); drop_at(pos(0, 6))
check("dropping text into an unchecked row still works", "DROP" in lines()[0])

# ── dragging a checked row's text out (would MOVE it away) ────────────────────
_passed = []
_orig_move = QTextEdit.mouseMoveEvent
QTextEdit.mouseMoveEvent = lambda self, ev: _passed.append(True)
def press_and_move_inside_selection():
    _passed.clear()
    c = QTextCursor(doc); c.setPosition(te.textCursor().selectionStart() + 1)
    p = QPointF(te.cursorRect(c).center())
    te.mousePressEvent(QMouseEvent(QMouseEvent.Type.MouseButtonPress, p, p,
                                   Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton,
                                   Qt.KeyboardModifier.NoModifier))
    p2 = p + QPointF(40, 30)
    te.mouseMoveEvent(QMouseEvent(QMouseEvent.Type.MouseMove, p2, p2,
                                  Qt.MouseButton.NoButton, Qt.MouseButton.LeftButton,
                                  Qt.KeyboardModifier.NoModifier))
    te.mouseReleaseEvent(QMouseEvent(QMouseEvent.Type.MouseButtonRelease, p2, p2,
                                     Qt.MouseButton.LeftButton, Qt.MouseButton.NoButton,
                                     Qt.KeyboardModifier.NoModifier))
    return bool(_passed)
setup(); select(pos(0, 2), pos(0, 6))
check("(sanity) a drag from an unchecked selection reaches Qt", press_and_move_inside_selection())
setup(); select(pos(1, 2), pos(1, 9))
check("a drag from a checked row's selection never reaches Qt (no drag-move)",
      not press_and_move_inside_selection())
QTextEdit.mouseMoveEvent = _orig_move

print()
print("FAILED:" if fails else "ALL PASS", *fails, sep="\n  " if fails else "")
sys.exit(1 if fails else 0)
