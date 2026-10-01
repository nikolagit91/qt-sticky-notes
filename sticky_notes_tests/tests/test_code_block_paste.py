import sys, os, tempfile, atexit, shutil
_SB = tempfile.mkdtemp(prefix="sn_cbp_")
atexit.register(lambda: shutil.rmtree(_SB, ignore_errors=True))
os.environ["HOME"] = _SB
os.environ["XDG_CONFIG_HOME"] = os.path.join(_SB, ".config")
os.environ["XDG_DATA_HOME"]   = os.path.join(_SB, ".local", "share")
os.environ.setdefault("XDG_RUNTIME_DIR", _SB)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ.pop("DISPLAY", None); os.environ.pop("WAYLAND_DISPLAY", None)
os.makedirs(os.path.join(_SB, ".local", "share", "sticky_notes"), exist_ok=True)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import QMessageBox, QApplication
QMessageBox.information = staticmethod(lambda *a, **k: None)
from PyQt6.QtCore import QMimeData

fails = []
def check(name, cond):
    print(f"  {'PASS' if cond else 'FAIL'}   {name}")
    if not cond: fails.append(name)

from sticky_notes.app import StickyNotesApp
from sticky_notes.note import StickyNote
from sticky_notes.widgets import CODE_FONT_FAMILY, CODE_BLOCK_MARGIN
app = StickyNotesApp(sys.argv[:1])

def all_code(te):
    d = te.document()
    return all(te._is_code_block(d.findBlockByNumber(i)) for i in range(d.blockCount()))
def proper_marker(te):
    """Every code block must carry the SAME contract toggle_code_block makes: a
    TRANSPARENT marker background (so paintEvent's rounded box shows, not an
    opaque native square) and the L/R text-inset margins. An opaque bg / zero
    margins is the paste bug — visually a square edge-to-edge fill, no padding."""
    d = te.document()
    for i in range(d.blockCount()):
        bf = d.findBlockByNumber(i).blockFormat()
        if bf.background().color().alpha() != 0:      # opaque fill = bug
            return False
        if round(bf.leftMargin()) != CODE_BLOCK_MARGIN or round(bf.rightMargin()) != CODE_BLOCK_MARGIN:
            return False
    return True
def paste(te, text):
    md = QMimeData(); md.setText(text); te.insertFromMimeData(md)

# 1) Empty code line + single-line paste → line stays a code block with the text.
n1 = StickyNote(app, "a", {"id": "a", "geometry": [0, 0, 300, 200]})
te = n1.text_edit
te.toggle_code_block()
paste(te, "hello")
check("empty code line + paste keeps the code block", te._is_code_block(te.document().begin()) is True)
check("pasted text is present", "hello" in te.toPlainText())

# 2) Multi-line paste into a code block → EVERY resulting line is code.
n2 = StickyNote(app, "b", {"id": "b", "geometry": [0, 0, 300, 200]})
te2 = n2.text_edit
te2.toggle_code_block()
paste(te2, "line1\nline2\nline3")
check("multi-line paste: 3 blocks", te2.document().blockCount() == 3)
check("multi-line paste: all lines are code blocks", all_code(te2))
check("multi-line paste: all blocks are proper markers (transparent bg + margins)",
      proper_marker(te2))
cc = te2.textCursor(); cc.movePosition(cc.MoveOperation.End)
cc.movePosition(cc.MoveOperation.StartOfBlock, cc.MoveMode.KeepAnchor)
check("last pasted line is monospace", CODE_FONT_FAMILY in (cc.charFormat().fontFamilies() or []))
check("last pasted line carries code_fg foreground",
      cc.charFormat().foreground().color().name().lower() == te2.code_fg_color.name().lower())

# 2b) RICH (HTML) paste — the real-world case (browser/editor) that used to dump
# the code block. In a code block it must still land as plain, all-code text.
n2b = StickyNote(app, "b2", {"id": "b2", "geometry": [0, 0, 300, 200]})
te2b = n2b.text_edit
te2b.toggle_code_block()
md = QMimeData(); md.setText("r1\nr2"); md.setHtml("<p>r1</p><p>r2</p>")
te2b.insertFromMimeData(md)
check("rich paste into code block: all blocks code", all_code(te2b))
n2b.hide(); n2b.deleteLater()

# 3) Type then paste multi-line → the rest is NOT dumped into a plain section.
n3 = StickyNote(app, "c", {"id": "c", "geometry": [0, 0, 300, 200]})
te3 = n3.text_edit
te3.toggle_code_block()
c = te3.textCursor(); c.insertText("ab")
paste(te3, "cd\nef")
check("type+paste: all resulting blocks are code", all_code(te3))
check("type+paste: all blocks are proper markers", proper_marker(te3))

# 4) Ctrl+Shift+V path (paste_as_plain_text) also stays code.
n4 = StickyNote(app, "d", {"id": "d", "geometry": [0, 0, 300, 200]})
te4 = n4.text_edit
te4.toggle_code_block()
QApplication.clipboard().setText("p1\np2")
te4.paste_as_plain_text()
check("paste-as-plain into code block stays all code", all_code(te4))
check("paste-as-plain: all blocks are proper markers", proper_marker(te4))

for n in (n1, n2, n3, n4):
    n.hide(); n.deleteLater()
print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
