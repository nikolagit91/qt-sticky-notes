import sys, os, json, time, tempfile, atexit, shutil
_SB = tempfile.mkdtemp(prefix="sn_test_")
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
QMessageBox.warning     = staticmethod(lambda *a, **k: None)
QMessageBox.exec        = lambda self, *a, **k: QMessageBox.StandardButton.Ok

from sticky_notes.app import StickyNotesApp
app = StickyNotesApp(sys.argv[:1])
app._snap_to_grid = app._snap_to_notes = app._snap_size = False
for e in list(app.notes.values()):
    e.hide(); e.deleteLater()
app.notes.clear()

from PyQt6.QtGui import QTextCursor

# ── tekst s URL-om: sadrzaj unesen, URL postao pravi link ────────────────────
app.clipboard().setText("vidi https://example.com danas")
n = app.create_note_from_clipboard()
check("nota stvorena", n is not None and n.note_id in app.notes)
plain = n.text_edit.toPlainText()
check("tekst prenesen", "vidi" in plain and "danas" in plain)

def hrefs(te):
    out = set()
    doc = te.document()
    b = doc.begin()
    while b.isValid():
        for i in range(b.length() - 1):
            c = QTextCursor(doc); c.setPosition(b.position() + i)
            c.setPosition(b.position() + i + 1, QTextCursor.MoveMode.KeepAnchor)
            f = c.charFormat()
            if f.isAnchor() and f.anchorHref():
                out.add(f.anchorHref())
        b = b.next()
    return out

def format_at_plain_index(te, plain_idx):
    """Map a plain-text character index to its QTextCharFormat, walking blocks
    the same way toPlainText() joins them (a newline between blocks) — so the
    index lines up with plain.find()/plain.index() results even across
    multiple paragraphs."""
    doc = te.document()
    b = doc.begin()
    idx = plain_idx
    while b.isValid():
        blen = b.length() - 1  # exclude the block's own trailing separator
        if idx < blen:
            c = QTextCursor(doc); c.setPosition(b.position() + idx)
            c.setPosition(b.position() + idx + 1, QTextCursor.MoveMode.KeepAnchor)
            return c.charFormat()
        idx -= blen + 1  # + 1 for the newline toPlainText() inserts between blocks
        b = b.next()
    return None

check("URL je klikabilan link", "https://example.com" in hrefs(n.text_edit))
check("tocno jedan link u dokumentu", len(hrefs(n.text_edit)) == 1)
# Negativna tvrdnja s pravom pozitivnom polovicom iznad ("URL je klikabilan
# link"): ovdje se stvarno gleda charFormat() znaka IZVAN URL-a, ne samo broj
# razlicitih adresa (koji bi bio 1 i da je citav redak postao jedan link).
before_fmt = format_at_plain_index(n.text_edit, plain.index("vidi"))
after_fmt  = format_at_plain_index(n.text_edit, plain.rindex("danas"))
check("tekst PRIJE linka nema anchor svojstvo", before_fmt is not None and not before_fmt.isAnchor())
check("tekst NAKON linka nema anchor svojstvo", after_fmt is not None and not after_fmt.isAnchor())

# ── prazan clipboard: nota se svejedno stvori, prazna ────────────────────────
app.clipboard().clear()
n2 = app.create_note_from_clipboard()
check("prazan clipboard: nota stvorena", n2 is not None)
check("prazan clipboard: sadrzaj prazan", n2.text_edit.toPlainText().strip() == "")

print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
