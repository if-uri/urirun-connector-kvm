# Author: Tom Sapletta · Part of the ifURI solution.
"""vguard — perceive-verify-act guards for reliable computer-use over the urirun mesh.

Zasada: nigdy nie działaj na ZAŁOŻONYM stanie. Każdą akcję bramkuj tanim sprawdzeniem
i wykrywaj zmianę sytuacji (ingerencja usera), żeby nie wykonać niepotrzebnej/błędnej
czynności. Warstwy taniej→drożej — eskaluj tylko gdy trzeba:

  1. dhash(ROI)         — perceptual hash małego wycinka: CZY coś się zmieniło (µs, bez OCR).
  2. anchor(text)       — celowany OCR: czy oczekiwany element JEST (ms, `ui/query/verify`).
  3. (wizja LLM)        — pełny zrzut do modelu, tylko gdy 1–2 niejednoznaczne.

Pętla: settle() → assert precond() → ref=snapshot() → [guard: zmiana? abort] → act()
       → assert postcond() → skip-if-goal-satisfied.
"""
from __future__ import annotations

import base64
import hashlib
import json
import time
import urllib.request


class Screen:
    def __init__(self, node_url: str):
        self.url = node_url.rstrip("/")

    def _run(self, uri: str, payload: dict, timeout: float = 40) -> dict:
        body = json.dumps({"uri": uri, "mode": "execute", "payload": payload}).encode()
        req = urllib.request.Request(self.url + "/run", data=body,
                                     headers={"Content-Type": "application/json"})
        env = json.load(urllib.request.urlopen(req, timeout=timeout))
        val = (env.get("result") or {}).get("value")
        return val if isinstance(val, dict) else (env.get("result") or {})

    # --- percepcja ---
    def capture(self, scope: str = "all") -> bytes | None:
        v = self._run("kvm://host/screen/query/capture", {"base64": True, "scope": scope})
        b64 = v.get("pngBase64")
        return base64.b64decode(b64) if b64 else None

    def dhash(self, png: bytes | None = None, size: int = 16) -> int:
        """Perceptual hash (różnicowy) — tolerancyjny na drobny szum, czuły na realną zmianę
        układu. Wymaga PIL; bez niego spada do sha1 bajtów (czuły, ale wciąż wykrywa zmianę)."""
        png = png or self.capture()
        if not png:
            return 0
        try:
            import io
            from PIL import Image
            im = Image.open(io.BytesIO(png)).convert("L").resize((size + 1, size))
            px = im.load()
            bits = 0
            for y in range(size):
                for x in range(size):
                    bits = (bits << 1) | (1 if px[x, y] > px[x + 1, y] else 0)
            return bits
        except Exception:
            return int(hashlib.sha1(png).hexdigest()[:16], 16)

    @staticmethod
    def hamming(a: int, b: int) -> int:
        return bin(a ^ b).count("1")

    def anchor(self, text: str) -> bool:
        """Kotwica: czy oczekiwany tekst JEST na ekranie (celowany OCR)."""
        return bool(self._run("kvm://host/ui/query/verify", {"text": text}).get("present"))

    # --- strażnicy ---
    def settle(self, timeout: float = 10, interval: float = 0.6, stable: int = 2, tol: int = 4) -> int:
        """Czekaj aż ekran przestanie się zmieniać (koniec ładowania) — zamiast sleep na sztywno.
        Zwraca finalny dhash. Kończy po `stable` kolejnych stabilnych odczytach albo timeout."""
        prev, ok, t0 = None, 0, time.time()
        while time.time() - t0 < timeout:
            h = self.dhash()
            if prev is not None and self.hamming(h, prev) <= tol:
                ok += 1
                if ok >= stable:
                    return h
            else:
                ok = 0
            prev = h
            time.sleep(interval)
        return prev or 0

    def changed_since(self, ref: int, threshold: int = 6) -> bool:
        """STRAŻNIK zmiany: czy ekran zmienił się vs stan z chwili decyzji (ingerencja usera,
        wyskakujące okno, przełączone okno). Jeśli tak — przerwij zaplanowaną akcję i re-perceive."""
        return self.hamming(self.dhash(), ref) > threshold

    def guarded(self, *, precond: str, do, postcond: str, goal: str | None = None) -> dict:
        """Wykonaj `do()` tylko gdy precond (kotwica) spełniony i ekran się nie zmienił od decyzji;
        potem potwierdź postcond. Zwraca {ok, reason}. Nie działa, gdy goal już spełniony."""
        if goal and self.anchor(goal):
            return {"ok": True, "reason": "goal-already-satisfied", "acted": False}
        if not self.anchor(precond):
            return {"ok": False, "reason": f"precond-missing:{precond}", "acted": False}
        ref = self.dhash()
        if self.changed_since(ref):
            return {"ok": False, "reason": "screen-changed-before-act", "acted": False}
        do()
        self.settle(timeout=4, stable=2)
        if not self.anchor(postcond):
            return {"ok": False, "reason": f"postcond-missing:{postcond}", "acted": True}
        return {"ok": True, "reason": "confirmed", "acted": True}
