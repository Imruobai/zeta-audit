"""Keep the English and Chinese READMEs from drifting apart.

A translated README rots silently: someone edits a number in README.md, and the Chinese
version keeps quoting the old one for months. This test extracts the parts that must not
change under translation — measured figures, sha256, file paths, and the *executable* part
of every command — and asserts the two files agree.

Command comments may be translated; the command itself may not be altered.
"""

from __future__ import annotations

import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

ROOT = pathlib.Path(__file__).resolve().parents[1]
EN = ROOT / "README.md"
ZH = ROOT / "README.zh-CN.md"

PATTERNS = {
    "float literals": r"\b\d+\.\d+e-\d+\b",
    "thousands-separated integers": r"\b\d{1,3}(?:,\d{3})+\b",
    "sha256 digests": r"\b[0-9a-f]{64}\b",
    "mpmath symbols": r"mpmath\.\w+",
    "repo paths": r"(?:docs|zeta_audit|data|out)/[\w./-]+\.(?:py|md|txt|json)",
}


def commands(text: str) -> set[str]:
    out = set()
    for line in text.splitlines():
        s = line.strip()
        if not (s.startswith("zeta-audit") or s.startswith("python -m zeta_audit")):
            continue
        out.add(" ".join(s.split("#")[0].split()))
    return out


def main() -> int:
    if not ZH.exists():
        print(f"[SKIP] {ZH.name} not present")
        return 0
    en = EN.read_text(encoding="utf-8")
    zh = ZH.read_text(encoding="utf-8")
    failures: list[str] = []

    for label, pat in PATTERNS.items():
        a, b = set(re.findall(pat, en)), set(re.findall(pat, zh))
        only_en, only_zh = a - b, b - a
        if only_en or only_zh:
            failures.append(f"{label}: missing in zh={sorted(only_en)} extra in zh={sorted(only_zh)}")
        print(f"[{'PASS' if not (only_en or only_zh) else 'FAIL'}] {label}: en={len(a)} zh={len(b)}")

    ce, cz = commands(en), commands(zh)
    if ce != cz:
        failures.append(f"command bodies differ: only_en={sorted(ce - cz)} only_zh={sorted(cz - ce)}")
    print(f"[{'PASS' if ce == cz else 'FAIL'}] command bodies: en={len(ce)} zh={len(cz)}")

    eh = [line for line in en.splitlines() if line.startswith("## ")]
    zh_h = [line for line in zh.splitlines() if line.startswith("## ")]
    if len(eh) != len(zh_h):
        failures.append(f"H2 section count differs: en={len(eh)} zh={len(zh_h)}")
    print(f"[{'PASS' if len(eh) == len(zh_h) else 'FAIL'}] H2 sections: en={len(eh)} zh={len(zh_h)}")

    for name, text in (("en", en), ("zh", zh)):
        n = text.count("```")
        if n % 2:
            failures.append(f"unbalanced code fences in {name}: {n}")
        print(f"[{'PASS' if n % 2 == 0 else 'FAIL'}] code fences {name}: {n}")

    # the language switcher must point both ways
    if "README.zh-CN.md" not in en[:400]:
        failures.append("README.md lacks a link to README.zh-CN.md near the top")
    if "README.md" not in zh[:400]:
        failures.append("README.zh-CN.md lacks a link back to README.md near the top")
    print(f"[{'PASS' if not failures else 'FAIL'}] language switcher present in both")

    if failures:
        print("\nFAILURES:")
        for f in failures:
            print("  -", f)
        return 1
    print("\nREADMEs are consistent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())