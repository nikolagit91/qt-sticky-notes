"""The global search palette follows a LIVE theme change.

The palette is built once and reused (app.show_search). Its frame, search box
and empty-state label bake UI.* colours into stylesheets at construction, so a
theme switch after the first open used to leave them in the old theme while the
result rows (painted per-frame by the delegate) followed the new one — light
rows on a light frame, i.e. nearly unreadable.

Measured on the rendered pixels (grab), not on the stylesheet strings: what the
user sees is what must match."""
import sys, os, tempfile, atexit, shutil
_SB = tempfile.mkdtemp(prefix="sn_searchtheme_")
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

from sticky_notes import theme
from sticky_notes.app import StickyNotesApp

app = StickyNotesApp(sys.argv[:1])
for e in list(app.notes.values()):
    e.hide(); e.deleteLater()
app.notes.clear()
app.create_new_note(content="hello world", color="#fff59d", color_dark="#2b2b30")

def pump():
    for _ in range(5):
        app.processEvents()

def sample(palette):
    """(frame background, search-box background) as rendered."""
    img = palette.grab().toImage()
    frame_px = img.pixelColor(img.width() // 2, img.height() - 5).name()   # bottom padding of the frame
    box = palette.search.geometry()
    top_left = palette.search.mapTo(palette, box.topLeft() - box.topLeft())
    box_px = img.pixelColor(top_left.x() + 6, top_left.y() + box.height() // 2).name()
    return frame_px, box_px

def open_search():
    app.show_search(); pump()
    return app._search_palette

# Control: first open happens in dark → built with dark colours.
app._set_theme("dark"); pump()
p = open_search()
frame, box = sample(p)
check("control: palette first opened in dark has dark frame", frame == theme.DARK_UI["WINDOW_BG"].lower())
check("control: palette first opened in dark has dark search box", box == theme.DARK_UI["SURFACE"].lower())
p.close(); pump()

# The user's flow: palette already built (dark), theme switched live, reopened.
app._set_theme("light"); pump()
p = open_search()
frame, box = sample(p)
check(f"after live switch to light: frame is light ({frame} vs {theme.LIGHT_UI['WINDOW_BG']})",
      frame == theme.LIGHT_UI["WINDOW_BG"].lower())
check(f"after live switch to light: search box is light ({box} vs {theme.LIGHT_UI['SURFACE']})",
      box == theme.LIGHT_UI["SURFACE"].lower())
p.close(); pump()

app._set_theme("dark"); pump()
p = open_search()
frame, box = sample(p)
check(f"after live switch back to dark: frame is dark ({frame})", frame == theme.DARK_UI["WINDOW_BG"].lower())
check(f"after live switch back to dark: search box is dark ({box})", box == theme.DARK_UI["SURFACE"].lower())

# Switching while the palette is OPEN (e.g. the Auto schedule crossing its
# boundary) must restyle it in place too.
app._set_theme("light"); pump()
frame, box = sample(p)
check(f"switch while open: frame restyled to light ({frame})", frame == theme.LIGHT_UI["WINDOW_BG"].lower())
check(f"switch while open: search box restyled to light ({box})", box == theme.LIGHT_UI["SURFACE"].lower())
check("palette object reused (never recreated by a theme change)", app._search_palette is p)
p.close(); pump()

print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
