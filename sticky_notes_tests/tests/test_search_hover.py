"""The search palette's highlight follows the MOUSE, not just the arrow keys.

Hovering a result must move the selection there, so clicking the row you are
looking at activates that row (before, the highlight only moved with ↑/↓ and a
hover left it stale). Hover itself can't be synthesised offscreen, so this
guards the invariant it is built on: the list tracks the mouse and its
itemEntered signal drives the current row.
"""
import sys, os, tempfile, atexit, shutil
_SB = tempfile.mkdtemp(prefix="sn_searchhover_")
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

from sticky_notes.app import StickyNotesApp
from sticky_notes.search_palette import SearchPalette

app = StickyNotesApp(sys.argv[:1])
app._snap_to_grid = app._snap_to_notes = app._snap_size = False
for e in list(app.notes.values()):
    e.hide(); e.deleteLater()
app.notes.clear()

for body in ("alpha", "beta", "gamma"):
    app.create_new_note(content=body)

pal = SearchPalette(app)
check("three results listed", pal.list.count() == 3)
check("starts on the first row", pal.list.currentRow() == 0)

# The viewport is what actually receives the mouse; without tracking on it Qt
# never emits itemEntered unless a button is held down.
check("list tracks the mouse", pal.list.hasMouseTracking())
check("viewport tracks the mouse", pal.list.viewport().hasMouseTracking())

# itemEntered is Qt's "pointer moved onto this row" signal — the hover path.
pal.list.itemEntered.emit(pal.list.item(2))
check("hovering the third row selects it", pal.list.currentRow() == 2)
pal.list.itemEntered.emit(pal.list.item(1))
check("hovering the second row selects it", pal.list.currentRow() == 1)

# Hover must not steal typing focus away from the search box.
check("list still takes no focus",
      pal.list.focusPolicy().name == "NoFocus")

# Arrow keys keep working alongside hover.
pal._move(1)
check("arrows still move from the hovered row", pal.list.currentRow() == 2)

print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
