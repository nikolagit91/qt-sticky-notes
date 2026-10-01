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

from PyQt6.QtGui import QTextListFormat, QTextCursor
from sticky_notes import export
from sticky_notes.widgets import CHECK_EMPTY, CHECK_DONE

note = app.create_new_note()
te = note.text_edit

# ── to_plain_text: bullet markeri + ugniježđena uvlaka ────────────────────────
te.setPlainText("prvi\ndrugi")
c = te.textCursor(); c.movePosition(QTextCursor.MoveOperation.Start)
c.movePosition(QTextCursor.MoveOperation.End, QTextCursor.MoveMode.KeepAnchor)
fmt = QTextListFormat(); fmt.setStyle(QTextListFormat.Style.ListDisc)
c.createList(fmt)
out = export.to_plain_text(te.document())
check("disc marker na svakoj stavci", out.splitlines() == ["● prvi", "● drugi"])
check("izlaz zavrsava newlineom", out.endswith("\n"))

te.setPlainText("stavka")
c = te.textCursor(); c.movePosition(QTextCursor.MoveOperation.Start)
fmt = QTextListFormat(); fmt.setStyle(QTextListFormat.Style.ListDecimal); fmt.setIndent(2)
c.createList(fmt)
out = export.to_plain_text(te.document())
check("decimal marker + uvlaka za indent 2", out.splitlines()[0] == "    1. stavka")

# ── to_plain_text: checkbox linije postaju ASCII ──────────────────────────────
te.setPlainText(f"{CHECK_EMPTY} kupiti\n{CHECK_DONE} gotovo")
out = export.to_plain_text(te.document())
check("prazna kucica -> [ ]", out.splitlines()[0] == "[ ] kupiti")
check("kvacica -> [x]",       out.splitlines()[1] == "[x] gotovo")

# ── suggest_filename ─────────────────────────────────────────────────────────
check("obican naslov prolazi", export.suggest_filename("Popis za ducan") == "Popis za ducan")
check("nedopusteni znakovi se brisu", export.suggest_filename('a/b:c*d?"e') == "abcde")
# TOCNO 40, ne "<= 40": s <= bi i rezanje na [:39] proslo zeleno (izmjereno).
check("cap na 40 znakova", len(export.suggest_filename("x" * 100)) == 40)
check("prazno -> 'note'", export.suggest_filename("   \n  ") == "note")
check("prva NEPRAZNA linija je izvor", export.suggest_filename("\n\nNaslov\ntijelo") == "Naslov")

# ── to_odt / to_pdf: smoke (fajl nastane, ispravan format) ────────────────────
te.setPlainText("izvoz proba")
odt = os.path.join(_SB, "out.odt")
export.to_odt(te.document(), odt)
check("odt postoji i nije prazan", os.path.getsize(odt) > 0)
check("odt je ZIP kontejner (ODF)", open(odt, "rb").read(2) == b"PK")

pdf = os.path.join(_SB, "out.pdf")
export.to_pdf(te.document(), pdf, page_color="#fff59d")
check("pdf postoji i nije prazan", os.path.getsize(pdf) > 0)
check("pdf header", open(pdf, "rb").read(5) == b"%PDF-")

pdf2 = os.path.join(_SB, "out2.pdf")
export.to_pdf(te.document(), pdf2)          # i bez boje stranice
check("pdf bez page_color radi", open(pdf2, "rb").read(5) == b"%PDF-")

print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
