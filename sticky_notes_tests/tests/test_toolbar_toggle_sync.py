"""Toolbar bold/italic/underline/strike buttons must flip IMMEDIATELY when you
toggle them off with no selection — not only after you type the next character.

Root cause: _update_toolbar_state probes the char to the LEFT of the caret when
there's no selection (so the size box follows the cursor into an existing word),
but right after a toggle the left char is the OLD run. The fix passes
prefer_current=True from the _fmt_* toggles so the buttons read currentCharFormat
(the format that will be typed next). This test guards both directions.

Headless + sandboxed.
"""
import sys, os, tempfile, atexit, shutil

_SB = tempfile.mkdtemp(prefix="sn_tb_")
atexit.register(lambda: shutil.rmtree(_SB, ignore_errors=True))
os.environ["HOME"] = _SB
os.environ["XDG_CONFIG_HOME"] = os.path.join(_SB, ".config")
os.environ["XDG_DATA_HOME"]   = os.path.join(_SB, ".local", "share")
os.environ.setdefault("XDG_RUNTIME_DIR", _SB)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ.pop("DISPLAY", None); os.environ.pop("WAYLAND_DISPLAY", None)
os.makedirs(os.path.join(_SB, ".local", "share", "sticky_notes"), exist_ok=True)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtGui import QTextCursor, QTextCharFormat, QFont
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

# ── type bold+underline text, then toggle both OFF with no selection ─────────
n._fmt_bold(); n._fmt_underline()
te.insertPlainText("hello")            # typed bold + underline
check("after typing: bold button checked", n.btn_bold.isChecked())
check("after typing: underline button checked", n.btn_underline.isChecked())

n._fmt_bold()                          # toggle bold OFF (no selection, caret at end)
check("toggle bold off → bold button UNCHECKS immediately", not n.btn_bold.isChecked())
check("toggle bold off → underline still checked", n.btn_underline.isChecked())

n._fmt_underline()                     # toggle underline OFF
check("toggle underline off → underline button UNCHECKS immediately", not n.btn_underline.isChecked())

# turning bold back ON with no selection reflects immediately too
n._fmt_bold()
check("toggle bold on → bold button CHECKS immediately", n.btn_bold.isChecked())

# ── regression: clicking INTO an existing bold word still lights up bold ─────
# (cursor move uses the default left-char probe, unaffected by the fix)
te.clear()
_norm = QTextCharFormat(); _norm.setFontWeight(QFont.Weight.Normal); _norm.setFontUnderline(False)
te.setCurrentCharFormat(_norm)         # start from a clean, non-bold state
n._fmt_bold()                          # bold ON
te.insertPlainText("BOLD")
n._fmt_bold()                          # bold OFF
te.insertPlainText(" plain")
c = te.textCursor(); c.setPosition(2); te.setTextCursor(c)   # caret inside "BOLD"
n._update_toolbar_state()              # default (cursor move) → probes left char
check("caret inside bold word → bold button checked (left-char probe intact)",
      n.btn_bold.isChecked())

print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
