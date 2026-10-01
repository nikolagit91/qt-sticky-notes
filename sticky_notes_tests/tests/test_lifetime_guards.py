"""Zastite zivotnog ciklusa iz reviewa (prolaz 1): L-1, L-2, L-3.

L-1: copy-button "kopirano" bljesak je padao nad obrisanom notom
     (Copy pa Ctrl+W unutar 1 s -> RuntimeError: QPushButton has been deleted).
L-2: odgodjeni retheme je padao nad zatvorenim Managerom.
L-3: zatvaranje note gasilo je 2 od 6 timera/animacija.
"""
import sys, os, tempfile, atexit, shutil
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
from PyQt6.QtCore import QEventLoop, QTimer
from PyQt6 import sip
from sticky_notes.app import StickyNotesApp

app = StickyNotesApp(sys.argv[:1])
app._snap_to_grid = app._snap_to_notes = app._snap_size = False
for e in list(app.notes.values()):
    e.hide(); e.deleteLater()
app.notes.clear()

def pump(ms):
    """Prava petlja — singleShot se NE okine s processEvents()."""
    loop = QEventLoop(); QTimer.singleShot(ms, loop.quit); loop.exec()

# Hvataj iznimke koje pobjegnu iz Qt slota (inace ih vidi samo excepthook).
caught = []
sys.excepthook = lambda t, v, tb: caught.append(f"{t.__name__}: {v}")

# ── L-1: copy bljesak ne smije opaliti nad obrisanom notom ───────────────────
n = app.create_new_note()
n.text_edit.setPlainText("print('x')")
n.text_edit.selectAll()
n.text_edit.toggle_code_block()
blk = n.text_edit.document().findBlockByNumber(0)
te = n.text_edit
te._copy_region = te.code_region_at(blk)
te._copy_current_region()

check("L-1: bljesak je pokrenut (gumb pokazuje kvacicu)", te._copy_btn.text() == "✓")
check("L-1: timer bljeska je PARENTAN na gumb (uzrok, ne posljedica)",
      te._copy_flash is not None and te._copy_flash.parent() is te._copy_btn)
check("L-1: timer je aktivan dok bljesak traje", te._copy_flash.isActive() is True)

app.move_note_to_trash(n.note_id)     # nota nestaje usred bljeska
pump(1400)                            # prezivi originalni rok od 1000 ms
check("L-1: nema pada nakon brisanja note usred bljeska", not caught)
if caught:
    print("        ", caught[-1])

# Pozitivna polovica: bez brisanja se bljesak UREDNO vrati na ikonu
caught.clear()
n2 = app.create_new_note()
n2.text_edit.setPlainText("print('y')")
n2.text_edit.selectAll(); n2.text_edit.toggle_code_block()
te2 = n2.text_edit
te2._copy_region = te2.code_region_at(te2.document().findBlockByNumber(0))
te2._copy_current_region()
pump(1400)
check("L-1 pozitivna polovica: bljesak se sam vrati kad nota zivi",
      te2._copy_btn.text() == "" and not caught)

# ── L-2: odgodjeni retheme preskace mrtav prozor ─────────────────────────────
caught.clear()
app.show_manager()
mgr = app._manager
app._theme = "light"
app._apply_theme_live("dark")          # naruci odgodjeni retheme
mgr.close()                            # closeEvent -> app._manager = None
pump(300)
check("L-2: nema pada kad se Manager zatvori prije odgodjenog rethemea", not caught)
if caught:
    print("        ", caught[-1])

# Pozitivna polovica: otvoren Manager SE preboji (guard nije ubio funkciju)
caught.clear()
app.show_manager()
mgr2 = app._manager
tab_prije = mgr2.tabs.currentIndex()
mgr2._search.setText("proba")
app._apply_theme_live("light")
pump(300)
check("L-2 pozitivna polovica: otvoren Manager je prezivio retheme",
      not sip.isdeleted(mgr2) and not caught)
check("L-2 pozitivna polovica: aktivni tab i pretraga sacuvani",
      mgr2.tabs.currentIndex() == tab_prije and mgr2._search.text() == "proba")
mgr2.close(); pump(100)

# ── L-3: zatvaranje note gasi SVE timere i animacije ─────────────────────────
n3 = app.create_new_note()
n3._save_timer.start(9000)
n3._snap_timer.start(9000)
n3._hide_debounce.start(9000)
n3._reveal_dwell.start(9000)
n3._toolbar_anim.start()
n3._header_anim.start()
svi = [n3._save_timer, n3._snap_timer, n3._hide_debounce, n3._reveal_dwell]
check("L-3: svi timeri pokrenuti prije zatvaranja", all(t.isActive() for t in svi))

n3.stop_timers()
check("L-3: stop_timers ugasio sva cetiri timera", not any(t.isActive() for t in svi))
from PyQt6.QtCore import QAbstractAnimation
check("L-3: stop_timers zaustavio obje animacije",
      n3._toolbar_anim.state() == QAbstractAnimation.State.Stopped
      and n3._header_anim.state() == QAbstractAnimation.State.Stopped)

n4 = app.create_new_note()
n4._snap_timer.start(9000)
app._close_note_widget(n4)
check("L-3: _close_note_widget gasi i timere koje prije nije",
      n4._snap_timer.isActive() is False)

sys.excepthook = sys.__excepthook__
print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
