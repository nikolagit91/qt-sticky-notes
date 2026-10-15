"""Guard: clicking a link to a local file/folder that no longer exists (renamed,
moved, deleted) tells the user so instead of silently doing nothing.

Before (2026-10-15): the click went straight to xdg-open, which fails with exit
code 4 on a missing path — and its output is sent to /dev/null, so nothing at
all happened. An EXISTING target must still open (incl. names with spaces and
non-ASCII, which the href carries percent-encoded), and web links are never
checked against the disk.

Headless + sandboxed: xdg-open and the message box are stubbed and recorded.
"""
import sys, os, tempfile, atexit, shutil, html
_SB = tempfile.mkdtemp(prefix="sn_lm_")
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
warnings = []
QMessageBox.warning = staticmethod(lambda parent, title, text, *a, **k: warnings.append(text))
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QTextCursor
from PyQt6.QtTest import QTest
import sticky_notes.widgets as W
opened = []
_real_popen = W.subprocess.Popen
def _fake_popen(args, **k):
    """Record xdg-open (the link opener); let every other process the app
    starts run for real."""
    if args and args[0] == "xdg-open":
        opened.append(args[-1])
        return None
    return _real_popen(args, **k)
W.subprocess.Popen = _fake_popen
from sticky_notes.app import StickyNotesApp

app = StickyNotesApp(sys.argv[:1])
for e in list(app.notes.values()):
    e.hide(); e.deleteLater()
app.notes.clear()
note = app.create_new_note(); te = note.text_edit
note.show(); app.processEvents()

def click_link(href):
    """Put one link in the note and click it like the user does."""
    warnings.clear(); opened.clear()
    te.setHtml(f'<p><a href="{html.escape(href, quote=True)}">LINKLINK</a></p>')
    c = QTextCursor(te.document()); c.setPosition(3)
    QTest.mouseClick(te.viewport(), Qt.MouseButton.LeftButton,
                     Qt.KeyboardModifier.NoModifier, te.cursorRect(c).center())
    app.processEvents()

files = os.path.join(_SB, "Slike")
os.makedirs(files)
img = os.path.join(files, "moja slika č.png")
open(img, "wb").write(b"x")
href_img = QUrl.fromLocalFile(img).toString()

# ── existing file (space + č in the name) → opens, no warning ────────────────
click_link(href_img)
check("existing file: opened", opened == [href_img])
check("existing file: no 'missing' warning", warnings == [])

# ── the same file renamed → warning naming the path, nothing opened ───────────
os.rename(img, os.path.join(files, "preimenovana.png"))
click_link(href_img)
check("renamed file: not handed to xdg-open", opened == [])
check("renamed file: user is told", len(warnings) == 1)
check("renamed file: message names the missing path", bool(warnings) and img in warnings[0])

# ── folders: existing opens, missing warns ───────────────────────────────────
href_dir = QUrl.fromLocalFile(files).toString()
click_link(href_dir)
check("existing folder: opened, no warning", opened == [href_dir] and warnings == [])
shutil.rmtree(files)
click_link(href_dir)
check("missing folder: user is told, nothing opened", opened == [] and len(warnings) == 1)

# ── web links are never checked against the disk ─────────────────────────────
click_link("https://example.com/nema/ovoga.png")
check("web link: opened as before, no warning",
      opened == ["https://example.com/nema/ovoga.png"] and warnings == [])

print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
