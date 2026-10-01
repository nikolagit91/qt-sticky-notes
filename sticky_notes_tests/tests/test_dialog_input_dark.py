"""Note dialogs keep their INPUTS readable in dark mode.

Same root cause as the message-box bug: a themed window's root sheet cascades
into child windows, so a dialog parented to the Manager inherits the dark
background — and any input whose colour nobody named keeps the palette default
(black), giving black text on #1e1f22. The rename dialog is raised from the
Manager, so its QLineEdit sits exactly in that trap.

_dialog_style() names the input colours, so the ink is stated rather than
inherited. Checked through the RESOLVED palette (what Qt will actually paint),
not by string-matching the stylesheet.
"""
import sys, os, tempfile, atexit, shutil
_SB = tempfile.mkdtemp(prefix="sn_dlginput_")
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

from PyQt6.QtWidgets import QLineEdit
from PyQt6.QtGui import QPalette, QColor

from sticky_notes import theme
from sticky_notes.app import StickyNotesApp
from sticky_notes.manager import NotesManager

app = StickyNotesApp(sys.argv[:1])
for e in list(app.notes.values()):
    e.hide(); e.deleteLater()
app.notes.clear()

def contrast(fg: QColor, bg: QColor) -> float:
    """WCAG contrast ratio — the honest measure of 'can you read it'."""
    def lum(c):
        def ch(v):
            v /= 255.0
            return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
        return 0.2126 * ch(c.red()) + 0.7152 * ch(c.green()) + 0.0722 * ch(c.blue())
    a, b = sorted((lum(fg), lum(bg)), reverse=True)
    return (a + 0.05) / (b + 0.05)

def probe_rename_input(note, parent):
    note._rename_dlg = None
    note._open_rename_dialog(parent=parent)
    dlg = note._rename_dlg
    dlg.show(); dlg.ensurePolished()
    le = next(w for w in dlg.findChildren(QLineEdit))
    le.ensurePolished()
    fg = le.palette().color(QPalette.ColorRole.Text)
    bg = le.palette().color(QPalette.ColorRole.Base)
    dlg.close(); note._rename_dlg = None
    return fg, bg

for name in ("dark", "light"):
    theme.apply_theme(name)
    note = app.create_new_note(content="probe " + name)
    mgr = NotesManager(app)

    fg, bg = probe_rename_input(note, mgr)
    ratio = contrast(fg, bg)
    print(f"    [{name}] rename input from Manager: {fg.name()} on {bg.name()} "
          f"→ contrast {ratio:.1f}:1")
    check(f"{name}: rename input from the Manager is readable (≥4.5:1)", ratio >= 4.5)

    fg, bg = probe_rename_input(note, None)   # raised from the note itself
    ratio = contrast(fg, bg)
    print(f"    [{name}] rename input from the note:  {fg.name()} on {bg.name()} "
          f"→ contrast {ratio:.1f}:1")
    check(f"{name}: rename input from the note is readable (≥4.5:1)", ratio >= 4.5)
    mgr.close()

theme.apply_theme("light")
print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
