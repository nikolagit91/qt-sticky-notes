"""Guard: checklist boxes in an ODT look like the note's — plain monochrome ☐ ☑,
not a colour emoji — and are plain text, not hyperlinks.

Before (2026-11-19, user report with an ODT): LibreOffice drew ☑ (U+2611, which
also has an emoji form) from Noto Color Emoji — a blue tile with a white tick —
because the text font (Noto Sans) lacks the glyph; the note (Qt) draws the
monochrome DejaVu Sans glyph. U+FE0E (text presentation) did NOT help in
LibreOffice; an explicit DejaVu Sans did (rendered and checked). Qt 6.4's ODF
writer only writes the OLD font-family property (0x2000), so setFontFamilies
alone wrote "Sans" — both are set. Also: the box went out as a hyperlink to the
app-internal "x-sticky-check", and the space after it as an empty hyperlink.
"""
import sys, os, tempfile, atexit, shutil, zipfile, re, subprocess
_SB = tempfile.mkdtemp(prefix="sn_eocb_")
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
from PyQt6.QtGui import QTextCharFormat, QTextCursor
from sticky_notes.app import StickyNotesApp
from sticky_notes.widgets import CHECK_DONE, CHECK_EMPTY, CHECK_HREF
from sticky_notes import export

app = StickyNotesApp(sys.argv[:1])
for e in list(app.notes.values()):
    e.hide(); e.deleteLater()
app.notes.clear()
n = app.create_new_note(); te = n.text_edit; doc = te.document()
n.show(); app.processEvents()

te.setCurrentCharFormat(QTextCharFormat()); te.setPlainText("gotovo\notvoreno")
for bn in (0, 1):
    c = te.textCursor(); c.setPosition(doc.findBlockByNumber(bn).position()); te.setTextCursor(c)
    te.toggle_checklist()
te.toggle_checkbox(0); app.processEvents()

odt = os.path.join(_SB, "c.odt"); export.to_odt(doc, odt)
xml = zipfile.ZipFile(odt).read("content.xml").decode()
styles = {m.group(1): m.group(2) for m in
          re.finditer(r'<style:style style:name="([^"]+)"[^>]*>(.*?)</style:style>', xml, re.S)}

def box_style(glyph):
    m = re.search(rf'<text:span text:style-name="([^"]+)">{glyph}</text:span>', xml)
    return m and styles.get(m.group(1), "")

for glyph, name in ((CHECK_DONE, "ticked ☑"), (CHECK_EMPTY, "empty ☐")):
    st = box_style(glyph)
    check(f"{name}: present as plain text in the ODT", st is not None)
    check(f"{name}: in a font with a monochrome glyph (DejaVu Sans), not the text font",
          bool(st) and 'fo:font-family="DejaVu Sans"' in st)
check("the box is not a hyperlink to the app-internal x-sticky-check", CHECK_HREF not in xml)
check("no empty hyperlink (the space after the box)", 'xlink:href=""' not in xml)

c = QTextCursor(doc); c.setPosition(0); c.setPosition(1, QTextCursor.MoveMode.KeepAnchor)
check("the live note is untouched (the box is still its clickable anchor)",
      c.charFormat().isAnchor() and c.charFormat().anchorHref() == CHECK_HREF)

# Real check through LibreOffice when it is installed: the PDF it makes from the
# ODT must not need the colour-emoji font.
if shutil.which("soffice") and shutil.which("pdffonts"):
    subprocess.run(["soffice", "--headless", "--convert-to", "pdf", "--outdir", _SB, odt],
                   capture_output=True, timeout=120)
    pdf = os.path.join(_SB, "c.pdf")
    fonts = subprocess.run(["pdffonts", pdf], capture_output=True, text=True).stdout if os.path.exists(pdf) else ""
    check("LibreOffice renders the ODT without the colour-emoji font",
          bool(fonts) and "Emoji" not in fonts)
else:
    print("  (LibreOffice / pdffonts not installed — render check skipped)")

print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
