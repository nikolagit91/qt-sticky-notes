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

from datetime import datetime
from sticky_notes.theme_schedule import coerce_hhmm, scheduled_theme, scheduled_theme_now

M = lambda h, m: h * 60 + m   # minute od ponoći

# ── scheduled_theme: wrap preko ponoći (20:00–07:00) ─────────────────────────
S, E = M(20, 0), M(7, 0)
check("21:00 je dark",                scheduled_theme(M(21, 0), S, E) == "dark")
check("02:30 je dark (iza ponoci)",   scheduled_theme(M(2, 30), S, E) == "dark")
check("12:00 je light",               scheduled_theme(M(12, 0), S, E) == "light")
check("granica 20:00 ukljucena",      scheduled_theme(M(20, 0), S, E) == "dark")
check("19:59 jos light",              scheduled_theme(M(19, 59), S, E) == "light")
check("granica 07:00 iskljucena",     scheduled_theme(M(7, 0),  S, E) == "light")
check("06:59 jos dark",               scheduled_theme(M(6, 59), S, E) == "dark")

# ── scheduled_theme: isti dan (09:00–17:00) ──────────────────────────────────
S2, E2 = M(9, 0), M(17, 0)
check("12:00 dark u dnevnom periodu",  scheduled_theme(M(12, 0), S2, E2) == "dark")
check("08:59 light prije pocetka",     scheduled_theme(M(8, 59), S2, E2) == "light")
check("17:00 light na kraju (isklj.)", scheduled_theme(M(17, 0), S2, E2) == "light")

# ── prazan period ────────────────────────────────────────────────────────────
check("start == end -> uvijek light (u tom trenutku)",
      scheduled_theme(M(12, 0), M(12, 0), M(12, 0)) == "light")
check("start == end -> light i u 00:00", scheduled_theme(0, M(12, 0), M(12, 0)) == "light")

# ── coerce_hhmm ──────────────────────────────────────────────────────────────
check("valjan string prolazi",        coerce_hhmm("20:00", "07:00") == "20:00")
check("normalizira '8:5' -> '08:05'", coerce_hhmm("8:5", "07:00") == "08:05")
check("kriv sat -> fallback",         coerce_hhmm("25:00", "07:00") == "07:00")
check("krivi minut -> fallback",      coerce_hhmm("12:99", "07:00") == "07:00")
check("broj umjesto stringa -> fallback", coerce_hhmm(80, "07:00") == "07:00")
check("None -> fallback",             coerce_hhmm(None, "07:00") == "07:00")
check("smece -> fallback",            coerce_hhmm("abc", "07:00") == "07:00")
check("prazno -> fallback",           coerce_hhmm("", "07:00") == "07:00")

# ── scheduled_theme_now: injektiran sat + otporan na kriva vremena ───────────
noon  = datetime(2026, 7, 20, 12, 0)
night = datetime(2026, 7, 20, 23, 0)
check("now=12:00 uz 20-07 -> light", scheduled_theme_now("20:00", "07:00", now=noon)  == "light")
check("now=23:00 uz 20-07 -> dark",  scheduled_theme_now("20:00", "07:00", now=night) == "dark")
check("kriva vremena padnu na default 20-07 (23h -> dark)",
      scheduled_theme_now("smece", None, now=night) == "dark")
check("kriva vremena padnu na default 20-07 (12h -> light)",
      scheduled_theme_now("smece", None, now=noon) == "light")

print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
