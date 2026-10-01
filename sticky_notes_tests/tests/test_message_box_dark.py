"""Message boxes stay readable in dark mode.

Root cause this guards: a themed container (Manager, Settings, Backups) sets a
root stylesheet like `QWidget { background: WINDOW_BG; }`. Qt style sheets
cascade to CHILD WINDOWS too, so a QMessageBox parented to one inherits the dark
background — but nothing ever set its text colour, so the label stayed the
palette default (black) and became almost invisible.

The fix is theme.message_box_style(): every container that can parent a message
box states the box's own background AND text colour. Painted pixels can't be
checked offscreen, so this guards that invariant structurally.
"""
import sys, os, tempfile, atexit, shutil
_SB = tempfile.mkdtemp(prefix="sn_msgdark_")
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

from sticky_notes import theme
from sticky_notes.theme import UI, message_box_style, settings_dialog_style

from sticky_notes.app import StickyNotesApp
app = StickyNotesApp(sys.argv[:1])

# ── the style itself ──────────────────────────────────────────────────────────
theme.apply_theme("dark")
dark_css = message_box_style()
check("dark: styles the box background", f"background: {UI.WINDOW_BG}" in dark_css)
check("dark: states the label colour", f"color: {UI.TEXT}" in dark_css)
check("dark: label colour is the LIGHT ink, not black",
      UI.TEXT.lower() not in ("#000000", "#000", "black"))
check("dark: targets QMessageBox labels", "QMessageBox QLabel" in dark_css)
check("dark: styles the buttons too (native ones go black-on-dark)",
      "QMessageBox QPushButton" in dark_css)

theme.apply_theme("light")
light_css = message_box_style()
check("light: follows the light palette", f"background: {UI.WINDOW_BG}" in light_css)
check("light and dark differ", light_css != dark_css)

# ── every themed container that can parent a message box carries the rules ────
theme.apply_theme("dark")
check("Settings dialog style carries the message-box rules",
      "QMessageBox QLabel" in settings_dialog_style())

from sticky_notes.manager import NotesManager
mgr = NotesManager(app)
check("Manager root style carries the message-box rules",
      "QMessageBox QLabel" in mgr.styleSheet())
check("Manager root style still sets its own background",
      f"background: {UI.WINDOW_BG}" in mgr.styleSheet())

# A real box parented to the Manager: it inherits the Manager's sheet, which now
# names a text colour instead of leaving it to the black palette default.
from PyQt6.QtWidgets import QMessageBox
box = QMessageBox(mgr)
box.setText("readable?")
inherited = box.parent().styleSheet()
check("box parented to the Manager inherits a sheet naming its text colour",
      f"color: {UI.TEXT}" in inherited)

theme.apply_theme("light")
print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
