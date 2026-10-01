"""Single-instance enforcement and cross-process commands over D-Bus.

The first launched instance owns a well-known name on the session bus and
exports a small object with slots (NewNote, Raise). Any later invocation — for
example the GNOME global shortcut running ``python3 -m sticky_notes --new-note``
— sees that the name is already taken, forwards its intent to the running
instance, and exits.

This is the Wayland-correct shape for a global hotkey on GNOME: the key is bound
at the compositor level (a GNOME custom shortcut), and the launched command
talks to the already-running app over D-Bus. Grabbing the key *inside* the
process does not work reliably under Wayland, which only delivers key events to
the focused window.

D-Bus also gives us robust single-instance for free: the bus releases a name
automatically when its owner disconnects, so a crashed instance never leaves a
stale lock behind (unlike a lock file).
"""

from PyQt6.QtCore import QObject, pyqtSlot, QTimer

from .config import DBUS_SERVICE, DBUS_PATH

# QtDBus ships with the pip PyQt6 wheel but, like QtSvg, can be a separate
# package on minimal apt installs (python3-pyqt6.qtdbus). Degrade gracefully:
# without it there is no single-instance guard and the global hotkey can't reach
# a running app, but the application itself still runs normally.
try:
    from PyQt6.QtDBus import QDBusConnection, QDBusMessage, QDBus
    _HAS_DBUS = True
except ImportError:
    _HAS_DBUS = False


class _IpcService(QObject):
    """Object exported on the session bus by the primary instance.

    Slots are dispatched on the main thread by Qt's event loop, so they may
    touch widgets directly. We still hop through ``QTimer.singleShot(0, ...)``
    so the real work runs *after* the D-Bus reply is sent, keeping the call
    site (a blocking call from the secondary process) snappy.
    """

    def __init__(self, app_ref):
        super().__init__()
        self._app = app_ref

    @pyqtSlot()
    def NewNote(self):
        QTimer.singleShot(0, self._app.create_new_note)

    @pyqtSlot()
    def NewNoteFromClipboard(self):
        QTimer.singleShot(0, self._app.create_note_from_clipboard)

    @pyqtSlot()
    def Raise(self):
        QTimer.singleShot(0, self._app.show_all_notes)

    @pyqtSlot()
    def Search(self):
        QTimer.singleShot(0, self._app.show_search)


class SingleInstance:
    """Acquire the bus name (primary) or detect an existing owner (secondary).

    Usage::

        si = SingleInstance(app)
        if si.is_primary:
            ...                   # keep `si` alive — it owns the exported object
        else:
            si.send_new_note()    # or si.send_raise(); then quit

    When D-Bus is unavailable (no QtDBus, or no session bus), ``is_primary`` is
    True so the app simply runs as a lone instance.
    """

    def __init__(self, app_ref):
        self._app = app_ref
        self._service = None
        self.is_primary = True       # lone instance if D-Bus is unavailable
        self._connected = False

        if not _HAS_DBUS:
            return
        try:
            bus = QDBusConnection.sessionBus()
            if not bus.isConnected():
                return               # no session bus (headless / unusual env)
            self._connected = True
            # registerService() returns False if another connection already owns
            # the name — that is how we detect we are the secondary instance.
            if bus.registerService(DBUS_SERVICE):
                self._service = _IpcService(app_ref)
                bus.registerObject(
                    DBUS_PATH, self._service,
                    QDBusConnection.RegisterOption.ExportAllSlots,
                )
                self.is_primary = True
            else:
                self.is_primary = False
        except Exception as e:
            # Any D-Bus hiccup → behave as a lone instance rather than crash.
            print(f"[ipc] D-Bus unavailable, running standalone: {e}")
            self.is_primary = True
            self._connected = False

    # ── secondary → primary ───────────────────────────────────────────────────
    def _send(self, method: str) -> bool:
        if not self._connected:
            return False
        try:
            bus = QDBusConnection.sessionBus()
            # Empty interface name lets the remote object dispatcher match the
            # method across all interfaces exported via ExportAllSlots. A
            # blocking call (short timeout) guarantees the message is delivered
            # before this secondary process exits.
            msg = QDBusMessage.createMethodCall(DBUS_SERVICE, DBUS_PATH, "", method)
            reply = bus.call(msg, QDBus.CallMode.Block, 5000)
            if reply.type() == QDBusMessage.MessageType.ErrorMessage:
                print(f"[ipc] remote call '{method}' failed: {reply.errorMessage()}")
                return False
            return True
        except Exception as e:
            print(f"[ipc] could not reach running instance: {e}")
            return False

    def send_new_note(self) -> bool:
        return self._send("NewNote")

    def send_new_note_from_clipboard(self) -> bool:
        return self._send("NewNoteFromClipboard")

    def send_raise(self) -> bool:
        return self._send("Raise")

    def send_search(self) -> bool:
        return self._send("Search")
