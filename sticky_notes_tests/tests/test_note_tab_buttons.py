"""§56: Note tab now has TWO 'Apply to New Notes' buttons — one for the font
section (family+size), one for the size section (width+height) — and the single
bottom button is gone. Verify the dialog builds, both buttons exist, and each
applies ONLY its own subset (no cross-wiring). Also verify the reworded opacity
hint is translated. Headless + isolated.
"""
import sys, os, tempfile, atexit, shutil

_SB = tempfile.mkdtemp(prefix="sn_tab_")
atexit.register(lambda: shutil.rmtree(_SB, ignore_errors=True))
os.environ["HOME"] = _SB
os.environ["XDG_CONFIG_HOME"] = os.path.join(_SB, ".config")
os.environ["XDG_DATA_HOME"]   = os.path.join(_SB, ".local", "share")
os.environ.setdefault("XDG_RUNTIME_DIR", _SB)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ.pop("DISPLAY", None); os.environ.pop("WAYLAND_DISPLAY", None)
os.makedirs(os.path.join(_SB, ".local", "share", "sticky_notes"), exist_ok=True)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import QApplication, QMessageBox, QPushButton, QSpinBox
QMessageBox.information = staticmethod(lambda *a, **k: None)

fails = []
def check(name, cond):
    print(f"  {'PASS' if cond else 'FAIL'}   {name}")
    if not cond: fails.append(name)

from sticky_notes.app import StickyNotesApp
from sticky_notes.i18n import tr, set_language, get_language
app = StickyNotesApp(sys.argv[:1])

# Known starting state
app._default_font_size   = 15
app._default_note_width  = 440
app._default_note_height = 300

app.show_settings()   # non-modal; builds the whole dialog
dlg = app._open_windows[-1]

apply_btns = [b for b in dlg.findChildren(QPushButton)
              if b.text() == tr("Apply to New Notes")]
check("exactly two 'Apply to New Notes' buttons", len(apply_btns) == 2)

# Identify the section spinboxes by their range maxima (font 72 / width 1200 /
# height 1000) — unambiguous across the whole dialog.
spins = dlg.findChildren(QSpinBox)
font_spin   = next(s for s in spins if s.maximum() == 72)
width_spin  = next(s for s in spins if s.maximum() == 1200)
height_spin = next(s for s in spins if s.maximum() == 1000)

# Set new values in all three, then click ONLY the font button (constructed
# first → apply_btns[0]) and confirm it moved font size but NOT the dimensions.
font_spin.setValue(22); width_spin.setValue(500); height_spin.setValue(400)
apply_btns[0].click()
check("font button applies font size", app._default_font_size == 22)
check("font button leaves width untouched",  app._default_note_width == 440)
check("font button leaves height untouched", app._default_note_height == 300)

# Now the size button (constructed second → apply_btns[1]) applies dimensions
# only, and does not disturb the font size just set.
apply_btns[1].click()
check("size button applies width",  app._default_note_width == 500)
check("size button applies height", app._default_note_height == 400)
check("size button leaves font size untouched", app._default_font_size == 22)

# Both persisted to disk
import json
from sticky_notes.config import SETTINGS_FILE
saved = json.load(open(SETTINGS_FILE))
check("persisted font_size=22",  saved.get("font_size")  == 22)
check("persisted note_width=500", saved.get("note_width") == 500)
check("persisted note_height=400", saved.get("note_height") == 400)

dlg.close()

# Reworded opacity hint is translated in hr
set_language("hr")
hint = tr("Makes the note paper see-through; text stays sharp. Applies to all current and future notes.")
check("hr hint translated (not English fallback)",
      hint.startswith("Čini") and "buduće" in hint)
set_language(get_language())

print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
