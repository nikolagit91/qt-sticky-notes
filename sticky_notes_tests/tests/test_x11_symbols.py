"""Guard against the §66 class of bug: a wrong libX11 symbol name (XGetProperty
instead of XGetWindowProperty) made _libx11() raise AttributeError, which every
x11 function swallowed (except -> return False/-1). Detach then silently no-oped
on the REAL machine while looking fine in headless tests (where no DISPLAY makes
everything no-op anyway). This test loads libX11 and declares every signature —
if any symbol name is wrong, _libx11() raises here and the test FAILS.

Note: this does NOT need a display. _libx11() only loads the library + declares
signatures; it does not open a display. So it runs the same headless as on X11.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

fails = []
def check(name, cond):
    print(f"  {'PASS' if cond else 'FAIL'}   {name}")
    if not cond: fails.append(name)

import sticky_notes.x11 as x11

# _libx11() must load libX11 and resolve/declare every symbol we use.
err = None
try:
    lib = x11._libx11()
except Exception as e:
    err = e
check(f"_libx11() loads without error (got: {err!r})", err is None)

# Every symbol we declared must actually be resolvable in libX11.
for sym in ("XOpenDisplay", "XInternAtom", "XChangeProperty", "XGetWMHints",
            "XAllocWMHints", "XSetWMHints", "XFree", "XFlush",
            "XDefaultRootWindow", "XSendEvent"):
    ok = True
    try:
        getattr(x11._libx11(), sym)
    except Exception:
        ok = False
    check(f"libX11 exports {sym}", ok)

# The public helpers must never raise, even off-X11 (they no-op / return sentinels).
for call, label in [
    (lambda: x11.detach_window_group(123), "detach_window_group"),
    (lambda: x11.set_skip_taskbar(123),    "set_skip_taskbar"),
    (lambda: x11.set_above(123, True),     "set_above"),
]:
    ok = True
    try:
        call()
    except Exception:
        ok = False
    check(f"{label}() never raises off-X11", ok)

print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
