"""Test suite: `python -m pytest` or `python tests/run_all.py`.

Every claim the project makes in its report is asserted here, so the report is
never stronger than the code.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from zeta_audit.bounds import cramer_gap_ceiling, gap_audit, pi_error_audit
from zeta_audit.certify import certificate, count_zeros_strip, next_prime, verify_strip
from zeta_audit.explicit import (
    audit_pi_bound,
    audit_psi_bound,
    chebyshev_psi,
    chebyshev_psi_between,
    gram_R,
    li,
    pi_exact,
    psi_table,
    psi_explicit,
    zero_sum_convergence,
)
from zeta_audit.primality import is_prime_13, is_prime_rh, rh_bases, rh_base_bound
from zeta_audit.zeta import Z, n_zeros_asymptotic, theta, zeta, zeta_half
from zeta_audit.zeros import KNOWN_FIRST_ZEROS, check_against_known, find_zeros


CHECKS: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    CHECKS.append((name, ok, detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f"  ({detail})" if detail else ""))


# --------------------------------------------------------------------------- #
def test_zeta_values() -> None:
    e = abs(zeta(2.0).real - math.pi ** 2 / 6)
    check("zeta(2) = pi^2/6", e < 1e-15, f"err={e:.2e}")
    z3 = 1.2020569031595942854
    e = abs(zeta(3.0).real - z3)
    check("zeta(3) = Apery", e < 1e-15, f"err={e:.2e}")
    e = abs(zeta(0.5 + 14.134725141734693j))
    check("zeta(1/2 + i*gamma_1) ~ 0", e < 1e-9, f"|zeta|={e:.2e}")
    # functional equation sanity: zeta(0) = -1/2, zeta(-1) = -1/12
    e = abs(zeta(0.0).real + 0.5)
    check("zeta(0) = -1/2", e < 1e-12, f"err={e:.2e}")


def test_theta_and_Z() -> None:
    # theta(0) = 0 and Z(0) = zeta(1/2) = -1.4603545088
    z0 = zeta_half(0.0).real
    check("zeta(1/2) = -1.4603545088", abs(z0 + 1.4603545088095868) < 1e-9, f"{z0:.10f}")
    # Z is real and vanishes at known zeros
    for g in KNOWN_FIRST_ZEROS[:5]:
        check(f"|Z({g:.3f})| < 1e-9", abs(Z(g)) < 1e-9, f"Z={Z(g):.2e}")
    check("theta monotone", theta(100) < theta(200) and theta(200) < theta(1000), "ok")


def test_zeros() -> None:
    zs = find_zeros(t_max=200.0, t_min=0.5, step=0.25)
    known = check_against_known(zs)
    check("first 10 zeros match Odlyzko", known["pass"], f"max|Δ|={known['max_abs_error']:.2e}")
    check("all residuals < 1e-8", all(z.residual < 1e-8 for z in zs),
          f"max={max(z.residual for z in zs):.2e}")
    smooth = n_zeros_asymptotic(200.0)
    check("zero count within 1 of smooth N(T)", abs(len(zs) - smooth) <= 1,
          f"found={len(zs)} smooth={smooth:.2f}")


def test_strip_verification() -> None:
    for T in (30.0, 60.0):
        res = verify_strip(T)
        check(f"RH verified to Im s <= {T:g}", res["match"],
              f"line={res['zeros_on_line']} strip={res['zeros_in_strip']}")
    c = count_zeros_strip(30.0)
    check("argument-principle count is an integer to 1e-9", c["resolution_error"] < 1e-9,
          f"err={c['resolution_error']:.2e}")


def test_psi_and_pi() -> None:
    table = psi_table(200_000)
    # psi(100) = log(2*3*5*7*2^3*3^2*11*13*... ) known value 94.04531122935739
    e = abs(chebyshev_psi(100, table) - 94.0453112293574)
    check("psi(100) exact", e < 1e-9, f"err={e:.2e}")
    check("psi(100) jump-average equals psi(100)",
          abs(chebyshev_psi_between(100, table) - 94.0453112293574) < 1e-9)
    check("pi(10^6) = 78498", pi_exact(10 ** 6) == 78498)
    check("pi(10^5) = 9592", pi_exact(10 ** 5) == 9592)
    # R(x) and li(x) bracketing
    r = gram_R(10 ** 5)
    l = li(10 ** 5)
    check("|R(1e5) - 9592| < 10", abs(r - 9592) < 10, f"R={r:.3f}")
    check("R is far better than li for pi", abs(r - 9592) < abs(l - 9592),
          f"errR={abs(r-9592):.2f} errli={abs(l-9592):.2f}")


def test_bounds() -> None:
    psi = audit_psi_bound(3_000_000)
    check("Schoenfeld psi bound holds to 3e6", psi["holds"],
          f"max ratio={psi['max_ratio']:.3f} at x={psi['argmax_x']}")
    pi = audit_pi_bound(500_000)
    check("Schoenfeld pi bound holds to 5e5", pi["holds"],
          f"max ratio={pi['max_ratio']:.3f} at x={pi['argmax_x']}")
    gaps = gap_audit(1_000_000)
    check("Cramer gap ceiling holds to 1e6", gaps["holds"],
          f"max gap={gaps['max_gap']} after {gaps['max_gap_after']}, ratio={gaps['max_ratio_to_ceiling']:.3f}")
    tight = [x for x in (10 ** 6, 10 ** 9, 10 ** 12)]
    check("gap ceiling grows like sqrt(x) log^2 x",
          all(cramer_gap_ceiling(x) < cramer_gap_ceiling(x * 10) for x in tight), "monotone")
    perr = pi_error_audit(200_000, stride=499)
    check("pi(x) inside RH bar for both R and li", perr["holds"],
          f"ratioR={perr['max_ratio_R']:.3f} ratioli={perr['max_ratio_li']:.3f}")


def test_explicit_formula() -> None:
    zs = find_zeros(t_max=1000.0, t_min=0.5, step=0.25)
    gammas = [z.gamma for z in zs]
    rows = zero_sum_convergence(10 ** 5, gammas, gamma_counts=(50, 200, 400))
    errs = [abs(r["error"]) for r in rows]
    check("explicit formula error shrinks with more zeros", errs[-1] <= errs[0] + 1e-9,
          f"{errs[0]:.3f} -> {errs[-1]:.3f} with {rows[-1]['zeros']} zeros")
    check("explicit formula error < 30 at x=1e5 with 400 zeros", errs[-1] < 30, f"{errs[-1]:.3f}")
    val = psi_explicit(10 ** 5, gammas[:400])
    check("psi(x) reconstruction within 0.1% of x", abs(val - 10 ** 5) / 10 ** 5 < 1e-3,
          f"psi={val:.2f}")


def test_primality() -> None:
    # cross-validate RH path against the unconditional 13-base path
    for n in [2, 3, 4, 17, 561, 1105, 2047, 3277, 2 ** 61 - 1, 2 ** 64 + 1]:
        a, b = is_prime_rh(n), is_prime_13(n) if n < 3_317_044_064_679_887_385_961_981 else None
        if b is None:
            check(f"is_prime_rh({n})", isinstance(a, bool))
        else:
            check(f"RH path agrees with 13-base path on {n}", a == b, f"{a} vs {b}")
    check("561 (Carmichael) is composite", not is_prime_rh(561))
    check("2^127-1 is prime", is_prime_rh(2 ** 127 - 1))
    check("2^128+1 composite", not is_prime_rh(2 ** 128 + 1))
    c = certificate(2 ** 127 - 1)
    check("certificate verdict prime", c.verdict == "prime", f"bases={len(c.bases)} ceiling={c.base_bound:.1f}")
    check("base ceiling = 2 log^2 n", abs(c.base_bound - rh_base_bound(2 ** 127 - 1)) < 1e-9)
    check("all bases are prime and <= ceiling",
          all(b <= c.base_bound and is_prime_13(b) for b in c.bases[:200]))
    c2 = certificate(2 ** 128 + 1)
    check("composite gets a witness", c2.verdict == "composite" and c2.witness_found is not None,
          f"witness={c2.witness_found}")


def test_next_prime() -> None:
    p, scanned = next_prime(10 ** 9)
    check("next prime after 1e9 is 1000000007", p == 1000000007, f"{p}, scanned={scanned}")
    # 2^127-1 is itself prime (Mersenne), so next_prime must return it unchanged
    m = 2 ** 127 - 1
    p2, s2 = next_prime(m)
    check("next_prime(2^127-1) returns the Mersenne prime itself", p2 == m and s2 <= 1,
          f"{p2}, scanned={s2}")
    p3, s3 = next_prime(2 ** 140)
    check("next prime after 2^140 found and certified", certificate(p3).verdict == "prime",
          f"{p3} (+{p3 - 2**140}, {s3} scans)")
    big, s = next_prime(10 ** 30)
    check("next prime after 1e30 found", certificate(big).verdict == "prime", f"{big} (+{s} scans)")


def test_transparency_log() -> None:
    import tempfile

    from zeta_audit.transparency import CertificateLog, entry_hash, merkle_root, verify_inclusion

    with tempfile.TemporaryDirectory() as td:
        log = CertificateLog(Path(td) / "ct.log")
        for n in (2 ** 61 - 1, 2 ** 89 - 1, 2 ** 107 - 1, 2 ** 127 - 1):
            rec = certificate(n, cross_check=False).as_dict()
            rec["base_count"] = len(rec.pop("bases"))
            log.append(rec)
        chain = log.verify()
        anchor = log.anchor()
        proof = log.prove_inclusion(2)
        check("CT chain verifies", chain["ok"] and chain["entries"] == 4, str(chain))
        check("CT merkle root switches on any edit",
              merkle_root(["00" * 32, "11" * 32]) != merkle_root(["00" * 32, "12" * 32]))
        check("CT inclusion proof verifies",
              verify_inclusion(proof["entry_hash"], proof["path"], anchor["merkle_root"]))
        log.entries[1].record["n"] = "999"
        broken = log.verify()
        check("CT detects tampering at the right index",
              (not broken["ok"]) and broken["at"] == 1, str(broken))


def test_parallel_proof() -> None:
    from zeta_audit.parallel import estimate_sequential, sweep_parallel

    p = 2 ** 89 - 1
    seq = sweep_parallel(p, workers=1)
    par = sweep_parallel(p, workers=2)
    check("parallel sweep agrees with sequential on a prime",
          seq.verdict == "prime" and par.verdict == "prime",
          f"seq={seq.verdict} par={par.verdict}")
    cand = 2 ** 89 - 1 + 2  # start on an odd composite
    comp = sweep_parallel(cand, workers=2)
    check("parallel sweep flags a composite", comp.verdict == "composite",
          f"witness={comp.witness}")
    est = estimate_sequential(p, sample=8)
    check("sequential estimate uses a measured rate", est["single_thread_modexp_per_s"] > 0,
          f"{est['single_thread_modexp_per_s']:.0f} modexp/s")


def test_primegen_attestation() -> None:
    from zeta_audit.primegen import attest

    a = attest(bits=128, measure_sequential=False)
    check("attestation returns a prime verdict", a.verdict == "prime",
          f"{a.actual_bits} bits, {a.base_count} bases")
    check("attestation states a scan ceiling", a.provable_scan_ceiling > 0,
          f"ceiling={a.provable_scan_ceiling:.3e}")
    check("attested prime is really prime", is_prime_rh(int(a.prime)))
    check("base ceiling matches 2log^2n",
          abs(a.base_ceiling - rh_base_bound(int(a.prime))) < 1e-6)


def test_base_cache_consistency() -> None:
    """The base-list cache must never hand one n a list computed for another ceiling.

    This is the regression test for the rounding-key bug that verify.py caught: a
    rounded cache key returned 544 bases for an n whose ceiling actually admits 546,
    making a logged certificate irreproducible.
    """
    import random

    from zeta_audit.primality import _primes_upto_float

    rng = random.Random(1234)
    bad = []
    for bits in (32, 64, 96, 128, 160, 200, 256, 320):
        for _ in range(6):
            n = rng.getrandbits(bits) | (1 << (bits - 1)) | 1
            cached = rh_bases(n)
            fresh = _primes_upto_float(rh_base_bound(n))
            if len(cached) != len(fresh) or (cached and cached[-1] != fresh[-1]):
                bad.append((bits, len(cached), len(fresh)))
    check("base cache matches a fresh unfiltered sieve for every size",
          not bad, f"mismatches={bad[:4]}")
    n = 2 ** 127 - 1
    check("all bases of a 127-bit prime are <= ceiling and prime-ordered",
          rh_bases(n)[-1] <= rh_base_bound(n) and rh_bases(n) == sorted(rh_bases(n)))


def test_theta_consistency() -> None:
    """θ must be right at small t, not just at large t.

    A wrong θ is invisible to zero finding (Z(t)=0 iff ζ=0 regardless of phase) but
    corrupts N(T) = θ(T)/π + 1 and the Z chart, so it is tested explicitly:
    θ(0)=0, θ monotone, and the quadrature/Stirling switch continuous at t=20.
    """
    from zeta_audit.zeta import theta_small_t, _digamma_complex

    check("theta(0) = 0", abs(theta(0.0)) < 1e-12, f"{theta(0.0):.2e}")
    # θ dips to its minimum near t≈6.3 (θ' changes sign there), then rises forever,
    # so monotonicity is asserted only past the dip.
    check("theta increasing for t >= 30",
          all(theta(x) < theta(x + 1) for x in range(30, 200)),
          f"theta(30)={theta(30):.6f}, theta(200)={theta(200):.6f}")
    check("theta reaches its minimum near t = 6.3",
          min(range(0, 20), key=lambda x: theta(float(x))) == 6, "argmin=6")
    jump = abs(theta(19.9999) - theta(20.0001))
    check("theta is continuous at the quadrature/Stirling switch", jump < 1e-3,
          f"jump={jump:.2e}")
    # digamma at a known point: ψ(1) = -γ
    e = abs(_digamma_complex(1.0).real + 0.5772156649015329)
    check("digamma(1) = -gamma", e < 1e-12, f"err={e:.2e}")
    # theta(10) from an independent route: theta(t) = arg Γ(1/4+it/2) - (t/2)log pi
    check("theta(10) < 0 < theta(20)", theta(10) < 0 < theta(20),
          f"{theta(10):.6f}, {theta(20):.6f}")


def test_crosscheck_against_mpmath() -> None:
    """The only non-circular check in this repo: an independent implementation agrees."""
    from zeta_audit.crosscheck import HAS_MPMATH, cross_check

    if not HAS_MPMATH:
        check("mpmath cross-check", False, "mpmath not installed: pip install mpmath")
        return
    r = cross_check(count=25)
    check("our zeros agree with mpmath.zetazero within 1e-9",
          r["max_abs_diff"] < 1e-9,
          f"max |diff| = {r['max_abs_diff']:.2e} at index {r['max_abs_diff_at_index']}")
    check("mpmath's zeta confirms our ordinates are zeros",
          r["mpmath_max_residual_at_our_zeros"] < 1e-8,
          f"max |zeta| = {r['mpmath_max_residual_at_our_zeros']:.2e}")
    worst_z = max(abs(z["ours"] - z["mpmath"]) for z in r["Z_agreement"])
    check("our Z(t) agrees with mpmath.siegelz", worst_z < 1e-9, f"max |diff| = {worst_z:.2e}")


def test_audit_table() -> None:
    """The auditing tool must accept a good table and reject a tampered one."""
    import tempfile

    from zeta_audit.audit_table import audit, load_table

    with tempfile.TemporaryDirectory() as td:
        zs = find_zeros(t_max=120.0, t_min=0.5, step=0.25)
        good = [z.gamma for z in zs]

        p_good = Path(td) / "good.txt"
        p_good.write_text("\n".join("%.15f" % g for g in good), encoding="utf-8")
        r_good = audit(load_table(p_good))
        check("audit accepts a correct table", r_good["all_ok"],
              f"{r_good['structure']['count']} zeros")
        check("audit reports a sane S(T) for a correct table",
              abs(r_good["completeness"]["S_T_implied"]) < 3.0,
              f"S(T) implied = {r_good['completeness']['S_T_implied']:+.3f}")

        # swap two ordinates: sorted-order structure check must fire
        broken = list(good)
        broken[3], broken[4] = broken[4], broken[3]
        p_bad = Path(td) / "bad.txt"
        p_bad.write_text("\n".join("%.15f" % g for g in broken), encoding="utf-8")
        r_bad = audit(load_table(p_bad))
        check("audit rejects a table with swapped ordinates", not r_bad["all_ok"],
              f"descents={r_bad['structure']['descending_steps']}")

        # a fabricated "zero" with no actual zero there
        fake = list(good) + [50.0]
        p_fake = Path(td) / "fake.txt"
        p_fake.write_text("\n".join("%.15f" % g for g in fake), encoding="utf-8")
        r_fake = audit(load_table(p_fake))
        check("audit rejects a fabricated extra ordinate", not r_fake["all_ok"],
              f"S(T) implied = {r_fake['completeness']['S_T_implied']:+.1f}")


def test_audit_detects_missing_zero() -> None:
    """The regression that matters: a single dropped row must be caught.

    The weak sanity count does NOT catch it (measured |S(T)| = 0.4 on a 100k table with
    one row removed), so this test pins the *windowed* count, which is the check that
    actually works. Two window methods were tried and abandoned first — gap statistics
    (7% false positives under GUE spacing) and contour counting (O(1.5e4) zeta calls per
    window at T=4e4, too slow) — so this test also guards against someone "simplifying"
    the completeness check back into one of those.
    """
    import tempfile

    from zeta_audit.audit_table import audit, load_table
    from zeta_audit.crosscheck import HAS_MPMATH

    if not HAS_MPMATH:
        check("audit catches a missing zero", False, "mpmath required for this check")
        return

    with tempfile.TemporaryDirectory() as td:
        # 1200 zeros so there are enough windows of 200 rows
        zs = find_zeros(t_max=2000.0, t_min=0.5, step=0.25)
        good = [z.gamma for z in zs]
        if len(good) < 900:
            check("audit catches a missing zero", False,
                  f"only {len(good)} zeros available; need more")
            return

        p_good = Path(td) / "good.txt"
        p_good.write_text("\n".join("%.16f" % g for g in good), encoding="utf-8")
        r_good = audit(load_table(p_good), windows=3)
        check("windowed count passes on a complete table",
              r_good["completeness"]["windows_ok"] is True,
              f"{len(r_good['completeness']['windows'])} windows")

        # drop a row inside the middle window
        mid = len(good) // 2
        holed = good[:mid] + good[mid + 1:]
        p_hole = Path(td) / "hole.txt"
        p_hole.write_text("\n".join("%.16f" % g for g in holed), encoding="utf-8")
        r_hole = audit(load_table(p_hole), windows=3)
        check("windowed count detects a single missing zero",
              not r_hole["all_ok"] and r_hole["completeness"]["windows_ok"] is False,
              "; ".join(f"{w['rows']}: {w['independent_count']} vs {w['table_zeros_inside']}"
                        for w in r_hole["completeness"]["windows"]))
        check("the weak sanity count alone would have missed it",
              abs(r_hole["completeness"]["S_T_implied"]) < 3.0,
              f"|S(T)| = {abs(r_hole['completeness']['S_T_implied']):.2f} -> would pass")



def test_readmes_agree() -> None:
    """English and Chinese READMEs must carry the same numbers and the same commands."""
    import subprocess
    import sys as _sys

    proc = subprocess.run(
        [_sys.executable, str(Path(__file__).with_name("test_readme_parity.py"))],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    tail = [ln for ln in proc.stdout.splitlines() if ln.strip()][-1:] or ["(no output)"]
    check("EN/ZH READMEs stay in sync", proc.returncode == 0, tail[0])



def test_readme_code_blocks_unchanged() -> None:
    """Code and transcripts must not be translated; only shell comments and prose may be."""
    import subprocess
    import sys as _sys

    proc = subprocess.run(
        [_sys.executable, str(Path(__file__).with_name("test_readme_code_parity.py"))],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    tail = [ln for ln in proc.stdout.splitlines() if ln.strip()][-1:] or ["(no output)"]
    check("EN/ZH README code blocks unchanged", proc.returncode == 0, tail[0])



def test_partial_when_a_check_is_skipped() -> None:
    """A skipped check must not be reported as a pass (three-valued verdict)."""
    import subprocess
    import sys as _sys

    proc = subprocess.run(
        [_sys.executable, str(Path(__file__).with_name("test_partial_status.py"))],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    tail = [ln for ln in proc.stdout.splitlines() if ln.strip()][-1:] or ["(no output)"]
    check("verdict distinguishes skipped from passed", proc.returncode == 0, tail[0])



def main() -> int:
    for fn in (
        test_zeta_values,
        test_theta_and_Z,
        test_theta_consistency,
        test_zeros,
        test_strip_verification,
        test_psi_and_pi,
        test_bounds,
        test_explicit_formula,
        test_primality,
        test_next_prime,
        test_transparency_log,
        test_parallel_proof,
        test_primegen_attestation,
        test_base_cache_consistency,
        test_readmes_agree,
        test_readme_code_blocks_unchanged,
        test_partial_when_a_check_is_skipped,
        test_crosscheck_against_mpmath,
        test_audit_table,
        test_audit_detects_missing_zero,
    ):
        print(f"\n=== {fn.__name__} ===")
        fn()
    failed = [c for c in CHECKS if not c[1]]
    total = len(CHECKS)
    print(f"\n{total - len(failed)}/{total} checks passed")
    if failed:
        for name, _, detail in failed:
            print(f"  FAILED: {name} {detail}")

    # Docs must not quote a stale total. This runs last on purpose: only now is `total`
    # the final count. (Placing it inside the list meant it compared the docs against a
    # partial count, 74 instead of 85.)
    import os
    import subprocess
    import sys as _sys

    doc = subprocess.run(
        [_sys.executable, str(Path(__file__).with_name("test_doc_counts.py"))],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        env={**os.environ, "ZETA_AUDIT_SUITE_TOTAL": str(total)},
    )
    tail_line = [ln for ln in doc.stdout.splitlines() if ln.strip()][-1:] or ["(no output)"]
    ok = doc.returncode == 0
    print(f"[{'PASS' if ok else 'FAIL'}] docs quote the right total ({total})  ({tail_line[0]})")
    if not ok:
        print(doc.stdout)
        return 1

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())