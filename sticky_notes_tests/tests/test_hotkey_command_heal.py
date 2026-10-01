"""A registered shortcut whose COMMAND is stale (e.g. a headless test once wrote
a /tmp path into the real dconf, or the app moved) must self-heal: register()
already rewrites the command, and command_is_current() lets the app detect the
mismatch so _sync_hotkey can re-register while preserving the user's binding."""
import sys, os, tempfile, atexit, shutil
_SB = tempfile.mkdtemp(prefix="sn_hkheal_")
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

import sticky_notes.hotkey as hk_mod

class _FakeSettings:
    def __init__(self, store, path=None):
        self._store = store; self._path = path
    def get_strv(self, key): return list(self._store["list"])
    def set_strv(self, key, val):
        self._store["list"] = list(val); self._store["list_writes"].append(list(val))
    def get_string(self, key): return self._store["sub"].get((self._path, key), "")
    def set_string(self, key, val): self._store["sub"][(self._path, key)] = val

def make_fake_gio(store):
    class _Settings:
        @staticmethod
        def new(schema): return _FakeSettings(store)
        @staticmethod
        def new_with_path(schema, path): return _FakeSettings(store, path)
        @staticmethod
        def sync(): pass
    class _Gio:
        Settings = _Settings
    return _Gio

hk = hk_mod.SEARCH
path = "/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom0/"
STALE = "/tmp/sn_gone_1234/.local/share/sticky_notes/start.sh --search"

# Existing entry with the user's binding but a STALE /tmp command.
store = {"list": [path],
         "sub": {(path, "name"): hk.name, (path, "command"): STALE,
                 (path, "binding"): "<Super><Shift>f"},
         "list_writes": []}
hk_mod._gio = lambda: make_fake_gio(store)

check("stale command detected (command_is_current False)",
      hk_mod.command_is_current(hk) is False)

# Re-registering with the same binding heals the command, keeps the accelerator.
hk_mod.register(hk, "<Super><Shift>f")
check("register heals command to command_for", store["sub"][(path, "command")] == hk_mod.command_for(hk))
check("binding preserved through heal", store["sub"][(path, "binding")] == "<Super><Shift>f")
check("command_is_current True after heal", hk_mod.command_is_current(hk) is True)

# A correct command reports current (no needless churn).
check("current command reports True", hk_mod.command_is_current(hk) is True)

print("FAILS:", fails)
sys.exit(1 if fails else 0)
