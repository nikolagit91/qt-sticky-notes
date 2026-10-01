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
from sticky_notes.widgets import CHECK_EMPTY, CHECK_DONE, CHECK_HREF

note = app.create_new_note()
te = note.text_edit
doc = te.document()

def texts():
    return [doc.findBlockByNumber(i).text() for i in range(doc.blockCount())]

def make_check_lines(lines, indents):
    te.setPlainText("\n".join(lines))
    for bn in range(len(lines)):
        b = doc.findBlockByNumber(bn)
        c = te.textCursor(); c.setPosition(b.position()); te.setTextCursor(c)
        te.toggle_checklist()
    for bn, ind in enumerate(indents):
        if ind:
            for _ in range(ind):
                te._change_indent(doc.findBlockByNumber(bn), +1)

# ── move_block: susjedna zamjena cuva tekst i indent ─────────────────────────
make_check_lines(["A", "B", "C"], [0, 0, 0])
te.move_block(0, 1)
check("move_block: A i B zamijenjeni", [t[2:] for t in texts()] == ["B", "A", "C"])
check("move_block: sve i dalje checklist linije",
      all(t[:1] in (CHECK_EMPTY, CHECK_DONE) for t in texts()))

# ── move_range: podstablo se seli kao cjelina ────────────────────────────────
# Iza odredista MORA postojati jos redaka. S odredistem na samom kraju liste
# clamp u _insert_blocks_at_gap svede i ispravan i pokvaren izracun dst_after na
# istu vrijednost, pa tvrdnja ne moze pasti (izmjereno: sabotaza dst_after=dst
# prolazila je zeleno). "Y" je tu da cilj padne u SREDINU.
make_check_lines(["P", "d1", "d2", "X", "Y"], [0, 1, 1, 0, 0])
te.move_range(0, 2, 4)          # podstablo P+d1+d2 izmedju X i Y
check("move_range: podstablo izmedju X i Y",
      [t[2:] for t in texts()] == ["X", "P", "d1", "d2", "Y"])
check("move_range: indenti djece prezivjeli",
      QTextCursor(doc.findBlockByNumber(2)).blockFormat().indent() == 1
      and QTextCursor(doc.findBlockByNumber(3)).blockFormat().indent() == 1)
check("move_range: roditelj i susjedi ostali bez uvlake",
      QTextCursor(doc.findBlockByNumber(1)).blockFormat().indent() == 0
      and QTextCursor(doc.findBlockByNumber(4)).blockFormat().indent() == 0)

# ── move_range u vlastiti raspon je no-op ────────────────────────────────────
# Pozitivna polovica prvo: dokaz da ISTI poziv s odredistem IZVAN raspona
# stvarno pomice — inace "nista se nije promijenilo" prolazi i na funkciji koja
# ne radi nista.
before = texts()
te.move_range(1, 3, 2)
check("drop unutar vlastitog raspona = no-op", texts() == before)
te.move_range(1, 3, 5)          # isti raspon, odrediste IZVAN njega
check("isti raspon s odredistem izvan sebe SE pomice (pozitivna polovica)",
      texts() != before and [t[2:] for t in texts()] == ["X", "Y", "P", "d1", "d2"])

# ── normalize_checkboxes: round-trip kroz toHtml/setHtml ─────────────────────
make_check_lines(["kupiti"], [0])
html = te.toHtml()
te.setHtml(html)
te.normalize_checkboxes()
b0 = doc.findBlockByNumber(0)
probe = QTextCursor(doc); probe.setPosition(b0.position())
probe.setPosition(b0.position() + 1, QTextCursor.MoveMode.KeepAnchor)
f = probe.charFormat()
check("round-trip: kucica je i dalje anchor s CHECK_HREF", f.anchorHref() == CHECK_HREF)
check("round-trip: kucica NIJE podvucena (a anchor JE — pozitivna polovica)",
      f.isAnchor() and not f.fontUnderline())
check("round-trip: glyph ostao", b0.text()[:1] == CHECK_EMPTY)

print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
