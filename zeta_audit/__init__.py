"""zeta-edge: verifiable ζ(s) / prime-distribution reference.

Two things live here, with different epistemic status:

  * unconditional: ζ/θ/Z evaluation, zero finding with residuals, the
    argument-principle strip count, and the redundant ψ/R cross-checks;
  * conditional: the Schoenfeld / Cramér error bars (on RH) and the
    Miller–Rabin base bound (on ERH/GRH, not RH).

Anything conditional prints the hypothesis it used, so a reader can never
mistake it for a theorem.
"""

from .zeta import zeta, zeta_half, theta, Z, n_zeros_asymptotic
from .zeros import Zero, find_zeros, audit, check_against_known
from .primality import is_prime_rh, is_prime_13, rh_bases, Certificate, certify
from .certify import (
    verify_strip,
    count_zeros_strip,
    certificate,
    next_prime,
    audit_certifier,
    PrimeCertificate,
)
from .transparency import CertificateLog, merkle_root, entry_hash, verify_inclusion
from .primegen import attest, batch as attest_batch
from .parallel import sweep_parallel, estimate_sequential

__version__ = "0.4.1"


def __getattr__(name):
    """Lazy re-exports for the modules that are also runnable as ``-m`` entry points.

    Importing ``audit_table``/``crosscheck`` eagerly here makes
    ``python -m zeta_audit.audit_table`` emit a RuntimeWarning (runpy sees the module
    already imported before it executes it). Deferring them to first access keeps
    ``zeta_audit.audit_zero_table`` working as public API and the CLI clean.
    """
    if name in ("audit_zero_table", "load_table"):
        from . import audit_table

        return getattr(audit_table, "audit" if name == "audit_zero_table" else "load_table")
    if name == "cross_check":
        from .crosscheck import cross_check

        return cross_check
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "zeta",
    "zeta_half",
    "theta",
    "Z",
    "n_zeros_asymptotic",
    "Zero",
    "find_zeros",
    "audit",
    "check_against_known",
    "is_prime_rh",
    "is_prime_13",
    "rh_bases",
    "Certificate",
    "certify",
    "verify_strip",
    "count_zeros_strip",
    "certificate",
    "next_prime",
    "audit_certifier",
    "PrimeCertificate",
    "CertificateLog",
    "merkle_root",
    "entry_hash",
    "verify_inclusion",
    "attest",
    "attest_batch",
    "sweep_parallel",
    "estimate_sequential",
    "audit_zero_table",
    "load_table",
    "cross_check",
]