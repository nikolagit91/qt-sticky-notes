"""Settings checkbox indicators must be explicitly styled in BOTH themes.

Bug: with the app in light theme but GNOME set to a dark system theme, the
Settings checkboxes rendered as solid black. Cause — settings_dialog_style()
only styled QCheckBox::indicator in dark app theme; light theme left the native
indicator, which Qt paints from the GNOME system palette (dark → black box).

Guard: the indicator must carry an explicit background in either app theme, so
it never inherits the system checkbox look. This is a string-invariant guard —
the real visual bug only reproduces under a live GNOME dark session, so we pin
the invariant that makes the app independent of the system theme."""
import sys, os, tempfile, atexit, shutil
_SB = tempfile.mkdtemp(prefix="sn_ckind_")
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

from PyQt6.QtWidgets import QApplication
_app = QApplication(sys.argv[:1])
from sticky_notes.theme import apply_theme, settings_dialog_style, UI

def indicator_block(css):
    """Return the `QCheckBox::indicator { ... }` body (the unchecked state)."""
    i = css.find("QCheckBox::indicator {")
    if i < 0:
        return ""
    return css[i:css.find("}", i)]

for theme in ("light", "dark"):
    apply_theme(theme)
    css = settings_dialog_style("/tmp/_tick.png")
    blk = indicator_block(css)
    check(f"{theme}: checkbox indicator is explicitly styled", blk != "")
    check(f"{theme}: indicator has an explicit background (not native)",
          "background" in blk)
    check(f"{theme}: indicator background is the theme surface {UI.SURFACE}",
          f"background: {UI.SURFACE}" in blk)
    check(f"{theme}: checked state fills with the accent + tick",
          "QCheckBox::indicator:checked" in css and "image: url(" in css)

print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
