# Author: Tom Sapletta · Part of the ifURI solution.
"""Warm mutter-screencast capture worker — the Tier-1 lever from PERFORMANCE-REFACTOR.

Cold capture pays the GNOME ScreenCast negotiation (CreateSession → RecordMonitor →
Start → PipeWireStreamAdded) on EVERY frame (~700–1200 ms). This daemon pays it ONCE,
keeps the pipewire node alive, and serves frames over a unix socket; each request runs
only a tiny `pipewiresrc path=N num-buffers=1 ! pngenc` pipeline on the already-open
stream. Exits by itself after ``idle`` seconds without requests, so the compositor's
"screen is being shared" indicator does not stay on forever.

Runs under a SYSTEM python (dbus+gi+gstreamer — see ``_mutter_python`` in backends.py),
NOT the node venv; stdlib-only besides dbus/gi. Spawned on demand by the ``mutter-warm``
capture backend; standalone use:

    python3 capture_worker.py /run/user/1000/urirun-kvm-warm-0.sock 0 120

Protocol: one JSON line per connection ``{"output": "/abs/path.png"}`` →
one JSON line back ``{"ok": true, "path": …, "connector": …, "monitors": […]}``.
"""
from __future__ import annotations

import json
import os
import socket
import sys

import dbus  # type: ignore
import dbus.mainloop.glib  # type: ignore
import gi  # type: ignore

gi.require_version("Gst", "1.0")
from gi.repository import GLib, Gst  # type: ignore  # noqa: E402

# Bumped together with the backend's _WARM_PROTO on any request/response change:
# a live worker predating the last deploy answers with its old value and the backend
# retires it (unlink + respawn) instead of silently using stale behaviour.
PROTO = 3


def _current_modes(physical):
    """(connector → current WxH, connector → display name) from the physical list."""
    modes, names = {}, {}
    for spec, mode_list, props in physical:
        conn = str(spec[0])
        names[conn] = str(props.get("display-name") or "")
        for mode in mode_list:
            if bool(mode[6].get("is-current")):
                modes[conn] = (int(mode[1]), int(mode[2]))
                break
    return modes, names


def _monitor_entry(idx, lm, modes, names):
    """One logical-monitor dict (or None for a headless entry)."""
    x, y, scale = int(lm[0]), int(lm[1]), float(lm[2])
    primary, mons = lm[4], lm[5]
    if not mons:
        return None
    conn = str(mons[0][0])
    width, height = modes.get(conn, (0, 0))
    return {"index": idx + 1, "connector": conn, "primary": bool(primary),
            "x": x, "y": y, "scale": scale, "width": width, "height": height,
            "logicalWidth": int(round(width / scale)) if scale and width else 0,
            "logicalHeight": int(round(height / scale)) if scale and height else 0,
            "displayName": names.get(conn, "")}


def _monitors_bbox(monitors):
    rects = [(m["x"], m["y"], m["logicalWidth"], m["logicalHeight"])
             for m in monitors if m["logicalWidth"] > 0 and m["logicalHeight"] > 0]
    if not rects:
        return None
    minx = min(r[0] for r in rects); miny = min(r[1] for r in rects)
    maxx = max(r[0] + r[2] for r in rects); maxy = max(r[1] + r[3] for r in rects)
    return [minx, miny, maxx - minx, maxy - miny]


def logical_monitors(bus):
    """Active logical monitors from Mutter DisplayConfig (same shape as the cold script)."""
    dc = dbus.Interface(bus.get_object("org.gnome.Mutter.DisplayConfig",
                                       "/org/gnome/Mutter/DisplayConfig"),
                        "org.gnome.Mutter.DisplayConfig")
    _s, physical, logical, _p = dc.GetCurrentState()
    modes, names = _current_modes(physical)
    out = [m for m in (_monitor_entry(i, lm, modes, names) for i, lm in enumerate(logical)) if m]
    primary_conn = next((m["connector"] for m in out if m["primary"]), None)
    fb = out[0]["connector"] if out else None
    return out, primary_conn or fb, _monitors_bbox(out)


def _resolve_target(monitors, primary, selector: str):
    """(record_all, connector) for the requested selector ('all'/'-1'/monitor number)."""
    if selector in ("all", "-1"):
        return True, None
    try:
        num = int(selector)
    except ValueError:
        num = 0
    conn = monitors[num - 1]["connector"] if 0 < num <= len(monitors) else primary
    if not conn:
        raise RuntimeError("no active monitor")
    return False, conn


def open_stream(bus, selector: str):
    """Negotiate the ScreenCast session ONCE; return (session, pw_node, meta)."""
    monitors, primary, bbox = logical_monitors(bus)
    record_all, conn = _resolve_target(monitors, primary, selector)
    sc = dbus.Interface(bus.get_object("org.gnome.Mutter.ScreenCast",
                                       "/org/gnome/Mutter/ScreenCast"),
                        "org.gnome.Mutter.ScreenCast")
    session = dbus.Interface(bus.get_object("org.gnome.Mutter.ScreenCast", sc.CreateSession({})),
                             "org.gnome.Mutter.ScreenCast.Session")
    if record_all:
        stream = (session.RecordArea(bbox[0], bbox[1], bbox[2], bbox[3],
                                     {"cursor-mode": dbus.UInt32(1)}) if bbox
                  else session.RecordVirtual({"cursor-mode": dbus.UInt32(1)}))
    else:
        stream = session.RecordMonitor(conn, {"cursor-mode": dbus.UInt32(1)})
    state: dict = {}
    loop = GLib.MainLoop()
    bus.add_signal_receiver(lambda n: (state.__setitem__("node", int(n)), loop.quit()),
                            dbus_interface="org.gnome.Mutter.ScreenCast.Stream",
                            path=stream, signal_name="PipeWireStreamAdded")
    session.Start()
    GLib.timeout_add_seconds(10, lambda: (loop.quit(), False)[1])
    loop.run()
    node = state.get("node")
    if node is None:
        session.Stop()
        raise RuntimeError("no pipewire node (ScreenCast unavailable/restricted)")
    if record_all:
        src_wh = (bbox[2], bbox[3]) if bbox else (0, 0)
    else:
        src_wh = next(((m["width"], m["height"]) for m in monitors if m["connector"] == conn),
                      (0, 0))
    meta = {"scope": "all-monitors" if record_all else "monitor",
            "connector": conn or "", "monitor": -1 if record_all else int(selector or "0"),
            "monitors": monitors, "bbox": bbox or [], "srcSize": list(src_wh)}
    return session, node, meta


def _scale_caps(meta: dict, max_width: int) -> str:
    """gst videoscale stage when the caller wants ≤max_width — png-encoding the
    scaled frame is ~4x cheaper than full-res encode + PIL resize in the handler."""
    src_w, src_h = (meta.get("srcSize") or [0, 0])[:2]
    if not max_width or not src_w or src_w <= max_width:
        return ""
    h = max(2, int(round(src_h * max_width / src_w)) // 2 * 2)
    return "! videoscale ! video/x-raw,width=%d,height=%d " % (max_width, h)


def grab_frame(pw_node: int, output: str, meta: dict, max_width: int = 0,
               fmt: str = "png") -> None:
    """One frame off the WARM pipewire node — no dbus, just a tiny gst pipeline.
    ``fmt='jpeg'`` swaps pngenc for jpegenc (quality 85): ~4-6x smaller payload to
    base64/JSON — for perception loops, not for pixel-exact artifacts."""
    enc = "jpegenc quality=85" if fmt == "jpeg" else "pngenc snapshot=true"
    pipe = Gst.parse_launch(
        "pipewiresrc path=%d num-buffers=1 ! videoconvert %s! %s "
        "! filesink location=%s" % (pw_node, _scale_caps(meta, max_width), enc, output))
    pipe.set_state(Gst.State.PLAYING)
    msg = pipe.get_bus().timed_pop_filtered(
        10 * Gst.SECOND, Gst.MessageType.EOS | Gst.MessageType.ERROR)
    pipe.set_state(Gst.State.NULL)
    if msg and msg.type == Gst.MessageType.ERROR:
        err, _dbg = msg.parse_error()
        raise RuntimeError("gstreamer: %s" % err)


def serve(sock_path: str, selector: str, idle: int) -> None:
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    bus = dbus.SessionBus()
    session, pw_node, meta = open_stream(bus, selector)
    Gst.init(None)
    try:
        os.unlink(sock_path)
    except OSError:
        pass
    srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    srv.bind(sock_path)
    srv.listen(4)
    srv.settimeout(max(10, idle))
    print(json.dumps({"ready": True, "socket": sock_path, "pwNode": pw_node, **meta}),
          flush=True)
    try:
        while True:
            try:
                client, _addr = srv.accept()
            except socket.timeout:
                break  # idle — release the stream, the backend respawns us on demand
            with client:
                _handle(client, pw_node, meta)
    finally:
        try:
            session.Stop()
        except Exception:  # noqa: BLE001 - compositor may already have dropped us
            pass
        try:
            os.unlink(sock_path)
        except OSError:
            pass


def _handle(client: socket.socket, pw_node: int, meta: dict) -> None:
    import time
    client.settimeout(15)
    try:
        req = json.loads(client.makefile("r").readline() or "{}")
        output = str(req.get("output") or "")
        if not output:
            raise ValueError("missing 'output'")
        t0 = time.monotonic()
        grab_frame(pw_node, output, meta, int(req.get("max_width") or 0),
                   str(req.get("fmt") or "png"))
        resp = {"ok": True, "path": output, **meta, "proto": PROTO,
                "grabMs": int((time.monotonic() - t0) * 1000)}
    except Exception as exc:  # noqa: BLE001 - report to caller, keep serving
        resp = {"ok": False, "error": str(exc)}
    try:
        client.sendall((json.dumps(resp) + "\n").encode("utf-8"))
    except OSError:
        pass


if __name__ == "__main__":
    serve(sys.argv[1],
          sys.argv[2] if len(sys.argv) > 2 else "0",
          int(sys.argv[3]) if len(sys.argv) > 3 else 120)
