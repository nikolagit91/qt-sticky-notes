"""Settings tabs must fit the dialog width in every language, without scroll arrows.

Bug: longer translated tab labels (German, French) overflowed the Settings
dialog — the dialog opened at dlg.sizeHint() width (which undershoots the tab
bar's own width), so QTabBar showed scroll arrows. And `:selected { font-weight:
600 }` made the active tab wider than the others, so clicking a long tab grew
the tab bar past the fixed dialog width → arrows appeared on click.

Guards two invariants, in en/de/fr:
  1. the dialog is at least as wide as its tab bar wants (tabs fit, no arrows);
  2. the tab bar's width does not depend on which tab is selected (no bold shift).
Offscreen measures geometry; the real arrows are a GNOME render, but the width
invariant is what makes them impossible."""
import sys, os, tempfile, atexit, shutil
_SB = tempfile.mkdtemp(prefix="sn_tabfit_")
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

from PyQt6.QtWidgets import QDialog
from sticky_notes.app import StickyNotesApp
from sticky_notes.i18n import set_language, tr
app = StickyNotesApp(sys.argv[:1])

for lang in ("en", "de", "fr"):
    set_language(lang)
    app.show_settings()
    dlg = [w for w in app._open_windows
           if isinstance(w, QDialog) and w.windowTitle() == tr("Settings")][-1]
    tabs = dlg._tabs
    tb = tabs.tabBar()

    # (1) dialog wide enough for the tab bar → no scroll arrows
    check(f"[{lang}] dialog fits the tab bar ({dlg.width()} >= {tb.sizeHint().width()})",
          dlg.width() >= tb.sizeHint().width())

    # (2) tab-bar width is stable regardless of which tab is selected (no bold shift)
    widths = []
    for i in range(tabs.count()):
        tabs.setCurrentIndex(i)
        widths.append(tb.sizeHint().width())
    check(f"[{lang}] selecting a tab does not change tab-bar width (min={min(widths)} max={max(widths)})",
          min(widths) == max(widths))

    dlg.close()
    if dlg in app._open_windows:
        app._open_windows.remove(dlg)

print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
