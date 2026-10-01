"""Settings must open big enough for its tallest tab, not squashed.

The dialog's hint labels are word-wrapped, so their height depends on a width
Qt doesn't know at show() time — relying on the show-time sizeHint let GNOME
under-size the window and compress the current tab toward its minimum ("Settings
sometimes opens squished"). show_settings pins an explicit size to the built
content's hint, so the initial geometry is deterministic.

Offscreen can't reproduce the WM under-sizing, so this guards the invariant that
we DO size the window to fit the content — remove the resize and the note tab
(the tallest) no longer fits, and this fails.
"""
import sys, os, tempfile, atexit, shutil
_SB = tempfile.mkdtemp(prefix="sn_setsize_")
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

app.show_settings()
dlg = next(w for w in app._open_windows
           if isinstance(w, QDialog) and w.windowTitle() == "Settings")
tabs = dlg._tabs

# The tallest tab's content must fit inside the opened dialog. If the window is
# sized only to the floor (minimumHeight) the tab is squashed and this fails.
tallest = max(tabs.widget(i).sizeHint().height() for i in range(tabs.count()))
check("dialog opens taller than its minimum floor",
      dlg.height() > dlg.minimumHeight())
check("dialog opens tall enough for the tallest tab's content",
      dlg.height() >= tallest)

print("ALL PASS" if not fails else f"FAILS: {fails}")
sys.exit(1 if fails else 0)
