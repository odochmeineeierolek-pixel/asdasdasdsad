"""Lokaler Musikplayer (mp3/wav/wma/m4a) über Windows-MCI. Alle MCI-Aufrufe laufen in einem Thread."""
import queue
import threading
from pathlib import Path

from .mci import mci

EXTS = {".mp3", ".wav", ".wma", ".m4a"}
ALIAS = "ymusic"


class MusicPlayer:
    def __init__(self, settings):
        self.s = settings
        self.tracks = []
        self.index = -1
        self.state = "stopped"
        self._q = queue.Queue()
        threading.Thread(target=self._run, daemon=True).start()

    def load_folder(self, folder):
        try:
            self.tracks = sorted(p for p in Path(folder).rglob("*") if p.suffix.lower() in EXTS)[:5000]
        except Exception:
            self.tracks = []
        return len(self.tracks)

    def ensure_loaded(self):
        if not self.tracks and self.s.get("music_folder"):
            self.load_folder(self.s.get("music_folder"))
        return bool(self.tracks)

    def find(self, query):
        q = query.lower().strip()
        for i, p in enumerate(self.tracks):
            if q and q in p.stem.lower():
                return i
        return None

    def play(self, index=None):
        if not self.ensure_loaded():
            return None
        if index is None:
            index = 0 if self.index < 0 else self.index
        self.index = index % len(self.tracks)
        self._q.put(("play", self.index))
        return self.tracks[self.index].stem

    def next(self):
        return self.play((self.index + 1) if self.index >= 0 else 0)

    def prev(self):
        return self.play((self.index - 1) if self.index >= 0 else 0)

    def pause(self):
        self._q.put(("pause", None))

    def resume(self):
        self._q.put(("resume", None))

    def stop(self):
        self._q.put(("stop", None))

    def set_volume(self, percent):
        percent = max(0, min(100, int(percent)))
        self.s.set("volume", percent)
        self._q.put(("volume", percent))

    def _vol(self):
        mci(f"setaudio {ALIAS} volume to {int(self.s.get('volume')) * 10}")

    def _close(self):
        mci(f"stop {ALIAS}")
        mci(f"close {ALIAS}")

    def _run(self):
        while True:
            try:
                cmd, arg = self._q.get(timeout=0.3)
            except queue.Empty:
                cmd, arg = None, None
            if cmd == "play":
                self._close()
                err, _ = mci(f'open "{self.tracks[arg]}" type mpegvideo alias {ALIAS}')
                if err == 0:
                    self._vol()
                    mci(f"play {ALIAS}")
                    self.state = "playing"
                else:
                    self.state = "stopped"
            elif cmd == "pause":
                mci(f"pause {ALIAS}")
                self.state = "paused"
            elif cmd == "resume":
                mci(f"resume {ALIAS}")
                self.state = "playing"
            elif cmd == "stop":
                self._close()
                self.state = "stopped"
            elif cmd == "volume":
                self._vol()
            elif self.state == "playing" and self.tracks:
                _, mode = mci(f"status {ALIAS} mode")
                if mode == "stopped":
                    self.index = (self.index + 1) % len(self.tracks)
                    self._q.put(("play", self.index))
