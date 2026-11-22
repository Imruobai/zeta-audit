"""Classify fenced blocks by content, not by language tag.

The parity test needs three categories because the Chinese README legitimately translates
some blocks:

  code      - shell/python: only comments may differ
  tree      - the directory listing: paths and indentation must survive, prose may be translated
  metrics   - the three-line measured-results summary: numbers must survive, labels may be translated
  transcript- real program output: must be byte-identical (it is evidence)

Classify by inspecting content, so a future edit that changes a block's role is caught
rather than silently reclassified.
"""

from __future__ import annotations

import pathlib
import re
import sys

# Windows consoles are not UTF-8 by default; this file prints non-ASCII text.
import _console  # noqa: F401  (side effect: force UTF-8 on stdout/stderr)

ROOT = pathlib.Path(__file__).resolve().parents[1]
EN = ROOT / "README.md"
ZH = ROOT / "README.zh-CN.md"


def fenced(text: str) -> list[tuple[str, str]]:
    return [(m.group(1), m.group(2))
            for m in re.finditer(r"```(\w*)\n(.*?)```", text, re.S)]


def classify(tag: str, body: str) -> str:
    if tag in ("bash", "python"):
        return "code"
    stripped = body.strip()
    # directory listing: mostly "name.py   description" lines with indentation
    lines = [ln for ln in stripped.splitlines() if ln.strip()]
    path_like = sum(1 for ln in lines if re.match(r"^\s*[\w./-]+\.(py|txt|md)\s", ln))
    if path_like >= max(3, len(lines) // 2):
        return "tree"
    # transcript: line-broken key/value output with a RESULT line or a long sha256
    if "RESULT:" in stripped or re.search(r"\b[0-9a-f]{64}\b", stripped):
        return "transcript"
    return "metrics"


def norm_tree(body: str) -> list[str]:
    """Paths and nesting only; trailing descriptions dropped."""
    out = []
    for ln in body.splitlines():
        if not ln.strip():
            continue
        indent = len(ln) - len(ln.lstrip())
        token = ln.strip().split()[0]
        out.append(f"{indent}:{token}")
    return out


def norm_metrics(body: str) -> list[str]:
    """Numeric content as a multiset.

    Translation may legitimately reorder a clause ("error -31.79 at 50 zeros" becomes
    "50 个零点时误差 -31.79"), so comparison is by multiset, not by position. What must not
    change is *which* figures appear and how many times.
    """
    return sorted(re.findall(r"-?\d[\d,]*(?:\.\d+)?(?:e-?\d+)?", body))


def main() -> int:
    if not ZH.exists():
        print("[SKIP] Chinese README absent")
        return 0
    en_b = fenced(EN.read_text(encoding="utf-8"))
    zh_b = fenced(ZH.read_text(encoding="utf-8"))

    failures: list[str] = []
    print(f"blocks: en={len(en_b)} zh={len(zh_b)}")
    if len(en_b) != len(zh_b):
        failures.append("block count differs")

    for i, ((te, be), (tz, bz)) in enumerate(zip(en_b, zh_b)):
        kind = classify(te, be)
        kind_zh = classify(tz, bz)
        if kind != kind_zh:
            failures.append(f"block {i}: classified {kind} in EN but {kind_zh} in ZH")
            print(f"[FAIL] block {i}: {kind} vs {kind_zh}")
            continue

        if kind == "code":
            norm = lambda t, b: "\n".join(
                ln.split(" #")[0].rstrip() if ln.find(" #") != -1 else ln.rstrip()
                for ln in b.splitlines()) if t == "bash" else b
            same = norm(te, be) == norm(tz, bz)
        elif kind == "tree":
            same = norm_tree(be) == norm_tree(bz)
        elif kind == "metrics":
            same = norm_metrics(be) == norm_metrics(bz)
        else:  # transcript
            same = be == bz

        print(f"[{'PASS' if same else 'FAIL'}] block {i} ({kind})")
        if not same:
            failures.append(f"block {i} ({kind}) differs beyond translation")
            if kind == "metrics":
                print("   EN numbers:", norm_metrics(be))
                print("   ZH numbers:", norm_metrics(bz))
            if kind == "tree":
                import difflib
                for d in list(difflib.unified_diff(
                        norm_tree(be), norm_tree(bz), "en", "zh", lineterm=""))[:14]:
                    print("   ", d)

    # python samples must compile
    for body in [b for t, b in zh_b if t == "python"]:
        try:
            compile(body, "<zh>", "exec")
            print("[PASS] zh python sample compiles")
        except SyntaxError as e:
            failures.append(f"zh python sample does not compile: {e}")

    if failures:
        print("\nFAILURES:")
        for f in failures:
            print("  -", f.encode("ascii", "backslashreplace").decode("ascii"))
        return 1
    print("\nparity holds for every block")
    return 0


if __name__ == "__main__":
    sys.exit(main())