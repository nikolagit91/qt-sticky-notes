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

from sticky_notes.search import make_snippet, find_live_matches, note_search_text

# ── make_snippet ─────────────────────────────────────────────────────────────
check("prazan tekst -> prazan snippet", make_snippet("", "x") == "")
long = "rijec " * 50                                   # ~300 znakova
head = make_snippet(long, "")
check("bez upita: pocetak + elipsa", head.endswith("…") and head.startswith("rijec"))
s = make_snippet("A" * 100 + " CILJ " + "B" * 100, "CILJ")
check("pogodak je u snippetu", "CILJ" in s)
check("elipse s obje strane centriranog pogotka", s.startswith("…") and s.endswith("…"))
check("visak whitespacea kolabiran", "\n" not in make_snippet("a\n\n  b", ""))
check("case-insensitive pogodak", "CILJ" in make_snippet("xx CILJ yy", "cilj"))

# ── note_search_text: pohranjena nota (HTML) i naslov ────────────────────────
data = {"content": "<p>Mlijeko i <b>Jaja</b></p>", "title": "Popis"}
t = note_search_text(data, None)
check("HTML renderiran u cisti tekst, lowercase", "mlijeko i jaja" in t)
check("naslov ukljucen u tekst pretrage", "popis" in t)

# ── find_live_matches: naslovni pogoci ispred tjelesnih ──────────────────────
n1 = app.create_new_note(); n1.text_edit.setPlainText("nema veze"); n1.set_title("projekt alfa")
# Pojam MORA biti izvan prvog retka: nota bez vlastitog imena uzima prvi redak
# kao display_title, pa bi "alfa" u njemu ovu notu gurnula u title_hits i
# provjera redoslijeda ispod ne bi mogla pasti.
n2 = app.create_new_note(); n2.text_edit.setPlainText("prvi redak bez pojma\nspomen alfa u tijelu")
n3 = app.create_new_note(); n3.text_edit.setPlainText("nista slicno")
res = find_live_matches("alfa", app.notes)
check("nadjena tocno dva pogotka", len(res) == 2)
check("naslovni pogodak je PRVI", res[0][0] is n1)
check("tjelesni pogodak je DRUGI", res[1][0] is n2)
check("nepogodak NIJE u rezultatima", all(r[0] is not n3 for r in res))
check("prazan upit vraca sve note", len(find_live_matches("", app.notes)) == len(app.notes))

print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
