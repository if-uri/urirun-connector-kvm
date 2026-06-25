#!/usr/bin/env python
"""Robust calibration: minimal inline-onclick marker page (spaces as %20, no <script>,
no fullscreen-exiting Escape). Verify load + one marker, then full grid + fit."""
import base64, io, time, sys
import numpy as np
from PIL import Image
from urirun.node.client import NodeClient

ID = "/home/tom/.ssh/id_ed25519"
SW, SH = 1440, 900
nc = NodeClient("http://192.168.188.201:8765", identity=ID)

# body is black; clicking sets innerHTML to a 30x30 magenta box at the click point.
# every space is %20 so the omnibox keeps it as ONE data: URL; %23 -> # on decode.
PAGE = ("data:text/html,<body%20style=margin:0;height:100vh;background:%23000%20"
        "onclick=\"document.body.innerHTML='<b%20style=position:fixed;left:'"
        "+(event.clientX-15)+'px;top:'+(event.clientY-15)+'px;width:30px;height:30px;"
        "background:%23f0f></b>'\">")

def run(route, payload=None):
    return nc.run(f"kvm://laptop/{route}", payload or {})

def cap():
    v = run("screen/query/capture", {"base64": True}).get("result", {}).get("value", {})
    return np.asarray(Image.open(io.BytesIO(base64.b64decode(v["pngBase64"]))).convert("RGB")).astype(int)

def magenta_frac(a):
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    return float(((r > 170) & (b > 170) & (g < 120)).mean())

def find_box(a):
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    mask = (r > 170) & (b > 170) & (g < 120)
    ys, xs = np.where(mask)
    return (float(xs.mean()), float(ys.mean()), len(xs)) if len(xs) >= 200 else None

# 1) load + go fullscreen
run("input/command/key", {"keys": "ctrl+l"}); time.sleep(0.5)
run("input/command/type", {"text": PAGE}); time.sleep(0.4)
run("input/command/key", {"keys": "Return"}); time.sleep(2.2)
black = 1 - magenta_frac(cap())
run("input/command/key", {"keys": "f11"}); time.sleep(1.3)
print(f"page loaded? black coverage {black*100:.0f}% (expect high; magenta only after click)")

# 2) probe one click (center) to confirm a marker appears
run("input/command/click", {"x": 720, "y": 450}); time.sleep(0.8)
m = find_box(cap())
print("probe center ->", m)
if not m:
    print("FAIL: no marker after center click; aborting");
    run("input/command/key", {"keys": "f11"}); sys.exit(1)

# 3) full grid (no Escape between — onclick clears old marker by replacing innerHTML)
targets = [(x, y) for y in (130, 300, 450, 600, 770) for x in (180, 540, 900, 1260)]
pairs = []
for (tx, ty) in targets:
    run("input/command/click", {"x": tx, "y": ty}); time.sleep(0.7)
    b = find_box(cap())
    if b:
        pairs.append((tx, ty, b[0], b[1]))
        print(f"  cmd({tx:4d},{ty:3d}) -> land({b[0]:6.1f},{b[1]:6.1f}) px={b[2]}")
    else:
        print(f"  cmd({tx:4d},{ty:3d}) -> none")

run("input/command/key", {"keys": "f11"}); time.sleep(0.3)  # exit fullscreen
if len(pairs) < 4:
    print("FAIL few markers", len(pairs)); sys.exit(1)

P = np.array(pairs, float)
ax, bx = np.polyfit(P[:, 0], P[:, 2], 1)
ay, by = np.polyfit(P[:, 1], P[:, 3], 1)
rx = P[:, 2] - (ax * P[:, 0] + bx); ry = P[:, 3] - (ay * P[:, 1] + by)
print(f"\nfit X: land={ax:.4f}*cmd+{bx:.2f} (resid<= {np.abs(rx).max():.1f}px, n={len(P)})")
print(f"fit Y: land={ay:.4f}*cmd+{by:.2f} (resid<= {np.abs(ry).max():.1f}px)")
print(f"\nURIRUN_KVM_CALIB={ax:.5f},{bx:.3f},{ay:.5f},{by:.3f}")
