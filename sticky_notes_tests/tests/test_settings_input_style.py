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

# Offscreen NE moze dokazati kako se strelice CRTAJU (to ide na rucnu GNOME
# checklistu). Ovaj test cuva INVARIJANTU stila: Settings root-sheet mora
# (1) obojati QTimeEdit da prati temu i (2) eksplicitno dimenzionirati
# up/down gumbe i strelice za QSpinBox I QTimeEdit — jer cim se stilizira
# kutija slozenog widgeta, Qt prestaje crtati native pod-kontrole i one nestanu
# ako se ne navedu. (Uzor: reminder dijalog, note_dialogs.py.)
from sticky_notes.theme import apply_theme, settings_dialog_style, UI

for theme in ("light", "dark"):
    apply_theme(theme)
    css = settings_dialog_style("/tmp/check.png")

    # (2) QTimeEdit prati temu — dobije obojenu pozadinu (UI.SURFACE)
    check(f"[{theme}] QTimeEdit je obojan (prati temu)",
          "QTimeEdit" in css and UI.SURFACE in css)

    # (1) strelice spinboxa su eksplicitno dimenzionirane (inace nestanu)
    check(f"[{theme}] QSpinBox up-button dimenzioniran",
          "QSpinBox::up-button" in css)
    check(f"[{theme}] QSpinBox down-button dimenzioniran",
          "QSpinBox::down-button" in css)
    check(f"[{theme}] QSpinBox up-arrow dimenzioniran",
          "QSpinBox::up-arrow" in css)

    # time boxovi dobivaju iste velike gumbe kao reminder
    check(f"[{theme}] QTimeEdit up-button dimenzioniran",
          "QTimeEdit::up-button" in css)
    check(f"[{theme}] QTimeEdit up-arrow dimenzioniran",
          "QTimeEdit::up-arrow" in css)

    # gumbi su POZICIONIRANI (bez subcontrol-position strelica se ne vidi)
    check(f"[{theme}] up-button pozicioniran gore-desno",
          "subcontrol-position: top right" in css)
    check(f"[{theme}] down-button pozicioniran dolje-desno",
          "subcontrol-position: bottom right" in css)

print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
