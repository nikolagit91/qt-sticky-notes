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
from sticky_notes.widgets import CHECK_EMPTY, CHECK_DONE

note = app.create_new_note()
te = note.text_edit

def build_tree():
    """roditelj / dva uvucena djeteta / separator (obican red) / samostalna stavka."""
    te.setPlainText("roditelj\ndijete1\ndijete2\nobicno\nsolo")
    doc = te.document()
    # sve osim "obicno" pretvori u checklist stavke
    for bn in (0, 1, 2, 4):
        b = doc.findBlockByNumber(bn)
        c = te.textCursor(); c.setPosition(b.position()); te.setTextCursor(c)
        te.toggle_checklist()
    # uvuci djecu (Tab razina 1)
    for bn in (1, 2):
        te._change_indent(doc.findBlockByNumber(bn), +1)
    return doc

def glyph(bn):
    return te.document().findBlockByNumber(bn).text()[:1]

doc = build_tree()
check("postavljeno: 4 checklist linije", all(glyph(b) in (CHECK_EMPTY, CHECK_DONE) for b in (0,1,2,4)))
check("postavljeno: separator NIJE checklist", glyph(3) not in (CHECK_EMPTY, CHECK_DONE))
check("_descendants(0) == [1, 2]", te._descendants(0) == [1, 2])
check("_parent_of(1) == 0", te._parent_of(1) == 0)
check("separator prekida lanac: _parent_of(4) je None", te._parent_of(4) is None)

# ── kaskada prema dolje: check roditelja oznaci cijelo podstablo ─────────────
te.toggle_checkbox(doc.findBlockByNumber(0).position())
check("roditelj oznacen", glyph(0) == CHECK_DONE)
check("dijete1 kaskadno oznaceno", glyph(1) == CHECK_DONE)
check("dijete2 kaskadno oznaceno", glyph(2) == CHECK_DONE)
check("solo stavka NETAKNUTA (iza separatora)", glyph(4) == CHECK_EMPTY)

# ── kaskada prema gore: uncheck djeteta skida roditelja ──────────────────────
te.toggle_checkbox(doc.findBlockByNumber(1).position())
check("dijete1 odznaceno", glyph(1) == CHECK_EMPTY)
check("roditelj automatski odznacen", glyph(0) == CHECK_EMPTY)
check("dijete2 ostalo oznaceno", glyph(2) == CHECK_DONE)

# ── roditelj se sam oznaci kad su SVA djeca gotova ───────────────────────────
# SVJEZE stablo namjerno: da se ovdje krene od roditelja koji je EMPTY. Na
# nastavku prethodnog scenarija roditelj je vec bio DONE, pa je tvrdnja prolazila
# i s ISKLJUCENOM kaskadom prema gore — mjerila je zateceno stanje, ne prijelaz.
doc = build_tree()
check("svjeze stablo: roditelj krece kao EMPTY", glyph(0) == CHECK_EMPTY)
te.toggle_checkbox(doc.findBlockByNumber(1).position())
check("jedno dijete gotovo NIJE dosta za roditelja", glyph(0) == CHECK_EMPTY)
te.toggle_checkbox(doc.findBlockByNumber(2).position())
check("oba djeteta gotova -> roditelj automatski oznacen", glyph(0) == CHECK_DONE)

# ── progress broji SAMO listove ──────────────────────────────────────────────
done, total = te.checklist_progress()
check("total = 3 (2 djeteta + solo; roditelj se NE broji)", total == 3)
check("done = 2 (djeca gotova, solo nije)", done == 2)
te.toggle_checkbox(doc.findBlockByNumber(4).position())
check("nakon solo checka done = 3", te.checklist_progress() == (3, 3))

# ── precrtavanje gotove stavke ───────────────────────────────────────────────
b1 = doc.findBlockByNumber(1)
probe = QTextCursor(doc); probe.setPosition(b1.position() + 3)
probe.setPosition(b1.position() + 4, QTextCursor.MoveMode.KeepAnchor)
check("tekst gotove stavke je precrtan", probe.charFormat().fontStrikeOut() is True)
b4 = doc.findBlockByNumber(3)   # "obicno" — separator
probe = QTextCursor(doc); probe.setPosition(b4.position() + 1)
probe.setPosition(b4.position() + 2, QTextCursor.MoveMode.KeepAnchor)
check("separator NIJE precrtan (pozitivna polovica)", probe.charFormat().fontStrikeOut() is False)

print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
