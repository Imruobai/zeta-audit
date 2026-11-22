"""Command line interface: `python -m zetaedge <command>`."""

from __future__ import annotations

import argparse
import json
import sys
import time

from . import __version__
from .bounds import gap_audit, pi_error_audit
from .certify import audit_certifier, certificate, count_zeros_strip, next_prime, verify_strip
from .explicit import audit_pi_bound, audit_psi_bound
from .zeros import audit, check_against_known, find_zeros


def _dump(obj) -> None:
    print(json.dumps(obj, indent=2, ensure_ascii=False, default=str))


def cmd_zeros(a) -> int:
    t0 = time.time()
    zs = find_zeros(t_max=a.t_max, t_min=a.t_min, step=a.step)
    out = {
        "elapsed_s": round(time.time() - t0, 3),
        "audit": audit(zs, a.t_max),
        "known_check": check_against_known(zs),
        "first": [z.as_dict() for z in zs[: min(10, len(zs))]],
        "last": [z.as_dict() for z in zs[-3:]],
    }
    if a.json:
        _dump(out)
    else:
        print(f"zeros found : {out['audit']['zeros_found']}")
        print(f"max residual: {out['audit']['max_residual']:.3e}")
        print(f"vs published: max |Δγ| = {out['known_check']['max_abs_error']:.3e} "
              f"({'PASS' if out['known_check']['pass'] else 'CHECK'})")
        print(f"elapsed     : {out['elapsed_s']}s")
    if a.dump:
        with open(a.dump, "w", encoding="utf-8") as fh:
            json.dump([z.as_dict() for z in zs], fh, indent=1)
        print(f"wrote {a.dump}")
    return 0


def cmd_strip(a) -> int:
    t0 = time.time()
    out = verify_strip(a.t_max, step=a.step)
    out["elapsed_s"] = round(time.time() - t0, 3)
    _dump(out)
    return 0 if out["match"] else 1


def cmd_certify(a) -> int:
    n = int(a.n, 0) if not a.n.startswith("0x") else int(a.n, 16)
    cert = certificate(n)
    print(cert.block())
    return 0 if cert.verdict == "prime" else 1


def cmd_nextprime(a) -> int:
    n = int(a.n, 0) if not a.n.startswith("0x") else int(a.n, 16)
    t0 = time.time()
    p, scanned = next_prime(n)
    cert = certificate(p)
    out = {
        "input": str(n),
        "next_prime": str(p),
        "delta": str(p - n),
        "candidates_scanned": scanned,
        "elapsed_s": round(time.time() - t0, 2),
        "certificate": cert.as_dict(),
    }
    if a.json:
        _dump(out)
    else:
        print(cert.block())
        print(f"start   : {n}")
        print(f"next    : {p}  (+{p-n})")
        print(f"scanned : {scanned} candidates in {out['elapsed_s']}s")
    return 0


def cmd_bounds(a) -> int:
    t0 = time.time()
    psi = audit_psi_bound(a.x_max)
    pi = audit_pi_bound(min(a.x_max, a.pi_max))
    gaps = gap_audit(a.x_max)
    perr = pi_error_audit(min(a.x_max, a.pi_max))
    _dump({
        "elapsed_s": round(time.time() - t0, 2),
        "schoenfeld_psi": psi,
        "schoenfeld_pi": pi,
        "prime_gap_ceiling": {k: v for k, v in gaps.items() if k != "records"},
        "gap_records": gaps["records"],
        "pi_vs_R": {k: v for k, v in perr.items() if k != "rows"},
    })
    return 0


def cmd_audit(a) -> int:
    _dump(audit_certifier(bits_list=tuple(int(b) for b in a.bits.split(",")), samples=a.samples))
    return 0


def cmd_crosscheck(a) -> int:
    from .crosscheck import cross_check

    r = cross_check(count=a.count)
    _dump(r)
    return 0 if r.get("available") and r.get("max_abs_diff", 1.0) < 1e-9 else 1


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="zetaedge",
        description="zero verification (unconditional) and labelled conditional prime certificates",
    )
    p.add_argument("--version", action="version", version=f"zetaedge {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    z = sub.add_parser("zeros", help="find and audit zeros on the critical line")
    z.add_argument("--t-max", type=float, default=1000.0)
    z.add_argument("--t-min", type=float, default=6.0)
    z.add_argument("--step", type=float, default=0.25)
    z.add_argument("--json", action="store_true")
    z.add_argument("--dump", default="")
    z.set_defaults(func=cmd_zeros)

    s = sub.add_parser("strip", help="argument-principle RH verification up to height T")
    s.add_argument("--t-max", type=float, default=100.0)
    s.add_argument("--step", type=float, default=0.01)
    s.set_defaults(func=cmd_strip)

    c = sub.add_parser("certify", help="emit a prime certificate for n")
    c.add_argument("n")
    c.set_defaults(func=cmd_certify)

    nx = sub.add_parser("nextprime", help="next prime >= n plus its certificate")
    nx.add_argument("n")
    nx.add_argument("--json", action="store_true")
    nx.set_defaults(func=cmd_nextprime)

    b = sub.add_parser("bounds", help="audit the RH-conditional error bars (labelled per-bound)")
    b.add_argument("--x-max", type=int, default=10_000_000)
    b.add_argument("--pi-max", type=int, default=2_000_000)
    b.set_defaults(func=cmd_bounds)

    au = sub.add_parser("audit", help="benchmark the certifier over key sizes")
    au.add_argument("--bits", default="64,128,256")
    au.add_argument("--samples", type=int, default=4)
    au.set_defaults(func=cmd_audit)

    cc = sub.add_parser("crosscheck", help="compare zeros and Z(t) against mpmath")
    cc.add_argument("--count", type=int, default=25)
    cc.set_defaults(func=cmd_crosscheck)
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())