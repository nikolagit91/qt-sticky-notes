"""theme.border_visible / coerce_border_mode: the border's 3-way decision.

Pure functions, no widgets — the border mode ('off'/'always'/'auto') plus the
note's luminance decide whether the outer border is drawn. Auto keys off a
dedicated threshold (BORDER_LIGHT_THRESHOLD), separate from auto-contrast.
"""
import sys, os
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ.pop("DISPLAY", None); os.environ.pop("WAYLAND_DISPLAY", None)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtGui import QColor
from sticky_notes.theme import border_visible, coerce_border_mode, BORDER_MODES

fails = []
def check(name, cond):
    print(f"  {'PASS' if cond else 'FAIL'}   {name}")
    if not cond: fails.append(name)

yellow, charcoal = QColor("#fff59d"), QColor("#2b2b30")
white, black = QColor("#ffffff"), QColor("#000000")

check("modes are exactly off/always/auto", BORDER_MODES == ("off", "always", "auto"))

check("off never draws (light note)", border_visible("off", yellow) is False)
check("off never draws (dark note)", border_visible("off", charcoal) is False)
check("always draws on a light note", border_visible("always", yellow) is True)
check("always draws on a dark note", border_visible("always", charcoal) is True)
check("auto draws on a light (yellow) note", border_visible("auto", yellow) is True)
check("auto draws on white", border_visible("auto", white) is True)
check("auto does NOT draw on a charcoal note", border_visible("auto", charcoal) is False)
check("auto does NOT draw on black", border_visible("auto", black) is False)
check("unknown mode never draws", border_visible("bogus", yellow) is False)

check("migrate old bool True -> always", coerce_border_mode(True) == "always")
check("migrate old bool False -> off", coerce_border_mode(False) == "off")
check("keep a valid mode string", coerce_border_mode("auto") == "auto")
check("keep 'always'", coerce_border_mode("always") == "always")
check("keep 'off'", coerce_border_mode("off") == "off")
check("unknown string -> off", coerce_border_mode("bogus") == "off")
check("None -> off", coerce_border_mode(None) == "off")

print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
