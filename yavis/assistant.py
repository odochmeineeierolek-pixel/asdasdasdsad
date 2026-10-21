"""Kern: verbindet Spracherkennung, Befehle, Sprachmodell und Sprachausgabe."""
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse

from . import voices
from .brain import Brain
from .config import Settings, home_dir
from .memory import Memory
from .music import MusicPlayer
from .skills import Skills
from .stt import Listener
from .voices import EMO_MAP, Speaker
from .wake import split_wake


class Hooks:
    """Wird von der Oberfläche überschrieben."""
    def log(self, role, text): pass
    def state(self, s): pass
    def emotion(self, e): pass
    def level(self, v): pass
    def notice(self, kind): pass
    def confirm(self, question): return False


def pop_sentence(buf):
    for m in re.finditer(r"[.!?…]+\s|\n", buf):
        if m.end() >= 14:
            return buf[:m.end()].strip(), buf[m.end():]
    return None, buf


class Assistant:
    def __init__(self, hooks=None, settings=None, memory=None):
        self.hooks = hooks or Hooks()
        self.s = settings or Settings()
        self.mem = memory or Memory(home_dir() / "memory.db")
        self.speaker = Speaker(self.s, on_speaking=self._on_speaking, on_idle=self._on_idle)
        self.music = MusicPlayer(self.s)
        self.brain = Brain(self.s, self.mem)
        self.skills = Skills(self.s, self.mem, self.music)
        self.skills.notify = lambda text: self.say(text, "neutral")
        self.skills.stop_cb = self.stop
        self.history = []
        self.last_reply = ""
        self.awake_until = 0.0
        self.listener = None
        self._cancel = threading.Event()
        self.pool = ThreadPoolExecutor(max_workers=1)

    @property
    def title(self):
        return self.s.get("user_title") or "Master"

    # ---------- Zuhören ----------
    def start_listening(self):
        if self.listener and self.listener.is_alive():
            return
        self.listener = Listener(self.s, self.on_heard, self.hooks.level, self._listener_state, self.speaker.busy)
        self.listener.start()

    def set_muted(self, muted):
        if self.listener:
            self.listener.muted = muted
        self.hooks.state("muted" if muted else "idle")

    def activate(self):
        """Mikrofon-Taste: die nächsten 10 Sekunden ohne Namen zuhören."""
        self.awake_until = time.time() + 10
        self.start_listening()

    def _listener_state(self, st):
        if st.startswith("error:"):
            self.hooks.log("system", st[6:])
            self.hooks.state("error")
        elif st == "hearing":
            self.hooks.state("listening")
        elif st == "ready":
            self.hooks.state("idle")
        elif st == "loading":
            self.hooks.state("loading")

    def on_heard(self, text):
        found, rest = split_wake(text, self.s.get("wake_words"))
        now = time.time()
        if found:
            if rest.strip():
                self.submit(rest)
            else:
                self.say(f"Ja, {self.title}?", "nett")
                self.awake_until = now + 12
        elif now < self.awake_until:
            self.submit(text)

    # ---------- Eingabe ----------
    def submit(self, text):
        self.pool.submit(self._process, text.strip())

    def stop(self):
        self._cancel.set()
        self.speaker.stop()
        self.hooks.state("idle")

    def _on_speaking(self, flag):
        self.hooks.state("speaking" if flag else "idle")

    def _on_idle(self):
        self.awake_until = time.time() + 8  # Folgefrage ohne Namen möglich

    def say(self, text, emotion="neutral", log=True):
        mood = self.s.get("mood")
        emo = mood if mood in ("neutral", "nett", "boese", "traurig") else emotion
        if log:
            self.hooks.log("yavis", text)
        self.hooks.emotion(emo)
        self.speaker.say(text, emo)

    def _process(self, text):
        if not text:
            return
        self._cancel.clear()
        self.hooks.log("user", text)
        self.mem.log(f"Eingabe: {text[:80]}")
        self.hooks.state("thinking")
        try:
            res = self.skills.handle(text)
            if res is None:
                self._ask(text, history=True)
            else:
                self._apply(res)
        except Exception as ex:
            self.say(f"Da ist ein Fehler passiert, {self.title}: {str(ex)[:100]}", "traurig")
        finally:
            if not self.speaker.speaking:
                self.hooks.state("idle")

    def _apply(self, res):
        if res.confirm and not self.hooks.confirm(res.confirm):
            self.say(f"Okay, abgebrochen, {self.title}.", "neutral")
            return
        text = res.text
        if res.action:
            text = res.action() or text
        if text and res.speak:
            self.say(text, res.emotion or "neutral")
        elif text:
            self.hooks.log("yavis", text)
        if res.llm_task:
            self._ask(res.llm_task, history=False, sources=res.sources)

    def _ask(self, prompt, history=True, sources=None):
        if not self.brain.available():
            self.say(f"Mein lokales Gehirn Ollama läuft noch nicht, {self.title}. Öffne die Einstellungen und installiere es.", "traurig")
            self.hooks.notice("ollama_missing")
            return
        if not self.brain.has_model():
            self.say(f"Das Sprachmodell ist noch nicht geladen, {self.title}. Du kannst es in den Einstellungen herunterladen.", "traurig")
            self.hooks.notice("model_missing")
            return
        msgs = (self.history[-10:] if history else []) + [{"role": "user", "content": prompt}]
        emotion, pending, buf, full = None, "", "", ""
        for chunk in self.brain.stream(msgs, self._cancel):
            if self._cancel.is_set():
                break
            if emotion is None:
                pending += chunk
                m = re.match(r"\s*\[(\w+)\]\s*", pending)
                if m:
                    emotion, chunk = EMO_MAP.get(m.group(1).lower(), "neutral"), pending[m.end():]
                elif len(pending) > 24 or (pending.strip() and not pending.lstrip().startswith("[")):
                    emotion, chunk = "neutral", pending
                else:
                    continue
            buf += chunk
            full += chunk
            while True:
                sent, buf = pop_sentence(buf)
                if not sent:
                    break
                self.say(sent, emotion)
        if buf.strip() and not self._cancel.is_set():
            self.say(buf.strip(), emotion or "neutral")
        if self._cancel.is_set():
            return
        if sources:
            self.hooks.log("system", "Quellen: " + ", ".join(sources))
            doms = [urlparse(u).netloc.replace("www.", "") for u in sources]
            self.say("Quellen: " + ", ".join(doms) + ".", "neutral", log=False)
        full = full.strip()
        self.last_reply = full
        if history:
            self.history += [{"role": "user", "content": prompt}, {"role": "assistant", "content": full}]
            self.history = self.history[-20:]

    # ---------- Lernen aus Feedback ----------
    def feedback(self, good, note=""):
        if good:
            self.mem.add("feedback", f"Gute Antwort: {self.last_reply[:120]}", 1)
        else:
            self.mem.add("feedback", note.strip() or f"Antwort war nicht gut: {self.last_reply[:120]}", 0)

    def generate_text(self, prompt):
        """Für den Verkaufs-Tab: Text erzeugen, nicht vorlesen."""
        if not self.brain.available() or not self.brain.has_model():
            return "Ollama oder das Modell ist nicht bereit (siehe Einstellungen)."
        return re.sub(r"^\s*\[\w+\]\s*", "", self.brain.complete(prompt))
