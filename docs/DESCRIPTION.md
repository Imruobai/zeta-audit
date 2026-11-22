# Description

Text fields for the repository and for PyPI. Everything factual here is copied from
`REPORT.md`, which is generated from artifacts in `out/`; refresh both before publishing.

---

## 1. GitHub About field (limit: 350 characters, single line)

**Recommended: 191 characters.** Leads with the thing that is hard to do, not with a
feature list; the second sentence is what a reader needs to judge whether it is for them.

```
Audit a Riemann zeta zero table and catch a missing zero. Four checks: row structure, |zeta(1/2+it)| residuals, an independent mpmath cross-check, and a windowed count taken from zeta itself.
```

Shorter alternatives, all measured:

| chars | text | when to use |
| --- | --- | --- |
| 117 | `Point a CLI at a Riemann zeta zero table and get a verdict. Catches a missing zero, which no residual check can find.` | you want attitude; also names the differentiator in one breath |
| 102 | `Audit Riemann zeta zero tables: structure, residuals, independent cross-check, missing-zero detection.` | fits without truncation in GitHub's narrow list views |
| 220 | `Audit a Riemann zeta zero table: structure, residuals, an independent mpmath cross-check, and a windowed count that catches a missing zero. Demonstrated on Odlyzko's 100k-row table with a negative control that must fail.` | the earlier draft; longest, mentions the evidence |

Notes on the limit:

- 350 is characters, not bytes. All candidates above are pure ASCII, so bytes == chars and
  no em dash / Greek letters are involved (those count as 1 char each but render as
  mojibake on some terminals, which is why they are avoided here).
- GitHub truncates long descriptions in narrow list and search surfaces around 100-160
  characters. The 191-char recommendation survives to the differentiator ("catch a missing
  zero"), which is in the first 69 characters.
- Never put a newline in this field; it is a single-line input.

## 2. PyPI summary (one sentence, <= 200 chars)

```
Audit a Riemann zeta zero table: structure, residuals, independent cross-check, and a windowed count that detects a missing zero.
```

Character count: 128 (single line; PyPI's summary field is one line).

## 3. PyPI long description

Drop this into `pyproject.toml` as `readme`, or use it verbatim as the PyPI project page
intro. It is deliberately shorter than the repository README: the README carries the
measurements, this carries the reason to install.

---

### zeta-audit

**Point it at a zero table someone gave you and get a verdict.**

```bash
pip install "zeta-audit[crosscheck]"
zeta-audit zeros.txt
```

Zero tables are load-bearing "trust me" files. Every numerical use of the Riemann zeta
function depends on them, they are distributed as opaque data, and there is no standard
check step. Tools like [Arb](https://arblib.org) and [mpmath](https://mpmath.org) compute
zeros rigorously, but they *produce*; they do not audit a file you were handed.

`zeta-audit` runs four checks:

| check | catches | how |
| --- | --- | --- |
| structure | swapped, duplicated, descending ordinates | ordering and duplicate scan |
| residuals | fabricated points | \|zeta(1/2+igamma)\| at sampled ordinates, by two evaluators |
| independent | systematically wrong values | ordinates against `mpmath.zetazero` |
| completeness | **missing** zeros | windowed count taken from zeta alone, compared with the table's rows |

### The check that matters

Every listed ordinate can be correct while the file silently skips one. That failure is
invisible to residual checks and to a count-versus-smooth sanity check.

Demonstrated on Odlyzko's `zeros1`  -  100,000 ordinates, height <= 74,920.8, sha256
`3436c916...`:

```
complete table           -> ALL CHECKS PASSED
same file, one row gone  -> FAILED, and the mismatch names the right window
                           (weak |S(T)| count: 0.405  -  would have passed)
```

### What it is not

- **Not a crypto result.** The Riemann Hypothesis says nothing about factoring.
- **Not proof-grade arithmetic.** Arb gives rigorous enclosures; this gives float estimates
  with a measured ~1e-12 agreement to mpmath. Use Arb when you need proof.
- **Not exhaustive.** Completeness is sampled (3 windows x 200 rows out of 100,000 by
  default; `--windows N` trades time for coverage). A hole outside the sampled windows is
  missed.

### Install

```bash
pip install zeta-audit                  # numpy only
pip install "zeta-audit[crosscheck]"    # + mpmath, enables the independent checks
```

Python >= 3.10. Without mpmath the independent and windowed checks report **skipped** rather
than passing.

### Formats

Auto-detected: bare ordinates, `index ordinate`, `gamma=...`, comma- or tab-separated, `#`
comments. Odlyzko and LMFDB downloads parse untouched  -  the audit above used Odlyzko's file
as published.

MIT. The most useful thing you can send is a table this tool gets wrong.

---

## 4. GitHub topics

```
riemann-zeta  zeta-zeros  number-theory  verification  data-validation  mpmath
odlyzko  lmfdb  python  cli
```

## 5. First-commit / release summary line

```
v0.4.0  -  renamed from zetaedge; windowed completeness check that actually detects a
missing zero, pinned by a negative control.
```

---

## Checklist before pasting any of the above

```bash
python pipeline.py       # ~4.5 min; regenerates out/ including the 100k audit
python report.py         # REPORT.md from out/*.json only
python verify.py         # exit 0
python tests/run_all.py  # 81 checks
```

Then confirm:
- `out/odlyzko_negative_control.json` still has `detected: true`
- the sha256 you quote matches `out/odlyzko_audit.json`
- `pip install -e .` works (not verified on the authoring machine  -  no setuptools there)

**Placeholder to fill:** the `[project.urls]` block in `pyproject.toml` still reads
`https://github.com/USER/zeta-audit`. Replace `USER` before publishing, or remove the block.