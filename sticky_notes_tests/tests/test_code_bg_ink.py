import sys, os, tempfile, atexit, shutil
_SB = tempfile.mkdtemp(prefix="sn_cbg_")
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

from PyQt6.QtGui import QColor
from sticky_notes.theme import Ink, DARK_INK, LIGHT_INK, note_ink, _rel_luminance

check("Ink has a code_bg field", "code_bg" in Ink.__dataclass_fields__)
check("Ink has a code_fg field", "code_fg" in Ink.__dataclass_fields__)
check("Ink has an inline_bg field", "inline_bg" in Ink.__dataclass_fields__)
# The static inks now carry the INLINE-code overlay; the block box is computed
# per note by note_ink (a dark, saturated version of the note's own hue).
check("light-set inline overlay is light (white tint)", LIGHT_INK.inline_bg.red() == 255)
check("dark-set inline overlay is dark (black tint)", DARK_INK.inline_bg.red() == 0)
# note_ink builds an opaque, DARK block box + a LIGHT text colour, on any note.
for hexv in ("#fff8b8", "#E3F2FD", "#000000"):
    ink = note_ink(QColor(hexv), auto=True)
    check(f"note_ink({hexv}) code_bg is an opaque dark box",
          ink.code_bg.alpha() == 255 and _rel_luminance(ink.code_bg) < 0.20)
    check(f"note_ink({hexv}) code_fg is light", _rel_luminance(ink.code_fg) > 0.55)

print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
import sys; sys.exit(1 if fails else 0)
