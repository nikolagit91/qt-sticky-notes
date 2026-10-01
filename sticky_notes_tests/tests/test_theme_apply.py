"""apply_theme swaps the chrome UI palette (Light/Dark) and rebuilds the
module-level text-style constants so already-imported style strings pick up the
new colours on next read. No app build needed — pure theme module test."""
import sys, os, tempfile, atexit, shutil

_SB = tempfile.mkdtemp(prefix="sn_theme_")
atexit.register(lambda: shutil.rmtree(_SB, ignore_errors=True))
os.environ["HOME"] = _SB
os.environ["XDG_CONFIG_HOME"] = os.path.join(_SB, ".config")
os.environ["XDG_DATA_HOME"]   = os.path.join(_SB, ".local", "share")
os.environ.setdefault("XDG_RUNTIME_DIR", _SB)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ.pop("DISPLAY", None); os.environ.pop("WAYLAND_DISPLAY", None)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sticky_notes.theme as th

fails = []
def check(name, cond):
    print(f"  {'PASS' if cond else 'FAIL'}   {name}")
    if not cond: fails.append(name)

# light is default
th.apply_theme("light")
light_bg = th.UI.WINDOW_BG
check("light WINDOW_BG matches LIGHT_UI", th.UI.WINDOW_BG == th.LIGHT_UI["WINDOW_BG"])
check("current_theme light", th.current_theme() == "light")
check("LABEL_STYLE holds light TEXT", th.UI.TEXT in th.UI.LABEL_STYLE)

# swap to dark changes colour slots AND the live text-style attributes on UI
th.apply_theme("dark")
check("dark WINDOW_BG changed", th.UI.WINDOW_BG == th.DARK_UI["WINDOW_BG"] != light_bg)
check("dark TEXT applied", th.UI.TEXT == th.DARK_UI["TEXT"])
check("LABEL_STYLE rebuilt with dark TEXT", th.DARK_UI["TEXT"] in th.UI.LABEL_STYLE)
check("HINT_STYLE rebuilt with dark TEXT_MUTED", th.DARK_UI["TEXT_MUTED"] in th.UI.HINT_STYLE)

# round-trip back to light
th.apply_theme("light")
check("round-trip light WINDOW_BG", th.UI.WINDOW_BG == light_bg)
check("unknown name falls back to light", (th.apply_theme("bogus") or th.current_theme()) == "light")

print("FAILS:", fails)
sys.exit(1 if fails else 0)
