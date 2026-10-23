"""Minimaler Zugriff auf die Windows-Mediensteuerung (MCI) ohne Zusatzpakete."""
import ctypes
import os


def mci(cmd: str):
    if os.name != "nt":
        return 1, ""
    buf = ctypes.create_unicode_buffer(256)
    err = ctypes.windll.winmm.mciSendStringW(cmd, buf, 255, 0)
    return err, buf.value
