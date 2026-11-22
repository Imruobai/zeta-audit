# Release notes

## v0.4.1: a skipped check no longer reports success

Found by installing the built wheel into a clean venv with only numpy. The CLI printed
`ALL CHECKS PASSED` and exited 0 after skipping `independent` and the windowed count, the
two checks that can actually detect a **missing** zero. The README promised the opposite
("skipped, not passed"), so the code was wrong, not the promise.

### The verdict is now three-valued

| status | meaning | exit code |
| --- | --- | --- |
| `passed` | every check ran and every check passed | 0 |
| `partial` | something was skipped; what ran passed | 2 |
| `failed` | at least one check that ran did not pass | 1 |

`audit()` returns `status` and `checks_skipped` alongside `all_ok`, and `all_ok` is True
only for `passed`. `tests/test_partial_status.py` exercises whichever branch the current
environment can reach, so the invariant is checked with and without mpmath.

### Packaging

- SPDX `license = "MIT"` plus `license-files`; the deprecated `License ::` classifier is
  gone, so `python -m build` no longer warns.
- `twine check` passes on both sdist and wheel (previously unverified on the authoring
  machine, where no setuptools existed).
- Added `CITATION.cff`, `CONTRIBUTING.md`, GitHub Actions CI (3 Pythons x Ubuntu plus one
  Windows, a numpy-only job that asserts the PARTIAL exit code, and a build job that
  installs the wheel and runs it), and a tag-triggered PyPI trusted-publishing workflow.


## v0.4.0 — renamed to `zeta-audit`

The distribution is now **`zeta-audit`** (`import zeta_audit`, CLI `zeta-audit`).
`zetaedge` said nothing about what the tool does; `audit` does, and it is the honest verb —
the arithmetic here is float, not certified, so `verify` would have overpromised.

### Breaking

- package `zetaedge` -> `zeta_audit`
- `pip install zetaedge` -> `pip install zeta-audit`
- console script `zetaedge` -> `zeta-audit-cli`; the main tool stays `zeta-audit`
- `python -m zetaedge...` -> `python -m zeta_audit...`

Nothing else changed in this release; the 5 checks and the negative control pass
unchanged.

### Packaging

- `readme` now points at `docs/PYPI_README.md`, a shorter project page generated from
  `docs/DESCRIPTION.md` section 3, so PyPI does not inherit the full repository README.
- added `classifiers`, `[project.urls]`, `py.typed`, and a `pytest` dev extra.
- **`[project.urls]` still contains `USER`**: replace it before publishing.


## v0.3.1 — the completeness check actually works

Three earlier attempts at detecting a **missing** zero were wrong. This release replaces all
of them with one that works, and pins the failure modes so they cannot come back.

### The negative control that exposed it

Odlyzko's `zeros1` (100,000 ordinates, height ≤ 74,920.8, sha256 `3436c916…`) is now
committed as `data/odlyzko_zeros1.txt`. The pipeline audits it, then audits the same file
with one row deleted at index 50,050.

| table | weak sanity `\|S(T)\|` | windowed count | verdict |
| --- | --- | --- | --- |
| complete | 0.595 | 200/200, 200/200, 200/200 | PASS |
| one row deleted | **0.405** | 200/200, **201 vs 200**, 200/200 | FAIL, correct window |

The weak check passes on the broken table. That is the finding: a count-versus-smooth
check cannot see a single hole.

### Rejected approaches (all three, with measurements)

| approach | failure |
| --- | --- |
| local gap statistics | ~7% false positives under GUE spacing — 7,155 of 99,999 gaps flagged on a **correct** table |
| argument-principle window count | correct but O(\|Z\|/step) ζ evaluations: ~1.5·10⁴ points × 6 ms at T ≈ 4·10⁴, unusable |
| `nzeros` evaluated at an ordinate | float rounding returns *k* or *k−1* unpredictably (γ₃ → 2, not 3) |

The shipped method: mpmath `nzeros` at midpoints **between** ordinates, difference of two
counts, compared with the table's rows in that window.

### Also changed

- `count_zeros_window(t_lo, t_hi)` added to `certify.py`; `_contour` generalised to an
  arbitrary height interval. Kept because it is the only *certified-by-ζ* count in the repo,
  even though `nzeros` is what the fast path uses.
- `zeta_audit/__init__.py` re-exports the CLI-entry-point modules lazily, removing a
  `runpy` RuntimeWarning from `python -m zeta_audit.audit_table`.
- `--strip` flag replaced by `--windows N`.
- Tests: 78 → 81. New `test_audit_detects_missing_zero` asserts both that a hole is caught
  *and* that the weak check would have missed it.

### Known gap

Windowed completeness is **sampled**: 3 windows × 200 rows out of 100,000. A hole outside
the sampled windows is missed. `--windows` trades time for coverage; nothing here does an
exhaustive per-window sweep.

---

## v0.3.0 — the repo becomes a tool

**What changed, and why.** The previous version was a collection of verified computations
looking for a purpose. This version has one: **audit a zero table someone handed you.**

### New: `zeta-audit`

```bash
pip install "zeta-audit[crosscheck]"
zeta-audit zeros.txt
```

Four checks, each aimed at a distinct failure mode:

| check | catches | mechanism |
| --- | --- | --- |
| structure | swapped / duplicated / descending ordinates | ordering + duplicate scan |
| residuals | fabricated ordinates | \|ζ(½+iγ)\| at sampled points, by our evaluator **and** mpmath |
| independent | systematically wrong values | ordinate comparison with `mpmath.zetazero` |
| completeness | **missing** zeros | count vs θ(T)/π+1, plus argument-principle strip count |

Exit code 0 iff every check that could run passed. `--json` emits the full report;
`--strip` adds the argument-principle count (slow at large T).

Parser is format-tolerant: bare ordinates, `index ordinate`, `gamma=…`, comma/tab
separated, `#` comments. Odlyzko and LMFDB files parse without conversion.

### New: `zeta_audit crosscheck`

Compares our zeros and Z(t) against mpmath, the only non-circular check in the project.

```
zeros vs mpmath.zetazero (first 50):  max |Δγ| = 1.4e-11
Z(t)  vs mpmath.siegelz (t = 1000):   max |Δ|  = 1.2e-11
mpmath ζ at our ordinates:            max |ζ|  = 1.9e-11
```

mpmath is an **optional** dependency. Without it the independent check reports
`"available": false` rather than silently passing.

### Corrected: the Miller–Rabin hypothesis

The `a ≤ 2 log²n` base bound is **ERH/GRH**, not RH. RH does not control Dirichlet
L-zeros, so it does not yield that test. v0.2.0 labelled it "RH-conditional"; that was
wrong. Certificates now print the hypothesis explicitly and state the unconditional range
(n < 3.317·10²⁴ via the 13-base set). Primary source: Bach, *Analytic Methods in the Theory
of Numbers* (1990) — see `PAPER.md` §7.

### Also corrected

Schoenfeld's and Cramér's bounds are described as **conditional on RH** throughout. Earlier
prose said "are now theorems", which they are not.

### New: `docs/COMPARISON.md`

Point-by-point comparison with existing work, including the rows where this repo loses
(Arb for rigour, Arb/Platt for certified zero isolation, LMFDB/Odlyzko for the tables
themselves, zeta-lab for two-route verification at scale). Read it before trusting the
README's claims.

### Withdrawn

- Prime certificates as a product (slow, and the hypothesis was mislabelled).
- A transparency log for primes (no ecosystem).
- Error bars as a service (mpmath does it in three lines).

The underlying code for the first two remains, labelled as demonstration.

### Still unverified

Packaging is declared in `pyproject.toml` but has not been built on the authoring machine
(no setuptools in that environment). `pip install -e .` is expected to work; the test suite
runs from a checkout regardless.

---

## v0.2.0 — first public release

Dependency-free ζ/θ/Z, zero finder with residuals, argument-principle strip verification,
ψ/π/R with redundant implementations, Schoenfeld/Cramér audits, conditional primality
certificates, hash-chained log with Merkle proofs, SVG charts, stdlib HTTP wrapper.

## v0.1.0 — internal

Initial pipeline and test harness.