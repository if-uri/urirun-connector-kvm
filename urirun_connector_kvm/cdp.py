# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.
#
# KVM CDP shim: re-exports the generic protocol surface from urirun.connectors.surfaces.cdp
# and adds only what is kvm-specific — endpoint wired to URIRUN_KVM_CDP_URL, launch that
# uses kvm's session_env(), and the DOM find/act UI contract (text/role/name semantics).
#
# Protocol, transport, discovery, snapshot primitives and launch helper live in the generic
# surface so browser-debug / webpage / chrome-plugin connectors share a single CDP client.
from __future__ import annotations

import json
import os
import subprocess

try:
    from .backends import BackendError
except ImportError:  # pragma: no cover - flat deploy
    from backends import BackendError  # type: ignore

from urirun.connectors.surfaces import cdp as _surface

# wire kvm-specific endpoint resolver (reads URIRUN_KVM_CDP_URL / URIRUN_KVM_CDP_PORT)
# and session env (display-aware env for the Chrome subprocess)
def _kvm_endpoint() -> str:
    return (os.environ.get("URIRUN_KVM_CDP_URL") or "http://127.0.0.1:9222").rstrip("/")

try:
    from .backends import session_env as _session_env
except ImportError:  # pragma: no cover - flat deploy
    from backends import session_env as _session_env  # type: ignore

_surface.configure(endpoint=_kvm_endpoint, env=_session_env)

# --------------------------------------------------------------------------- #
# re-exports — same function objects as the generic surface; monkeypatch on this
# module's namespace (cdp.reachable, cdp.navigate, …) reaches the router because
# control.py / core.py call these qualified (cdp.reachable()) not as bare imports.
# --------------------------------------------------------------------------- #
endpoint = _surface.endpoint
reachable = _surface.reachable
navigate = _surface.navigate
page_ready = _surface.page_ready
evaluate = _surface.evaluate          # raw JS eval (snapshot/restore/navigate-inverse capture)
CdpError = _surface.CdpError          # raised by evaluate when no page / JS throws

# --------------------------------------------------------------------------- #
# launch — kept here (not re-exported) because tests patch cdp._find_chrome and
# cdp.os.makedirs through this module's namespace, and because start_session calls
# reachable() / navigate() / session_env() all kvm-qualified.
# --------------------------------------------------------------------------- #
_CHROME_CANDIDATES = ("google-chrome-stable", "google-chrome", "chromium-browser",
                      "chromium", "brave-browser", "microsoft-edge")
_AUTH_FILES = ("Local State", "Default/Cookies", "Default/Network/Cookies",
               "Default/Login Data", "Default/Preferences", "Default/Web Data")


def _find_chrome() -> str:
    import shutil
    for c in (os.environ.get("URIRUN_KVM_CHROME"), *_CHROME_CANDIDATES):
        if c and shutil.which(c):
            return shutil.which(c)
    raise BackendError("no chrome/chromium binary found")


def _copy_auth(src: str, dst: str) -> list:
    import shutil
    copied = []
    src = os.path.expanduser(src)
    for rel in _AUTH_FILES:
        s, d = os.path.join(src, rel), os.path.join(dst, rel)
        if os.path.exists(s):
            os.makedirs(os.path.dirname(d), exist_ok=True)
            try:
                shutil.copy2(s, d)
                copied.append(rel)
            except Exception:  # noqa: BLE001
                pass
    return copied


def start_session(url: str = "", user_data_dir: str = "", copy_from: str = "") -> dict:
    """Reuse a live CDP endpoint, or LAUNCH a dedicated-profile debug Chrome and return
    IMMEDIATELY — does NOT block on the debug port binding.

    Spawns AT MOST one instance: if already reachable it REUSES. Callers must poll
    readiness with await_ready rather than re-calling (re-calling spawns competing
    Chrome instances that fight over the profile SingletonLock). ``copy_from`` clones
    auth files first so the debug profile opens already logged in."""
    base = endpoint()
    if reachable():
        nav = None
        if url:
            try:
                nav = navigate(url)
            except Exception as exc:  # noqa: BLE001
                nav = {"ok": False, "error": str(exc)}
        return {"ok": True, "reused": True, "launching": False, "endpoint": base, "navigate": nav}
    port = base.rsplit(":", 1)[-1].split("/")[0]
    ddir = user_data_dir or f"/tmp/urirun-kvm-cdp-{port}"
    os.makedirs(ddir, exist_ok=True)
    copied = _copy_auth(copy_from, ddir) if copy_from else []
    argv = [_find_chrome(), f"--remote-debugging-port={port}", f"--user-data-dir={ddir}",
            "--no-first-run", "--no-default-browser-check", "--force-renderer-accessibility"]
    if url:
        argv.append(url)
    proc = subprocess.Popen(argv, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            start_new_session=True, env=_session_env())
    return {"ok": True, "reused": False, "launching": True, "endpoint": base, "pid": proc.pid,
            "userDataDir": ddir, "authCopied": copied}


def await_ready(timeout: float = 12.0) -> dict:
    """Poll until the CDP debug endpoint is reachable, WITHOUT launching anything.
    Idempotent; safe to call repeatedly (never spawns a competing Chrome)."""
    import time as _t
    base = endpoint()
    deadline = _t.monotonic() + max(0.0, float(timeout))
    while True:
        if reachable():
            return {"ok": True, "ready": True, "endpoint": base}
        if _t.monotonic() >= deadline:
            return {"ok": False, "ready": False, "endpoint": base,
                    "error": "debugger not reachable within timeout"}
        _t.sleep(0.5)


def launch_session(url: str = "", user_data_dir: str = "", copy_from: str = "",
                   wait: float = 14.0) -> dict:
    """Back-compat one-shot: start_session then await_ready. Prefer the split in handlers
    (start returns fast; readiness polls on its own budget) so Chrome's cold-start
    can't blow the node handler's exec cap."""
    r = start_session(url=url, user_data_dir=user_data_dir, copy_from=copy_from)
    if r.get("reused"):
        return r
    ready = await_ready(timeout=wait)
    r["ok"] = bool(ready.get("ready"))
    r["launching"] = not ready.get("ready")
    if not ready.get("ready"):
        r["error"] = ready.get("error", "debugger did not come up within timeout")
    return r


# --------------------------------------------------------------------------- #
# DOM find / act — kvm UI contract (text / role / name semantics over CDP).
# These call _surface.evaluate() so transport lives in the generic surface.
# --------------------------------------------------------------------------- #
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
            value:(best.value!==undefined?best.value:(best.textContent||'')),
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
    try:
        res = _surface.evaluate(_JS.replace("__ARG__", arg))
    except _surface.CdpError as exc:
        raise BackendError(str(exc)) from exc
    if not isinstance(res, dict):
        raise BackendError(f"cdp: unexpected eval result {res!r}")
    res.setdefault("found", False)
    res["via"] = "cdp"
    res["coord_space"] = "viewport-css"
    return res


def find(text: str = "", role: str = "", name: str = "") -> dict:
    return _run("locate", text, role, name)


def act(op: str, text: str = "", role: str = "", name: str = "", value: str = "") -> dict:
    res = _run(op, text, role, name, value)
    if not res.get("found"):
        raise BackendError(f"cdp: element not found (text={text!r} role={role!r} name={name!r})")
    res["ok"] = True
    return res
