"""Jedna neserijalizabilna nota ne smije kostati SVE ostale njihove izmjene.

Review prolaz 4, D-1. _do_save je gradio listu jednim comprehensionom:
    data = [n.get_data() for n in self.notes.values()]
Iznimka u bilo kojoj noti rusi cijelo spremanje -> na disku ostaje staro stanje
SVIH nota, a korisnik ne vidi nista osim retka na stderr.

Strana za ucitavanje (_load_notes) vec tolerira los zapis i preskace ga; strana
za spremanje sada radi isto, uz to da za preskocenu notu zadrzi njenu ZADNJU
ISPRAVNU kopiju s diska, pa se ne gubi ni ona.
"""
import sys, os, json, tempfile, atexit, shutil
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
from sticky_notes.app import StickyNotesApp
from sticky_notes.config import DATA_FILE

app = StickyNotesApp(sys.argv[:1])
app._snap_to_grid = app._snap_to_notes = app._snap_size = False
for e in list(app.notes.values()):
    e.hide(); e.deleteLater()
app.notes.clear()

def on_disk():
    try:
        return json.load(open(DATA_FILE, encoding="utf-8"))
    except Exception:
        return []

A = app.create_new_note(); A.text_edit.setPlainText("nota A original")
B = app.create_new_note(); B.text_edit.setPlainText("nota B original")
app._do_save()
check("pripremа: obje note na disku", len(on_disk()) == 2)

# B postane neserijalizabilna (isto sto se dogodi ako joj C++ objekt nestane)
orig = type(B).get_data
def bad(self):
    if self is B:
        raise ValueError("simulirana greska u get_data")
    return orig(self)
type(B).get_data = bad

A.text_edit.setPlainText("nota A IZMIJENJENA")
app._do_save()
type(B).get_data = orig

disk = on_disk()
tekst = json.dumps(disk, ensure_ascii=False)
check("izmjena ISPRAVNE note je spremljena unatoc losoj susjedi",
      "IZMIJENJENA" in tekst)
check("losa nota NIJE ispala iz fajla (zadrzana zadnja ispravna kopija)",
      any(d.get("id") == B.note_id for d in disk))
check("losa nota zadrzala svoj zadnji ispravan sadrzaj",
      "nota B original" in tekst)
check("broj zapisa nepromijenjen", len(disk) == 2)

# Nakon oporavka sve se sprema normalno
B.text_edit.setPlainText("nota B popravljena")
app._do_save()
tekst2 = json.dumps(on_disk(), ensure_ascii=False)
check("nakon oporavka se obje note normalno spremaju",
      "IZMIJENJENA" in tekst2 and "popravljena" in tekst2)

# Nema zaostalog .tmp ni u jednom slucaju
check("nema zaostalog .tmp fajla", not os.path.exists(DATA_FILE + ".tmp"))

print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
