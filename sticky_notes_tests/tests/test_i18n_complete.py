"""Guard: every language in LANGUAGES (except en, the fallback) must translate
every tr("literal") in the package AND every cheat-sheet section title/note.

Parses source (AST) so multi-line implicit-concatenated strings resolve fully.
Strict for ALL languages: a new UI string ships only once every language has it.

NOTE: this checks key PRESENCE, not that a translation differs from its English
source — a value left byte-identical to the source string still passes. Genuine
cognates and file-format tokens (e.g. "OK", "PDF (*.pdf)") legitimately match;
translation quality beyond presence is verified by review, not by this guard."""
import ast, glob, os, sys

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _ROOT)
from sticky_notes.i18n import _TRANSLATIONS, LANGUAGES
from sticky_notes import shortcuts

# Collect every tr("literal") in the package.
tr_literals = set()
for f in sorted(glob.glob(os.path.join(_ROOT, "sticky_notes", "*.py"))):
    tree = ast.parse(open(f, encoding="utf-8").read(), f)
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == "tr" and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str) and node.args[0].value):
            tr_literals.add(node.args[0].value)

# Cheat-sheet translates data (titles/notes) — invisible to the tr() scan above.
cheat = {t for t, _ in shortcuts.sections()} | set(shortcuts.SECTION_NOTES.values())
required = tr_literals | cheat

codes = [c for c, _ in LANGUAGES if c != "en"]
fail_total = 0
for code in codes:
    d = _TRANSLATIONS.get(code, {})
    missing = sorted(s for s in required if s not in d)
    if missing:
        fail_total += len(missing)
        print(f"  FAIL   [{code}] {len(missing)} untranslated string(s):")
        for s in missing[:8]:
            print(f"           {s[:66]!r}")
        if len(missing) > 8:
            print(f"           … +{len(missing) - 8} more")
    else:
        print(f"  PASS   [{code}] all {len(required)} strings translated")

if fail_total:
    print(f"\n{fail_total} FAIL")
    sys.exit(1)
print("\nALL PASS")
sys.exit(0)
