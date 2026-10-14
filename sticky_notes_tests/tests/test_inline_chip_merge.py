"""One contiguous inline-code run gets ONE chip, even when it is made of several
text fragments.

Qt splits text into fragments wherever the char format differs at all. Text
typed in inline mode and text pasted into the span carry slightly different
formats, so they are separate fragments. The chips used to be built per
FRAGMENT: two rounded chips met at the seam, leaving notches top and bottom
where the rounded corners touched, and overlapping in the middle (reported:
type "asfsdf " in inline mode, then paste "cd ~/..." → visible seam).

Measured on the layout (chip rects) and on rendered pixels at the seam."""
import sys, os, tempfile, atexit, shutil
_SB = tempfile.mkdtemp(prefix="sn_chipmerge_")
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
from PyQt6.QtCore import QMimeData, QPoint
from PyQt6.QtGui import QTextCursor
from PyQt6.QtTest import QTest

fails = []
def check(name, cond):
    print(f"  {'PASS' if cond else 'FAIL'}   {name}")
    if not cond: fails.append(name)

from sticky_notes.app import StickyNotesApp
from sticky_notes.note import StickyNote
app = StickyNotesApp(sys.argv[:1])

def pump():
    for _ in range(5):
        app.processEvents()

def fragments_in_block0(te):
    it = te.document().begin().begin(); n = 0
    while not it.atEnd():
        if it.fragment().isValid(): n += 1
        it += 1
    return n

note = StickyNote(app, "n", {"id": "n", "geometry": [0, 0, 420, 200], "color": "#fff59d"})
note.show(); pump()
te = note.text_edit
te.setFocus()
te.toggle_inline_code()                     # no selection → typing format becomes inline
QTest.keyClicks(te, "asfsdf ")              # typed in inline mode, incl. the space
md = QMimeData()                             # like copying from a web page
md.setHtml("<span style='color:#202124'>cd ~/x</span>"); md.setText("cd ~/x")
te.insertFromMimeData(md)
pump()

check("text is one inline line", te.document().toPlainText() == "asfsdf cd ~/x")
check("precondition: typed + pasted text are separate fragments (the trigger)",
      fragments_in_block0(te) >= 2)
rects = te._inline_run_rects()
check(f"one contiguous inline run → ONE chip (got {len(rects)})", len(rects) == 1)

# Pixels: just inside the top and bottom edge of the chip, at the seam (the
# boundary between the typed space and the pasted 'c'), must be chip colour —
# same as a point well inside the typed part. Notches = paper colour there.
te.viewport().update(); pump()
img = note.grab().toImage()
seam_pos = len("asfsdf ")
c = QTextCursor(te.document()); c.setPosition(seam_pos)
seam_x = te.cursorRect(c).x()
c.setPosition(2); ref_x = te.cursorRect(c).x()
top = int(min(r.top() for r in rects)) + 1
bottom = int(max(r.bottom() for r in rects)) - 1
def px(x, y):
    p = te.viewport().mapTo(note, QPoint(int(x), int(y)))
    return img.pixelColor(p.x(), p.y()).name()
ref_top, ref_bot = px(ref_x, top), px(ref_x, bottom)
check(f"no notch at the TOP of the seam ({px(seam_x, top)} vs {ref_top})", px(seam_x, top) == ref_top)
check(f"no notch at the BOTTOM of the seam ({px(seam_x, bottom)} vs {ref_bot})", px(seam_x, bottom) == ref_bot)

# A run interrupted by plain text is still TWO chips (merging must not bridge a gap).
n2 = StickyNote(app, "m", {"id": "m", "geometry": [0, 0, 420, 200], "color": "#fff59d"})
n2.show(); pump()
t2 = n2.text_edit
t2.textCursor().insertText("aa bb cc")
for word in ("aa", "cc"):
    t2.setTextCursor(t2.document().find(word)); t2.toggle_inline_code()
check(f"two runs separated by plain text stay two chips (got {len(t2._inline_run_rects())})",
      len(t2._inline_run_rects()) == 2)

note.hide(); note.deleteLater(); n2.hide(); n2.deleteLater()
print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
