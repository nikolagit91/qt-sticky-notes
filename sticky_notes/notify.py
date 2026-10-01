"""Desktop notifications via the freedesktop D-Bus interface, with actions.

Notifications go through ``org.freedesktop.Notifications`` — the same service
behind ``notify-send``, which GNOME implements. Unlike a plain tray balloon this
lets us attach action buttons (e.g. "Snooze") and listen for ``ActionInvoked``
to route the click back to the right note.

Everything degrades gracefully: if QtDBus is missing, there is no session bus,
or no notification daemon is running, :meth:`Notifier.send` returns ``None`` and
the caller falls back to a tray balloon (or simply skips the popup). The app
itself never depends on notifications being available.
"""

from PyQt6.QtCore import QObject, pyqtSlot, QMetaType

# QtDBus ships with the pip PyQt6 wheel but can be a separate package on minimal
# apt installs (python3-pyqt6.qtdbus) — degrade gracefully, same as ipc.py.
try:
    from PyQt6.QtDBus import (
        QDBusConnection, QDBusInterface, QDBusMessage, QDBusArgument,
    )
    _HAS_DBUS = True
except ImportError:
    _HAS_DBUS = False

_NOTIFY_SERVICE = "org.freedesktop.Notifications"
_NOTIFY_PATH    = "/org/freedesktop/Notifications"

# Notify's signature is `susssasa{sv}i`. PyQt6 marshals a plain Python int as
# 'i' and a list as 'av', which the daemon rejects ("no such method"). So we
# build replaces_id (uint32) and the actions array (as) by hand with these
# metatype ids via QDBusArgument.
_UINT = QMetaType.Type.UInt.value
_QSTR = QMetaType.Type.QString.value


class Notifier(QObject):
    """Sends notifications and routes their action buttons back to callbacks.

    `send()` returns a notification id (int) on success or ``None`` if the popup
    couldn't be delivered. When the user clicks an action button, the daemon
    emits ``ActionInvoked(id, key)`` and we invoke the callback registered for
    that id with the action key.
    """

    def __init__(self):
        super().__init__()
        self._iface = None
        self._bus = None
        self._handlers: dict[int, callable] = {}   # notif_id → on_action(key)

        if not _HAS_DBUS:
            return
        try:
            bus = QDBusConnection.sessionBus()
            if not bus.isConnected():
                return
            iface = QDBusInterface(_NOTIFY_SERVICE, _NOTIFY_PATH,
                                   _NOTIFY_SERVICE, bus)
            if not iface.isValid():
                return            # no notification daemon → caller uses fallback
            self._iface = iface
            self._bus = bus
        except Exception as e:
            print(f"[notify] D-Bus notifications unavailable: {e}")
            self._iface = None
            return

        # Route the daemon's action/close signals back to us. This is best-effort
        # and kept separate so that, even if the signal hookup fails, sending
        # notifications still works (only the action buttons would be inert).
        try:
            bus.connect(_NOTIFY_SERVICE, _NOTIFY_PATH, _NOTIFY_SERVICE,
                        "ActionInvoked", self._on_action)
            bus.connect(_NOTIFY_SERVICE, _NOTIFY_PATH, _NOTIFY_SERVICE,
                        "NotificationClosed", self._on_closed)
        except Exception as e:
            print(f"[notify] action routing unavailable (notifications still work): {e}")

    def is_available(self) -> bool:
        return self._iface is not None

    def send(self, summary: str, body: str, actions=None, on_action=None,
             icon: str = "sticky-notes", timeout: int = -1):
        """Show a notification. ``actions`` is a list of (key, label) pairs and
        ``on_action`` a callback receiving the chosen key. Returns the
        notification id, or ``None`` if it couldn't be sent.
        """
        if self._iface is None or self._bus is None:
            return None
        try:
            # replaces_id = 0 as uint32
            rid = QDBusArgument()
            rid.add(0, _UINT)
            # actions as an array of strings (key, label, key, label, …)
            act = QDBusArgument()
            act.beginArray(_QSTR)
            for key, label in (actions or []):
                act.add(str(key), _QSTR)
                act.add(str(label), _QSTR)
            act.endArray()

            msg = QDBusMessage.createMethodCall(
                _NOTIFY_SERVICE, _NOTIFY_PATH, _NOTIFY_SERVICE, "Notify")
            msg.setArguments([
                "Sticky Notes", rid, str(icon), str(summary), str(body),
                act, {}, int(timeout),
            ])
            reply = self._bus.call(msg)
            if reply.type() == QDBusMessage.MessageType.ErrorMessage:
                print(f"[notify] Notify failed: {reply.errorMessage()}")
                return None
            args = reply.arguments()
            if not args or args[0] is None:
                return None
            notif_id = int(args[0])
            if on_action and actions:
                self._handlers[notif_id] = on_action
            return notif_id
        except Exception as e:
            print(f"[notify] send failed: {e}")
            return None

    # ── daemon signals ─────────────────────────────────────────────────────────
    # Received as the raw QDBusMessage and unpacked by hand. This sidesteps
    # D-Bus argument-type matching (the daemon sends uint32 ids), which is what a
    # typed @pyqtSlot('uint', str) trips over; the message form just works.
    @pyqtSlot(QDBusMessage)
    def _on_action(self, message):
        args = message.arguments()
        if len(args) < 2:
            return
        cb = self._handlers.pop(int(args[0]), None)
        if cb:
            cb(str(args[1]))

    @pyqtSlot(QDBusMessage)
    def _on_closed(self, message):
        # Drop any handler for a dismissed/expired notification so it can't fire
        # later and to avoid leaking entries.
        args = message.arguments()
        if args:
            self._handlers.pop(int(args[0]), None)
