"""A link keeps the two cues that say "this is a link": its colour and its
underline. Other formatting (bold/italic/size) stays allowed.

Before, selecting a link and hitting Underline or a text colour restyled it —
you could end up with a link that looks like plain text but still opens on
click. Colour and underline now skip link characters; the rest of the selection
is formatted normally."""
import sys, os, tempfile, atexit, shutil
_SB = tempfile.mkdtemp(prefix="sn_linklock_")
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
from PyQt6.QtCore import QMimeData
from PyQt6.QtGui import QTextCursor, QFont
QMessageBox.information = staticmethod(lambda *a, **k: None)

fails = []
def check(name, cond):
    print(f"  {'PASS' if cond else 'FAIL'}   {name}")
    if not cond: fails.append(name)

from sticky_notes.app import StickyNotesApp
from sticky_notes.widgets import _LINK_COLOR_WEB

app = StickyNotesApp(sys.argv[:1])
for e in list(app.notes.values()):
    e.hide(); e.deleteLater()
app.notes.clear()
n = app.create_new_note(); te = n.text_edit
n.resize(420, 260); n.show(); app.processEvents()

def fresh_link(prefix="", suffix=""):
    te.clear(); app.processEvents()
    if prefix:
        te.textCursor().insertText(prefix)
    md = QMimeData(); md.setText("http://example.com")
    te.insertFromMimeData(md); app.processEvents()
    if suffix:
        te.textCursor().insertText(suffix)
    app.processEvents()

def select_all_text():
    c = te.textCursor()
    c.movePosition(QTextCursor.MoveOperation.Start)
    c.movePosition(QTextCursor.MoveOperation.End, QTextCursor.MoveMode.KeepAnchor)
    te.setTextCursor(c)

def fmt_at(pos):
    c = QTextCursor(te.document()); c.setPosition(pos)
    c.setPosition(pos + 1, QTextCursor.MoveMode.KeepAnchor)
    return c.charFormat()

# ── underline is locked on a link ───────────────────────────────────────────
fresh_link()
select_all_text()
n._fmt_underline()            # would toggle underline OFF on the link
app.processEvents()
f = fmt_at(1)
check("link keeps its underline", f.fontUnderline() is True)
check("link is still a link", f.isAnchor() is True)

# ── colour is locked on a link ──────────────────────────────────────────────
fresh_link()
select_all_text()
n._apply_text_color("#e53935")
app.processEvents()
f = fmt_at(1)
check("link keeps its own colour", f.foreground().color().name() == _LINK_COLOR_WEB)

# ── bold IS allowed on a link (other formatting stays free) ────────────────
fresh_link()
select_all_text()
n._fmt_bold()
app.processEvents()
check("bold still applies to a link", fmt_at(1).fontWeight() >= QFont.Weight.DemiBold)

# ── plain text in a MIXED selection is still formatted ─────────────────────
fresh_link(prefix="before ", suffix=" after")
select_all_text()
n._apply_text_color("#e53935")
app.processEvents()
check("plain text before the link takes the new colour",
      fmt_at(1).foreground().color().name() == "#e53935")
link_pos = te.document().begin().text().find("http")
check("the link inside the selection keeps its colour",
      fmt_at(link_pos + 1).foreground().color().name() == _LINK_COLOR_WEB)
tail = te.document().begin().text().rfind("after")
check("plain text after the link takes the new colour",
      fmt_at(tail).foreground().color().name() == "#e53935")

# ── with no selection, the typing format still changes (unchanged behaviour) ─
te.clear(); app.processEvents()
n._apply_text_color("#2e7d32")
check("no selection → typing colour still changes",
      te.currentCharFormat().foreground().color().name() == "#2e7d32")

print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
