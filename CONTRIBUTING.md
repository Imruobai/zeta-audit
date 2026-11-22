# Contributing

Thanks for looking. This project has one job — audit a zero table and report honestly — so
contributions are judged by whether they make that job more correct or more trustworthy.

## The most useful thing you can send

**A zero table that this tool gets wrong.** Either:

- a table it passes that is actually broken (a false negative), or
- a table it fails that is actually fine (a false positive).

Open an issue with the file (or a sha256 plus a few lines if the file is large), the
command you ran, and the output. Reproducibility matters more than the size of the finding.

## Bugs

1. Open an issue describing the wrong output and the input that produced it.
2. A fixing pull request should include a test that **fails on the base commit** and passes
   with the change. `tests/run_all.py` is the entry point; individual concerns live in
   their own files under `tests/`.

## Code changes

```bash
git clone https://github.com/Imruobai/zeta-audit
cd zeta-audit
pip install -e ".[crosscheck]"
python tests/run_all.py     # must be fully green
python verify.py            # must exit 0
```

House rules that exist for a reason, please do not relax them:

- **A skipped check is not a pass.** Without mpmath the independent and windowed checks
  report `PARTIAL` and exit 2. This is load-bearing: the tool's entire claim is that it can
  find a *missing* zero, and only those checks can.
- **Transcripts in the README are real.** If you change program output, regenerate the
  README block from an actual run. `tests/test_readme_code_parity.py` fails on a hand-edited
  transcript.
- **Labels for conditional statements stay.** Schoenfeld and Cramér bounds are labelled
  "conditional on RH"; the Miller–Rabin base bound is labelled "ERH/GRH, not RH". Both are
  stated where they appear, in code and in the block that prints them. Do not simplify them
  away.
- **Do not describe this repo as "certified" or "rigorous".** The arithmetic is float; Arb
  gives enclosures and this does not. The README says so and that honesty is the point.

## Adding a zero-table format

`load_table` in `zeta_audit/audit_table.py` auto-detects formats. If yours is not parsed:

1. Add a case to `load_table` and a fixture under `tests/`.
2. Keep the parser tolerant but **never silently skip a line**. A format the tool half-reads
   is worse than one it refuses, because a partial parse can look like a passing audit.

## What will be declined

- Claims about the Riemann Hypothesis itself. This tool audits data; it says nothing about
  whether RH is true, and pull requests that blur that will be closed.
- Speed optimisations to the ζ evaluator that do not preserve the measured agreement with
  mpmath (currently ~1e-12; the cross-check test pins it).
- Adding a dependency. numpy is the only hard one; mpmath is optional and must stay optional.

## Reporting a security issue

Nothing here handles untrusted network input by default, but `zeta_audit/serve.py` starts an
HTTP service. If you find an issue there, open a private security advisory rather than a
public issue.