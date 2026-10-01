"""Native X11 helpers via ctypes + the system libX11 — no extra dependencies.

Why this exists: Qt puts every top-level window of the application into one
shared X11 window group (they all carry the same WM_CLIENT_LEADER and WM_HINTS
group leader). GNOME/Mutter treats that group as a single stacking unit, so the
moment one note gets "always on top" (_NET_WM_STATE_ABOVE), Mutter lifts the
*whole group* above other applications — every other note then behaves as if it
were pinned too.

`detach_window_group()` gives a window its own group (itself as leader), so
Mutter stops stacking the notes together. Everything here is best-effort: on a
pure-Wayland session, with libX11 missing, or on any error, the functions simply
return False and the caller carries on (the app still works, just without the
fix). This keeps the rest of the codebase free of X11 knowledge.
"""

import ctypes
import ctypes.util

# Predefined X atom for the WINDOW property type (X11/Xatom.h: XA_WINDOW = 33).
_XA_WINDOW = 33
# XUtil.h: WindowGroupHint = (1L << 6). Marks WM_HINTS.window_group as valid.
_WINDOW_GROUP_HINT = 1 << 6
_PROP_MODE_REPLACE = 0
# EWMH _NET_WM_STATE client-message action (root-window message to a mapped win).
_NET_WM_STATE_REMOVE = 0
_NET_WM_STATE_ADD = 1
_CLIENT_MESSAGE = 33                       # Xlib event type
_SUBSTRUCTURE_NOTIFY = 1 << 19
_SUBSTRUCTURE_REDIRECT = 1 << 20


class _XClientMessageEvent(ctypes.Structure):
    """Mirror of Xlib's XClientMessageEvent (data as the long[5] union member)."""
    _fields_ = [
        ("type",         ctypes.c_int),
        ("serial",       ctypes.c_ulong),
        ("send_event",   ctypes.c_int),
        ("display",      ctypes.c_void_p),
        ("window",       ctypes.c_ulong),
        ("message_type", ctypes.c_ulong),
        ("format",       ctypes.c_int),
        ("data",         ctypes.c_long * 5),
    ]


class _XEvent(ctypes.Union):
    """Padded to the full XEvent size so XSendEvent reads a valid event."""
    _fields_ = [
        ("type",    ctypes.c_int),
        ("xclient", _XClientMessageEvent),
        ("pad",     ctypes.c_long * 24),
    ]


class _XWMHints(ctypes.Structure):
    """Mirror of Xlib's XWMHints struct (field order/types must match exactly)."""
    _fields_ = [
        ("flags",         ctypes.c_long),
        ("input",         ctypes.c_int),
        ("initial_state", ctypes.c_int),
        ("icon_pixmap",   ctypes.c_ulong),
        ("icon_window",   ctypes.c_ulong),
        ("icon_x",        ctypes.c_int),
        ("icon_y",        ctypes.c_int),
        ("icon_mask",     ctypes.c_ulong),
        ("window_group",  ctypes.c_ulong),
    ]


_lib = None       # cached CDLL handle for libX11
_display = None   # cached Display* (opened once, reused)


def _libx11():
    """Load libX11 once and declare the signatures we use."""
    global _lib
    if _lib is None:
        name = ctypes.util.find_library("X11")
        if not name:
            raise OSError("libX11 not found")
        lib = ctypes.CDLL(name)
        lib.XOpenDisplay.restype  = ctypes.c_void_p
        lib.XOpenDisplay.argtypes = [ctypes.c_char_p]
        lib.XInternAtom.restype   = ctypes.c_ulong
        lib.XInternAtom.argtypes  = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int]
        lib.XChangeProperty.argtypes = [
            ctypes.c_void_p, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_ulong,
            ctypes.c_int, ctypes.c_int, ctypes.c_void_p, ctypes.c_int,
        ]
        lib.XGetWMHints.restype   = ctypes.POINTER(_XWMHints)
        lib.XGetWMHints.argtypes  = [ctypes.c_void_p, ctypes.c_ulong]
        lib.XAllocWMHints.restype = ctypes.POINTER(_XWMHints)
        lib.XSetWMHints.argtypes  = [ctypes.c_void_p, ctypes.c_ulong,
                                     ctypes.POINTER(_XWMHints)]
        lib.XFree.argtypes        = [ctypes.c_void_p]
        lib.XFlush.argtypes       = [ctypes.c_void_p]
        lib.XDefaultRootWindow.restype  = ctypes.c_ulong
        lib.XDefaultRootWindow.argtypes = [ctypes.c_void_p]
        lib.XSendEvent.restype    = ctypes.c_int
        lib.XSendEvent.argtypes   = [ctypes.c_void_p, ctypes.c_ulong, ctypes.c_int,
                                     ctypes.c_long, ctypes.c_void_p]
        _lib = lib
    return _lib


def _disp():
    """Open the X display once (uses $DISPLAY) and reuse it."""
    global _display
    if _display is None:
        dpy = _libx11().XOpenDisplay(None)
        if not dpy:
            raise OSError("cannot open X display")
        _display = dpy
    return _display


def detach_window_group(win_id: int) -> bool:
    """Give `win_id` its own X11 window group so Mutter stops stacking it with the
    app's other notes. Sets BOTH WM_CLIENT_LEADER and WM_HINTS.window_group to the
    window itself (§11 of the handoff — the version the user confirmed working on
    the Tool windows). Best-effort: no-op on Wayland / without libX11 / on error.

    NOTE: setting the leader to SELF is not the same as deleting it. Deleting
    WM_CLIENT_LEADER let Mutter fall back to grouping the windows by application
    (they kept stacking together); setting it to self makes each note its own
    leader = its own group. So we set, we don't delete.
    """
    if not win_id:
        return False
    try:
        lib = _libx11()
        dpy = _disp()
        win = ctypes.c_ulong(win_id)

        # WM_CLIENT_LEADER = self  (format 32 => array of C long, even on 64-bit)
        leader_atom = lib.XInternAtom(dpy, b"WM_CLIENT_LEADER", False)
        value = ctypes.c_ulong(win_id)
        lib.XChangeProperty(dpy, win, leader_atom, _XA_WINDOW, 32,
                            _PROP_MODE_REPLACE, ctypes.byref(value), 1)

        # WM_HINTS.window_group = self
        hints_ptr = lib.XGetWMHints(dpy, win)
        if not hints_ptr:
            hints_ptr = lib.XAllocWMHints()
        if hints_ptr:
            hints = hints_ptr.contents
            hints.flags |= _WINDOW_GROUP_HINT
            hints.window_group = win_id
            lib.XSetWMHints(dpy, win, hints_ptr)
            lib.XFree(hints_ptr)

        lib.XFlush(dpy)
        return True
    except Exception:
        return False


def set_skip_taskbar(win_id: int) -> bool:
    """Write _NET_WM_STATE = [SKIP_TASKBAR, SKIP_PAGER] on the window. Notes are
    normal Qt.Window top-levels (so Mutter stops grouping the app's utility windows
    together — the pin-leak); this restores the taskbar / dash / Alt-Tab hiding that
    Qt.Tool used to give for free. Honoured when written BEFORE the window is mapped
    (Mutter reads _NET_WM_STATE at map); post-map calls are best-effort.

    ⚠️ This writes the property with PropModeReplace, i.e. it overwrites the
    ENTIRE _NET_WM_STATE array with [SKIP_TASKBAR, SKIP_PAGER]. Any other state
    already on the window — notably _NET_WM_STATE_ABOVE, which is how pin is
    implemented (set_above) — is dropped. Callers must re-apply the pin after
    calling this. Best-effort; no-op off X11."""
    if not win_id:
        return False
    try:
        lib = _libx11()
        dpy = _disp()
        state = lib.XInternAtom(dpy, b"_NET_WM_STATE", False)
        atoms = [lib.XInternAtom(dpy, b"_NET_WM_STATE_SKIP_TASKBAR", False),
                 lib.XInternAtom(dpy, b"_NET_WM_STATE_SKIP_PAGER", False)]
        arr = (ctypes.c_ulong * len(atoms))(*atoms)
        _XA_ATOM = 4
        lib.XChangeProperty(dpy, ctypes.c_ulong(win_id), state, _XA_ATOM, 32,
                            _PROP_MODE_REPLACE, ctypes.cast(arr, ctypes.c_void_p),
                            len(atoms))
        lib.XFlush(dpy)
        return True
    except Exception:
        return False


def set_above(win_id: int, enable: bool) -> bool:
    """Add/remove _NET_WM_STATE_ABOVE (always-on-top) on a MAPPED window via the
    EWMH client-message to the root window — the spec-correct way to change a
    live window's state. Used for PIN: unlike Qt's WindowStaysOnTopHint (which
    recreates the native window → flicker + drops skip-taskbar → dock dot), this
    leaves the window untouched, so a pinned note stays hidden from the dock.
    Best-effort; no-op off X11 / on error."""
    if not win_id:
        return False
    try:
        lib = _libx11()
        dpy = _disp()
        state = lib.XInternAtom(dpy, b"_NET_WM_STATE", False)
        above = lib.XInternAtom(dpy, b"_NET_WM_STATE_ABOVE", False)
        root  = lib.XDefaultRootWindow(dpy)
        ev = _XEvent()
        ev.xclient.type = _CLIENT_MESSAGE
        ev.xclient.send_event = 1
        ev.xclient.display = dpy
        ev.xclient.window = win_id
        ev.xclient.message_type = state
        ev.xclient.format = 32
        ev.xclient.data[0] = _NET_WM_STATE_ADD if enable else _NET_WM_STATE_REMOVE
        ev.xclient.data[1] = above
        ev.xclient.data[2] = 0
        ev.xclient.data[3] = 1          # source indication: normal application
        ev.xclient.data[4] = 0
        mask = _SUBSTRUCTURE_REDIRECT | _SUBSTRUCTURE_NOTIFY
        lib.XSendEvent(dpy, root, False, mask, ctypes.byref(ev))
        lib.XFlush(dpy)
        return True
    except Exception:
        return False

