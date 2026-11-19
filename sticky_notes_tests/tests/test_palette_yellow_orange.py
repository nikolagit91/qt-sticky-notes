"""Guard: the palette's yellow and orange are readable on light notes, and text
coloured with the OLD shades is moved to the new ones.

Before (2026-11-19, contrast measured on all 8 light notes): yellow #f9a825
1.6–1.8:1 (on a yellow note practically invisible), orange #e67c13 2.3–2.6:1.
Darkening the same hue turned both into the same brown (rendered,
~/Pictures/sticky-probe/yellow_orange_shades.png), so the user picked variant D
(…_v2.png): hues pulled apart — yellow → gold #957200, orange → red-orange
#d04c00 — both ≥3.5:1 on every light note. The dark twins are unchanged.
Old shades (saved, pasted) are stored as the new ones via theme.store_colour.
"""
import sys, os, tempfile, atexit, shutil
_SB = tempfile.mkdtemp(prefix="sn_pyo_")
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

from PyQt6.QtCore import Qt, QMimeData
from PyQt6.QtWidgets import QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from PyQt6.QtGui import QTextCursor, QColor, QTextCharFormat
from sticky_notes.app import StickyNotesApp
from sticky_notes.note import StickyNote
from sticky_notes import theme

OLD_YELLOW, OLD_ORANGE = "#f9a825", "#e67c13"
NEW_YELLOW, NEW_ORANGE = "#957200", "#d04c00"
TWIN = dict(theme.TEXT_PALETTE)
LIGHT = [l for l, _ in theme.TEXT_PALETTE]
LIGHT_NOTE, DARK_NOTE = "#fff59d", "#2b2b30"

def ratio(a, b):
    la, lb = sorted((theme._rel_luminance(QColor(a)), theme._rel_luminance(QColor(b))), reverse=True)
    return (la + 0.05) / (lb + 0.05)

# ── the palette ───────────────────────────────────────────────────────────────
check("yellow slot is the new gold, orange slot the new red-orange",
      LIGHT[6] == NEW_YELLOW and LIGHT[5] == NEW_ORANGE)
check("the dark twins are unchanged",
      TWIN.get(NEW_YELLOW) == "#fdd663" and TWIN.get(NEW_ORANGE) == "#fcad70")
light_notes = list(StickyNote.NOTE_COLORS.values())
for c in (NEW_YELLOW, NEW_ORANGE):
    worst = min(ratio(c, n) for n in light_notes)
    check(f"{c} readable on every light note (≥3.5, got {worst:.2f})", worst >= 3.5)
check("old shades are no longer offered", OLD_YELLOW not in LIGHT and OLD_ORANGE not in LIGHT)
check("store_colour moves the old shades to the new ones",
      theme.store_colour(OLD_YELLOW) == NEW_YELLOW and theme.store_colour(OLD_ORANGE) == NEW_ORANGE)

# ── app ───────────────────────────────────────────────────────────────────────
app = StickyNotesApp(sys.argv[:1])
for e in list(app.notes.values()):
    e.hide(); e.deleteLater()
app.notes.clear()

def colour_at(d, p, drawn=False):
    blk = d.findBlock(p); rel = p - blk.position()
    if drawn:
        for r in blk.layout().formats():
            if r.start <= rel < r.start + r.length and \
                    r.format.foreground().style() != Qt.BrushStyle.NoBrush:
                return r.format.foreground().color().name().lower()
    c = QTextCursor(d); c.setPosition(p); c.setPosition(p + 1, QTextCursor.MoveMode.KeepAnchor)
    f = c.charFormat()
    return None if f.foreground().style() == Qt.BrushStyle.NoBrush else f.foreground().color().name().lower()

html = (f'<p><span style="color:{OLD_YELLOW}">zuto</span></p>'
        f'<p><span style="color:{OLD_ORANGE}">narancasto</span></p>')
for base, label in ((LIGHT_NOTE, "light"), (DARK_NOTE, "dark")):
    ld = StickyNote(app, data={"content": html, "content_type": "html", "color": base})
    ld.show(); app.processEvents()
    d = ld.text_edit.document()
    y, o = d.findBlockByNumber(0).position(), d.findBlockByNumber(1).position()
    check(f"load ({label} note): old yellow/orange stored as the new shades",
          colour_at(d, y) == NEW_YELLOW and colour_at(d, o) == NEW_ORANGE)
    want = (NEW_YELLOW, NEW_ORANGE) if label == "light" else ("#fdd663", "#fcad70")
    check(f"load ({label} note): drawn as {want}",
          (colour_at(d, y, True), colour_at(d, o, True)) == want)
    check(f"load ({label} note): no undo step", not d.isUndoAvailable())

n = app.create_new_note(); n.show(); app.processEvents()
te = n.text_edit; te.setCurrentCharFormat(QTextCharFormat()); te.setPlainText("")
md = QMimeData(); md.setHtml(f'<span style="color:{OLD_ORANGE}">staro</span>'); md.setText("staro")
te.insertFromMimeData(md); app.processEvents()
check("paste of the old orange is stored as the new one", colour_at(te.document(), 0) == NEW_ORANGE)

print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
