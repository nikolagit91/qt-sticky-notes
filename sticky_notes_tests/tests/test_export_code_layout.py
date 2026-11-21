"""Guard: code in PDF/ODT exports sits like in the note.

Before (2026-11-21, user report + measured on PDF/ODT renders at 96 DPI):
1. A code block's box was shifted right by the block's 9px L/R margin and its
   text sat flush against the box edge (PDF box x=84, ODT x=85, normal text
   x=76; glyph 1–2px inside). On screen the editor PAINTS the box 9px wider
   than the text column (aligned with normal text, text inset 9px); a cloned
   document has no paintEvent, and Qt's block background starts AFTER the margin.
2. ODT: code wasn't monospace — Qt 6.4's ODF writer writes only the OLD
   font-family property (0x2000); fonts set with setFontFamilies came out "Sans".
3. ODT: text typed after switching inline code OFF carries an explicit EMPTY
   background (NoBrush); the ODF writer wrote it as BLACK.
4. ODT (user report 2026-11-21, LibreOffice on screen): a code block of several
   lines showed a LIGHTER LINE between them — each line is its own paragraph,
   LibreOffice fills each separately and anti-aliases the shared edge (measured
   row 46→64 grey). Joining them with an equal border+padding did NOT cure it
   (the user's own note still showed it, 46→57) — only ONE paragraph does. And a
   soft-wrapped tail of a long code line sat flush against the box edge (the
   inset was only a first-line indent).
5. ODT: Qt's ODF writer writes a line break (U+2028, Shift+Enter) as a stray
   <text:tab/> + <text:line-break/>.
"""
import sys, os, tempfile, atexit, shutil, zipfile, re, subprocess
_SB = tempfile.mkdtemp(prefix="sn_ecl_")
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

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from PyQt6.QtGui import QTextCharFormat, QTextCursor, QColor, QImage
from sticky_notes.app import StickyNotesApp
from sticky_notes.widgets import CODE_BLOCK_MARGIN, CODE_FONT_FAMILY
from sticky_notes import export

app = StickyNotesApp(sys.argv[:1])
for e in list(app.notes.values()):
    e.hide(); e.deleteLater()
app.notes.clear()
n = app.create_new_note(); te = n.text_edit; doc = te.document()
n.show(); app.processEvents()
PAGE = "#fff59d"

# line 0 plain, line 1 code block, line 2 inline code from the line start, then
# plain text typed after switching inline OFF, line 3 a code block toggled back off
te.setCurrentCharFormat(QTextCharFormat())
te.setPlainText("Obican red teksta\nkod_u_bloku()\n\nbio kod pa nije")
c = te.textCursor(); c.setPosition(doc.findBlockByNumber(1).position()); te.setTextCursor(c)
te.toggle_code_block()
c = te.textCursor(); c.setPosition(doc.findBlockByNumber(3).position()); te.setTextCursor(c)
te.toggle_code_block(); te.toggle_code_block()
c = te.textCursor(); c.setPosition(doc.findBlockByNumber(2).position()); te.setTextCursor(c)
te.toggle_inline_code(); te.insertPlainText("inline_kod"); te.toggle_inline_code()
te.insertPlainText(" i dalje"); app.processEvents()
# line 4–6 a three-line code block (Enter inside the block), line 8 one LONG code
# line that soft-wraps
LONG = "dugi_red = " + "abc + " * 30
c = te.textCursor(); c.movePosition(QTextCursor.MoveOperation.End); te.setTextCursor(c)
te.insertPlainText("\nprvi_red()\ndrugi_red()\ntreci_red()\n\n" + LONG)
c = te.textCursor(); c.setPosition(doc.findBlockByNumber(4).position())
c.setPosition(doc.findBlockByNumber(6).position() + 3, QTextCursor.MoveMode.KeepAnchor)
te.setTextCursor(c); te.toggle_code_block()
c = te.textCursor(); c.setPosition(doc.findBlockByNumber(8).position()); te.setTextCursor(c)
te.toggle_code_block(); app.processEvents()
# line 9: plain text with a Shift+Enter line break (U+2028)
c = te.textCursor(); c.movePosition(QTextCursor.MoveOperation.End); te.setTextCursor(c)
te.insertPlainText("\nshift\u2028enter")
if doc.lastBlock().blockFormat().background().style() != Qt.BrushStyle.NoBrush:
    te.toggle_code_block()                    # the new line inherited the code block
app.processEvents()

USER_NOTE = """<html><body style=" font-family:'Ubuntu Sans'; font-size:13pt;">
<p style="-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px;"><br /></p>
<p style="-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px;"><br /></p>
<p style=" margin-top:11px; margin-bottom:0px; margin-left:9px; margin-right:9px; background-color:transparent;"><span style=" font-family:'Monospace'; color:#ececec;">testiramo traa</span></p>
<p style=" margin-top:0px; margin-bottom:0px; margin-left:9px; margin-right:9px; background-color:transparent;"><span style=" font-family:'Monospace'; color:#ececec;">da vidim hoce li raditi</span></p>
<p style=" margin-top:0px; margin-bottom:0px; margin-left:9px; margin-right:9px; background-color:transparent;"><span style=" font-family:'Monospace'; color:#ececec;">baldadsa</span></p>
<p style="-qt-paragraph-type:empty; margin-top:0px; margin-bottom:11px; margin-left:9px; margin-right:9px; font-family:'Monospace'; color:#ececec; background-color:transparent;"><br /></p>
<p style="-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px;"><br /></p>
<p style=" margin-top:0px; margin-bottom:0px;"><span style=" font-family:'Monospace'; background-color:transparent;">inline kod</span> </p>
</body></html>"""

def bands(img, bg, x0, x1, y1):
    """Rows of ink: [(y0, y1, first x, last x)] differing from bg."""
    b = QColor(bg); out = []; inb = False
    far = lambda c: abs(c.red()-b.red()) + abs(c.green()-b.green()) + abs(c.blue()-b.blue()) > 60
    for y in range(y1):
        xs = [x for x in range(x0, x1) if far(img.pixelColor(x, y))]
        if xs and not inb: s = y; inb = True; a, z = min(xs), max(xs)
        elif xs: a, z = min(a, min(xs)), max(z, max(xs))
        elif inb: out.append((s, y, a, z)); inb = False
    return out

def code_geometry(img, band):
    """(box left, first light glyph column) inside the code band."""
    y0, y1, a, _ = band
    mid = range(y0 + (y1 - y0) // 4, y1 - (y1 - y0) // 4)
    box = None
    for x in range(a, a + 60):
        col = [img.pixelColor(x, y).lightness() for y in mid]
        if box is None and sum(v < 110 for v in col) >= len(col) * 0.9:
            box = x; continue
        if box is not None and any(v > 150 for v in col):
            return box, x
    return box, None

def check_layout(img, bg, label):
    img = img.convertToFormat(QImage.Format.Format_RGB32)
    bs = bands(img, bg, 30, img.width() - 30, img.height() // 4)
    if len(bs) < 3:
        check(f"{label}: found the text rows ({len(bs)})", False); return
    text_left, code = bs[0][2], bs[1]
    box, glyph = code_geometry(img, code)
    check(f"{label}: code box aligned with normal text (box {box}, text {text_left})",
          box is not None and abs(box - text_left) <= 3)
    check(f"{label}: code text inset inside the box (glyph {glyph} − box {box} ≥ {CODE_BLOCK_MARGIN - 2})",
          box is not None and glyph is not None and glyph - box >= CODE_BLOCK_MARGIN - 2)

# ── PDF ───────────────────────────────────────────────────────────────────────
if shutil.which("pdftoppm"):
    pdf = os.path.join(_SB, "k.pdf"); export.to_pdf(doc, pdf, PAGE)
    subprocess.run(["pdftoppm", "-r", "96", "-png", "-singlefile", pdf, os.path.join(_SB, "kpdf")], check=True)
    check_layout(QImage(os.path.join(_SB, "kpdf.png")), PAGE, "PDF")
else:
    print("  (pdftoppm not installed — PDF layout check skipped)")

# ── ODT ───────────────────────────────────────────────────────────────────────
odt = os.path.join(_SB, "k.odt"); export.to_odt(doc, odt)
xml = zipfile.ZipFile(odt).read("content.xml").decode()
styles = {m.group(1): m.group(2) for m in
          re.finditer(r'<style:style style:name="([^"]+)"[^>]*>(.*?)</style:style>', xml, re.S)}
def span_style(text):
    m = re.search(rf'<text:span text:style-name="([^"]+)">{re.escape(text)}</text:span>', xml)
    return styles.get(m.group(1), "") if m else ""
def para_style(text):
    m = re.search(rf'<text:p text:style-name="([^"]+)">(?:(?!</text:p>).)*{re.escape(text)}', xml, re.S)
    return styles.get(m.group(1), "") if m else ""

mono = f'fo:font-family="{CODE_FONT_FAMILY}"'
check("ODT: code-block text is in the code font", mono in span_style("kod_u_bloku()"))
check("ODT: inline code is in the code font", mono in span_style("inline_kod"))
check("ODT: no black background anywhere (nothing here is black)",
      'background-color="#000000"' not in xml)
cp = para_style("kod_u_bloku()")
check("ODT: code paragraph has its box fill", "fo:background-color" in cp)
check("ODT: code box not shifted by a left margin",
      not re.search(r'fo:margin-left="(?!0)[0-9.]+', cp))
check("ODT: code text inset by padding (every line, not just the first)",
      re.search(r'fo:padding-left="[1-9][0-9.]*pt"', cp) is not None and "fo:text-indent" not in cp)
check("ODT: code box has vertical padding like the note",
      re.search(r'fo:padding-top="[1-9][0-9.]*pt"', cp) is not None)
check("ODT: a block toggled back off has no fill", "background" not in para_style("bio kod pa nije"))
check("ODT: a multi-line code block is ONE paragraph (lines joined by line breaks)",
      re.search(r'<text:p [^>]*>(?:(?!</text:p>).)*prvi_red\(\)(?:(?!</text:p>).)*'
                r'drugi_red\(\)(?:(?!</text:p>).)*treci_red\(\)', xml, re.S) is not None)
check("ODT: no stray tab written with a line break", "<text:tab/>" not in xml)
check("ODT: a Shift+Enter line break is kept", re.search(r"shift\s*<text:line-break/>\s*enter", xml) is not None)

if shutil.which("soffice") and shutil.which("pdftoppm"):
    out = os.path.join(_SB, "odtpdf")
    subprocess.run(["soffice", "--headless", "--convert-to", "pdf", "--outdir", out, odt],
                   capture_output=True, timeout=120)
    p = os.path.join(out, "k.pdf")
    if os.path.exists(p):
        subprocess.run(["pdftoppm", "-r", "96", "-png", "-singlefile", p, os.path.join(_SB, "kodt")], check=True)
        check_layout(QImage(os.path.join(_SB, "kodt.png")), "#ffffff", "ODT via LibreOffice")
        if shutil.which("pdffonts"):
            fonts = subprocess.run(["pdffonts", p], capture_output=True, text=True).stdout
            check("ODT via LibreOffice: a monospace font is used", "Mono" in fonts)
    # LibreOffice's SCREEN drawing path (the PDF filter doesn't show the seam)
    def screen_png(path):
        subprocess.run(["soffice", "--headless", "--convert-to", "png", "--outdir", out, path],
                       capture_output=True, timeout=120)
        png = os.path.splitext(os.path.join(out, os.path.basename(path)))[0] + ".png"
        return QImage(png).convertToFormat(QImage.Format.Format_RGB32) if os.path.exists(png) else None
    def code_boxes(img):
        return [b for b in bands(img, "#ffffff", 30, img.width() - 30, img.height())
                if b[3] - b[2] > img.width() * 0.6]
    def check_even_box(img, box, label):
        y0, y1, a, z = box
        x = a + (z - a) * 3 // 4                  # right of the text: plain fill
        col = [img.pixelColor(x, y).lightness() for y in range(y0 + 2, y1 - 2)]
        check(f"ODT on screen ({label}): one even fill, no lighter line between "
              f"the lines (lightness {min(col)}..{max(col)})", max(col) - min(col) <= 4)
    # the user's own note (2026-11-21) — the seam survived the border+padding join here
    n2 = app.create_new_note(); n2.text_edit.setHtml(USER_NOTE); app.processEvents()
    odt2 = os.path.join(_SB, "user.odt"); export.to_odt(n2.text_edit.document(), odt2)
    img2 = screen_png(odt2)
    if img2 is not None:
        b2 = code_boxes(img2)
        check(f"ODT on screen (user's note): one code box ({len(b2)})", len(b2) == 1)
        if b2: check_even_box(img2, b2[0], "user's note")
    img = screen_png(odt)
    if img is not None:
        boxes = code_boxes(img)
        check(f"ODT on screen: found the three code boxes ({len(boxes)})", len(boxes) == 3)
        if len(boxes) == 3:
            check_even_box(img, boxes[1], "three-line block")
            y0, y1, a, z = boxes[2]               # the soft-wrapped long line
            glyph = min((x for y in range(y0 + 2, y1 - 2) for x in range(a, z)   # skip the AA edge rows
                         if img.pixelColor(x, y).lightness() > 150), default=None)
            check(f"ODT on screen: every line of a wrapped code line sits inset "
                  f"(leftmost glyph {glyph} − box {a} ≥ {CODE_BLOCK_MARGIN - 2})",
                  glyph is not None and glyph - a >= CODE_BLOCK_MARGIN - 2)
else:
    print("  (LibreOffice not installed — ODT render check skipped)")

# ── the live note is untouched ────────────────────────────────────────────────
b1 = doc.findBlockByNumber(1)
check("live note: code block keeps its margins (box is painted on screen)",
      b1.blockFormat().leftMargin() == CODE_BLOCK_MARGIN)

print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
