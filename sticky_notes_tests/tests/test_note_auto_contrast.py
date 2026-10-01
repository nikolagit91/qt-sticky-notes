import sys, os, tempfile, atexit, shutil
_SB = tempfile.mkdtemp(prefix="sn_ac_")
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
from PyQt6.QtGui import QColor
QMessageBox.information = staticmethod(lambda *a, **k: None)
from sticky_notes.app import StickyNotesApp
app = StickyNotesApp(sys.argv[:1])   # single app instance (avoids teardown segfault)

fails = []
def check(name, cond):
    print(f"  {'PASS' if cond else 'FAIL'}   {name}")
    if not cond: fails.append(name)

from sticky_notes.theme import note_ink, DARK_INK, LIGHT_INK

# Light note (classic sticky yellow) -> DARK ink, header darker than base.
y = note_ink(QColor("#fff59d"))
check("yellow -> dark ink text #333", y.text == "#333333")
check("yellow -> dark ink idle #888", y.ink == "#888888")
check("yellow header is darker than base", y.header.lightness() < QColor("#fff59d").lightness())

# Clearly dark note -> LIGHT ink, header lighter than base.
d = note_ink(QColor("#1a2340"))
check("dark navy -> light ink text #f0f0f0", d.text == "#f0f0f0")
check("dark navy -> light ink idle #cccccc", d.ink == "#cccccc")
check("dark navy header is lighter than base", d.header.lightness() > QColor("#1a2340").lightness())

# Conservative: a medium grey stays on DARK ink.
m = note_ink(QColor("#7f7f7f"))
check("medium grey stays dark ink (conservative)", m.text == "#333333")

# ── Task 2: QSS builders ──────────────────────────────────────────────────────
from sticky_notes.theme import (fmt_btn_style, size_label_style, sep_style,
    header_btn_style, family_btn_style, close_btn_style, progress_label_style,
    text_color_btn_style, text_edit_style)

di, li = DARK_INK, LIGHT_INK
check("fmt_btn uses ink idle", "#888888" in fmt_btn_style(di))
check("fmt_btn extra decoration appended", "font-weight: bold;" in fmt_btn_style(di, "font-weight: bold;"))
check("fmt_btn light set uses light idle", "#cccccc" in fmt_btn_style(li))
check("text_edit uses ink text + selection", "#333333" in text_edit_style(di) and "rgba(0,0,0,0.18)" in text_edit_style(di))
check("text_edit light set", "#f0f0f0" in text_edit_style(li))
check("sep uses ink separator", "rgba(0,0,0,0.12)" in sep_style(di))
check("header_btn uses ink_dim idle", "#555555" in header_btn_style(di))
check("family_btn uses ink_dim", "#555555" in family_btn_style(di))
check("close_btn idle uses ink_dim, keeps red hover", "#555555" in close_btn_style(di) and "#e53935" in close_btn_style(di))
check("progress uses ink_dim", "#555555" in progress_label_style(di))
check("text_color keeps glyph colour", "#123456" in text_color_btn_style(di, "#123456"))
check("ink carries an SVG icon fill", di.icon == "#494c4e" and li.icon == "#cccccc")
check("note_ink auto=False forces dark ink on a dark colour",
      note_ink(QColor("#1a2340"), auto=False).text == "#333333")
check("note_ink auto=False keeps header darker than base",
      note_ink(QColor("#1a2340"), auto=False).header.lightness() < QColor("#1a2340").lightness())

# ── Task 3: _apply_ink wiring on a real note ──────────────────────────────────
from sticky_notes.note import StickyNote
note = StickyNote(app, "n", {"id": "n", "geometry": [100, 100, 400, 300]})
app.notes["n"] = note

note.color = "#1a2340"; note._apply_color()      # clearly dark
check("dark note: text_edit uses light text", "#f0f0f0" in note.text_edit.styleSheet())
check("dark note: bold button uses light idle", "#cccccc" in note.btn_bold.styleSheet())
check("dark note: bold decoration preserved", "font-weight: bold;" in note.btn_bold.styleSheet())
check("dark note: header lighter than base", note._qcolor_header.lightness() > QColor("#1a2340").lightness())
check("dark note: SVG icon fill is light", note._icon_fill == "#cccccc")
check("dark note: lock button hover matches ink", li.hover_bg in note.btn_lock.styleSheet())
check("dark note: toolbar-toggle hover matches ink", li.hover_bg in note.btn_toolbar_toggle.styleSheet())

note.color = "#fff59d"; note._apply_color()      # back to light
check("light note: text_edit uses dark text", "#333333" in note.text_edit.styleSheet())
check("light note: bold button uses dark idle", "#888888" in note.btn_bold.styleSheet())
check("light note: header darker than base", note._qcolor_header.lightness() < QColor("#fff59d").lightness())
check("light note: SVG icon fill is legacy dark", note._icon_fill == "#494c4e")

# Auto-contrast OFF: even a dark note keeps today's fixed dark ink.
check("app defaults auto-contrast ON", app._auto_contrast is True)
app._auto_contrast = False
note.color = "#1a2340"; note._apply_color()
check("auto off: dark note keeps dark text", "#333333" in note.text_edit.styleSheet())
check("auto off: dark note keeps legacy icon fill", note._icon_fill == "#494c4e")
app._auto_contrast = True
note._apply_color()
check("auto on again: dark note flips to light text", "#f0f0f0" in note.text_edit.styleSheet())
note.hide(); note.deleteLater()

# ── Manager rows follow the note colour too ───────────────────────────────────
from sticky_notes.manager import NotesManager, ElidingLabel
mgr = NotesManager(app)
dark_row = mgr._make_note_row({"id": "z", "color": "#1a2340", "display_title": "Dark"}, kind="trash")
check("manager: dark note row label uses light ink text",
      "#f0f0f0" in dark_row.findChild(ElidingLabel).styleSheet())
light_row = mgr._make_note_row({"id": "z2", "color": "#fff59d", "display_title": "Light"}, kind="trash")
check("manager: light note row label uses dark ink text",
      "#333333" in light_row.findChild(ElidingLabel).styleSheet())
mgr.deleteLater()

# The trash SVG has no explicit fill on its <path>, so tinting must reach it via
# the root <svg> fill (regression: it stayed black on dark rows).
from sticky_notes.icons import _make_lock_icon, _SVG_TRASH, _HAS_SVG
if _HAS_SVG:
    img = _make_lock_icon(_SVG_TRASH, 20, fill="#ff0000").pixmap(20, 20).toImage()
    reddish = any(
        img.pixelColor(x, y).alpha() > 200
        and img.pixelColor(x, y).red() > 150
        and img.pixelColor(x, y).green() < 100
        for y in range(img.height()) for x in range(img.width()))
    check("trash icon honours the fill colour", reddish)

# Manager row icon HOVER backgrounds follow the ink too (light on dark rows).
from PyQt6.QtWidgets import QPushButton
dn = StickyNote(app, "dk", {"id": "dk", "geometry": [0, 0, 300, 200]})
dn._set_color("#1a2340")     # light mode → writes the light slot, so get_data carries it
app.notes["dk"] = dn
mgr2 = NotesManager(app)
arow = mgr2._make_note_row(dn.get_data(), kind="active")
hovers = " ".join(b.styleSheet() for b in arow.findChildren(QPushButton))
check("manager: dark active-row icon hover is light", li.hover_bg in hovers)
mgr2.deleteLater(); dn.hide(); dn.deleteLater()

if not fails: print("\nALL PASS")
sys.exit(1 if fails else 0)
