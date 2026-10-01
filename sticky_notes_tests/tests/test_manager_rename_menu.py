"""Right-clicking a note row in the Manager offers Rename above Export.

Rename reuses the note's own rename dialog (note_dialogs._open_rename_dialog),
so there is exactly one rename path in the app — and set_title already
refreshes the Manager, so the row's label updates itself.

Archived rows have no live note widget behind them, so they keep Export only
rather than growing a second, divergent rename path.
"""
import sys, os, tempfile, atexit, shutil
_SB = tempfile.mkdtemp(prefix="sn_renamemenu_")
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

from PyQt6.QtWidgets import QMenu, QWidget
from PyQt6.QtCore import QPoint

# The menu is modal (exec blocks), so stand in for it: record what was offered
# and hand back whichever action the test wants "clicked".
seen = {"labels": [], "pick": None}
def fake_exec(self, *a, **k):
    seen["labels"] = [act.text() for act in self.actions()]
    want = seen["pick"]
    return next((act for act in self.actions() if act.text() == want), None)
QMenu.exec = fake_exec

from sticky_notes.app import StickyNotesApp
from sticky_notes.manager import NotesManager

app = StickyNotesApp(sys.argv[:1])
app._snap_to_grid = app._snap_to_notes = app._snap_size = False
for e in list(app.notes.values()):
    e.hide(); e.deleteLater()
app.notes.clear()

note = app.create_new_note(content="groceries")
mgr = NotesManager(app)
row = QWidget()
data = note.get_data()

# ── active note: Rename, then Export ─────────────────────────────────────────
seen["pick"] = None
mgr._show_note_row_menu(row, QPoint(0, 0), data)
check("active row offers exactly Rename and Export", seen["labels"] == ["Rename", "Export"])
check("Rename comes first", seen["labels"][0] == "Rename")

# ── picking Rename opens the note's own dialog, anchored on the Manager ──────
# The dialog must be parented to the MANAGER when raised from there: a dialog is
# transient-for its parent, so parenting it to the note makes Mutter pull that
# note forward (and un-hide it) just to rename it from the list.
real_open = note._open_rename_dialog
opened = []
note._open_rename_dialog = lambda parent=None: opened.append(parent)
seen["pick"] = "Rename"
mgr._show_note_row_menu(row, QPoint(0, 0), data)
check("picking Rename opens the note's rename dialog", len(opened) == 1)
check("the Manager passes itself as the dialog's parent", opened == [mgr])
note._open_rename_dialog = real_open

# ── the real dialog honours it, and the note's own path is unchanged ─────────
seen["pick"] = "Rename"
mgr._show_note_row_menu(row, QPoint(0, 0), data)
check("dialog raised from the Manager is parented to the Manager",
      note._rename_dlg.parent() is mgr)
note._rename_dlg.close(); note._rename_dlg = None

note._open_rename_dialog()          # as the note's own context menu does
check("dialog raised from the note is still parented to the note",
      note._rename_dlg.parent() is note)
note._rename_dlg.close(); note._rename_dlg = None

# ── picking Export still exports that one note ───────────────────────────────
exported = []
app.export_single_note = lambda d, parent: exported.append(d)
seen["pick"] = "Export"
mgr._show_note_row_menu(row, QPoint(0, 0), data)
check("picking Export still exports the row's note", exported == [data])

# ── archived row (no live note): Export only ─────────────────────────────────
seen["pick"] = None
mgr._show_note_row_menu(row, QPoint(0, 0), {"id": "not-a-live-note", "content": ""})
check("archived row offers Export only", seen["labels"] == ["Export"])

print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
