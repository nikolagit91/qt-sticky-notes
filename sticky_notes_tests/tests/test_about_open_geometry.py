"""About must open deterministically: pinned to its content size and centred on
the primary screen. show_about used to leave both to the show-time sizeHint and
the WM's placement, so it "opened differently each time" (size + position varied)
— the same root-cause class as the old "Settings opens squished" fix.

Under the offscreen QPA platform, Qt auto-centres and auto-sizes a freshly-shown
top-level QDialog on its own, so asserting only the FINAL geometry (dlg.x()/y()/
width()/height()) passes even without show_about's explicit resize()+move() call
— it can't discriminate the fix from Qt's own default placement. Instead this
spies on QDialog.resize/move to record every call made on the About dialog, and
asserts that show_about itself issued a resize(sizeHint()) and a move() to the
exact centre computed from primaryScreen().availableGeometry() — the calls, not
just the coincidental end state. Remove the resize()+move() block and no such
calls are recorded, and this fails.
"""
import sys, os, tempfile, atexit, shutil
_SB = tempfile.mkdtemp(prefix="sn_aboutgeo_")
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

# Spy on QDialog.resize/move: record every (self, args) call, then delegate to
# the real implementation so behaviour (and downstream geometry) is unchanged.
_orig_resize = QDialog.resize
_orig_move = QDialog.move
resize_calls = []
move_calls = []

def _spy_resize(self, *a, **k):
    resize_calls.append((self, a, k))
    return _orig_resize(self, *a, **k)

def _spy_move(self, *a, **k):
    move_calls.append((self, a, k))
    return _orig_move(self, *a, **k)

QDialog.resize = _spy_resize
QDialog.move = _spy_move
try:
    app.show_about()
finally:
    QDialog.resize = _orig_resize
    QDialog.move = _orig_move

dlg = next(w for w in app._open_windows
           if isinstance(w, QDialog) and w.windowTitle() == "About Sticky Notes")

# 1) real, content-derived size (not zero, honours the min-width floor)
check("dialog has a real content-derived size",
      dlg.width() >= 360 and dlg.height() > 0)

# 2) show_about explicitly resized this dialog to its own sizeHint (proves the
#    resize() call happened, not just that Qt auto-sized it to fit)
hint = dlg.sizeHint()
dlg_resize_calls = [c for c in resize_calls if c[0] is dlg]
check("show_about called dlg.resize(dlg.sizeHint())",
      any(
          (c[1] == (hint,)) or
          (c[1] == (hint.width(), hint.height()))
          for c in dlg_resize_calls
      ))

# 3) show_about explicitly moved this dialog to the exact centre computed from
#    primaryScreen().availableGeometry() and its own size (proves the move()
#    call happened, not just that Qt auto-centred a freshly-shown dialog)
avail = app.primaryScreen().availableGeometry()
w, h = dlg.width(), dlg.height()
cx = avail.left() + (avail.width()  - w) // 2
cy = avail.top()  + (avail.height() - h) // 2
dlg_move_calls = [c for c in move_calls if c[0] is dlg]
check("show_about called dlg.move(<computed centre>)",
      any(
          (c[1] == (cx, cy)) or
          (len(c[1]) == 1 and hasattr(c[1][0], "x") and c[1][0].x() == cx and c[1][0].y() == cy)
          for c in dlg_move_calls
      ))

print("ALL PASS" if not fails else f"FAILS: {fails}")
sys.exit(1 if fails else 0)
