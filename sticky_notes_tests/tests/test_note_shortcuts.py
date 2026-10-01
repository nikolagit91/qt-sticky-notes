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

from PyQt6.QtGui import QShortcut
from PyQt6.QtWidgets import QMenu
from sticky_notes.app import StickyNotesApp
app = StickyNotesApp(sys.argv[:1])
app._snap_to_grid = app._snap_to_notes = app._snap_size = False
for e in list(app.notes.values()):
    e.hide(); e.deleteLater()
app.notes.clear()

n = app.create_new_note()
seqs = {sc.key().toString() for sc in n.findChildren(QShortcut)}
check("Ctrl+D shortcut present", "Ctrl+D" in seqs)
check("Ctrl+E shortcut present", "Ctrl+E" in seqs)
check("Ctrl+W shortcut present", "Ctrl+W" in seqs)
check("F1 shortcut present", "F1" in seqs)

before = len(app.notes)
n._copy_note()
check("Ctrl+D slot duplicates note", len(app.notes) == before + 1)

m = n._build_export_menu(n)
check("export menu is a QMenu", isinstance(m, QMenu))
check("export menu has 4 actions (txt/odt/pdf/png)", len(m.actions()) == 4)

# ── new shortcuts: present AND wired to the right slot ────────────────────────
def sc_for(seq):
    return next((sc for sc in n.findChildren(QShortcut)
                 if sc.key().toString() == seq), None)

for seq in ("F2", "Ctrl+P", "Ctrl+L", "Ctrl+=", "Ctrl+-", "Ctrl+Shift+M"):
    check(f"{seq} shortcut present", seq in seqs)

# Fire the actual signal, so this proves the CONNECTION, not just the key.
# (Can't monkeypatch the slot — it's bound at connect time — so check the real
# dialog: raised from the note itself, it must be parented to the note.)
sc_for("F2").activated.emit()
check("F2 opens the rename dialog", n._rename_dlg is not None and n._rename_dlg.isVisible())
check("F2 anchors it on the note (default parent)", n._rename_dlg.parent() is n)
n._rename_dlg.close(); n._rename_dlg = None

was = n._pinned
sc_for("Ctrl+P").activated.emit()
check("Ctrl+P toggles pin", n._pinned is (not was))

was = n.locked
sc_for("Ctrl+L").activated.emit()
check("Ctrl+L toggles lock", n.locked is (not was))
sc_for("Ctrl+L").activated.emit()          # unlock again for the editing checks
check("Ctrl+L unlocks again", n.locked is False)

n._font_size = 14; n._apply_font_size(14)
sc_for("Ctrl+=").activated.emit()
check("Ctrl+= grows the font", n._font_size == 15)
sc_for("Ctrl+-").activated.emit()
check("Ctrl+- shrinks the font", n._font_size == 14)

# ── Ctrl+Shift+M code block: gated on the code-blocks setting ─────────────────
def is_code():
    te = n.text_edit
    return te._is_code_block(te.textCursor().block())

app._code_blocks = False
sc_for("Ctrl+Shift+M").activated.emit()
check("Ctrl+Shift+M is a no-op when code blocks are off", not is_code())
app._code_blocks = True
sc_for("Ctrl+Shift+M").activated.emit()
check("Ctrl+Shift+M makes a code block when on", is_code())
sc_for("Ctrl+Shift+M").activated.emit()
check("Ctrl+Shift+M toggles the code block back off", not is_code())

# ── editing shortcuts are inert on a LOCKED (read-only) note ──────────────────
n._font_size = 14; n._apply_font_size(14)
n.toggle_lock(True)
sc_for("Ctrl+=").activated.emit()
check("Ctrl+= does nothing on a locked note", n._font_size == 14)
sc_for("Ctrl+Shift+M").activated.emit()
check("Ctrl+Shift+M does nothing on a locked note", not is_code())
n.toggle_lock(False)

print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
