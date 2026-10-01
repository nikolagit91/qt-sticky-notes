"""Regression: pasted web headings must be resizable.

Web <h1>..<h6> put a char-level QTextFormat.FontSizeAdjustment on the text. Qt
applies that relative modifier when rendering and it OVERRIDES the point size,
so setFontPointSize() changed the model but the heading's rendered size never
moved ("resize does nothing on pasted headings"). Paste normalization must clear
FontSizeAdjustment (and the paragraph margins) so pasted text behaves like typed.
"""
import sys, os, tempfile, atexit, shutil

_SB = tempfile.mkdtemp(prefix="sn_phr_")
atexit.register(lambda: shutil.rmtree(_SB, ignore_errors=True))
os.environ["HOME"] = _SB
os.environ["XDG_CONFIG_HOME"] = os.path.join(_SB, ".config")
os.environ["XDG_DATA_HOME"]   = os.path.join(_SB, ".local", "share")
os.environ.setdefault("XDG_RUNTIME_DIR", _SB)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ.pop("DISPLAY", None); os.environ.pop("WAYLAND_DISPLAY", None)
os.makedirs(os.path.join(_SB, ".local", "share", "sticky_notes"), exist_ok=True)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QMimeData
from PyQt6.QtGui import QTextCursor, QTextFormat

fails = []
def check(name, cond):
    print(f"  {'PASS' if cond else 'FAIL'}   {name}")
    if not cond: fails.append(name)

app = QApplication(sys.argv[:1])
f = app.font(); f.setPointSizeF(13); app.setFont(f)
from sticky_notes.widgets import NoteTextEdit

web = ('<h1>Naslov</h1>'
       '<p style="font-size:24px">Veliki red</p>')
md = QMimeData(); md.setHtml(web); md.setText("Naslov\nVeliki red")
te = NoteTextEdit(); te.resize(400, 300)
te.insertFromMimeData(md)
doc = te.document()

# 1) No character may keep the heading FontSizeAdjustment after paste.
def _cf(d, p):
    c = QTextCursor(d); c.setPosition(p); c.setPosition(p + 1, QTextCursor.MoveMode.KeepAnchor)
    return c.charFormat()
leftover = [p for p in range(doc.characterCount() - 1)
            if _cf(doc, p).hasProperty(QTextFormat.Property.FontSizeAdjustment)]
check("no FontSizeAdjustment survives paste", leftover == [])

# 2) The heading block's RENDERED height must shrink when we resize it small.
doc.setTextWidth(380)
lay = doc.documentLayout(); b0 = doc.firstBlock()
h_before = lay.blockBoundingRect(b0).height()
for p in range(0, 6):                       # "Naslov"
    ch = QTextCursor(doc); ch.setPosition(p); ch.setPosition(p + 1, QTextCursor.MoveMode.KeepAnchor)
    g = ch.charFormat(); g.setFontPointSize(8); ch.setCharFormat(g)
doc.setTextWidth(380)
h_after = lay.blockBoundingRect(b0).height()
check(f"heading rendered height shrinks ({h_before:.0f}->{h_after:.0f})", h_after < h_before - 5)

# 3) Paragraph margins from <p>/<h1> are stripped (typed text has none).
margins = []
b = doc.firstBlock()
while b.isValid():
    bf = b.blockFormat()
    if bf.topMargin() or bf.bottomMargin():
        margins.append(b.blockNumber())
    b = b.next()
check("no paragraph top/bottom margins remain", margins == [])

print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
