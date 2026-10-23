"""Programmkatalog (44 Einträge), Freigabe-Liste und sicherer Start. Nur Katalogeinträge oder vom Nutzer
hinzugefügte Pfade werden gestartet – nie frei erfundene Befehle."""
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

NO_WINDOW = 0x08000000


@dataclass(frozen=True)
class Entry:
    id: str
    name: str
    kind: str      # "cmd" (start <ziel>), "uri", "lnk" (Startmenü-Suche), "path"
    target: str
    aliases: tuple


def _e(i, n, k, t, *a):
    return Entry(i, n, k, t, tuple(x.lower() for x in (a or (n,))))


CATALOG = [
    _e("chrome", "Google Chrome", "cmd", "chrome", "chrome", "google chrome"),
    _e("edge", "Microsoft Edge", "cmd", "msedge", "edge", "microsoft edge"),
    _e("firefox", "Firefox", "cmd", "firefox", "firefox"),
    _e("brave", "Brave", "lnk", "brave", "brave"),
    _e("opera", "Opera", "lnk", "opera", "opera"),
    _e("spotify", "Spotify", "uri", "spotify:", "spotify"),
    _e("steam", "Steam", "uri", "steam://open/main", "steam"),
    _e("discord", "Discord", "lnk", "discord", "discord"),
    _e("epic", "Epic Games", "lnk", "epic games", "epic games", "epic"),
    _e("battlenet", "Battle.net", "lnk", "battle.net", "battle.net", "battlenet", "blizzard"),
    _e("gog", "GOG Galaxy", "lnk", "gog galaxy", "gog", "gog galaxy"),
    _e("ea", "EA App", "lnk", "ea", "ea app", "origin"),
    _e("ubisoft", "Ubisoft Connect", "lnk", "ubisoft connect", "ubisoft", "uplay"),
    _e("minecraft", "Minecraft Launcher", "lnk", "minecraft", "minecraft"),
    _e("notepad", "Editor", "cmd", "notepad", "editor", "notepad", "notizblock"),
    _e("calc", "Rechner", "cmd", "calc", "rechner", "taschenrechner"),
    _e("explorer", "Datei-Explorer", "cmd", "explorer", "explorer", "datei explorer", "dateien"),
    _e("paint", "Paint", "cmd", "mspaint", "paint"),
    _e("taskmgr", "Task-Manager", "cmd", "taskmgr", "task-manager", "taskmanager", "task manager"),
    _e("settings", "Windows-Einstellungen", "uri", "ms-settings:", "einstellungen", "windows einstellungen"),
    _e("word", "Word", "cmd", "winword", "word"),
    _e("excel", "Excel", "cmd", "excel", "excel"),
    _e("powerpoint", "PowerPoint", "cmd", "powerpnt", "powerpoint"),
    _e("outlook", "Outlook", "cmd", "outlook", "outlook"),
    _e("onenote", "OneNote", "lnk", "onenote", "onenote"),
    _e("teams", "Microsoft Teams", "lnk", "teams", "teams", "microsoft teams"),
    _e("zoom", "Zoom", "lnk", "zoom", "zoom"),
    _e("whatsapp", "WhatsApp", "lnk", "whatsapp", "whatsapp"),
    _e("telegram", "Telegram", "lnk", "telegram", "telegram"),
    _e("signal", "Signal", "lnk", "signal", "signal"),
    _e("vscode", "Visual Studio Code", "cmd", "code", "vs code", "visual studio code", "vscode", "code editor"),
    _e("obs", "OBS Studio", "lnk", "obs studio", "obs", "obs studio"),
    _e("vlc", "VLC Media Player", "lnk", "vlc", "vlc"),
    _e("audacity", "Audacity", "lnk", "audacity", "audacity"),
    _e("gimp", "GIMP", "lnk", "gimp", "gimp"),
    _e("blender", "Blender", "lnk", "blender", "blender"),
    _e("snip", "Snipping Tool", "cmd", "snippingtool", "snipping tool", "ausschneiden"),
    _e("camera", "Kamera", "uri", "microsoft.windows.camera:", "kamera"),
    _e("photos", "Fotos", "uri", "ms-photos:", "fotos"),
    _e("store", "Microsoft Store", "uri", "ms-windows-store:", "microsoft store", "store"),
    _e("control", "Systemsteuerung", "cmd", "control", "systemsteuerung"),
    _e("devmgmt", "Geräte-Manager", "cmd", "devmgmt.msc", "geräte-manager", "gerätemanager", "geraetemanager"),
    _e("calendar", "Kalender", "uri", "outlookcal:", "kalender"),
    _e("xbox", "Xbox", "uri", "xbox:", "xbox"),
]
BY_ID = {e.id: e for e in CATALOG}
DEFAULT_CAT = {}
for _c, _ids in {
    "Browser": "chrome edge firefox brave opera",
    "Spiele": "steam epic battlenet gog ea ubisoft minecraft xbox",
    "Medien": "spotify vlc audacity obs photos camera paint gimp blender",
    "Kommunikation": "discord teams zoom whatsapp telegram signal outlook",
    "Büro": "word excel powerpoint onenote notepad calc calendar",
    "Entwicklung": "vscode",
    "System": "explorer taskmgr settings store control devmgmt snip",
}.items():
    for _i in _ids.split():
        DEFAULT_CAT[_i] = _c


def category_of(settings, entry):
    return (settings.get("prog_cat") or {}).get(entry.id) or DEFAULT_CAT.get(entry.id, "Eigene")


SENSITIVE_OFF = {"devmgmt", "control"}  # standardmäßig nicht freigegeben


def default_allowed():
    return [e.id for e in CATALOG if e.id not in SENSITIVE_OFF]


def custom_entries(settings):
    out = []
    for name, path in (settings.get("custom_programs") or {}).items():
        out.append(Entry("custom:" + name, name, "path", path, (name.lower(),)))
    return out


def all_entries(settings):
    return CATALOG + custom_entries(settings)


def allowed_ids(settings):
    a = settings.get("allowed_programs")
    base = default_allowed() if a is None else list(a)
    return set(base) | {e.id for e in custom_entries(settings)} if a is None else set(base)


def is_allowed(settings, entry):
    return entry.id in allowed_ids(settings)


_start_cache = None


def scan_start_menu(force=False):
    """Alle Startmenü-Verknüpfungen: Name -> Pfad."""
    global _start_cache
    if _start_cache is not None and not force:
        return _start_cache
    found = {}
    roots = [os.environ.get("ProgramData", ""), os.environ.get("APPDATA", "")]
    for r in roots:
        base = Path(r) / "Microsoft" / "Windows" / "Start Menu" / "Programs"
        if base.is_dir():
            try:
                for p in base.rglob("*.lnk"):
                    if "uninstall" not in p.stem.lower() and "deinstall" not in p.stem.lower():
                        found.setdefault(p.stem, str(p))
            except Exception:
                pass
    _start_cache = found
    return found


def find_shortcut(hint):
    hint = hint.lower()
    for name, path in scan_start_menu().items():
        if hint in name.lower():
            return path
    return None


def launch(entry):
    """Startet einen Eintrag. Gibt (ok, Meldung) zurück."""
    if os.name != "nt":
        return False, "Programme starten funktioniert nur unter Windows."
    try:
        if entry.kind == "path":
            os.startfile(entry.target)  # noqa
        elif entry.kind == "lnk":
            p = find_shortcut(entry.target)
            if not p:
                return False, f"{entry.name} ist auf diesem PC nicht installiert oder nicht im Startmenü."
            os.startfile(p)  # noqa
        else:
            subprocess.Popen(["cmd", "/c", "start", "", entry.target], creationflags=NO_WINDOW)
        return True, ""
    except Exception as ex:  # pragma: no cover
        return False, f"{entry.name} konnte nicht gestartet werden: {ex}"
