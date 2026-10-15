"""Guard: ticking an item by its box moves the caret to the END of the line, so
the next key continues from there (Enter → a fresh item below) instead of
landing before the box; typing into an UNCHECKED item is never struck; and a
fresh item made below a done one isn't struck either.

(Typing INTO a checked item used to be allowed and forced struck; since
2026-10-14 a checked row is locked — test_checklist_checked_locked.py.)
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

from PyQt6.QtWidgets import QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from PyQt6.QtGui import QTextCursor
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

def line(bn):
    return doc.findBlockByNumber(bn).text()

def body_struck(bn):
    b = doc.findBlockByNumber(bn); text = b.text()
    skip = 2 if (len(text) > 1 and text[1] == " ") else 1
    probe = QTextCursor(doc)
    probe.setPosition(b.position() + skip)
    probe.setPosition(b.position() + skip + 1, QTextCursor.MoveMode.KeepAnchor)
    return probe.charFormat().fontStrikeOut()

def type_(text):
    te.setFocus(); QTest.keyClicks(te, text)

# ── 1) tick an EMPTY item by "clicking" its box (caret on the box), then type ─
te.setPlainText(""); c = te.textCursor(); c.setPosition(0); te.setTextCursor(c)
te.toggle_checklist()                                        # "☐ "
c = te.textCursor(); c.setPosition(doc.findBlockByNumber(0).position()); te.setTextCursor(c)
te.toggle_checkbox(doc.findBlockByNumber(0).position())      # tick + caret → end of line
check("tick moves the caret to the end of the line",
      te.textCursor().position() == doc.findBlockByNumber(0).position() + len(line(0)))
type_("milk")
check("empty-then-tick: typing into the (locked) done item is refused",
      line(0) == f"{CHECK_DONE} ")

# ── 2) an UNCHECKED item: typed text is NOT struck ────────────────────────────
te.setPlainText(""); c = te.textCursor(); c.setPosition(0); te.setTextCursor(c)
te.toggle_checklist()
c = te.textCursor(); c.movePosition(QTextCursor.MoveOperation.End); te.setTextCursor(c)
type_("bread")
check("unchecked item: text lands after the box (☐ bread)", line(0) == f"{CHECK_EMPTY} bread")
check("unchecked item: typed text is NOT struck", body_struck(0) is False)

# ── 3) done item + Enter → fresh unchecked item below, typed text not struck ──
te.setPlainText(""); c = te.textCursor(); c.setPosition(0); te.setTextCursor(c)
te.toggle_checklist()
type_("done")
te.toggle_checkbox(doc.findBlockByNumber(0).position())     # tick → caret to the end
te._handle_checklist_enter()                                 # new unchecked item below
type_("todo")
check("done line still struck", body_struck(0) is True)
check("fresh item below (unchecked) is NOT struck", body_struck(1) is False)

print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
