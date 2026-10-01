"""Link colours are consistent and readable.

Two problems this locks down:
(a) A link pasted as rich text (copied from a browser) kept the SOURCE's colour
    — Qt's HTML insert brought #0000ff, or whatever the site styled it. Pasted
    links are now normalised to the app's own link colours + underline.
(b) The link colours were fixed, so on a dark note they collapsed — violet hit
    1.72:1 on charcoal. Each kind now has a dark-note variant, applied to new
    links and re-applied to existing ones when the note's ink flips.
"""
import sys, os, tempfile, atexit, shutil
_SB = tempfile.mkdtemp(prefix="sn_linkcol_")
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
from PyQt6.QtCore import QMimeData, QUrl
from PyQt6.QtGui import QTextCursor, QColor
QMessageBox.information = staticmethod(lambda *a, **k: None)

fails = []
def check(name, cond):
    print(f"  {'PASS' if cond else 'FAIL'}   {name}")
    if not cond: fails.append(name)

from sticky_notes.theme import link_color, LINK_COLORS, _rel_luminance
from sticky_notes.app import StickyNotesApp

def contrast(a, b):
    x, y = sorted((_rel_luminance(QColor(a)), _rel_luminance(QColor(b))), reverse=True)
    return (x + 0.05) / (y + 0.05)

# ── the palette itself ──────────────────────────────────────────────────────
check("three link kinds", set(LINK_COLORS) == {"web", "folder", "file"})
check("light web colour unchanged", link_color("web", False) == "#1a73e8")
check("unknown kind falls back to web", link_color("bogus", False) == "#1a73e8")
for kind in ("web", "folder", "file"):
    dark_c = link_color(kind, True)
    check(f"{kind}: dark variant differs from light",
          dark_c != link_color(kind, False))
    for bg, label in (("#2b2b30", "charcoal"), ("#000000", "black"), ("#34383f", "graphite")):
        check(f"{kind}: dark variant readable on {label} (>=4.5:1)",
              contrast(dark_c, bg) >= 4.5)

app = StickyNotesApp(sys.argv[:1])
for e in list(app.notes.values()):
    e.hide(); e.deleteLater()
app.notes.clear()
n = app.create_new_note(); te = n.text_edit; n.show(); app.processEvents()

def first_link_fmt():
    d = te.document()
    for i in range(d.characterCount() - 1):
        c = QTextCursor(d); c.setPosition(i)
        c.setPosition(i + 1, QTextCursor.MoveMode.KeepAnchor)
        f = c.charFormat()
        if f.isAnchor() and f.anchorHref().startswith(("http", "file")):
            return f
    return None

def paste(md):
    te.clear(); app.processEvents()
    te.insertFromMimeData(md); app.processEvents()

# ── (a) rich paste is normalised to OUR colour ─────────────────────────────
md = QMimeData(); md.setHtml('<a href="http://example.com">ex</a>'); md.setText("ex")
paste(md)
f = first_link_fmt()
check("html paste uses our web colour, not the source's",
      f is not None and f.foreground().color().name() == link_color("web", False))
check("html paste keeps the link underlined", f is not None and f.fontUnderline())

md = QMimeData()
md.setHtml('<a href="http://x.com" style="color:#ff00ff">ex</a>'); md.setText("ex")
paste(md)
f = first_link_fmt()
check("a site-styled link colour is overridden too",
      f is not None and f.foreground().color().name() == link_color("web", False))

# ── our own paths keep their kind colours ──────────────────────────────────
md = QMimeData(); md.setUrls([QUrl.fromLocalFile("/home")]); paste(md)
check("folder drop uses the folder colour",
      first_link_fmt().foreground().color().name() == link_color("folder", False))
md = QMimeData(); md.setUrls([QUrl.fromLocalFile("/etc/hostname")]); paste(md)
check("file drop uses the file colour",
      first_link_fmt().foreground().color().name() == link_color("file", False))

# ── (b) links follow the note's ink ────────────────────────────────────────
md = QMimeData(); md.setText("http://example.com"); paste(md)
check("light note → light web colour",
      first_link_fmt().foreground().color().name() == link_color("web", False))

n.color = "#2b2b30"; n._apply_color(); app.processEvents()
check("existing link recoloured for a dark note",
      first_link_fmt().foreground().color().name() == link_color("web", True))

n.color = "#fff59d"; n._apply_color(); app.processEvents()
check("switching back to a light note restores the light colour",
      first_link_fmt().foreground().color().name() == link_color("web", False))

# a link inserted while the note is dark starts dark
n.color = "#2b2b30"; n._apply_color(); app.processEvents()
md = QMimeData(); md.setText("http://example.com"); paste(md)
check("link inserted on a dark note uses the dark colour",
      first_link_fmt().foreground().color().name() == link_color("web", True))

# ── auto-contrast OFF keeps the light colours (consistent with the grip) ───
app._auto_contrast = False
n._apply_color(); app.processEvents()
check("auto-contrast off → links stay on the light colours",
      first_link_fmt().foreground().color().name() == link_color("web", False))
app._auto_contrast = True

# ── the BLOCK char format must not keep a link colour ───────────────────────
# Qt draws a list item's bullet with the BLOCK char format, so a link colour
# stranded there paints the bullet blue/violet. Old notes carry exactly that.
from PyQt6.QtGui import QTextCharFormat, QTextListFormat
te.clear(); app.processEvents()
n.color = "#fff59d"; n._apply_color(); app.processEvents()
n._fmt_bullet(QTextListFormat.Style.ListDisc); app.processEvents()
md = QMimeData(); md.setText("http://example.com")
te.insertFromMimeData(md); app.processEvents()

blk = te.document().findBlockByNumber(0)
c = QTextCursor(blk)
bcf = QTextCharFormat(blk.charFormat())
bcf.setForeground(QColor("#0000ff"))       # strand a link colour, as old notes do
c.setBlockCharFormat(bcf)
check("precondition: block char format polluted with a link colour",
      te.document().findBlockByNumber(0).charFormat().foreground().color().name() == "#0000ff")

te.recolor_links(); app.processEvents()
got = te.document().findBlockByNumber(0).charFormat().foreground().color().name()
check("block char format no longer carries a link colour (bullet not blue)",
      got != "#0000ff")
check("block char format falls back to the note's ink", got == te.checkbox_text_color)

# a block char format the user legitimately coloured must be left alone
te.clear(); app.processEvents()
n._fmt_bullet(QTextListFormat.Style.ListDisc); app.processEvents()
te.textCursor().insertText("plain"); app.processEvents()
blk = te.document().findBlockByNumber(0)
c = QTextCursor(blk)
bcf = QTextCharFormat(blk.charFormat()); bcf.setForeground(QColor("#e53935"))
c.setBlockCharFormat(bcf)
te.recolor_links(); app.processEvents()
check("a user-chosen block colour is not touched",
      te.document().findBlockByNumber(0).charFormat().foreground().color().name() == "#e53935")

print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
