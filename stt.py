"""Lokale Dauer-Spracherkennung: sounddevice + einfache Pegel-VAD + faster-whisper (offline nach Modell-Download)."""
import queue
import threading
from collections import deque

from .config import home_dir

HALLUCINATIONS = ("untertitel", "amara.org", "vielen dank fürs zuschauen", "copyright")


class Listener(threading.Thread):
    def __init__(self, settings, on_text, on_level, on_state, busy):
        super().__init__(daemon=True)
        self.s, self.on_text, self.on_level, self.on_state, self.busy = settings, on_text, on_level, on_state, busy
        self.muted = False
        self._quit = threading.Event()

    def stop(self):
        self._quit.set()

    def run(self):
        try:
            import numpy as np
            import sounddevice as sd
            from faster_whisper import WhisperModel
        except Exception as ex:
            self.on_state(f"error:Spracherkennung nicht verfügbar ({ex})")
            return
        try:
            self.on_state("loading")
            model = WhisperModel(self.s.get("whisper_model"), device="cpu", compute_type="int8",
                                 download_root=str(home_dir() / "models"))
            self.on_state("ready")
            sr, block = 16000, 512
            q = queue.Queue()

            def cb(indata, frames, t, status):
                q.put(indata[:, 0].copy())

            floor, active, silence = 0.005, False, 0
            speech, pre = [], deque(maxlen=10)
            with sd.InputStream(samplerate=sr, channels=1, dtype="float32", blocksize=block, callback=cb):
                while not self._quit.is_set():
                    try:
                        blk = q.get(timeout=0.2)
                    except queue.Empty:
                        continue
                    if self.muted or self.busy():
                        speech, active = [], False
                        pre.clear()
                        self.on_level(0.0)
                        continue
                    rms = float((blk ** 2).mean() ** 0.5)
                    self.on_level(min(1.0, rms * 14))
                    if not active:
                        floor = 0.96 * floor + 0.04 * rms
                        pre.append(blk)
                        if rms > max(0.015, floor * 3.5):
                            active, speech, silence = True, list(pre), 0
                            self.on_state("hearing")
                    else:
                        speech.append(blk)
                        silence = silence + 1 if rms < max(0.01, floor * 2.5) else 0
                        if silence > int(0.8 * sr / block) or len(speech) > int(15 * sr / block):
                            audio = np.concatenate(speech)
                            active, speech = False, []
                            pre.clear()
                            self.on_state("ready")
                            if len(audio) > 0.35 * sr:
                                self._transcribe(model, audio)
                                while not q.empty():
                                    q.get_nowait()
        except Exception as ex:
            self.on_state(f"error:Mikrofon/Spracherkennung: {ex}")

    def _transcribe(self, model, audio):
        prompt = "YAVIS, Master. " + ", ".join(self.s.get("wake_words")) + "."
        segs, _ = model.transcribe(audio, language="de", beam_size=1, temperature=0.0,
                                   condition_on_previous_text=False, initial_prompt=prompt,
                                   no_speech_threshold=0.6)
        text = " ".join(s.text for s in segs).strip()
        low = text.lower()
        if len(text) < 2 or any(h in low for h in HALLUCINATIONS):
            return
        self.on_text(text)
