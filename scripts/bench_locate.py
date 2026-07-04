# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.
#
"""Effectiveness benchmark for kvm ``locate`` backends (tesseract / easyocr / imgl / vql).

Answers, with numbers, "which backend should ui/vnc locate trust on THIS machine":
found-rate, center error in px against ground truth, and latency — on a synthetic
golden set (UI-like labels at known positions on dark and light backgrounds, native
and 0.77x-downscaled like a noVNC canvas) plus any real frames you pass in.

Usage:
    python scripts/bench_locate.py                          # synthetic golden set
    python scripts/bench_locate.py --frame shot.png --query Applications \
                                   --frame shot.png --query "Workspace 1@62,891"
    python scripts/bench_locate.py --json bench.json        # machine-readable output

A query may carry ground truth as ``text@cx,cy`` — then center error is scored;
without it only found/latency are recorded. AT-SPI is excluded by design: it reads
the live accessibility tree, not an image, so it cannot be scored on frames.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from urirun_connector_kvm import backends as B  # noqa: E402

IMAGE_BACKENDS = ("tesseract", "easyocr", "imgl", "vql")
_LABELS = [  # text, (x, y) top-left anchor — sparse UI-ish layout
    ("Applications", (120, 80)), ("Reconfigure", (120, 130)), ("Save Document", (420, 300)),
    ("Cancel", (640, 300)), ("Workspace 1", (30, 560)), ("File Manager", (420, 90)),
]


def synth_golden(outdir: Path) -> list[dict]:
    """Render golden frames: dark + light theme at native res, plus a 0.77x downscale
    of the dark one (what OCR sees through a scaled noVNC canvas)."""
    from PIL import Image, ImageDraw, ImageFont
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 15)
    except OSError:
        font = ImageFont.load_default()
    cases = []
    for theme, bg, fg in (("dark", (28, 28, 30), (225, 225, 228)), ("light", (240, 240, 242), (25, 25, 28))):
        im = Image.new("RGB", (800, 600), bg)
        d = ImageDraw.Draw(im)
        truths = {}
        for text, (x, y) in _LABELS:
            d.text((x, y), text, fill=fg, font=font)
            x0, y0, x1, y1 = d.textbbox((x, y), text, font=font)
            truths[text] = ((x0 + x1) // 2, (y0 + y1) // 2)
        p = outdir / f"golden_{theme}.png"
        im.save(p)
        cases.append({"frame": str(p), "truths": truths, "tag": theme})
        if theme == "dark":  # the noVNC-canvas condition: same frame at 0.77x
            ps = outdir / "golden_dark_scaled.png"
            im.resize((int(im.width * 0.77), int(im.height * 0.77)), Image.LANCZOS).save(ps)
            cases.append({"frame": str(ps),
                          "truths": {t: (int(c[0] * 0.77), int(c[1] * 0.77)) for t, c in truths.items()},
                          "tag": "dark-scaled-0.77x"})
    return cases


def run_case(backend, frame: str, query: str, truth) -> dict:
    t0 = time.time()
    try:
        r = backend.fn(image=frame, query=query)
        found, center = bool(r.get("found")), r.get("center")
    except Exception as exc:  # noqa: BLE001 - a miss/an error scores the same: not found
        found, center = False, None
        r = {"error": str(exc)}
    row = {"query": query, "found": found, "latency_s": round(time.time() - t0, 3)}
    if found and truth and center:
        row["err_px"] = round(((center[0] - truth[0]) ** 2 + (center[1] - truth[1]) ** 2) ** 0.5, 1)
        # a hit >40px off clicks the wrong widget — count it as a wrong hit, not a find
        row["hit"] = row["err_px"] <= 40
    elif truth:
        row["hit"] = False
    return row


def summarize(rows: list[dict]) -> dict:
    scored = [r for r in rows if "hit" in r]
    return {
        "cases": len(rows),
        "found_rate": round(sum(r["found"] for r in rows) / len(rows), 2) if rows else None,
        "hit_rate": round(sum(r["hit"] for r in scored) / len(scored), 2) if scored else None,
        "median_err_px": (round(statistics.median(r["err_px"] for r in scored if "err_px" in r), 1)
                          if any("err_px" in r for r in scored) else None),
        "median_latency_s": round(statistics.median(r["latency_s"] for r in rows), 2) if rows else None,
    }


def parse_args(argv):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--frame", action="append", default=[], help="real frame PNG (repeat)")
    ap.add_argument("--query", action="append", default=[], help="query for the frame at the same position; 'text@cx,cy' adds ground truth")
    ap.add_argument("--json", default="", help="write full results JSON here")
    ap.add_argument("--no-synth", action="store_true", help="skip the synthetic golden set")
    return ap.parse_args(argv)


def build_cases(args) -> list[dict]:
    cases = [] if args.no_synth else synth_golden(Path(tempfile.mkdtemp(prefix="kvm_bench_")))
    for frame, q in zip(args.frame, args.query):
        text, _, at = q.partition("@")
        truth = tuple(int(v) for v in at.split(",")) if at else None
        cases.append({"frame": frame, "truths": {text: truth}, "tag": Path(frame).name})
    return cases


def main(argv=None) -> int:
    args = parse_args(argv)
    cases = build_cases(args)
    available = [b for b in B.backends_for("locate") if b.name in IMAGE_BACKENDS and b.available()]
    print(f"backends: {[b.name for b in available]}  |  cases: "
          f"{sum(len(c['truths']) for c in cases)} queries over {len(cases)} frames\n")
    results = {}
    for b in available:
        rows = [dict(run_case(b, c["frame"], q, t), frame=c["tag"])
                for c in cases for q, t in c["truths"].items()]
        results[b.name] = {"summary": summarize(rows), "rows": rows}
        s = results[b.name]["summary"]
        print(f"{b.name:10s} found {s['found_rate']:>4}  hit {str(s['hit_rate']):>4}  "
              f"err {str(s['median_err_px']):>6}px  lat {s['median_latency_s']:>5}s")
    for name, res in results.items():
        misses = [r for r in res["rows"] if not r.get("hit", r["found"])]
        if misses:
            print(f"\n{name} misses: " + ", ".join(f"{r['query']}({r['frame']})" for r in misses[:8]))
    if args.json:
        Path(args.json).write_text(json.dumps(results, indent=2))
        print(f"\nJSON -> {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
