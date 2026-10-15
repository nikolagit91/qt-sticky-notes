"""Guard: dismissing the bullet-style picker without choosing (a click outside
it) leaves the toolbar's bullet button showing the TRUTH — highlighted only if
the caret is in a list.

Root cause (2026-10-15): btn_bullet is checkable, and a checkable button flips
its own state on click BEFORE `clicked` opens the picker. Dismissing the picker
changed nothing, and the dismissing click is eaten by the popup (the caret
doesn't move → no toolbar refresh), so the flipped state stuck until the next
click or keystroke. Both directions: lit outside a list, dark inside one.

Headless + sandboxed.
"""
import sys, os, tempfile, atexit, shutil

_SB = tempfile.mkdtemp(prefix="sn_bp_")
atexit.register(lambda: shutil.rmtree(_SB, ignore_errors=True))
os.environ["HOME"] = _SB
os.environ["XDG_CONFIG_HOME"] = os.path.join(_SB, ".config")
os.environ["XDG_DATA_HOME"]   = os.path.join(_SB, ".local", "share")
os.environ.setdefault("XDG_RUNTIME_DIR", _SB)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ.pop("DISPLAY", None); os.environ.pop("WAYLAND_DISPLAY", None)
os.makedirs(os.path.join(_SB, ".local", "share", "sticky_notes"), exist_ok=True)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import QMessageBox, QDialog
from PyQt6.QtGui import QTextCursor, QTextListFormat
QMessageBox.information = staticmethod(lambda *a, **k: None)

fails = []
def check(name, cond):
    print(f"  {'PASS' if cond else 'FAIL'}   {name}")
    if not cond: fails.append(name)

from sticky_notes.app import StickyNotesApp
from sticky_notes.note import StickyNote
app = StickyNotesApp(sys.argv[:1])
n = StickyNote(app, "z", {"id": "z", "geometry": [10, 10, 300, 200]})
n.show()
te = n.text_edit

# The picker is a modal popup; a click outside closes it as "rejected". Stand in
# for that: exec() returns at once, nothing chosen.
QDialog.exec = lambda self: QDialog.DialogCode.Rejected

# ── 1) caret NOT in a list: open + dismiss → button must not stay lit ─────────
te.setPlainText("plain line")
c = te.textCursor(); c.movePosition(QTextCursor.MoveOperation.End); te.setTextCursor(c)
n._update_toolbar_state()
check("(setup) not in a list, button off", not n.btn_bullet.isChecked())
n.btn_bullet.click()
check("outside a list: dismissed picker leaves the button OFF", not n.btn_bullet.isChecked())
check("outside a list: text untouched", te.textCursor().currentList() is None)

# ── 2) caret IN a list: open + dismiss → button must stay lit ─────────────────
c = te.textCursor(); c.createList(QTextListFormat.Style.ListDisc); te.setTextCursor(c)
n._update_toolbar_state()
check("(setup) in a list, button on", n.btn_bullet.isChecked())
n.btn_bullet.click()
check("inside a list: dismissed picker leaves the button ON", n.btn_bullet.isChecked())
check("inside a list: still a list", te.textCursor().currentList() is not None)

print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
