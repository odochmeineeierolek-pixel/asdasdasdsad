import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
os.environ["YAVIS_HOME"] = tempfile.mkdtemp()

from yavis import programs, voices
from yavis.config import Settings
from yavis.memory import Memory
from yavis.skills import Skills, safe_calc
from yavis.wake import split_wake


class FakeMusic:
    tracks = []
    def play(self, i=None): return None
    def next(self): return None
    def prev(self): return None
    def pause(self): pass
    def resume(self): pass
    def stop(self): pass
    def set_volume(self, v): pass
    def ensure_loaded(self): return False
    def find(self, q): return None


def make():
    d = tempfile.mkdtemp()
    s = Settings(os.path.join(d, "s.json"))
    m = Memory(os.path.join(d, "m.db"))
    return Skills(s, m, FakeMusic()), s, m


def test_catalog_and_voices():
    assert len(programs.CATALOG) >= 40 and len({e.id for e in programs.CATALOG}) == len(programs.CATALOG)
    assert len(voices.VOICES) >= 30 and len({v.id for v in voices.VOICES}) == len(voices.VOICES)
    assert voices.BY_ID[voices.DEFAULT_VOICE]


def test_wake():
    assert split_wake("Hey Yavis, öffne YouTube", ["yavis"]) == (True, "öffne YouTube")
    assert split_wake("Yarvis wie spät ist es", ["yavis"])[0]
    assert split_wake("Hallo zusammen, schönes Wetter", ["yavis"])[0] is False
    assert split_wake("Computer, hilf mir", ["computer"])[0]


def test_calc_is_safe():
    assert safe_calc("2+3*4") == 14
    for bad in ("__import__('os')", "2**9999", "open('x')"):
        try:
            safe_calc(bad)
            assert False, bad
        except Exception:
            pass


def test_skill_routing():
    sk, s, m = make()
    assert "Uhr" in sk.handle("Wie spät ist es?").text
    assert "14" in sk.handle("was ist 2 plus 3 mal 4").text
    assert sk.handle("Erzähl mir etwas über die Geschichte Roms") is None
    r = sk.handle("sei neutral")
    assert s.get("mood") == "neutral" and r.emotion == "neutral"
    assert "Master" in sk.handle("sag mal wie viel uhr").text
    assert "Gemerkt" in sk.handle("merk dir dass ich Kaffee mag").text
    assert m.facts() == ["ich kaffee mag"]
    assert sk.handle("Kaufe das Produkt").text.startswith("Das mache ich nicht")
    assert sk.handle("wechsle die stimme zu harter mann").text
    assert "hart" in s.get("voice")


def test_programs_need_permission():
    sk, s, m = make()
    s.set("allowed_programs", ["calc"])
    assert "nicht freigegeben" in sk.handle("öffne chrome").text
    assert "kenne ich nicht" in sk.handle("öffne blablaprogramm").text
    import webbrowser
    opened = []
    webbrowser.open = lambda url, *a, **k: opened.append(url)
    assert sk.handle("öffne youtube").text.startswith("Ich öffne youtube")
    assert opened == ["https://www.youtube.com"]


def test_memory_crud():
    _, _, m = make()
    i = m.add("notes", "Test")
    assert m.list("notes")[0][1] == "Test"
    m.delete("notes", i)
    assert m.list("notes") == []
    try:
        m.add("x; drop table", "a")
        assert False
    except ValueError:
        pass




def test_memory_migrates_old_schema():
    import sqlite3
    d = tempfile.mkdtemp()
    path = os.path.join(d, "old.db")
    c = sqlite3.connect(path)
    c.execute("CREATE TABLE facts(key TEXT, value TEXT)")
    c.commit(); c.close()
    m = Memory(path)
    m.add("facts", "neu")
    assert m.facts() == ["neu"]


def test_macro_and_categories():
    sk, s, m = make()
    import webbrowser
    opened = []
    webbrowser.open = lambda url, *a, **k: opened.append(url)
    s.set("macros", {"Chillmodus": "youtube, netflix"})
    r = sk.handle("chillmodus")
    assert "youtube" in r.text and len(opened) == 2
    assert programs.category_of(s, programs.BY_ID["chrome"]) == "Browser"
    assert s.get("theme")["accent"] == "#ffd400" and len(s.get("task_cards")) == 6


if __name__ == "__main__":
    for n, f in list(globals().items()):
        if n.startswith("test_"):
            f()
            print("ok", n)
