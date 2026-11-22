"""Append-only, hash-chained log of prime certificates ("RH certificate transparency").

Why this is the sellable shape of the post-proof dividend: a *proof* is only worth
money to an auditor if the auditor can re-check it without re-running your code.
So every certificate is written into a tamper-evident log:

  entry_hash = SHA256(prev_hash || canonical(record))
  merkle_root over the day's entry hashes = the 32-byte anchor you publish

Any third party can (1) recompute a single certificate from n and the theorem,
(2) recompute the chain, (3) compare the anchor against what you published. No
trust in the vendor, no access to the vendor's infrastructure.

Pure stdlib, ~140 lines, no dependencies.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from pathlib import Path

GENESIS = "0" * 64


def canonical(record: dict) -> bytes:
    return json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def entry_hash(prev: str, record: dict) -> str:
    h = hashlib.sha256()
    h.update(prev.encode())
    h.update(b"|")
    h.update(canonical(record))
    return h.hexdigest()


def merkle_root(hashes: list[str]) -> str:
    """Binary Merkle root over hex leaf hashes; odd leaf is promoted unchanged."""
    if not hashes:
        return GENESIS
    layer = [bytes.fromhex(h) for h in hashes]
    while len(layer) > 1:
        if len(layer) % 2:
            layer.append(layer[-1])
        layer = [hashlib.sha256(layer[i] + layer[i + 1]).digest() for i in range(0, len(layer), 2)]
    return layer[0].hex()


@dataclass
class LogEntry:
    seq: int
    prev_hash: str
    record: dict
    hash: str
    ts: float = field(default_factory=time.time)

    def as_dict(self) -> dict:
        return {"seq": self.seq, "prev": self.prev_hash, "record": self.record,
                "hash": self.hash, "ts": self.ts}


class CertificateLog:
    """JSONL append-only log with an in-memory index and Merkle anchors."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.entries: list[LogEntry] = []
        if self.path.exists():
            self._load()

    # -------------------------------------------------------------- io
    def _load(self) -> None:
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            raw = json.loads(line)
            self.entries.append(LogEntry(raw["seq"], raw["prev"], raw["record"], raw["hash"], raw["ts"]))

    def append(self, record: dict) -> LogEntry:
        prev = self.entries[-1].hash if self.entries else GENESIS
        h = entry_hash(prev, record)
        e = LogEntry(seq=len(self.entries), prev_hash=prev, record=record, hash=h)
        self.entries.append(e)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(e.as_dict(), ensure_ascii=False) + "\n")
        return e

    # ---------------------------------------------------------- verify
    def verify(self) -> dict:
        """Recompute the whole chain; report the first break, if any."""
        prev = GENESIS
        for i, e in enumerate(self.entries):
            if e.seq != i:
                return {"ok": False, "reason": "sequence gap", "at": i}
            if e.prev_hash != prev:
                return {"ok": False, "reason": "prev hash mismatch", "at": i}
            if entry_hash(prev, e.record) != e.hash:
                return {"ok": False, "reason": "entry hash mismatch", "at": i}
            prev = e.hash
        return {"ok": True, "entries": len(self.entries), "head": prev}

    def anchor(self) -> dict:
        """Publishable 32-byte commitment: Merkle root + head + count."""
        hashes = [e.hash for e in self.entries]
        return {
            "entries": len(hashes),
            "head": hashes[-1] if hashes else GENESIS,
            "merkle_root": merkle_root(hashes),
            "ts": time.time(),
        }

    def prove_inclusion(self, seq: int) -> dict:
        """Merkle audit path for one entry (what an auditor needs to check a single record)."""
        if not 0 <= seq < len(self.entries):
            raise IndexError(seq)
        layer = [bytes.fromhex(e.hash) for e in self.entries]
        idx = seq
        path = []
        while len(layer) > 1:
            if len(layer) % 2:
                layer.append(layer[-1])
            sib = idx ^ 1
            path.append({"side": "right" if sib > idx else "left", "hash": layer[sib].hex()})
            layer = [hashlib.sha256(layer[i] + layer[i + 1]).digest() for i in range(0, len(layer), 2)]
            idx //= 2
        return {"seq": seq, "entry_hash": self.entries[seq].hash, "path": path,
                "root": layer[0].hex(), "entries": len(self.entries)}


def verify_inclusion(entry_hash_hex: str, path: list[dict], root_hex: str) -> bool:
    cur = bytes.fromhex(entry_hash_hex)
    for node in path:
        sib = bytes.fromhex(node["hash"])
        cur = hashlib.sha256(cur + sib).digest() if node["side"] == "right" else hashlib.sha256(sib + cur).digest()
    return cur.hex() == root_hex