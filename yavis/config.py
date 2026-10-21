"""Einstellungen (JSON) und Speicherort."""
import copy
import json
import os
import threading
from pathlib import Path


def home_dir() -> Path:
    base = os.environ.get("YAVIS_HOME")
    if base:
        p = Path(base)
    elif os.name == "nt":
        p = Path(os.environ.get("APPDATA", str(Path.home()))) / "YAVIS"
    else:
        p = Path.home() / ".yavis"
    p.mkdir(parents=True, exist_ok=True)
    return p


DEFAULTS = {
    "user_title": "Master",
    "wake_words": ["yavis", "jarvis"],
    "ollama_url": "http://localhost:11434",
    "model": "llama3.2:3b",
    "voice": "katja-warm",
    "voice_rate": 0,
    "voice_pitch": 0,
    "offline_voice": False,
    "mood": "auto",          # auto | neutral | nett | boese | traurig
    "show_text": False,      # Standard: nur Sprache
    "always_listen": True,
    "whisper_model": "small",
    "allowed_programs": None,  # None = Standardliste
    "custom_programs": {},     # Name -> Pfad
    "music_folder": "",
    "volume": 80,            # Musik
    "voice_volume": 80,      # Stimme
    "theme": {"accent": "#ffd400", "primary": "#e10600", "bg": "#0a0a0a", "panel": "#121212", "text": "#f2f2f2"},
    "font_size": 14,
    "orb_scale": 100,
    "prog_cat": {},
    "prog_order": [],
    "prog_categories": ["Browser", "Spiele", "Medien", "Kommunikation", "Büro", "Entwicklung", "System", "Eigene"],
    "project_categories": ["Arbeit", "Privat", "Lernen", "Sonstiges"],
    "projects": [],          # [{id,name,cat,note}]
    "macros": {},            # Satz -> "chrome, word, spotify"
    "task_cards": [
        {"title": "Chat & Fragen", "desc": "Fundierte Antworten, komplexe Themen erklärt", "prompt": "Erkläre mir einfach: "},
        {"title": "Texte schreiben", "desc": "Von E-Mails bis Blogartikel", "prompt": "Schreibe einen Text über: "},
        {"title": "Code & Programmieren", "desc": "Schreiben, erklären, optimieren", "prompt": "Hilf mir beim Programmieren: "},
        {"title": "Analysieren & Planen", "desc": "Aufgaben strukturieren, Tag planen", "prompt": "plane meinen tag"},
        {"title": "Ideen & Kreativität", "desc": "Brainstorming und Konzepte", "prompt": "Gib mir 5 Ideen für: "},
        {"title": "Verkauf & Preise", "desc": "Beschreibungen, Angebote, Preisrecherche", "prompt": "preise "},
    ],
    "quick": [
        {"name": "YouTube öffnen", "cmd": "öffne youtube"},
        {"name": "Musik abspielen", "cmd": "spiel musik"},
        {"name": "Webrecherche", "cmd": "recherchiere "},
        {"name": "Wetter", "cmd": "wetter"},
        {"name": "Screenshot", "cmd": "mach einen screenshot"},
    ],
}


class Settings:
    def __init__(self, path=None):
        self.path = Path(path) if path else home_dir() / "settings.json"
        self._lock = threading.RLock()
        self.data = copy.deepcopy(DEFAULTS)
        self.load()

    def load(self):
        try:
            loaded = json.loads(self.path.read_text(encoding="utf-8"))
            with self._lock:
                for k, v in loaded.items():
                    if k in DEFAULTS:
                        self.data[k] = v
        except Exception:
            pass

    def save(self):
        with self._lock:
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8")
            tmp.replace(self.path)

    def get(self, key):
        with self._lock:
            return copy.deepcopy(self.data.get(key, DEFAULTS.get(key)))

    def set(self, key, value):
        with self._lock:
            self.data[key] = value
        self.save()
