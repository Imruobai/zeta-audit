# Launch copy

Copy-paste material for introducing `zeta-audit`. Every number here is copied from
`REPORT.md`, which is generated from artifacts — refresh both before publishing
(`python pipeline.py && python report.py`), and do not type a figure that is not in there.

---

## One-liner

> A CLI that audits a Riemann zeta zero table: structure, residuals, an independent
> cross-check, and a windowed count that catches a **missing** zero.

## GitHub "About" field

```
Audit a Riemann zeta zero table: structure, residuals, mpmath cross-check, and a
windowed count that detects a missing zero.
```

## Short description (repo description / PyPI summary, ~140 chars)

```
Point it at a zero table someone gave you and get a verdict: structure, residuals,
independent cross-check, and a count that catches a missing zero.
```

---

## Announcement post (short)

**A small tool for a small, real problem.**

Zero tables are load-bearing "trust me" files. Every numerical use of ζ depends on them,
they arrive as opaque data, and there is no standard check step. Arb and mpmath *produce*
zeros rigorously; nothing obvious *audits someone else's file*.

`zeta-audit zeros.txt` runs four checks:

- **structure** — swapped, duplicated, descending ordinates
- **residuals** — |ζ(½+iγ)| at sampled ordinates, by two evaluators
- **independent** — ordinates against `mpmath.zetazero`
- **completeness** — a windowed count taken from ζ alone, compared with the table's rows

The last one is the interesting one, and it took three failed attempts to get right
(detailed in the README, with measurements). The failure it catches is the one residual
checks cannot: **every listed ordinate can be correct while the file silently skips one.**

Demonstrated on Odlyzko's `zeros1` (100,000 ordinates, height ≤ 74,920.8):

```
complete table          → ALL CHECKS PASSED
same file, one row gone → FAILED, and the mismatch names the right window
                          (weak |S(T)| count: 0.405, would have passed)
```

**What it is not.** Not a crypto breakthrough — RH says nothing about factoring. Not a
primality tool worth using — the conditional prime certificates in the repo are ~100×
slower than Miller–Rabin and rest on ERH/GRH, not RH. Not proof-grade arithmetic — Arb
gives rigorous enclosures and this does not.

**Limits, stated up front.** Windowed completeness is sampled (3 windows × 200 rows out of
100k). Float, not certified. Strip verification stops at T = 600 in pure Python.

MIT, numpy only, mpmath optional (without it the independent checks report *skipped*
rather than passing).

---

## Longer post (technical audience)

### The problem

A zero table is a file of numbers that a lot of mathematics silently depends on. When one
is published, it is usually consumed as opaque data. If it has a row out of order, you will
probably notice. If it is **missing** a zero — the harder failure — you will not, because
every number it does contain is correct.

### What the tool does that is not obvious

The obvious checks are cheap and mostly useless:

| check | verdict |
| --- | --- |
| sorted? duplicated? | catches transcription errors, nothing else |
| is \|ζ(½+iγ)\| ≈ 0 at each γ? | confirms listed rows, cannot see absent rows |
| does count ≈ θ(T)/π+1? | **too weak.** Measured on a 100k table with one row deleted: \|S(T)\| = 0.4, passes |

Three attempts at a real completeness check, and why the first two died:

1. **Local gap statistics.** A missing zero doubles one gap. In theory this is visible. In
   practice, with Gaussian-unitary spacing, ~7% of *legitimate* gaps exceed 2× their local
   median — on a correct 100k table, 7,155 of 99,999 gaps flagged. The signal is not
   separable from the scatter.
2. **Argument-principle window count.** Correct, and this is the method that gives a
   *certified-by-ζ* answer. But it costs O(|Z|/step) ζ evaluations: at T ≈ 4·10⁴, about
   1.5·10⁴ points at 6 ms each, per window. Usable at T = 100, not at T = 40,000.
3. **`mpmath.nzeros`.** Built on Turing's method, 0.1 s at T = 70,000. But do **not** call it
   at an ordinate: float rounding makes `nzeros(γ_k)` return *k* or *k−1* unpredictably
   (γ₃ returns 2). Evaluate at midpoints strictly between ordinates instead.

The shipped check is (3) with the midpoint rule, three windows of 200 rows, compared against
the table's own row count in each window.

### The negative control

This is the part that makes the claim credible, so the pipeline runs it every time:

| table | weak `\|S(T)\|` | windowed count | verdict |
| --- | --- | --- | --- |
| Odlyzko `zeros1`, complete | 0.595 | 200/200, 200/200, 200/200 | PASS |
| same, one row deleted at 50,050 | **0.405** | 200/200, **201 vs 200**, 200/200 | FAIL |

The weak check passes on the broken table. The windowed check fails, and it fails at the
right window. `test_audit_detects_missing_zero` asserts both halves — that a hole is caught,
and that the weak check would have missed it — so a future "simplification" back into any
of the three rejected methods fails CI.

### Where this sits

It is a narrow gap, not a startup. The nearest existing work is a verification *component*
inside [zeta-lab](https://github.com/teal-sea/zeta-lab), which pairs Arb isolation with an
mpmath bracket check; their own docs note that the completeness count is shared between
routes unless an independent count is added. [Arb](https://arblib.org) is the reference for
rigorous zero isolation and this tool does not compete with it. [LMFDB](https://www.lmfdb.org/zeros/zeta/)
and [Odlyzko](https://www.dtc.umn.edu/~odlyzko/zeta_tables/index.html) are where the actual
tables come from; this checks a file, it does not replace the file.

`docs/COMPARISON.md` has the point-by-point, including the rows where this repo loses.

---

## Q&A you should expect

**"Does this help with the Riemann Hypothesis?"**
No. It audits zero *data*. It says nothing about whether RH is true.

**"Is RH proved now?"**
Not in a way this repo takes a position on. The conditional statements here
(Schoenfeld, Cramér) stay labelled conditional because that is what the literature says. If
that changes, the labels are generated and change with it.

**"Why not just use Arb?"**
Use Arb to *compute*. Use this to check a file someone handed you, including files produced
by Arb. They are different jobs.

**"Is it rigorous?"**
No, and it says so. Float arithmetic with a measured ~1e-12 agreement to mpmath. Arb gives
enclosures; this gives a second opinion.

**"What is it bad at?"**
Sampled completeness (3 windows × 200 rows out of 100k — a hole outside the sampled windows
is missed), high heights in pure Python (strip verification stops at T = 600), and anything
requiring a proof rather than an estimate.

---

## Before publishing: checklist

```bash
python pipeline.py     # ~4.5 min; regenerates out/ including the 100k audit
python report.py       # REPORT.md from out/*.json only
python verify.py       # exit 0
python tests/run_all.py  # 84 checks
```

Then confirm the numbers you quote appear in `REPORT.md`, and that
`out/odlyzko_negative_control.json` still reports `detected: true`.