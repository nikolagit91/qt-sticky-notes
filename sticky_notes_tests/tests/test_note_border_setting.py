"""The outer border is a 3-way Settings mode: Off / Always / Auto.

Off = borderless (default); Always = border on every note; Auto = border only on
light notes. Persisted as a mode string (old bool migrates), applied live, and
the Note tab exposes it as a combobox.
"""
import sys, os, tempfile, atexit, shutil, json
_SB = tempfile.mkdtemp(prefix="sn_borderset_")
atexit.register(lambda: shutil.rmtree(_SB, ignore_errors=True))
os.environ["HOME"] = _SB
os.environ["XDG_CONFIG_HOME"] = os.path.join(_SB, ".config")
os.environ["XDG_DATA_HOME"]   = os.path.join(_SB, ".local", "share")
os.environ.setdefault("XDG_RUNTIME_DIR", _SB)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ.pop("DISPLAY", None); os.environ.pop("WAYLAND_DISPLAY", None)
os.makedirs(os.path.join(_SB, ".local", "share", "sticky_notes"), exist_ok=True)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import QMessageBox, QComboBox
QMessageBox.information = staticmethod(lambda *a, **k: None)

fails = []
def check(name, cond):
    print(f"  {'PASS' if cond else 'FAIL'}   {name}")
    if not cond: fails.append(name)

from sticky_notes.app import StickyNotesApp
from sticky_notes.config import SETTINGS_FILE

app = StickyNotesApp(sys.argv[:1])
for e in list(app.notes.values()):
    e.hide(); e.deleteLater()
app.notes.clear()

# ── default + persistence ────────────────────────────────────────────────────
check("border mode defaults to 'off'", app._note_border == "off")

app._note_border = "auto"
app._save_backup_settings()
with open(SETTINGS_FILE, encoding="utf-8") as f:
    check("mode persists to settings.json", json.load(f).get("note_border") == "auto")
app._note_border = "off"
app._load_backup_settings()
check("mode loads back as 'auto'", app._note_border == "auto")

# ── old-bool migration on load ───────────────────────────────────────────────
def write_setting(val):
    with open(SETTINGS_FILE, encoding="utf-8") as f:
        data = json.load(f)
    data["note_border"] = val
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f)

write_setting(True);  app._load_backup_settings()
check("legacy bool True migrates to 'always'", app._note_border == "always")
write_setting(False); app._load_backup_settings()
check("legacy bool False migrates to 'off'", app._note_border == "off")
write_setting("nonsense"); app._load_backup_settings()
check("unknown persisted value falls back to 'off'", app._note_border == "off")

# ── live apply repaints notes ────────────────────────────────────────────────
app._note_border = "off"
n = app.create_new_note(content="hi")            # yellow (#fff59d) default light note
n.resize(300, 220); n.show(); app.processEvents()

def has_border():
    img = n.grab().toImage()
    y = img.height() // 2
    return img.pixelColor(0, y).name() != img.pixelColor(8, y).name()

check("off → no border on a light note", not has_border())

repainted = {"n": 0}
n.update = lambda *a, **k: repainted.__setitem__("n", repainted["n"] + 1)
app._note_border = "always"
app._apply_note_border()
check("changing the mode repaints open notes", repainted["n"] > 0)
del n.update
app.processEvents()
check("always → border on a light note", has_border())

app._note_border = "auto"; app._apply_note_border(); app.processEvents()
check("auto → border on a light (yellow) note", has_border())

# a dark note in auto mode gets NO border. Set the effective colour directly:
# theme is a restart-model setting, so flipping app._theme doesn't recompute an
# open note's self.color — assign it, then _apply_color refreshes _qcolor_base.
nd = app.create_new_note(content="dark")
nd.color = "#2b2b30"; nd._apply_color()
nd.resize(300, 220); nd.show(); app.processEvents()
def has_border_dark():
    img = nd.grab().toImage()
    y = img.height() // 2
    return img.pixelColor(0, y).name() != img.pixelColor(8, y).name()
check("auto → NO border on a dark (charcoal) note", not has_border_dark())

# ── Settings exposes a combobox with the three modes ─────────────────────────
app.show_settings()
dlg = next(w for w in app.topLevelWidgets()
           if w.windowTitle() == "Settings" and w.isVisible())
combos = dlg.findChildren(QComboBox)
modes = set()
for c in combos:
    for i in range(c.count()):
        d = c.itemData(i)
        if d in ("off", "always", "auto"):
            modes.add(d)
check("Settings combobox offers all three modes", modes == {"off", "always", "auto"})
dlg.close()

print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
