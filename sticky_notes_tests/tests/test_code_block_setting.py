import sys, os, tempfile, atexit, shutil
_SB = tempfile.mkdtemp(prefix="sn_cbset_")
atexit.register(lambda: shutil.rmtree(_SB, ignore_errors=True))
os.environ["HOME"] = _SB
os.environ["XDG_CONFIG_HOME"] = os.path.join(_SB, ".config")
os.environ["XDG_DATA_HOME"]   = os.path.join(_SB, ".local", "share")
os.environ.setdefault("XDG_RUNTIME_DIR", _SB)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ.pop("DISPLAY", None); os.environ.pop("WAYLAND_DISPLAY", None)
os.makedirs(os.path.join(_SB, ".local", "share", "sticky_notes"), exist_ok=True)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)

fails = []
def check(name, cond):
    print(f"  {'PASS' if cond else 'FAIL'}   {name}")
    if not cond: fails.append(name)

from sticky_notes.app import StickyNotesApp
from sticky_notes.note import StickyNote
app = StickyNotesApp(sys.argv[:1])
check("code blocks default OFF", app._code_blocks is False)

n1 = StickyNote(app, "a", {"id": "a", "geometry": [0, 0, 300, 200]}); app.notes["a"] = n1
check("code button hidden while setting is OFF", n1.btn_code.isHidden() is True)

app._code_blocks = True
app._apply_code_blocks()
check("_apply_code_blocks shows the button on open notes", n1.btn_code.isHidden() is False)

# a note built while the setting is ON shows the button immediately
n2 = StickyNote(app, "b", {"id": "b", "geometry": [0, 0, 300, 200]}); app.notes["b"] = n2
check("new note built with setting ON shows the button", n2.btn_code.isHidden() is False)

app._code_blocks = False
app._apply_code_blocks()
check("turning setting OFF hides the button again", n1.btn_code.isHidden() is True)
print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
