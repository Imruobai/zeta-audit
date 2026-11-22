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
| residuals | fabricated points | \|ζ(½+iγ)\| at sampled ordinates, by two evaluators |
| independent | systematically wrong values | ordinates against `mpmath.zetazero` |
| completeness | **missing** zeros | windowed count taken from ζ alone, compared with the table's rows |

### The check that matters

Every listed ordinate can be correct while the file silently skips one. That failure is
invisible to residual checks and to a count-versus-smooth sanity check.

Demonstrated on Odlyzko's `zeros1` — 100,000 ordinates, height ≤ 74,920.8, sha256
`3436c916…`:

```
complete table           → ALL CHECKS PASSED
same file, one row gone  → FAILED, and the mismatch names the right window
                           (weak |S(T)| count: 0.405 — would have passed)
```

### What it is not

- **Not a crypto result.** The Riemann Hypothesis says nothing about factoring.
- **Not proof-grade arithmetic.** Arb gives rigorous enclosures; this gives float estimates
  with a measured ~1e-12 agreement to mpmath. Use Arb when you need proof.
- **Not exhaustive.** Completeness is sampled (3 windows × 200 rows out of 100,000 by
  default; `--windows N` trades time for coverage). A hole outside the sampled windows is
  missed.

### Install

```bash
pip install zeta-audit                  # numpy only
pip install "zeta-audit[crosscheck]"    # + mpmath, enables the independent checks
```

Python ≥ 3.10. Without mpmath the independent and windowed checks report **skipped** rather
than passing.

### Formats

Auto-detected: bare ordinates, `index ordinate`, `gamma=…`, comma- or tab-separated, `#`
comments. Odlyzko and LMFDB downloads parse untouched — the audit above used Odlyzko's file
as published.

MIT. The most useful thing you can send is a table this tool gets wrong.
