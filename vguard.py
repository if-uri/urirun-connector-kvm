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
    def capture(self, scope: str = "all", max_width: int = 0) -> bytes | None:
        # max_width zmniejsza transfer 8× (scope=all ~1 MB → ~120 KB) — do dhash/settle wystarcza
        # zdrap 400–800 px, i tak skalujemy do 16 px. Pełny zrzut tylko gdy potrzebny do wizji.
        payload = {"base64": True, "scope": scope}
        if max_width:
            payload["max_width"] = max_width
        v = self._run("kvm://host/screen/query/capture", payload)
        b64 = v.get("pngBase64")
        return base64.b64decode(b64) if b64 else None

    def batch(self, steps: list[dict]) -> dict:
        """Wykonaj wiele kroków w JEDNYM wywołaniu (jeden subprocess zamiast N) — ~2–3× szybciej
        dla sekwencji. steps: [{'op':'type','text':...}, {'op':'key','keys':'Return'}, ...]."""
        return self._run("kvm://host/input/command/task_run", {"steps": steps})

    def guarded_batch(self, steps: list[dict], expect, tries: int = 3) -> dict:
        """SZYBKO I PEWNIE: batch akcji + POSTCOND (verify_texts) + retry. Naprawia ciche
        porażki — np. `type` który nie złapał fokusu (contenteditable jeszcze nie gotowy):
        pierwszy raz tekst nie ląduje, verify_texts to wykrywa, retry ląduje. Łączy zysk
        prędkości (batch+1 OCR) z niezawodnością (verify-before-act). expect: tekst/lista."""
        exp = [expect] if isinstance(expect, str) else list(expect)
        last = {}
        for i in range(tries):
            self.batch(steps)
            last = self.verify_texts(exp)
            if all(last.values()):
                return {"ok": True, "tries": i + 1}
        return {"ok": False, "tries": tries, "missing": [t for t, ok in last.items() if not ok]}

    def dhash(self, png: bytes | None = None, size: int = 16) -> int:
        """Perceptual hash (różnicowy) — tolerancyjny na drobny szum, czuły na realną zmianę
        układu. Wymaga PIL; bez niego spada do sha1 bajtów (czuły, ale wciąż wykrywa zmianę)."""
        png = png or self.capture(max_width=480)   # do detekcji zmiany mały zrzut wystarcza (8× mniej danych)
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

    def verify_texts(self, texts: list[str], max_width: int = 1600) -> dict:
        """SZYBKA wielo-kotwica: JEDNO capture + JEDNO OCR (@max_width) + sprawdzenie wielu
        tekstów lokalnie — zamiast N× ui/query/verify (każdy robi osobny capture+OCR ~6 s).
        OCR to główny koszt percepcji (tesseract ~5–8 s pełny; ~4,6 s @1600 bez utraty
        trafności). N kotwic za cenę JEDNEGO OCR. Zwraca {tekst: bool}."""
        cap = self._run("kvm://host/screen/query/capture", {"base64": False, "max_width": max_width})
        path = cap.get("path")
        if not path:
            return {t: False for t in texts}
        ocr = (self._run("ocr://host/image/query/text", {"image": path}).get("text") or "").lower()
        return {t: (t.lower() in ocr) for t in texts}

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
