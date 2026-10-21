"""YAVIS – Startpunkt. Läuft ohne Konsolenfenster (PyInstaller --noconsole)."""
import importlib
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

FATAL = ["PySide6.QtWidgets", "faster_whisper", "ctranslate2", "sounddevice", "numpy", "edge_tts", "psutil", "PIL"]
OPTIONAL = ["ddgs", "pyperclip", "pyttsx3"]


def selftest():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    lines, ok = [], True
    for mod in FATAL + OPTIONAL:
        try:
            importlib.import_module(mod)
            lines.append(f"OK    {mod}")
        except Exception as ex:
            lines.append(f"{'FAIL' if mod in FATAL else 'WARN'}  {mod}: {ex}")
            ok = ok and mod not in FATAL
    try:
        from PySide6.QtWidgets import QApplication
        from yavis.ui import MainWindow
        app = QApplication([])
        MainWindow(start_listener=False)
        lines.append("OK    Fenster wurde aufgebaut")
    except Exception as ex:
        ok = False
        lines.append(f"FAIL  Fenster: {ex!r}")
    out = Path(sys.executable).with_name("selftest.txt") if getattr(sys, "frozen", False) else Path("selftest.txt")
    out.write_text("\n".join(lines) + f"\nERGEBNIS: {'BESTANDEN' if ok else 'FEHLGESCHLAGEN'}\n", encoding="utf-8")
    print("\n".join(lines))
    return 0 if ok else 1


def main():
    if "--selftest" in sys.argv:
        return selftest()
    from PySide6.QtCore import QLockFile
    from PySide6.QtWidgets import QApplication
    from yavis.config import home_dir
    from yavis.ui import MainWindow
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    lock = QLockFile(str(home_dir() / "yavis.lock"))
    if not lock.tryLock(200):
        return 0  # läuft bereits
    win = MainWindow()
    if "--minimized" not in sys.argv:
        win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
