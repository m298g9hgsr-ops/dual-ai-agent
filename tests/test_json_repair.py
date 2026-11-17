"""Check the JSON repair path in src/utils/llm.py (offline, no network)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.utils.llm import json_from_llm

cases = [
    ('{"a": 1,}', {"a": 1}),
    ("{'target': 'http://x', 'steps': [{'tool': 'nmap'}]}", None),
    ('```json\n{"a": [1, 2]}\n```', {"a": [1, 2]}),
    ('Here is the result: {"a": 1} hope it helps', {"a": 1}),
    ('{"summary": "he said \'hi\'", "n": 3}', {"summary": "he said 'hi'", "n": 3}),
]
fail = 0
for text, expect in cases:
    try:
        got = json_from_llm(text)
        ok = expect is None or got == expect
        print(("PASS" if ok else "FAIL"), "->", got)
        fail += 0 if ok else 1
    except Exception as exc:
        print("FAIL", str(exc)[:90])
        fail += 1
print("all green" if not fail else f"{fail} failed")
sys.exit(1 if fail else 0)
