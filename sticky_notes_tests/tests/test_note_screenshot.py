import sys, os, tempfile, atexit, shutil
_SB = tempfile.mkdtemp(prefix="sn_png_")
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
from PyQt6.QtGui import QImage
QMessageBox.information = staticmethod(lambda *a, **k: None)

fails = []
def check(name, cond):
    print(f"  {'PASS' if cond else 'FAIL'}   {name}")
    if not cond: fails.append(name)

from sticky_notes.app import StickyNotesApp
from sticky_notes.note import StickyNote
from sticky_notes import export
app = StickyNotesApp(sys.argv[:1])

note = StickyNote(app, "n", {"id": "n", "geometry": [0, 0, 300, 200]})
note.color = "#1a2340"; note._apply_color()          # a dark note
note.text_edit.setPlainText("Hello\nWorld")
note.resize(300, 200)

out = os.path.join(_SB, "shot.png")
te_w = note.text_edit.width()
export.render_note_png(note, out)

check("PNG file was written", os.path.exists(out) and os.path.getsize(out) > 0)
img = QImage(out)
check("PNG loads with a non-zero size", not img.isNull() and img.width() > 0 and img.height() > 0)
# Rendered at 3x the on-screen size (crisp when zoomed), not the logical size.
check("PNG is rendered at PNG_SCALE resolution", img.width() == te_w * export.PNG_SCALE)
# Left-padding pixel, vertically centred → bare solid paper (#1a2340 = 26,35,64).
p = img.pixelColor(12, img.height() // 2)
check("padding pixel is the solid note colour",
      p.alpha() == 255 and abs(p.red()-26) <= 3 and abs(p.green()-35) <= 3 and abs(p.blue()-64) <= 3)
# Top-left corner is inside the rounded-corner cut → transparent.
check("corner pixel is transparent", img.pixelColor(0, 0).alpha() == 0)

# The Export… menu "png" branch must save through the Save-As dialog path.
from PyQt6.QtWidgets import QFileDialog
out2 = os.path.join(_SB, "via_menu.png")
QFileDialog.getSaveFileName = staticmethod(lambda *a, **k: (out2, "PNG image (*.png)"))
note.text_edit.setPlainText("Menu path")
note._export_as("png")
check("_export_as('png') wrote the file", os.path.exists(out2) and os.path.getsize(out2) > 0)
check("_export_as('png') output is a valid PNG", not QImage(out2).isNull())

note.hide(); note.deleteLater()
print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
