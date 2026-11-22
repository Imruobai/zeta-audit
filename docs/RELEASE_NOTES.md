# Release notes

## v0.3.0 — the repo becomes a tool

**What changed, and why.** The previous version was a collection of verified computations
looking for a purpose. This version has one: **audit a zero table someone handed you.**

### New: `zeta-audit`

```bash
pip install "zetaedge[crosscheck]"
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

### New: `zetaedge crosscheck`

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