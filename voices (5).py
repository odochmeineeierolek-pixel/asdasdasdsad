"""Stimmen: 16 Grundstimmen x Stilvarianten (56 Voreinstellungen) über Microsoft-Edge-Online-Stimmen
(kostenlos, ohne Schlüssel, Internet nötig) mit Offline-Rückfall über Windows-Stimmen (SAPI)."""
import asyncio
import os
import queue
import re
import threading
import time
from dataclasses import dataclass
from pathlib import Path

from .config import home_dir
from .mci import mci


@dataclass(frozen=True)
class Voice:
    id: str
    label: str
    edge: str
    gender: str
    pitch: int
    rate: int
    key: str


_F = [("de-DE-KatjaNeural", "Katja", "DE"), ("de-DE-AmalaNeural", "Amala", "DE"),
      ("de-DE-SeraphinaMultilingualNeural", "Seraphina", "DE"), ("de-AT-IngridNeural", "Ingrid", "AT"),
      ("de-CH-LeniNeural", "Leni", "CH"), ("en-US-AvaMultilingualNeural", "Ava", "multilingual"),
      ("en-US-EmmaMultilingualNeural", "Emma", "multilingual"), ("fr-FR-VivienneMultilingualNeural", "Vivienne", "multilingual")]
_M = [("de-DE-ConradNeural", "Conrad", "DE"), ("de-DE-KillianNeural", "Killian", "DE"),
      ("de-DE-FlorianMultilingualNeural", "Florian", "DE"), ("de-AT-JonasNeural", "Jonas", "AT"),
      ("de-CH-JanNeural", "Jan", "CH"), ("en-US-AndrewMultilingualNeural", "Andrew", "multilingual"),
      ("en-US-BrianMultilingualNeural", "Brian", "multilingual"), ("fr-FR-RemyMultilingualNeural", "Remy", "multilingual")]
_SF = [("warm", "warm & natürlich", 0, 0), ("samtig", "samtig, tief & langsam", -6, -12),
       ("hell", "hell & jung", 8, 4), ("mama", "Mama – sanft & fürsorglich", -3, -8)]
_SM = [("ruhig", "ruhig & freundlich", 0, 0), ("hart", "hart & tief", -16, -4),
       ("energisch", "energisch & schnell", 4, 10)]


def build_voices():
    out = []
    for group, styles, g in ((_F, _SF, "f"), (_M, _SM, "m")):
        for edge, name, region in group:
            for key, desc, pitch, rate in styles:
                out.append(Voice(f"{name.lower()}-{key}", f"{name} ({region}) – {desc}", edge, g, pitch, rate, key))
    return out


VOICES = build_voices()
BY_ID = {v.id: v for v in VOICES}
DEFAULT_VOICE = "katja-warm"

_ALIAS = {"sexy": "samtig", "mommy": "mama", "mutti": "mama", "mutter": "mama", "jung": "hell",
          "böse": "hart", "stark": "hart", "tief": "tief", "männlich": "mann", "weiblich": "frau"}
_STOP = {"die", "der", "das", "stimme", "wechsle", "wechsel", "zu", "auf", "zur", "eine", "ändere", "nimm",
         "bitte", "mir", "mit", "und", "in", "ein", "mal", "nutze", "stell", "stelle", "um", "ändern"}


def find_voice(query):
    toks = {_ALIAS.get(t, t) for t in re.findall(r"\w+", query.lower())} - _STOP
    gender = "f" if toks & {"frau", "mädchen"} else "m" if toks & {"mann", "männer"} else None
    best, score = None, 0
    for v in VOICES:
        vt = set(re.findall(r"\w+", (v.label + " " + v.key).lower()))
        hits = sum(1 for t in toks if any(t == w or (len(t) >= 4 and len(w) >= 4 and (t.startswith(w) or w.startswith(t))) for w in vt))
        s = 2 * hits + (1 if gender and v.gender == gender else 0)
        if gender and v.gender != gender:
            s -= 1
        if s > score:
            best, score = v, s
    return best


MOOD_TWEAK = {"neutral": (0, 0), "nett": (3, 0), "traurig": (-8, -18), "boese": (-5, 10)}
EMO_MAP = {"nett": "nett", "lieb": "nett", "freundlich": "nett", "glücklich": "nett", "neutral": "neutral",
           "traurig": "traurig", "boese": "boese", "böse": "boese", "wütend": "boese", "sauer": "boese"}


def clean_text(t):
    t = re.sub(r"[*_`#>]+", "", t)
    t = re.sub(r"https?://\S+", "", t)
    return re.sub(r"\s+", " ", t).strip()


class Speaker:
    """Zwei Threads: Synthese (Text -> mp3) und Wiedergabe. Satzweise, damit YAVIS schnell zu sprechen beginnt."""

    def __init__(self, settings, on_speaking=None, on_idle=None):
        self.s = settings
        self.on_speaking = on_speaking or (lambda f: None)
        self.on_idle = on_idle or (lambda: None)
        self._sq, self._pq = queue.Queue(), queue.Queue()
        self._lock = threading.Lock()
        self._pending = 0
        self._gen = 0
        self._last_end = 0.0
        self.tmp = home_dir() / "tmp"
        self.tmp.mkdir(exist_ok=True)
        threading.Thread(target=self._synth_loop, daemon=True).start()
        threading.Thread(target=self._play_loop, daemon=True).start()

    # --- API ---
    @property
    def speaking(self):
        return self._pending > 0

    def busy(self):
        return self._pending > 0 or (time.time() - self._last_end) < 0.6

    def say(self, text, emotion="neutral"):
        text = clean_text(text)
        if not text:
            return
        with self._lock:
            self._pending += 1
            first = self._pending == 1
        if first:
            self.on_speaking(True)
        self._sq.put((self._gen, text, emotion))

    def stop(self):
        with self._lock:
            self._gen += 1
        n = 0
        for q in (self._sq, self._pq):
            try:
                while True:
                    q.get_nowait()
                    n += 1
            except queue.Empty:
                pass
        self._done(n)

    # --- intern ---
    def _done(self, n=1):
        if n <= 0:
            return
        with self._lock:
            self._pending = max(0, self._pending - n)
            idle = self._pending == 0
        if idle:
            self._last_end = time.time()
            self.on_speaking(False)
            self.on_idle()

    def _params(self, emotion):
        v = BY_ID.get(self.s.get("voice")) or BY_ID[DEFAULT_VOICE]
        tp, tr = MOOD_TWEAK.get(emotion, (0, 0))
        pitch = max(-60, min(60, v.pitch + int(self.s.get("voice_pitch")) + tp))
        rate = max(-60, min(60, v.rate + int(self.s.get("voice_rate")) + tr))
        return v, pitch, rate

    def _synth_loop(self):
        while True:
            gen, text, emo = self._sq.get()
            if gen != self._gen:
                self._done()
                continue
            v, pitch, rate = self._params(emo)
            item = None
            if not self.s.get("offline_voice"):
                try:
                    path = str(self.tmp / f"s{int(time.time() * 1000) % 10**9}.mp3")
                    asyncio.run(self._edge(text, v.edge, rate, pitch, path))
                    item = ("mp3", path)
                except Exception:
                    item = None
            if item is None:
                item = ("sapi", text, rate)
            self._pq.put((gen, item))

    @staticmethod
    async def _edge(text, voice, rate, pitch, path):
        import edge_tts
        await edge_tts.Communicate(text, voice, rate=f"{rate:+d}%", pitch=f"{pitch:+d}Hz").save(path)

    def _play_loop(self):
        while True:
            gen, item = self._pq.get()
            try:
                if gen == self._gen:
                    if item[0] == "mp3":
                        self._play_mp3(item[1], gen)
                    else:
                        self._play_sapi(item[1], item[2], gen)
            except Exception:
                pass
            finally:
                if item[0] == "mp3":
                    try:
                        os.remove(item[1])
                    except OSError:
                        pass
            self._done()

    def _play_mp3(self, path, gen):
        alias = f"yv{int(time.time() * 1000) % 10**6}"
        err, _ = mci(f'open "{path}" type mpegvideo alias {alias}')
        if err:
            return
        mci(f"setaudio {alias} volume to {int(self.s.get('voice_volume')) * 10}")
        mci(f"play {alias}")
        while gen == self._gen:
            _, mode = mci(f"status {alias} mode")
            if mode != "playing":
                break
            time.sleep(0.03)
        mci(f"stop {alias}")
        mci(f"close {alias}")

    def _play_sapi(self, text, rate, gen):
        import pyttsx3
        eng = pyttsx3.init()
        for v in eng.getProperty("voices"):
            if any(k in (v.name + str(getattr(v, "languages", ""))).lower() for k in ("german", "deutsch", "de-de", "hedda", "katja", "stefan")):
                eng.setProperty("voice", v.id)
                break
        eng.setProperty("rate", int(175 * (1 + rate / 100)))
        eng.setProperty("volume", int(self.s.get("voice_volume")) / 100)
        eng.say(text)
        eng.runAndWait()
