import sys, os, tempfile, atexit, shutil
_SB = tempfile.mkdtemp(prefix="sn_pinink_")
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
app._auto_contrast = True

# Unpinned note recoloured to a very dark colour: the pin styling must follow
# the light ink (rgba(255,255,255,…)), not the legacy dark rgba(0,0,0,…).
note = StickyNote(app, "p", {"id": "p", "geometry": [0, 0, 300, 200], "color": "#fff8b8"})
check("starts unpinned", note._pinned is False)

note.color = "#111111"
note._apply_color()
style = note.btn_pin.styleSheet()
check("dark note: pin hover/press use light ink (255,255,255)", "255,255,255" in style)
check("dark note: pin no longer uses legacy dark rgba(0,0,0", "0,0,0" not in style)
check("dark note: pin icon is set even while unpinned", not note.btn_pin.icon().isNull())

# Pin it: a persistent ink-tinted background appears (light active_bg), still no
# legacy dark overlay.
note._pinned = True
note._refresh_pin_ui()
pstyle = note.btn_pin.styleSheet()
check("pinned dark note: has an active-bg overlay", pstyle.count("background") >= 2)
check("pinned dark note: overlay is light ink, not dark", "0,0,0" not in pstyle)

# Recolour to a light note: ink flips to dark, pin follows.
note.color = "#fff8b8"
note._apply_color()
lstyle = note.btn_pin.styleSheet()
check("light note: pin uses dark ink (0,0,0)", "0,0,0" in lstyle)

note.hide(); note.deleteLater()
print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
