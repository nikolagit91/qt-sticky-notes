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

import sticky_notes.hotkey as hk_mod

# ── A fake Gio/gsettings backend recording every write ──────────────────────
class _FakeSettings:
    def __init__(self, store, path=None):
        self._store = store; self._path = path
    def get_strv(self, key):
        return list(self._store["list"])
    def set_strv(self, key, val):
        self._store["list"] = list(val)
        self._store["list_writes"].append(list(val))
    def get_string(self, key):
        return self._store["sub"].get((self._path, key), "")
    def set_string(self, key, val):
        self._store["sub"][(self._path, key)] = val

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

hkR = hk_mod.NEW_NOTE
path = "/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/customX/"

# Entry ALREADY exists — the exact case where the old code left the list
# untouched and the daemon ignored the accelerator change.
store = {"list": [path], "sub": {(path, "name"): hkR.name}, "list_writes": []}
hk_mod._gio = lambda: make_fake_gio(store)

ok = hk_mod.register(hkR, "<Super>n")
check("register returns True", ok is True)
check("new binding written to sub-key", store["sub"][(path, "binding")] == "<Super>n")
check("list rewritten to force reload even though entry existed",
      len(store["list_writes"]) >= 2)
check("intermediate write dropped our path (change signal)",
      any(path not in w for w in store["list_writes"]))
check("final list still contains our path", store["list_writes"][-1] == [path])

print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
