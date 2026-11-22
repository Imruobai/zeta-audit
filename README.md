# zeta-edge

**Point it at a zero table someone gave you and get a verdict.**

```bash
pip install zetaedge[crosscheck]
zeta-audit zeros.txt
```

```
table      : zeros.txt
sha256     : 3ea44f34566744954d07d91bd6c59cc275d4f937bc3d3428ea7023d0fb7f4f95
ordinates  : 138  (14.134725 .. 299.840326)
structure  : ok  dupes=0 descents=0 nonpositive=0
residuals  : our max |zeta| = 2.565e-11 over 40 samples, mpmath 2.430e-11
independent: max |diff| vs mpmath = 3.936e-12 over 5 zeros
completeness: count=138 vs smooth N(T)=137.614  S(T) implied = +0.386

RESULT: ALL CHECKS PASSED
```

Four checks, each catching a different failure:

| check | catches | how |
| --- | --- | --- |
| **structure** | swapped, duplicated, or descending ordinates | ordering and duplicate scan |
| **residuals** | fabricated points | \|ζ(½+iγ)\| at sampled ordinates, by *two* evaluators |
| **independent** | systematically wrong values | ordinate comparison with mpmath's own zero finder |
| **completeness** | **missing** zeros | count vs θ(T)/π+1, and an argument-principle strip count |

The completeness check is the one that matters most and that residual checks cannot do: a
table can have every listed ordinate correct and still be missing zeros.

---

## Why this exists

Zero tables are load-bearing "trust me" files. Every numerical use of ζ depends on them,
they are distributed as opaque data, and there is no standard check step. The tools that
compute zeros rigorously (Arb, mpmath) are excellent but they *produce*; they do not audit
someone else's file.

This repo is the audit step, plus the reference material needed to trust the auditor.

## Status of everything else here (honest table)

Most of the stack exists elsewhere in stronger forms. See
**[docs/COMPARISON.md](docs/COMPARISON.md)** for the point-by-point. Summary:

| component | state |
| --- | --- |
| table auditing (above) | **the point of the repo**; nearest existing work is a verification *component* inside [zeta-lab](https://github.com/teal-sea/zeta-lab), not a CLI |
| ζ, θ, Z evaluation | weaker than [Arb](https://arblib.org) (float, not enclosures) — kept dependency-free and because it is what the cross-check cross-checks |
| zero isolation | weaker than Arb's `acb.zeta_zeros` (no rigorous enclosures) |
| argument-principle strip count | useful as an *independent* count; float grade, not certified |
| ψ(x)/R(x) double implementations | a real cross-check oracle for other people's code |
| conditional prime certificates | **demonstration only** — ~100× slower than MR, and based on ERH/GRH, not RH |
| "transparency log for primes" | **withdrawn** as a product; the generic log/Merkle code remains |

## Verification: what makes the numbers trustworthy

```bash
python tests/run_all.py    # 78 checks
python verify.py           # third-party re-check of committed artifacts
python pipeline.py         # regenerate everything (~5 min)
python report.py           # REPORT.md rendered from artifacts only
```

The single most important check is the one that is not circular: **agreement with
mpmath**, an independent implementation.

| check | result |
| --- | --- |
| our zeros vs `mpmath.zetazero`, first 50 | max \|Δγ\| = 1.4e-11 |
| our Z(t) vs `mpmath.siegelz` | max \|Δ\| = 1.5e-11 at t = 1000 |
| mpmath's ζ at our ordinates | max \|ζ\| = 1.9e-11 |

Every other check compares this code to itself or to a table typed in by hand — which is
why this one is stated separately. Measured results: **[REPORT.md](REPORT.md)**, generated
from `out/*.json`, so prose cannot drift from evidence.

```
zeros      649 zeros, 0 < γ ≤ 1000; max |ζ(½+iγ)| = 2.6e-11; Δγ vs published 8.7e-12
strip      T = 100 / 300 / 600: argument-principle count == on-line count (29/138/341)
explicit   ψ(10⁵): error −31.79 from 50 zeros → −0.27 from 600 zeros
```

## Install

```bash
pip install zetaedge                  # numpy only
pip install "zetaedge[crosscheck]"    # + mpmath, enables the independent checks
```

Python ≥ 3.10. Without mpmath the audit tool reports the independent check as
**skipped**, rather than silently claiming it ran.

## Usage

```bash
zeta-audit zeros.txt                       # the main entry point
zeta-audit zeros.txt --strip --json r.json # + argument-principle count

python -m zetaedge zeros --t-max 1000      # find zeros with residuals
python -m zetaedge strip --t-max 600       # argument-principle verification
python -m zetaedge bounds --x-max 10000000 # error-bar audits, each hypothesis labelled
python -m zetaedge crosscheck              # compare against mpmath
python -m zetaedge.serve --port 8788       # stdlib HTTP wrapper
```

```python
from zetaedge import load_table, audit_zero_table

report = audit_zero_table(load_table("zeros.txt"))
if not report["all_ok"]:
    print(report["completeness"])       # is a zero missing?
```

## Accepted table formats

Auto-detected; index columns, `key=value`, commas/tabs, and `#` comments all work:

```
14.134725141734693
1 14.134725141734693
gamma=14.134725141734693
```

Odlyzko and LMFDB downloads parse without conversion. If yours does not, that is a bug
report worth sending.

## Layout

```
zetaedge/
  audit_table.py   *** the table auditor (CLI: zeta-audit) ***
  crosscheck.py    mpmath cross-validation (optional dependency)
  zeta.py          ζ(s), θ(t), Hardy Z (dependency-free floats)
  zeros.py         zero finder + residual audit
  explicit.py      ψ(x), π(x), li, R(x), each with a redundant second implementation
  certify.py       argument-principle strip verification
  bounds.py        Schoenfeld / Cramér error bars, hypothesis labelled per bound
  primality.py     13-base unconditional test + ERH/GRH base sweep
  parallel.py      parallel sweep + measured sequential estimate
  transparency.py  hash-chained log, Merkle anchor, inclusion proofs
  primegen.py      attestation demonstration (not a product)
  plot.py          dependency-free SVG charts
  serve.py         stdlib HTTP service
pipeline.py / report.py / verify.py / tests/run_all.py
docs/COMPARISON.md  how this compares to existing work, including where it loses
```

## Limits

- **Float, not certified.** Arb gives rigorous enclosures; this gives estimates with a
  measured ~1e-12 agreement. If you need proof-grade arithmetic, use Arb and treat this as
  the second opinion.
- Strip verification tops out at T = 600 in pure Python; the method scales (Platt–Trudgian
  reached 3·10¹²), the interpreter does not.
- The `2 log²n` base bound is **ERH/GRH, not RH**. Certificates print the hypothesis.
- `CRAMER_C = 1/(4π)` is a conservative engineering constant, not the literature sharp
  value; audits print the ratio so you can substitute your own.

MIT. The most useful thing you can send is a table that this tool gets wrong.