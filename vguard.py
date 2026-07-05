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
import shutil
import subprocess
import time
import urllib.request


class Screen:
    def __init__(self, node_url: str):
        self.url = node_url.rstrip("/")
        self._ocr_cache: tuple[int, str] | None = None  # (dhash klatki, tekst) — patrz verify_texts

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

    def user_active(self, window: float = 1.2, tol: int = 6) -> bool:
        """Czy ktoś PRACUJE na maszynie? Dwa małe zrzuty w odstępie `window` s — różnica
        ponad próg = ekran żyje sam z siebie (user pisze/scrolluje, animacja). Lekcja
        z 2026-07-05: batch wpisał tekst w ŻYWĄ sesję usera na lenovo, bo nic tego nie
        sprawdziło. Przejęcie klawiatury/myszy zawsze poprzedzać tym testem."""
        a = self.dhash()
        time.sleep(window)
        return self.hamming(self.dhash(), a) > tol

    def guarded_batch(self, steps: list[dict], expect, tries: int = 3,
                      respect_user: bool = True) -> dict:
        """SZYBKO I PEWNIE: batch akcji + POSTCOND (verify_texts) + retry. Naprawia ciche
        porażki — np. `type` który nie złapał fokusu (contenteditable jeszcze nie gotowy):
        pierwszy raz tekst nie ląduje, verify_texts to wykrywa, retry ląduje. Łączy zysk
        prędkości (batch+1 OCR) z niezawodnością (verify-before-act). expect: tekst/lista.
        respect_user: NIE przejmuj wejścia, gdy na maszynie ktoś aktywnie pracuje."""
        if respect_user and self.user_active():
            return {"ok": False, "tries": 0, "reason": "user-active",
                    "missing": [expect] if isinstance(expect, str) else list(expect)}
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
        """Kotwica: czy oczekiwany tekst JEST na ekranie. Idzie przez verify_texts
        (OCR na hoście + cache dhash ~1,5 s; ekran statyczny ~1,1 s) zamiast
        node-side ui/query/verify (~4,6–6 s)."""
        return bool(self.verify_texts([text]).get(text))

    def ocr_host(self, png: bytes) -> str | None:
        """OCR zrzutu na HOŚCIE zamiast na węźle — wykorzystuje moc obliczeniową hosta
        (transport base64 po LAN ~260 KB @1600 to grosze). Zmierzone na lenovo:
        tesseract host ~0,45 s vs node-side OCR ~4,6 s (10×). None gdy brak tesseracta
        na hoście (wtedy fallback na ścieżkę node w verify_texts)."""
        if not shutil.which("tesseract"):
            return None
        r = subprocess.run(["tesseract", "stdin", "stdout", "--oem", "1", "--psm", "3"],
                           input=png, capture_output=True, timeout=30)
        return r.stdout.decode("utf-8", "replace") if r.returncode == 0 else None

    def verify_texts(self, texts: list[str], max_width: int = 1600,
                     engine: str = "host", region: tuple | None = None) -> dict:
        """SZYBKA wielo-kotwica: JEDNO capture + JEDNO OCR + N sprawdzeń. Zwraca {tekst: bool}.

        engine='host' (domyślnie): zrzut wraca base64 po LAN i OCR liczy HOST —
        ~1,5 s end-to-end (capture 1,1 + OCR 0,45) vs ~4,6+ s node-side. Dodatkowo
        cache po dhash: gdy ekran się nie zmienił od poprzedniego wywołania, OCR
        pomijany w całości (percepcja ~= koszt samego capture).
        engine='node': stara ścieżka (plik na węźle + ocr://host) — gdy host bez tesseracta.
        region=(cx,cy,w,h): capture TYLKO wycinka wokół spodziewanej kotwicy
        (mniejszy transfer i OCR); wymaga connectora z obsługą crop (redeploy ≥2026-07-05)."""
        payload: dict = {"base64": engine == "host", "max_width": max_width}
        if region:
            rcx, rcy, rw, rh = region
            payload.update({"cx": int(rcx), "cy": int(rcy), "crop_w": int(rw), "crop_h": int(rh),
                            "max_width": 0})
        cap = self._run("kvm://host/screen/query/capture", payload)
        if engine == "host" and not cap.get("pngBase64"):
            cap = self._run("kvm://host/screen/query/capture", payload)  # transient: retry raz
        if engine == "host" and cap.get("pngBase64"):
            png = base64.b64decode(cap["pngBase64"])
            h = self.dhash(png)
            if self._ocr_cache and self.hamming(h, self._ocr_cache[0]) <= 4:
                ocr = self._ocr_cache[1]           # ekran bez zmian — OCR z cache
            else:
                ocr = (self.ocr_host(png) or "").lower()
                if ocr:
                    self._ocr_cache = (h, ocr)
            if ocr:
                return {t: (t.lower() in ocr) for t in texts}
        path = cap.get("path")                      # fallback: OCR na węźle
        if not path:
            return {t: False for t in texts}
        try:
            ocr = (self._run("ocr://host/image/query/text", {"image": path}).get("text") or "").lower()
        except Exception:                           # węzeł bez trasy ocr:// — uczciwe "nie wiem" = False
            return {t: False for t in texts}
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
