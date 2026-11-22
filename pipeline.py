"""End-to-end pipeline: produce every artifact the report cites.

Run:  python pipeline.py            (writes into out/)
      python pipeline.py --fast     (smaller heights, ~seconds)

Artifacts
  out/zeros_1000.json      verified zero table + audit + published-value delta
  out/strip_verify.json    argument-principle RH verification (two heights)
  out/bounds.json          Schoenfeld psi/pi bars, Cramer gap ceiling, pi vs R
  out/certificates.json    prime certificates at 64..1024 bits + benchmark
  out/summary.json         the one-page numbers the report quotes
  out/*.svg                charts
"""

from __future__ import annotations

import argparse
import json
import math
import os
import time
from pathlib import Path

from zetaedge.bounds import gap_audit, pi_error_audit
from zetaedge.certify import audit_certifier, certificate, count_zeros_strip, next_prime, verify_strip
from zetaedge.explicit import audit_pi_bound, audit_psi_bound, zero_sum_convergence
from zetaedge.plot import Z_chart, error_chart, zeros_chart
from zetaedge.transparency import CertificateLog, verify_inclusion
from zetaedge.parallel import estimate_sequential, sweep_parallel
from zetaedge.primality import rh_bases, rh_base_bound
from zetaedge.zeta import Z, n_zeros_asymptotic, theta
from zetaedge.zeros import audit, check_against_known, find_zeros

OUT = Path(__file__).with_name("out")


def dump(name: str, obj) -> Path:
    OUT.mkdir(exist_ok=True)
    p = OUT / name
    p.write_text(json.dumps(obj, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print(f"  wrote {p.relative_to(OUT.parent)}  ({p.stat().st_size/1024:.1f} KB)")
    return p


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fast", action="store_true")
    a = ap.parse_args(argv)
    t_all = time.time()
    OUT.mkdir(exist_ok=True)
    summary: dict = {}

    # ---------------------------------------------------------------- zeros
    t0 = time.time()
    T = 1000.0 if not a.fast else 300.0
    zs = find_zeros(t_max=T, t_min=0.5, step=0.25)
    gammas = [z.gamma for z in zs]
    z_audit = audit(zs, T)
    known = check_against_known(zs)
    zeros_chart(gammas, OUT / "zeros.svg", T)
    dump("zeros_%d.json" % int(T), {
        "audit": z_audit,
        "published_delta": known,
        "gammas": gammas,
    })
    summary["zeros"] = {
        "height": T,
        "count": len(zs),
        "smooth_N_T": n_zeros_asymptotic(T),
        "S_T": z_audit["S_T"],
        "max_residual": z_audit["max_residual"],
        "max_delta_vs_published": known["max_abs_error"],
        "published_check_pass": known["pass"],
        "elapsed_s": round(time.time() - t0, 2),
    }

    # ------------------------------------------------------- strip theorem
    t0 = time.time()
    strip_rows = []
    for height in ((60.0, 100.0) if a.fast else (100.0, 300.0, 600.0)):
        res = verify_strip(height)
        strip_rows.append(res)
        print(f"  strip T={height:g}: line={res['zeros_on_line']} strip={res['zeros_in_strip']} match={res['match']}")
    dump("strip_verify.json", {"rows": strip_rows, "elapsed_s": round(time.time() - t0, 2)})
    summary["strip_verification"] = {
        "heights": [r["T"] for r in strip_rows],
        "all_match": all(r["match"] for r in strip_rows),
        "max_height_verified": max(r["T"] for r in strip_rows if r["match"]),
        "elapsed_s": round(time.time() - t0, 2),
    }

    # ----------------------------------------------------------- bounds
    t0 = time.time()
    x_max = 10_000_000 if not a.fast else 1_000_000
    psi = audit_psi_bound(x_max)
    pi = audit_pi_bound(min(x_max, 2_000_000))
    gaps = gap_audit(x_max)
    perr = pi_error_audit(min(x_max, 2_000_000), stride=499)
    dump("bounds.json", {
        "schoenfeld_psi": psi,
        "schoenfeld_pi": pi,
        "cramer_gap": {k: v for k, v in gaps.items() if k != "records"},
        "gap_records": gaps["records"],
        "pi_vs_R": {k: v for k, v in perr.items() if k != "rows"},
        "pi_samples": perr["rows"][:40],
    })
    summary["bounds"] = {
        "x_max": x_max,
        "psi_max_ratio": psi["max_ratio"],
        "psi_holds": psi["holds"],
        "pi_max_ratio": pi["max_ratio"],
        "pi_holds": pi["holds"],
        "gap_max_ratio": gaps["max_ratio_to_ceiling"],
        "gap_holds": gaps["holds"],
        "pi_R_max_ratio": perr["max_ratio_R"],
        "pi_li_max_ratio": perr["max_ratio_li"],
        "elapsed_s": round(time.time() - t0, 2),
    }

    # ------------------------------------------------- explicit formula
    t0 = time.time()
    rows = zero_sum_convergence(10 ** 5, gammas, gamma_counts=(50, 100, 200, 400, 600))
    error_chart(rows, OUT / "explicit_error.svg")
    dump("explicit_formula.json", {
        "x": 10 ** 5,
        "rows": rows,
        "note": "error at fixed x falls as more zeros enter the sum (zeros supply the √x budget)",
    })
    summary["explicit_formula"] = {
        "x": 10 ** 5,
        "first_error": rows[0]["error"],
        "last_error": rows[-1]["error"],
        "zeros_used": rows[-1]["zeros"],
        "elapsed_s": round(time.time() - t0, 2),
    }

    # ------------------------------------------------------ certificates
    t0 = time.time()
    certs = []
    for bits in (64, 96, 128, 192, 256, 384, 521):
        start = (1 << bits) - 1
        p, scanned = next_prime(start)
        cert = certificate(p, cross_check=bits <= 62)
        rec = cert.as_dict()
        # keep the base list out of the artifact (it is regenerable); keep the proof skeleton
        rec["base_count"] = len(cert.bases)
        rec["bases_preview"] = cert.bases[:16]
        rec["bases_tail"] = cert.bases[-4:]
        rec.pop("bases", None)
        rec["searched_from"] = str(start)
        rec["candidates_scanned"] = scanned
        certs.append(rec)
        print(f"  cert {bits:>3} bits: {cert.verdict}  bases={len(cert.bases)}  scanned={scanned}")
    t_prime = time.time()
    header = "NINETYNINETYMILLION"
    p, scanned = next_prime(10 ** 40)
    cert_np = certificate(p)
    np_rec = cert_np.as_dict()
    np_rec["base_count"] = len(cert_np.bases)
    np_rec["bases_preview"] = cert_np.bases[:16]
    np_rec.pop("bases", None)
    dump("certificates.json", {
        "generated_primes": certs,
        "next_prime_demo": {
            "start": str(10 ** 40),
            "next": str(p),
            "delta": str(p - 10 ** 40),
            "scanned": scanned,
            "certificate": np_rec,
            "elapsed_s": round(time.time() - t_prime, 2),
        },
    })
    summary["certificates"] = {
        "verdicts": {str(c["bits"]): c["verdict"] for c in certs},
        "base_counts": {str(c["bits"]): c["base_count"] for c in certs},
        "ceilings": {str(c["bits"]): round(c["base_bound"]) for c in certs},
        "elapsed_s": round(time.time() - t0, 2),
    }

    # --------------------------------------------------------- benchmark
    t0 = time.time()
    bench = audit_certifier(bits_list=(64, 96, 128, 192, 256), samples=4)
    dump("certifier_benchmark.json", bench)
    summary["certifier_benchmark"] = {
        "rows": bench["rows"],
        "elapsed_s": round(time.time() - t0, 2),
    }

    # ------------------------------------------------- transparency log
    t0 = time.time()
    log_path = OUT / "ct.log"
    if log_path.exists():
        log_path.unlink()
    log = CertificateLog(log_path)
    import secrets

    for bits in (64, 128, 192, 256, 384, 512):
        start = secrets.randbits(bits) | (1 << (bits - 1)) | 1
        p, scanned = next_prime(start)
        rec = certificate(p, cross_check=False).as_dict()
        rec["base_count"] = len(rec.pop("bases"))
        rec["candidates_scanned"] = scanned
        rec["requested_bits"] = bits
        log.append(rec)
    chain = log.verify()
    anchor = log.anchor()
    proof = log.prove_inclusion(3)
    inclusion_ok = verify_inclusion(proof["entry_hash"], proof["path"], anchor["merkle_root"])
    dump("ct_anchor.json", {
        "chain_verify": chain,
        "anchor": anchor,
        "sample_inclusion_proof": proof,
        "inclusion_verified": inclusion_ok,
        "log_file": "ct.log",
    })
    print(f"  CT log: {chain['entries']} entries, chain ok={chain['ok']}, inclusion ok={inclusion_ok}")
    summary["transparency"] = {
        "entries": chain["entries"],
        "chain_ok": chain["ok"],
        "merkle_root": anchor["merkle_root"],
        "inclusion_verified": inclusion_ok,
        "elapsed_s": round(time.time() - t0, 2),
    }

    # ------------------------------------------- parallel proof at scale
    t0 = time.time()
    par_rows = []
    import secrets as _s

    for bits in ((512,) if a.fast else (512, 1024)):
        start = _s.randbits(bits) | (1 << (bits - 1)) | 1
        p, scanned = next_prime(start)
        est = estimate_sequential(p)
        r = sweep_parallel(p)
        row = r.as_dict()
        row["base_ceiling"] = round(rh_base_bound(p), 1)
        row["candidates_scanned"] = scanned
        row.update(est)
        row["speedup"] = (
            round(est["sequential_estimate_s"] / r.elapsed_s, 1)
            if r.elapsed_s and est["sequential_estimate_s"] else None
        )
        par_rows.append(row)
        print(f"  parallel proof {bits} bits: {r.verdict} in {r.elapsed_s:.1f}s "
              f"({r.bases_tested} bases, {r.workers} workers, "
              f"seq est {est['sequential_estimate_s']:.0f}s -> {row['speedup']}x)")
    dump("parallel_proof.json", {"rows": par_rows, "cpus": os.cpu_count()})
    summary["parallel_proof"] = {"rows": par_rows, "elapsed_s": round(time.time() - t0, 2)}

    # -------------------------------------------------------- Z chart
    ts = [g for g in (i * 0.05 for i in range(0, 2000))]
    zvals = [Z(t) for t in ts]
    Z_chart(ts, zvals, OUT / "Z_0_100.svg", "Z(t) over t in [0, 100]: sign changes = zeros on the line")

    # --------------------------------------------- product surface: rhprime
    t0 = time.time()
    from zetaedge.primegen import batch as attest_batch

    att = attest_batch((128, 256, 512), log_path=OUT / "ct_primegen.log", out_dir=None,
                       reset_log=True)
    dump("attestations.json", att)
    # individual attestation files are the product surface a buyer receives
    for row in att["rows"]:
        dump(f"attestation_{row['requested_bits']}.json", row)
    summary["rhprime_attestations"] = {
        "count": len(att["rows"]),
        "rows": [
            {k: r[k] for k in ("requested_bits", "actual_bits", "delta_from_start",
                               "candidates_scanned", "base_count", "verdict",
                               "sequential_estimate_s", "elapsed_s")}
            for r in att["rows"]
        ],
        "log_chain_ok": att.get("chain", {}).get("ok"),
        "log_merkle_root": att.get("anchor", {}).get("merkle_root"),
        "elapsed_s": round(time.time() - t0, 2),
    }
    print(f"  rhprime: {len(att['rows'])} attestations, log chain ok="
          f"{att.get('chain', {}).get('ok')}")

    # ------------------------------------------------- mpmath cross-check
    t0 = time.time()
    from zetaedge.crosscheck import cross_check

    cc = cross_check(count=50)
    dump("crosscheck.json", cc)
    print(f"  cross-check: {cc.get('verdict')} (max |diff| = "
          f"{cc.get('max_abs_diff', float('nan')):.2e})")
    summary["crosscheck"] = {
        "available": cc.get("available"),
        "compared": cc.get("compared"),
        "max_abs_diff": cc.get("max_abs_diff"),
        "verdict": cc.get("verdict"),
        "elapsed_s": round(time.time() - t0, 2),
    }

    # -------------------------------------- the table audit tool on our own output
    t0 = time.time()
    from zetaedge.audit_table import audit as audit_table

    audit_path = OUT / "self_audit_input.txt"
    audit_path.write_text("\n".join("%.15f" % g for g in gammas), encoding="utf-8")
    self_audit = audit_table(
        __import__("zetaedge.audit_table", fromlist=["load_table"]).load_table(audit_path)
    )
    dump("self_audit.json", self_audit)
    print(f"  zeta-audit on our own table: all_ok={self_audit['all_ok']}")
    summary["table_audit_demo"] = {
        "target": "out/self_audit_input.txt (our own zero table)",
        "all_ok": self_audit["all_ok"],
        "structure_ok": self_audit["structure"]["ok"],
        "our_max_residual": self_audit["residuals"]["our_max_residual"],
        "mpmath_max_residual": self_audit["residuals"]["mpmath_max_residual"],
        "independent_max_diff": self_audit["independent"].get("max_abs_diff_vs_mpmath"),
        "S_T_implied": self_audit["completeness"]["S_T_implied"],
        "elapsed_s": round(time.time() - t0, 2),
    }

    summary["total_elapsed_s"] = round(time.time() - t_all, 1)

    # --------------------------------- third-party verification transcript
    t0 = time.time()
    import contextlib
    import io

    import verify as verifier  # local script, run as a black box

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        verify_code = verifier.main([
            "--log", str(OUT / "ct.log"),
            "--anchor", str(OUT / "ct_anchor.json"),
            "--tee", str(OUT / "verify_output.txt"),
        ])
    transcript = buf.getvalue().strip().splitlines()
    print(f"  verify.py exit={verify_code}: {transcript[-1] if transcript else '(no output)'}")
    summary["verification"] = {
        "exit_code": verify_code,
        "all_passed": verify_code == 0,
        "transcript": "out/verify_output.txt",
        "elapsed_s": round(time.time() - t0, 1),
    }
    summary["artifacts"] = sorted(p.name for p in OUT.iterdir() if p.is_file())
    dump("summary.json", summary)
    print(f"\ntotal {summary['total_elapsed_s']}s -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())