"""Guard: code in an ODT export is readable.

Before (2026-11-19, found while fixing the export ink): on screen a code
block's background and an inline-code chip's char background are TRANSPARENT
markers rgba(0,0,0,0) — the visible box/chip is painted by the editor. ODF has
no alpha, so ODT wrote them as solid BLACK: inline code came out as dark text
on a black box (unreadable — rendered through LibreOffice to check). PDF
already restored real fills (_restore_code_fills); ODT never did.
"""
import sys, os, tempfile, atexit, shutil, zipfile, re
_SB = tempfile.mkdtemp(prefix="sn_eoc_")
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

from PyQt6.QtWidgets import QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from PyQt6.QtGui import QColor, QTextCharFormat, QTextCursor
from sticky_notes.app import StickyNotesApp
from sticky_notes import export, theme

app = StickyNotesApp(sys.argv[:1])
for e in list(app.notes.values()):
    e.hide(); e.deleteLater()
app.notes.clear()
n = app.create_new_note(); te = n.text_edit; doc = te.document()
n.show(); app.processEvents()

def ratio(a, b):
    la, lb = sorted((theme._rel_luminance(QColor(a)), theme._rel_luminance(QColor(b))), reverse=True)
    return (la + 0.05) / (lb + 0.05)

def odt_styles(path):
    """{style-name: {'color':…, 'bg':…}} for text and paragraph automatic styles."""
    xml = zipfile.ZipFile(path).read("content.xml").decode()
    out = {}
    for m in re.finditer(r'<style:style style:name="([^"]+)"[^>]*>(.*?)</style:style>', xml, re.S):
        body = m.group(2)
        col = re.search(r'fo:color="(#[0-9a-fA-F]{6})"', body)
        bg = re.search(r'fo:background-color="(#[0-9a-fA-F]{6})"', body)
        out[m.group(1)] = {"color": col and col.group(1).lower(), "bg": bg and bg.group(1).lower()}
    return xml, out

def spans(xml, word):
    """Style names of the spans/paragraphs holding `word`."""
    names = re.findall(rf'<text:span text:style-name="([^"]+)">[^<]*{word}[^<]*</text:span>', xml)
    names += re.findall(rf'<text:p text:style-name="([^"]+)">[^<]*{word}', xml)
    return names

ink = theme.DARK_INK.text   # ODT = white paper = light-note ink

# ── inline code ───────────────────────────────────────────────────────────────
te.setCurrentCharFormat(QTextCharFormat()); te.setPlainText("prije kodic poslije")
c = te.textCursor(); c.setPosition(6); c.setPosition(11, QTextCursor.MoveMode.KeepAnchor)
te.setTextCursor(c); te.toggle_inline_code(); app.processEvents()
p = os.path.join(_SB, "i.odt"); export.to_odt(doc, p)
xml, st = odt_styles(p)
names = spans(xml, "kodic")
bgs = [st[s]["bg"] for s in names if s in st and st[s]["bg"]]
check("(setup) the inline-code span carries a background", bool(bgs))
check(f"inline code background is not black (got {bgs})", bgs and all(b != "#000000" for b in bgs))
check("inline code: text readable on its chip (≥4.5)",
      bgs and all(ratio(ink, b) >= 4.5 for b in bgs))

# ── code block ────────────────────────────────────────────────────────────────
te.setCurrentCharFormat(QTextCharFormat()); te.setPlainText("print(1)")
c = te.textCursor(); c.setPosition(1); te.setTextCursor(c); te.toggle_code_block(); app.processEvents()
p = os.path.join(_SB, "b.odt"); export.to_odt(doc, p)
xml, st = odt_styles(p)
all_bg = [v["bg"] for v in st.values() if v["bg"]]
code_fg = [v["color"] for v in st.values() if v["color"]]
check("(setup) the code block has a box background and a text colour", bool(all_bg) and bool(code_fg))
check(f"code block box is a real fill, not the black marker (got {all_bg})",
      all_bg and all(b != "#000000" for b in all_bg))
check("code block text readable on its box (≥4.5)",
      all_bg and code_fg and all(ratio(f, b) >= 4.5 for f in code_fg for b in all_bg))

check("the live note is untouched (still the transparent marker)",
      doc.begin().blockFormat().background().color().alpha() == 0)

print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
