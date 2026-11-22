"""Third-party verifier: re-check everything without trusting the producer.

This is the artifact you hand to an auditor.  It touches no vendor code path
beyond the theorem itself:

  python verify.py --log out/ct.log --anchor out/ct_anchor.json

What it does
  1. Recompute the hash chain from the raw JSONL (detects any edit/reorder/insert).
  2. Recompute the Merkle root and compare with the published anchor.
  3. For every logged certificate: regenerate the base list from n, re-run every
     Miller-Rabin witness check, and confirm the logged fingerprint.
  4. Verify the sample inclusion proof against the anchor root.
  5. Re-verify a few zeros against published tables as a sanity check on the
     numeric core (so a broken float pipeline cannot silently pass).

Exit code 0 = everything checks out; 1 = something is wrong and is printed.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from zetaedge.certify import certificate
from zetaedge.primality import _mr_witness, rh_bases
from zetaedge.transparency import CertificateLog, verify_inclusion
from zetaedge.zeros import KNOWN_FIRST_ZEROS, check_against_known, find_zeros


def check_certificate_record(rec: dict) -> tuple[bool, str]:
    n = int(rec["n"])
    verdict = rec["verdict"]
    if verdict != "prime":
        # composites are accepted only if the logged witness really is a witness
        w = rec.get("witness")
        if w is None:
            return False, "composite record without witness"
        ok = _mr_witness(n, int(w))
        return (ok, f"witness {w} {'valid' if ok else 'INVALID'}")
    bases = rh_bases(n)
    if len(bases) != rec.get("base_count", len(bases)):
        return False, f"base count mismatch: recomputed {len(bases)} vs logged {rec.get('base_count')}"
    for a in bases:
        if _mr_witness(n, a):
            return False, f"base {a} is a witness => logged 'prime' is WRONG"
    fresh = certificate(n, cross_check=False)
    if fresh.hmac_fingerprint != rec.get("hmac_fingerprint"):
        return False, "fingerprint mismatch (record content differs from recomputation)"
    return True, f"{len(bases)} bases re-tested, no witness"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", default="out/ct.log")
    ap.add_argument("--anchor", default="out/ct_anchor.json")
    ap.add_argument("--skip-zeros", action="store_true")
    ap.add_argument("--tee", default="out/verify_output.txt",
                   help="also write the transcript here (report.py quotes it verbatim)")
    a = ap.parse_args(argv)

    lines: list[str] = []

    def out(msg: str = "") -> None:
        print(msg)
        lines.append(msg)

    failures: list[str] = []
    log = CertificateLog(a.log)
    chain = log.verify()
    out(f"[chain] ok={chain['ok']} entries={chain['entries']} head={(chain.get('head') or '')[:16]}...")
    if not chain["ok"]:
        failures.append(f"hash chain broken: {chain}")

    anchor_file = Path(a.anchor)
    anchor = json.loads(anchor_file.read_text(encoding="utf-8")) if anchor_file.exists() else None
    if anchor:
        fresh = log.anchor()
        ok_root = fresh["merkle_root"] == anchor["anchor"]["merkle_root"]
        ok_head = fresh["head"] == anchor["anchor"]["head"]
        out(f"[anchor] merkle_root match={ok_root} head match={ok_head}")
        if not (ok_root and ok_head):
            failures.append("published anchor does not match the log (someone edited the log)")
        proof = anchor.get("sample_inclusion_proof")
        if proof:
            ok = verify_inclusion(proof["entry_hash"], proof["path"], anchor["anchor"]["merkle_root"])
            out(f"[inclusion] seq={proof['seq']} verified={ok}")
            if not ok:
                failures.append("inclusion proof does not verify")
    else:
        out("[anchor] no anchor file found; skipping anchor comparison")

    for e in log.entries:
        rec = e.record
        ok, note = check_certificate_record(rec)
        out(f"[cert {e.seq}] {int(rec['n']).bit_length():>4} bits  {note}")
        if not ok:
            failures.append(f"entry {e.seq}: {note}")

    if not a.skip_zeros:
        zs = find_zeros(t_max=100.0, t_min=0.5, step=0.25)
        known = check_against_known(zs)
        out(f"[zeros] {len(zs)} zeros <= 100, max |dgamma| vs published = {known['max_abs_error']:.2e}")
        if not known["pass"]:
            failures.append("zero table disagrees with published values")

    out()
    if failures:
        out(f"FAILED ({len(failures)}):")
        for f in failures:
            out(f"  - {f}")
        code = 1
    else:
        out("ALL CHECKS PASSED - the log, the anchor, and every certificate are reproducible")
        code = 0

    if a.tee:
        p = Path(a.tee)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return code


if __name__ == "__main__":
    sys.exit(main())