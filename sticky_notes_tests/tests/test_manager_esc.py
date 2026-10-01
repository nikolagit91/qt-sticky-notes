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

from PyQt6.QtGui import QKeyEvent
from PyQt6.QtCore import Qt, QEvent
from sticky_notes.app import StickyNotesApp
app = StickyNotesApp(sys.argv[:1])

app.show_manager()
mgr = app._manager
check("manager opened", mgr is not None)

closed = {"hit": False}
_orig = mgr.close
mgr.close = lambda: (closed.__setitem__("hit", True), _orig())[1]
ev = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier)
mgr.keyPressEvent(ev)
check("Esc closes manager", closed["hit"] is True)

app.show_manager()
mgr2 = app._manager
non_esc = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_A, Qt.KeyboardModifier.NoModifier)
mgr2.keyPressEvent(non_esc)   # must NOT close
check("non-Esc key does not close", app._manager is mgr2)

print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
