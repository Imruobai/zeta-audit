# How this compares to work that already exists

Written to answer "has someone done this already?" honestly, including the parts where the
answer is **yes and better**. If you are deciding whether to use or contribute to this
repo, read this before the README.

## The short version

**Most of the stack exists elsewhere, and two pieces exist in stronger forms.** What does
not obviously exist is a *table-audit tool* — point it at an opaque zero file, get a
verdict. That is now the repo's centre of gravity; everything else is supporting cast.

## Point-by-point

| Component | Already exists, and where | How this repo compares |
| --- | --- | --- |
| ζ(s), θ(t), Z(t) at arbitrary precision | [mpmath](https://mpmath.org) (`zeta`, `siegeltheta`, `siegelz`), [python-flint](https://github.com/flintlib/python-flint) / [Arb](https://arblib.org) | **Weaker.** Arb gives *rigorous enclosures*; ours are float estimates with a measured ~1e-12 agreement. We keep our own because it is dependency-free and it is the thing being cross-checked — not because it is better. Use Arb if you need rigour. |
| Zero isolation with certified completeness | [Arb](https://arblib.org) `acb.zeta_zeros` (Platt's algorithm, Turing's method for the count), wrapped by python-flint | **Weaker.** Arb is the reference implementation and its count *is* the completeness statement. Ours is a sign-change scan with a separate argument-principle count. |
| Zero tables | Odlyzko's [tables](https://www.dtc.umn.edu/~odlyzko/zeta_tables/index.html); [LMFDB](https://www.lmfdb.org/zeros/zeta/) (~10¹¹ zeros at 2⁻¹⁰² precision); [`passagemath-database-odlyzko-zeta`](https://pypi.org/project/passagemath-database-odlyzko-zeta/) ships the first 2,001,052 zeros | **Different job.** Those *are* the tables. This repo audits them. |
| Zero verification at scale | [teal-sea/zeta-lab](https://github.com/teal-sea/zeta-lab) — two-route zero layer: Arb isolation plus an mpmath `siegelz` bracket sign check that deliberately shares no code with Arb | **Weaker on rigour, comparable on idea.** They wrote the two-route idea down carefully (including the honest caveat that the completeness count is shared between routes unless an independent count is added). Our argument-principle count is an independent count, which is a genuine complement — but ours is float, theirs is Arb. |
| Curated zero datasets + analysis | a 2.1M-zero Odlyzko+LMFDB Parquet dataset with audit/spectral tooling, on [Zenodo](https://zenodo.org/records/22093842) | **Different job.** Dataset + dashboard versus a CLI checker. |
| Formalisation | Mathlib; and the RH claim itself now has an [independently run verification page](https://math.mit.edu/~drew/grh/) (MIT) | **Not attempted here.** See the section below. |
| Deterministic Miller–Rabin base bound | Bach 1990; Jaeschke 1993; Sorenson–Webster 2015 | **Correct but not novel**, and conditional on ERH/GRH — not RH. See §7 of [PAPER.md](PAPER.md). |

## Where this repo is actually differentiated

One thing, and it is narrow:

**`zeta-audit <table>` runs four independent checks on an arbitrary zero file and returns
a verdict**: sorted/duplicate structure, |ζ(½+iγ)| residual at sampled ordinates (by our
evaluator *and* by mpmath), ordinate agreement with mpmath's own zero finder, and
completeness against both the smooth count θ(T)/π+1 and an argument-principle strip count.

The completeness check is the one that catches a *missing* zero, which no residual check
can find. Nothing in the searches above is a "check this opaque table" CLI; the closest
work is `zeta-lab`'s zero layer, which is a verification *component* inside a larger
research codebase rather than a tool you point at someone else's file.

That is a small, real gap. It is not a startup.

## What was removed, and why

- **Prime certificates as a product.** Withdrawn. The sweep is ~100× slower than
  fixed-base Miller–Rabin at 512 bits, FIPS 186-4 already permits MR at 2⁻¹⁰⁰ error, and
  the underlying base bound is ERH/GRH, not RH. Code remains as a labelled demonstration.
- **`rhtrust`, a transparency log for primes.** Withdrawn: no ecosystem, no demand. The
  generic log/Merkle code stays because it is tested and reusable for other artifacts.
- **`rhbounds` as a service.** Withdrawn: anyone who needs π(x) error bars can call
  mpmath in three lines.

## The RH/GRH formalisation claim (context, not endorsement)

There is a claimed Lean 4 formalisation of RH and GRH announced at
[alpo.ge/remark.pdf](https://alpo.ge/remark.pdf) (20 November 2026), distributed only as
Lean source parts (`lean.tar.gz.part01`–`part14`, ~239 MB compressed / 175,187 modules).

At the time of writing there is an independent verification page by Andrew Sutherland at
MIT, [math.mit.edu/~drew/grh](https://math.mit.edu/~drew/grh/), reporting: all 175,187
modules compile on Lean v4.33.1, `#print axioms` for the five headline theorems returns
only `propext`, `Classical.choice`, `Quot.sound`, a sandboxed rebuild reproduces the
export byte for byte, and two independent kernels (nanoda, con-leche) accept the full
export.

That page also states the limit of what it shows, in its own words: *"A passing check
shows that the formal statements, as written in Lean against Mathlib's definitions, follow
from the three standard axioms according to the kernels used. It relies on those kernels
and on Mathlib's definitions being what they are intended to be."*

So the correct summary is: **a formal proof has been checked by an independent party
against a specific set of definitions.** Whether those definitions are the intended ones is
a separate question that a kernel cannot answer.

Two consequences for this repo:

1. **Nothing here changes.** The zero auditing and the ψ/R cross-checks are unconditional
   and independent of whether RH is settled.
2. **The conditional labels stay.** The Schoenfeld and Cramér statements are labelled
   "conditional on RH" because that is what the literature says, and because a
   formalisation of the *implication* is not the same as the *hypothesis* being accepted
   by the community. If that changes, the labels change with it — they are generated, not
   hard-coded into prose.

## If you only read one line

Use mpmath or Arb for computing; use this if you need to **check a table someone handed
you**. Corrections to the comparisons above are the most useful thing you can send.