# zeta-audit

**Point it at a zero table someone gave you and get a verdict.**

```bash
pip install "zeta-audit[crosscheck]"
zeta-audit zeros.txt
```

```
table       : zeros.txt
sha256      : 3436c916a7878261ac183fd7b9448c9a4736b8bbccf1356874a6ce1788541632
ordinates   : 100,000  (14.134725 .. 74920.827499)
structure   : ok  dupes=0 descents=0 nonpositive=0
residuals   : our max |zeta| = 3.8e-08 over 40 samples, mpmath 1.2e-08
independent : max |diff| vs mpmath = 2.7e-10 over 5 zeros
completeness: count=100,000 vs smooth N(T)=99999.405  S(T) implied = +0.595  (weak sanity check)
              window rows 24901..25100: table 200 vs independent count 200  [ok]
              window rows 49901..50100: table 200 vs independent count 200  [ok]
              window rows 74901..75100: table 200 vs independent count 200  [ok]

RESULT: ALL CHECKS PASSED
```

That is a real run on Odlyzko's `zeros1` — 100,000 zeros up to height 74,920.8
(sha256 `3436c916…`).

## The check that matters, and how it was tested

Most tables are wrong in the boring ways: a row out of order, a duplicate, a fabricated
point. Those are easy. The hard failure is a **missing** zero, because every listed
ordinate can be correct while the file silently skips one.

So the tool does not just verify what is there — it **counts**. Three windows of 200 rows
are picked, and the number of zeros inside each is recomputed from ζ alone, via an
independent implementation (mpmath's `nzeros`, Turing's method). Compare with the rows the
table lists.

Proof that this works, from `out/odlyzko_negative_control.json` — the same 100k table with
**one row deleted** at index 50,050:

```
completeness: count=99,999 vs smooth N(T)=99999.405  S(T) implied = -0.405  (weak sanity check)
              window rows 24900..25099: table 200 vs independent count 200  [ok]
              window rows 49900..50099: table 200 vs independent count 201  [MISMATCH]
              window rows 74900..75099: table 200 vs independent count 200  [ok]

RESULT: FAILED
```

It fails, and it points at the right window. Note the weak sanity line: `|S(T)| = 0.4`,
which **would have passed**. A count-vs-smooth check does not catch a single hole; only the
independent count does.

### Three approaches that did not work

Recorded because they are the obvious ideas and they are all wrong — someone will try them
again otherwise.

| attempt | why it fails |
| --- | --- |
| **local gap statistics** | under Gaussian-unitary spacing ~7% of legitimate gaps exceed 2× their local median. Measured: 7,155 of 99,999 gaps on a *correct* table flagged. A real hole is indistinguishable from ordinary scatter. |
| **argument-principle window count** | correct, but each window needs O(\|Z\|/step) ζ evaluations. At T ≈ 4·10⁴ that is ~1.5·10⁴ points × 6 ms, and it stopped being usable. `nzeros` does it in 0.1 s. |
| **`nzeros` evaluated at an ordinate** | floating-point rounding makes `nzeros(γ_k)` return *k* or *k−1* unpredictably (measured: γ₃ returns 2, not 3). The count must be taken strictly *between* ordinates. |

All three are pinned by `test_audit_detects_missing_zero`, so a later "simplification" back
into one of them fails CI.

## The four checks

| check | catches | how |
| --- | --- | --- |
| **structure** | swapped, duplicated, descending ordinates | ordering and duplicate scan |
| **residuals** | fabricated points | \|ζ(½+iγ)\| at sampled ordinates, by *two* evaluators |
| **independent** | systematically wrong values | ordinate comparison with `mpmath.zetazero` |
| **completeness** | **missing** zeros | windowed independent count (above) |

## Why this exists

Zero tables are load-bearing "trust me" files. Every numerical use of ζ depends on them,
they are distributed as opaque data, and there is no standard check step. The tools that
compute zeros rigorously — [Arb](https://arblib.org), [mpmath](https://mpmath.org) — are
excellent but they *produce*; they do not audit someone else's file.

This repo is the audit step, plus the reference material needed to trust the auditor.

## Status of everything else here (honest table)

Most of the stack exists elsewhere in stronger forms. See
**[docs/COMPARISON.md](docs/COMPARISON.md)** for the point-by-point. Summary:

| component | state |
| --- | --- |
| table auditing (above) | **the point of the repo**; nearest existing work is a verification *component* inside [zeta-lab](https://github.com/teal-sea/zeta-lab), not a CLI |
| ζ, θ, Z evaluation | weaker than Arb (float, not enclosures) — kept dependency-free and because it is what the cross-check cross-checks |
| zero isolation | weaker than Arb's `acb.zeta_zeros` (no rigorous enclosures) |
| argument-principle strip count | useful as an *independent* count; float grade, not certified |
| ψ(x)/R(x) double implementations | a real cross-check oracle for other people's code |
| conditional prime certificates | **demonstration only** — ~100× slower than MR, and based on ERH/GRH, not RH |
| "transparency log for primes" | **withdrawn** as a product; the generic log/Merkle code remains |

## Verification: what makes the numbers trustworthy

```bash
python tests/run_all.py    # 81 checks
python verify.py           # third-party re-check of committed artifacts
python pipeline.py         # regenerate everything (~5 min, includes the 100k audit)
python report.py           # REPORT.md rendered from artifacts only
```

The most important check is the one that is not circular: **agreement with mpmath**, an
independent implementation.

| check | result |
| --- | --- |
| our zeros vs `mpmath.zetazero`, first 50 | max \|Δγ\| = 1.4e-11 |
| our Z(t) vs `mpmath.siegelz` | max \|Δ\| = 1.5e-11 at t = 1000 |
| mpmath's ζ at our ordinates | max \|ζ\| = 1.9e-11 |
| Odlyzko `zeros1`, 100k rows | all four checks pass |
| same table, one row deleted | **FAILED**, correct window identified |

Measured results: **[REPORT.md](REPORT.md)**, generated from `out/*.json`, so prose cannot
drift from evidence.

```
zeros      649 zeros, 0 < γ ≤ 1000; max |ζ(½+iγ)| = 2.6e-11; Δγ vs published 8.7e-12
strip      T = 100 / 300 / 600: argument-principle count == on-line count (29/138/341)
explicit   ψ(10⁵): error −31.79 from 50 zeros → −0.27 from 600 zeros
```

## Install

```bash
pip install zeta-audit                 # numpy only
pip install "zeta-audit[crosscheck]"    # + mpmath, enables the independent checks
```

Python ≥ 3.10. Without mpmath the independent and windowed checks report **skipped**, not
passed.

## Usage

```bash
zeta-audit zeros.txt                       # the main entry point
zeta-audit zeros.txt --windows 5           # more independent windows
zeta-audit zeros.txt --json r.json         # full report

python -m zeta_audit zeros --t-max 1000      # find zeros with residuals
python -m zeta_audit strip --t-max 600       # argument-principle verification
python -m zeta_audit bounds --x-max 10000000 # error-bar audits, each hypothesis labelled
python -m zeta_audit crosscheck              # compare against mpmath
python -m zeta_audit.serve --port 8788       # stdlib HTTP wrapper
```

```python
from zeta_audit import load_table, audit_zero_table

report = audit_zero_table(load_table("zeros.txt"), windows=3)
if not report["all_ok"]:
    for w in report["completeness"]["windows"]:
        if not w["agree"]:
            print("possible hole near rows", w["rows"],
                  w["table_zeros_inside"], "vs", w["independent_count"])
```

## Accepted table formats

Auto-detected; index columns, `key=value`, commas/tabs, and `#` comments all work:

```
14.134725141734693
1 14.134725141734693
gamma=14.134725141734693
```

Odlyzko and LMFDB downloads parse without conversion — the 100k audit above used Odlyzko's
file untouched. If yours does not parse, that is a bug report worth sending.

## Layout

```
zeta_audit/
  audit_table.py   *** the table auditor (CLI: zeta-audit) ***
  crosscheck.py    mpmath cross-validation + nzeros windows (optional dependency)
  zeta.py          ζ(s), θ(t), Hardy Z (dependency-free floats)
  zeros.py         zero finder + residual audit
  explicit.py      ψ(x), π(x), li, R(x), each with a redundant second implementation
  certify.py       argument-principle strip and window counts
  bounds.py        Schoenfeld / Cramér error bars, hypothesis labelled per bound
  primality.py     13-base unconditional test + ERH/GRH base sweep
  parallel.py      parallel sweep + measured sequential estimate
  transparency.py  hash-chained log, Merkle anchor, inclusion proofs
  primegen.py      attestation demonstration (not a product)
  plot.py          dependency-free SVG charts
  serve.py         stdlib HTTP service
data/odlyzko_zeros1.txt   the 100k reference table the audit is tested against
pipeline.py / report.py / verify.py / tests/run_all.py
docs/COMPARISON.md  how this compares to existing work, including where it loses
docs/LAUNCH_COPY.md description, announcement posts, Q&A for introducing the repo
docs/DESCRIPTION.md repo About field, PyPI summary, long description, topics
docs/PYPI_README.md the PyPI project page (generated from DESCRIPTION.md section 3)
```

## Limits

- **Float, not certified.** Arb gives rigorous enclosures; this gives estimates with a
  measured ~1e-12 agreement. If you need proof-grade arithmetic, use Arb and treat this as
  the second opinion.
- **Windowed completeness is sampled, not exhaustive.** Three windows of 200 rows out of
  100,000. A hole outside the sampled windows is missed. `--windows` trades time for
  coverage; a full sweep is not what this tool does.
- Residual sampling is 40 ordinates out of 100k for the same reason.
- Strip verification tops out at T = 600 in pure Python; the method scales
  (Platt–Trudgian reached 3·10¹²), the interpreter does not.
- The `2 log²n` base bound is **ERH/GRH, not RH**. Certificates print the hypothesis.
- `CRAMER_C = 1/(4π)` is a conservative engineering constant, not the literature sharp
  value; audits print the ratio so you can substitute your own.

MIT. The most useful thing you can send is a table that this tool gets wrong.