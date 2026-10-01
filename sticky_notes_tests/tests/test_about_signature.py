"""The About dialog carries the author signature and a Ko-fi donate button.

Guards the 1.0 launch content: a signature label and a working donate button
wired to config.DONATE_URL. Runs offscreen — verifies structure, not the
browser call."""
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

from PyQt6.QtWidgets import QLabel, QDialog, QPushButton
from sticky_notes import config
from sticky_notes.app import StickyNotesApp
app = StickyNotesApp(sys.argv[:1])

app.show_about()
dlgs = [w for w in app._open_windows if isinstance(w, QDialog)
        and w.windowTitle() == "About Sticky Notes"]
check("about dialog opened once", len(dlgs) == 1)
dlg = dlgs[0]

all_labels = dlg.findChildren(QLabel)
labels = [l.text() for l in all_labels]
check("shows the author signature", any("Nikola Javorina" in t for t in labels))
check("title has plain 'Sticky Notes' text", any(t == "Sticky Notes" for t in labels))
check("no tofu emoji left in the title", not any("📝" in t for t in labels))
check("title carries a rendered icon pixmap",
      any(l.pixmap() is not None and not l.pixmap().isNull() for l in all_labels))

buttons = dlg.findChildren(QPushButton)
btexts = [b.text() for b in buttons]
donate = [b for b in buttons if "coffee" in b.text().lower() or "kav" in b.text().lower()]
check("has a donate button", len(donate) == 1)
check("still has an OK button", any(t == "OK" for t in btexts))

check("DONATE_URL is a non-empty ko-fi url",
      isinstance(config.DONATE_URL, str) and config.DONATE_URL.startswith("https://ko-fi.com/"))

# clicking the donate button must not raise (browser call is a no-op offscreen)
try:
    donate[0].click()
    clicked_ok = True
except Exception as e:
    print("   click raised:", e); clicked_ok = False
check("clicking donate does not raise", clicked_ok)

app.show_about()  # second call focuses existing, no duplicate
dlgs2 = [w for w in app._open_windows if isinstance(w, QDialog)
         and w.windowTitle() == "About Sticky Notes"]
check("no duplicate about dialog on re-open", len(dlgs2) == 1)

print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
