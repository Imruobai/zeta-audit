"""Minimal dependency-free SVG plotting (matplotlib is not available here)."""

from __future__ import annotations

import math
from pathlib import Path

W, H = 960, 540
PAD_L, PAD_R, PAD_T, PAD_B = 70, 30, 50, 60

FONT = "font-family='Consolas,Menlo,monospace'"


def _esc(s: str) -> str:
    """XML-escape text so titles like 'Im s <= 1000' do not break the SVG."""
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace("'", "&apos;").replace('"', "&quot;"))


def _sx(v, lo, hi):
    return PAD_L + (v - lo) / (hi - lo) * (W - PAD_L - PAD_R)


def _sy(v, lo, hi):
    return H - PAD_B - (v - lo) / (hi - lo) * (H - PAD_T - PAD_B)


def _axes(title: str, xlab: str, ylab: str, xticks, yticks, xlo, xhi, ylo, yhi) -> list[str]:
    out = [
        f"<svg xmlns='http://www.w3.org/2000/svg' width='{W}' height='{H}' viewBox='0 0 {W} {H}'>",
        f"<rect width='{W}' height='{H}' fill='#0d1117'/>",
        f"<text x='{W/2}' y='28' fill='#e6edf3' font-size='18' text-anchor='middle' {FONT}>{_esc(title)}</text>",
    ]
    for t in xticks:
        x = _sx(t, xlo, xhi)
        out.append(f"<line x1='{x:.1f}' y1='{H-PAD_B}' x2='{x:.1f}' y2='{H-PAD_B+5}' stroke='#30363d'/>")
        out.append(f"<text x='{x:.1f}' y='{H-PAD_B+20}' fill='#8b949e' font-size='11' text-anchor='middle' {FONT}>{t:g}</text>")
    for t in yticks:
        y = _sy(t, ylo, yhi)
        out.append(f"<line x1='{PAD_L-5}' y1='{y:.1f}' x2='{PAD_L}' y2='{y:.1f}' stroke='#30363d'/>")
        out.append(f"<line x1='{PAD_L}' y1='{y:.1f}' x2='{W-PAD_R}' y2='{y:.1f}' stroke='#1b2230'/>")
        out.append(f"<text x='{PAD_L-10}' y='{y+4:.1f}' fill='#8b949e' font-size='11' text-anchor='end' {FONT}>{t:g}</text>")
    out.append(f"<rect x='{PAD_L}' y='{PAD_T}' width='{W-PAD_L-PAD_R}' height='{H-PAD_T-PAD_B}' fill='none' stroke='#30363d'/>")
    out.append(f"<text x='{(PAD_L+W-PAD_R)/2:.0f}' y='{H-16}' fill='#8b949e' font-size='12' text-anchor='middle' {FONT}>{_esc(xlab)}</text>")
    out.append(f"<text x='18' y='{(PAD_T+H-PAD_B)/2:.0f}' fill='#8b949e' font-size='12' text-anchor='middle' {FONT} transform='rotate(-90 18 {(PAD_T+H-PAD_B)/2:.0f})'>{_esc(ylab)}</text>")
    return out


def _polyline(points, lo, hi, ylo, yhi, color, width=1.6, opacity=1.0):
    if not points:
        return ""
    d = " ".join(f"{_sx(x, lo, hi):.1f},{_sy(y, ylo, yhi):.1f}" for x, y in points)
    return f"<polyline points='{d}' fill='none' stroke='{color}' stroke-width='{width}' opacity='{opacity}'/>"


def plot_decay(points, lo, hi, ylo, yhi):
    """Points at (x, Z(x)) with zero crossings highlighted."""
    return points


def save(path: str | Path, body: list[str]) -> Path:
    p = Path(path)
    p.write_text("\n".join(body + ["</svg>"]), encoding="utf-8")
    return p


def zeros_chart(gammas, out: str | Path, t_max: float) -> Path:
    """Stems at every verified zero ordinate."""
    body = _axes(
        f"{len(gammas)} nontrivial zeros, all on Re s = 1/2, Im s <= {t_max:g}",
        "zero index", "γ (ordinate)",
        [1, len(gammas) // 4, len(gammas) // 2, 3 * len(gammas) // 4, len(gammas)],
        [0, 250, 500, 750, round(gammas[-1])],
        1, len(gammas), 0, gammas[-1],
    )
    body.append(_polyline([(i, g) for i, g in enumerate(gammas, 1)], 1, len(gammas), 0, gammas[-1], "#58a6ff", 1.2))
    body.append(f"<text x='{W-PAD_R-160}' y='{PAD_T+24}' fill='#58a6ff' font-size='12' {FONT}>first γ = {gammas[0]:.6f}</text>")
    body.append(f"<text x='{W-PAD_R-160}' y='{PAD_T+44}' fill='#58a6ff' font-size='12' {FONT}>1000th γ = {gammas[999]:.4f}</text>" if len(gammas) > 999 else "")
    return save(out, body)


def Z_chart(ts, zs, out: str | Path, title: str) -> Path:
    lo, hi = min(ts), max(ts)
    ylo, yhi = min(zs), max(zs)
    pad = 0.08 * (yhi - ylo)
    body = _axes(title, "t", "Z(t)  (= e^{iθ(t)} ζ(1/2+it))",
                 [lo, (lo + hi) / 2, hi], [-3, 0, 3], lo, hi, ylo - pad, yhi + pad)
    body.append(_polyline(list(zip(ts, zs)), lo, hi, ylo - pad, yhi + pad, "#3fb950", 1.4))
    body.append(f"<line x1='{PAD_L}' y1='{_sy(0, ylo-pad, yhi+pad):.1f}' x2='{W-PAD_R}' y2='{_sy(0, ylo-pad, yhi+pad):.1f}' stroke='#8b949e' stroke-dasharray='4 4'/>")
    return save(out, body)


def error_chart(rows, out: str | Path) -> Path:
    """|ψ(x) − explicit(x)| vs. number of zeros, on a log axis."""
    errs = [abs(r["error"]) for r in rows]
    ks = [r["zeros"] for r in rows]
    lo, hi = min(ks), max(ks)
    ylo, yhi = 1e-3, max(errs) * 3
    body = _axes("explicit formula truncation error at x = 10^5", "zeros used",
                 "|ψ(x) − ζ-sum| (log)", [lo, hi], [1e-2, 1, 10], lo, hi, ylo, yhi)
    pts = []
    for k, e in zip(ks, errs):
        y = math.log10(max(e, ylo)) / math.log10(yhi) * (math.log10(yhi) - math.log10(ylo)) + math.log10(ylo)
        pts.append((k, 10 ** y))
    body.append(_polyline(pts, lo, hi, ylo, yhi, "#f0883e", 2.0))
    for k, e in zip(ks, errs):
        x = _sx(k, lo, hi)
        y = _sy(max(e, ylo), ylo, yhi)
        body.append(f"<circle cx='{x:.1f}' cy='{y:.1f}' r='4' fill='#f0883e'/>")
        body.append(f"<text x='{x:.1f}' y='{y-10:.1f}' fill='#e6edf3' font-size='11' text-anchor='middle' {FONT}>{e:.3g}</text>")
    return save(out, body)