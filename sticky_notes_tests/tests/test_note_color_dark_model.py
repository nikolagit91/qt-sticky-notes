"""NoteData gains a color_dark slot: defaults to '', round-trips through
to_dict/from_dict, and old records without the key parse to ''."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sticky_notes.note_model import NoteData

fails = []
def check(name, cond):
    print(f"  {'PASS' if cond else 'FAIL'}   {name}")
    if not cond: fails.append(name)

# default is empty
check("color_dark defaults to ''", NoteData().color_dark == "")
# round-trips through to_dict/from_dict
d = NoteData(color="#fff59d", color_dark="#2b2b30").to_dict()
check("to_dict carries color_dark", d.get("color_dark") == "#2b2b30")
check("from_dict reads color_dark", NoteData.from_dict(d).color_dark == "#2b2b30")
# migration: an old record without color_dark parses to ''
old = {"id": "x", "color": "#E3F2FD"}
check("legacy record → color_dark ''", NoteData.from_dict(old).color_dark == "")

print("FAILS:", fails)
sys.exit(1 if fails else 0)
