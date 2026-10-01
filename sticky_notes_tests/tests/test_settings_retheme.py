"""Settings rebuilds its content in the SAME dialog on a live theme change:
the top-level window is never recreated, the active tab is preserved, and the
theme combobox no longer reveals the restart button (scale/language still do,
and that hint survives a theme rebuild)."""
import sys, os, tempfile, atexit, shutil
_SB = tempfile.mkdtemp(prefix="sn_setretheme_")
atexit.register(lambda: shutil.rmtree(_SB, ignore_errors=True))
os.environ["HOME"] = _SB
os.environ["XDG_CONFIG_HOME"] = os.path.join(_SB, ".config")
os.environ["XDG_DATA_HOME"]   = os.path.join(_SB, ".local", "share")
os.environ.setdefault("XDG_RUNTIME_DIR", _SB)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ.pop("DISPLAY", None); os.environ.pop("WAYLAND_DISPLAY", None)
os.makedirs(os.path.join(_SB, ".local", "share", "sticky_notes"), exist_ok=True)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import QMessageBox, QDialog, QTabWidget, QPushButton
from PyQt6.QtCore import QTimer, QEventLoop
QMessageBox.information = staticmethod(lambda *a, **k: None)

def settle():
    """Spin the event loop briefly so deferred singleShot(0) rebuilds fire —
    processEvents() alone doesn't run a 0-timer offscreen."""
    loop = QEventLoop()
    QTimer.singleShot(20, loop.quit)
    loop.exec()

fails = []
def check(name, cond):
    print(f"  {'PASS' if cond else 'FAIL'}   {name}")
    if not cond: fails.append(name)

from sticky_notes import theme
from sticky_notes.app import StickyNotesApp

app = StickyNotesApp(sys.argv[:1])
app._theme = "light"; theme.apply_theme("light")

app.show_settings()
dlg = next(w for w in app._open_windows if isinstance(w, QDialog)
           and w.windowTitle() == "Settings")
check("Settings carries a _retheme hook", callable(getattr(dlg, "_retheme", None)))
check("Settings tracks its tab widget", isinstance(getattr(dlg, "_tabs", None), QTabWidget))

# select a non-default tab, then retheme, and confirm the SAME dialog + tab
dlg._tabs.setCurrentIndex(2)
same_dialog = dlg
app._set_theme("dark")
settle()   # let the deferred rebuild run
check("the SAME dialog object survives (not recreated)",
      any(w is same_dialog for w in app._open_windows))
check("active tab preserved across the rebuild", same_dialog._tabs.currentIndex() == 2)
# the rebuilt content reflects the dark palette
tabs_style = same_dialog._tabs.styleSheet()
check("rebuilt Settings uses the dark border colour", theme.UI.BORDER in tabs_style)

# restart button: hidden after a theme change; _pending_restart drives it
def restart_btn(d):
    return next((b for b in d.findChildren(QPushButton) if b.text() == "Restart now"), None)
rb = restart_btn(same_dialog)
check("restart button hidden after a theme change", rb is not None and not rb.isVisible())

# simulate a scale/language change: set the flag + rebuild → hint survives
app._pending_restart = True
same_dialog._retheme()
settle()
rb = restart_btn(same_dialog)
check("restart hint survives a rebuild when _pending_restart is set",
      rb is not None and not rb.isHidden())

app._theme = "light"; theme.apply_theme("light")
print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
