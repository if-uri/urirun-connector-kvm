# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.
#
# Minimal stdlib Chrome DevTools Protocol client + DOM element finder/actuator, used by
# the `cdp` control strategy (control.py). No third-party deps: a hand-rolled WebSocket
# client (client-masked text frames) speaks Runtime.evaluate to the active page, and ALL
# element finding + acting happens IN-PAGE via JavaScript — so targeting is by DOM role /
# accessible-name / visible-text and acting is el.click() / focus+insertText. This is
# coordinate-free and role-exact (immune to OCR misreads and label/button ambiguity).
#
# Requires Chrome launched with --remote-debugging-port (the kvm `launch` backend adds it
# for chrome/chromium). Endpoint via URIRUN_KVM_CDP_URL (default http://127.0.0.1:9222).
from __future__ import annotations

import base64
import json
import os
import socket
import struct
import urllib.request

try:
    from .backends import BackendError
except ImportError:  # pragma: no cover - flat deploy
    from backends import BackendError  # type: ignore


def endpoint() -> str:
    return (os.environ.get("URIRUN_KVM_CDP_URL") or "http://127.0.0.1:9222").rstrip("/")


def _pages() -> list:
    with urllib.request.urlopen(endpoint() + "/json", timeout=3) as r:
        data = json.loads(r.read() or "[]")
    pages = [p for p in data if p.get("type") == "page" and p.get("webSocketDebuggerUrl")]
    # prefer a real http(s) page over about:blank/devtools (the active tab is usually first)
    real = [p for p in pages if (p.get("url", "").startswith(("http://", "https://")))]
    return real or pages


def reachable() -> bool:
    try:
        return bool(_pages())
    except Exception:  # noqa: BLE001
        return False


# ---- websocket (stdlib, client frames are masked) ------------------------- #
def _ws_connect(ws_url: str, timeout: float = 10.0):
    if not ws_url.startswith("ws://"):
        raise BackendError(f"unsupported cdp ws url: {ws_url}")
    hostport, _, path = ws_url[5:].partition("/")
    host, _, port = hostport.partition(":")
    s = socket.create_connection((host, int(port or 80)), timeout=timeout)
    key = base64.b64encode(os.urandom(16)).decode()
    s.sendall((f"GET /{path} HTTP/1.1\r\nHost: {hostport}\r\nUpgrade: websocket\r\n"
               f"Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\n"
               f"Sec-WebSocket-Version: 13\r\n\r\n").encode())
    buf = b""
    while b"\r\n\r\n" not in buf:
        chunk = s.recv(4096)
        if not chunk:
            raise BackendError("cdp ws handshake failed")
        buf += chunk
    return s


def _ws_send(s, data: str) -> None:
    payload = data.encode()
    n = len(payload)
    header = bytearray([0x81])  # FIN + text
    if n < 126:
        header.append(0x80 | n)
    elif n < 65536:
        header.append(0x80 | 126); header += struct.pack(">H", n)
    else:
        header.append(0x80 | 127); header += struct.pack(">Q", n)
    mask = os.urandom(4)
    header += mask
    s.sendall(bytes(header) + bytes(b ^ mask[i % 4] for i, b in enumerate(payload)))


def _ws_recv(s) -> str:
    def rd(n: int) -> bytes:
        b = b""
        while len(b) < n:
            c = s.recv(n - len(b))
            if not c:
                raise BackendError("cdp ws closed")
            b += c
        return b
    out = b""
    while True:
        h = rd(2)
        fin, ln = h[0] & 0x80, h[1] & 0x7F
        if ln == 126:
            ln = struct.unpack(">H", rd(2))[0]
        elif ln == 127:
            ln = struct.unpack(">Q", rd(8))[0]
        out += rd(ln) if ln else b""
        if fin:
            return out.decode("utf-8", "replace")


def _call(s, _id: int, method: str, params: dict | None = None) -> dict:
    _ws_send(s, json.dumps({"id": _id, "method": method, "params": params or {}}))
    for _ in range(300):                       # skip async events until our reply
        msg = json.loads(_ws_recv(s))
        if msg.get("id") == _id:
            return msg
    raise BackendError("no cdp response")


def _evaluate(expr: str):
    pages = _pages()
    if not pages:
        raise BackendError("no CDP page (launch chrome with --remote-debugging-port)")
    s = _ws_connect(pages[0]["webSocketDebuggerUrl"])
    try:
        r = _call(s, 1, "Runtime.evaluate",
                  {"expression": expr, "returnByValue": True, "awaitPromise": True})
        err = r.get("result", {}).get("exceptionDetails")
        if err:
            raise BackendError(f"cdp eval error: {err.get('text', err)}")
        return r.get("result", {}).get("result", {}).get("value")
    finally:
        try:
            s.close()
        except Exception:  # noqa: BLE001
            pass


# ---- in-page element finder + actuator (one JS, parameterised by op) ------- #
_JS = r"""
(function(q){
  function roleOf(el){
    var r=(el.getAttribute&&el.getAttribute('role'))||'';
    if(r) return r.toLowerCase();
    var m={BUTTON:'button',A:'link',INPUT:'textbox',TEXTAREA:'textbox',SELECT:'combobox'};
    if(el.tagName==='INPUT'){var t=(el.type||'').toLowerCase(); if(t==='button'||t==='submit')return'button';}
    if(el.isContentEditable) return 'textbox';
    return (m[el.tagName]||'').toLowerCase();
  }
  function nameOf(el){
    return ((el.getAttribute&&(el.getAttribute('aria-label')||el.getAttribute('placeholder')||el.getAttribute('title')))
            || el.value || el.innerText || el.textContent || '').trim();
  }
  var wantText=(q.text||q.name||'').trim().toLowerCase();
  var wantRole=(q.role||'').trim().toLowerCase();
  var best=null, bestArea=1e18;
  var all=document.querySelectorAll('*');
  for(var i=0;i<all.length;i++){
    var el=all[i], r=el.getBoundingClientRect();
    if(r.width<3||r.height<3) continue;
    if(r.bottom<0||r.top>innerHeight||r.right<0||r.left>innerWidth) continue;
    var rl=roleOf(el);
    if(wantRole && rl!==wantRole) continue;
    var nm=nameOf(el);
    if(wantText && nm.toLowerCase().indexOf(wantText)<0) continue;
    if(!wantText && !wantRole) continue;
    var area=r.width*r.height;
    if(area<bestArea){ best=el; bestArea=area; }    // smallest match = most specific
  }
  if(!best) return {found:false};
  var r=best.getBoundingClientRect();
  var info={found:true, role:roleOf(best), name:nameOf(best).slice(0,80),
            x:Math.round(r.left+r.width/2), y:Math.round(r.top+r.height/2),
            w:Math.round(r.width), h:Math.round(r.height)};
  if(q.op==='click'){ best.scrollIntoView({block:'center'}); best.click(); info.clicked=true; }
  else if(q.op==='fill'){
    best.focus();
    if(best.tagName==='INPUT'||best.tagName==='TEXTAREA'){
      best.value=q.value; best.dispatchEvent(new Event('input',{bubbles:true}));
    } else { try{document.execCommand('insertText',false,q.value);}catch(e){ best.textContent=q.value; } }
    info.filled=true;
  }
  return info;
})(__ARG__)
"""


def _run(op: str, text: str, role: str, name: str, value: str = "") -> dict:
    arg = json.dumps({"op": op, "text": text, "role": role, "name": name, "value": value})
    res = _evaluate(_JS.replace("__ARG__", arg))
    if not isinstance(res, dict):
        raise BackendError(f"cdp: unexpected eval result {res!r}")
    res.setdefault("found", False)
    res["via"] = "cdp"
    res["coord_space"] = "viewport-css"   # DOM coords; acting was done in-page, no OS input
    return res


def find(text: str = "", role: str = "", name: str = "") -> dict:
    return _run("locate", text, role, name)


def act(op: str, text: str = "", role: str = "", name: str = "", value: str = "") -> dict:
    res = _run(op, text, role, name, value)
    if not res.get("found"):
        raise BackendError(f"cdp: element not found (text={text!r} role={role!r} name={name!r})")
    res["ok"] = True
    return res
