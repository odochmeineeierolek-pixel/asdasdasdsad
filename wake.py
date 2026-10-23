"""Erkennung der Aktivierungswörter (tolerant gegenüber Whisper-Schreibweisen)."""
import difflib
import re

FILLER = {"hey", "hallo", "hi", "okay", "ok", "na", "he", "du", "liebe", "lieber"}


def split_wake(text: str, wake_words, threshold: float = 0.82):
    """Gibt (gefunden, Rest) zurück. Das Wort muss in den ersten 4 Wörtern stehen."""
    names = [w.strip().lower() for w in wake_words if w and " " not in w.strip() and len(w.strip()) >= 3]
    if not names:
        return False, text
    for m in list(re.finditer(r"\w+", text))[:4]:
        w = m.group().lower()
        if w in FILLER:
            continue
        if any(difflib.SequenceMatcher(None, w, n).ratio() >= threshold for n in names):
            rest = text[m.end():].lstrip(" ,.:;!?-–")
            return True, rest
        break  # erstes inhaltliches Wort passt nicht
    return False, text
