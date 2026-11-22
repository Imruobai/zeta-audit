# Demo page

`landing.html` is a single static page showing what the repo produces. No pricing, no
product framing — the story is "point this at a zero table and get a verdict".

## What the page shows

1. **A real `zeta-audit` run**, padded to the tool's actual output format.
2. **A real verifier transcript** from `out/verify_output.txt`.
3. **The mpmath cross-check table**, which is the only non-circular evidence.
4. **An honest-limits panel**, closing the page rather than footnoting it.

## Publishing

Static file, no external requests, no fonts, no trackers, no JavaScript.

```bash
python -m http.server -d docs 8000
# http://127.0.0.1:8000/landing.html
```

Refresh numbers first:

```bash
python pipeline.py && python report.py
```

Then update the `zeta-audit` sample and the cross-check table from `REPORT.md`. Do not
hand-type numbers that are not in `REPORT.md` — that is the failure mode the
report-generation step exists to prevent.

## If you would rather not maintain a page

Delete it. `REPORT.md` renders fine on GitHub and carries the same information with less
maintenance. The page only earns its keep if you need something to link from a post.

## Structure

```
docs/
  RELEASE_NOTES.md   what shipped, what was measured, what is not claimed
  COMPARISON.md      how this compares to existing work, including where it loses
  DEMO.md            this file
  landing.html       single static page, no dependencies
```