"""Sichere Hilfsfunktionen für das optionale Mining-Modul von YAVIS.

Keine Miner werden heruntergeladen oder automatisch installiert. Es wird ausschließlich
vom Benutzer ausgewählte Software gestartet, ohne Shell-Ausführung.
"""
from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import tempfile
import threading
import time
import urllib.request
import zipfile
from pathlib import Path
from typing import Optional


PEAKMINER_VERSION = "2.20.0"
PEAKMINER_URL = (
    "https://github.com/peakminer/peakminer/releases/download/v2.20.0/"
    "peakminer-2.20.0-windows-x86_64.zip"
)
PEAKMINER_SHA256 = "02872d966abfd82f8ab0ecd45e414820c37bb6a7ca06858b4967d27bd7d0a3f1"


def download_peakminer(destination: str | Path, *, opener=None) -> Path:
    """Download the pinned official Windows release, verify its SHA-256 and safely extract it.

    Does not start the miner. The user must configure a public wallet address and pool first.
    """
    destination = Path(destination).expanduser().resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(PEAKMINER_URL, headers={"User-Agent": "YAVIS-PeakMiner-Installer"})
    open_url = opener or urllib.request.urlopen
    digest = hashlib.sha256()
    with tempfile.TemporaryDirectory(prefix="yavis-peakminer-", dir=destination.parent) as tmp_name:
        tmp = Path(tmp_name)
        archive = tmp / "peakminer.zip"
        total = 0
        with open_url(request, timeout=45) as response, archive.open("wb") as out:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > 250 * 1024 * 1024:
                    raise RuntimeError("PeakMiner-Archiv überschreitet die Sicherheitsgrenze von 250 MB.")
                digest.update(chunk)
                out.write(chunk)
        if digest.hexdigest().lower() != PEAKMINER_SHA256:
            raise RuntimeError("SHA-256-Prüfung fehlgeschlagen. Der Download wurde nicht installiert.")
        if not zipfile.is_zipfile(archive):
            raise RuntimeError("Der offizielle Download ist kein gültiges ZIP-Archiv.")
        extracted = tmp / "extracted"
        extracted.mkdir()
        with zipfile.ZipFile(archive) as zf:
            root = extracted.resolve()
            for info in zf.infolist():
                member = (extracted / info.filename).resolve()
                if member != root and root not in member.parents:
                    raise RuntimeError("Unsicherer Pfad im ZIP-Archiv erkannt.")
            zf.extractall(extracted)
        exe_candidates = list(extracted.rglob("peakminer.exe"))
        if not exe_candidates:
            raise RuntimeError("Im geprüften Archiv wurde keine peakminer.exe gefunden.")
        staged = tmp / "install"
        shutil.move(str(extracted), str(staged))
        backup = destination.with_name(destination.name + ".old")
        if backup.exists():
            shutil.rmtree(backup, ignore_errors=True)
        if destination.exists():
            destination.replace(backup)
        try:
            staged.replace(destination)
        except Exception:
            if backup.exists() and not destination.exists():
                backup.replace(destination)
            raise
        if backup.exists():
            shutil.rmtree(backup, ignore_errors=True)
    installed = list(destination.rglob("peakminer.exe"))
    if not installed:
        raise RuntimeError("Installation abgeschlossen, aber peakminer.exe wurde nicht gefunden.")
    return installed[0]


def estimate_economics(power_w: float, electricity_eur_kwh: float,
                       gross_eur_day: float, uptime_percent: float = 100.0,
                       pool_fee_percent: float = 1.0) -> dict:
    """Calculate estimated energy cost and net profit; does not promise actual yield."""
    power_w = max(0.0, float(power_w))
    rate = max(0.0, float(electricity_eur_kwh))
    gross = max(0.0, float(gross_eur_day))
    uptime = min(100.0, max(0.0, float(uptime_percent))) / 100.0
    fee = min(100.0, max(0.0, float(pool_fee_percent))) / 100.0
    kwh_day = (power_w / 1000.0) * 24.0 * uptime
    electricity_day = kwh_day * rate
    gross_day = gross * uptime
    pool_fee_day = gross_day * fee
    net_day = gross_day - pool_fee_day - electricity_day
    return {
        "kwh_day": kwh_day,
        "electricity_day": electricity_day,
        "gross_day": gross_day,
        "pool_fee_day": pool_fee_day,
        "net_day": net_day,
        "net_month": net_day * 30.0,
        "net_year": net_day * 365.0,
        "break_even_gross_day": electricity_day / max(0.000001, 1.0 - fee),
    }


def build_peakminer_arguments(coin: str, wallet: str, worker: str = "yavis-rig1", pool: str | None = None) -> list[str]:
    """Build safe PeakMiner arguments for a supported coin and public wallet address.

    This never accepts a seed phrase/private key. Pearl is the recommended default for
    RTX 20xx+ cards; Quantus is also available for NVIDIA and supported AMD GPUs.
    """
    coins = {
        "Pearl (PRL)": ("pearl", "de.pearl.herominers.com:1200", "prl1"),
        "Quantus (QUAN)": ("quantus", "qtc.kryptex.network:7049", "qz"),
    }
    if coin not in coins:
        raise ValueError("Nicht unterstützte PeakMiner-Coin-Auswahl.")
    coin_arg, default_pool, prefix = coins[coin]
    wallet = str(wallet).strip()
    worker = str(worker).strip()
    pool = str(pool or default_pool).strip()
    if not wallet.startswith(prefix) or len(wallet) < 20 or any(ch.isspace() for ch in wallet):
        raise ValueError(f"Bitte eine gültige öffentliche {coin} Empfangsadresse eingeben.")
    if not worker or len(worker) > 32 or any(ch not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for ch in worker):
        raise ValueError("Workername darf nur Buchstaben, Zahlen, Bindestrich und Unterstrich enthalten.")
    if not pool or any(ch.isspace() for ch in pool) or "/" in pool or "\\" in pool:
        raise ValueError("Pool-Adresse ist ungültig.")
    return ["--coin", coin_arg, "--url", pool, "--user", f"{wallet}.{worker}",
            "--gpu-temp-stop", "80", "--gpu-temp-start", "70", "--api-port", "4068"]


def read_nvidia_metrics() -> dict:
    """Read GPU telemetry from NVIDIA's nvidia-smi, if installed and available."""
    command = ["nvidia-smi", "--query-gpu=name,temperature.gpu,power.draw,power.limit,utilization.gpu,memory.used,memory.total", "--format=csv,noheader,nounits"]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=3, check=True,
                                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        first = result.stdout.strip().splitlines()[0]
        parts = [p.strip() for p in first.split(",")]
        if len(parts) < 7:
            raise ValueError("Unerwartetes nvidia-smi-Format")
        def num(value):
            try:
                return float(value)
            except (TypeError, ValueError):
                return None
        return {"available": True, "name": parts[0], "temperature_c": num(parts[1]),
                "power_w": num(parts[2]), "power_limit_w": num(parts[3]),
                "utilization_percent": num(parts[4]), "memory_used_mb": num(parts[5]),
                "memory_total_mb": num(parts[6]), "error": ""}
    except Exception as exc:
        return {"available": False, "name": "NVIDIA-GPU nicht erkannt", "temperature_c": None,
                "power_w": None, "power_limit_w": None, "utilization_percent": None,
                "memory_used_mb": None, "memory_total_mb": None, "error": str(exc)}


class MinerController:
    """Start/stop only a user-selected miner executable; never invokes a shell."""
    def __init__(self):
        self.process: Optional[subprocess.Popen] = None
        self.log_path: Optional[Path] = None
        self.started_at: Optional[float] = None
        self._log_handle = None
        self._lock = threading.RLock()

    @property
    def running(self) -> bool:
        return self.process is not None and self.process.poll() is None

    def start(self, executable: str, arguments: list[str], log_path: str) -> None:
        with self._lock:
            if self.running:
                raise RuntimeError("Ein Mining-Prozess läuft bereits.")
            path = Path(executable).expanduser().resolve()
            if not path.is_file():
                raise FileNotFoundError("Miner-Programm wurde nicht gefunden.")
            if path.suffix.lower() not in (".exe", ".bat", ".cmd"):
                raise ValueError("Bitte eine ausführbare Windows-Datei (.exe) auswählen.")
            if path.suffix.lower() != ".exe":
                raise ValueError("Aus Sicherheitsgründen werden nur .exe-Dateien gestartet.")
            log = Path(log_path).expanduser().resolve()
            log.parent.mkdir(parents=True, exist_ok=True)
            self._log_handle = open(log, "a", encoding="utf-8", errors="replace")
            self._log_handle.write(f"\n--- YAVIS Mining gestartet: {time.strftime('%Y-%m-%d %H:%M:%S')} ---\n")
            self._log_handle.flush()
            try:
                self.process = subprocess.Popen([str(path), *arguments], cwd=str(path.parent),
                    stdin=subprocess.DEVNULL, stdout=self._log_handle, stderr=subprocess.STDOUT,
                    shell=False, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            except Exception:
                self._log_handle.close()
                self._log_handle = None
                self.process = None
                raise
            self.log_path = log
            self.started_at = time.time()

    def stop(self, timeout: float = 5.0) -> None:
        with self._lock:
            proc = self.process
            if proc is None:
                return
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=timeout)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    try:
                        proc.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        pass
            self.process = None
            self.started_at = None
            if self._log_handle:
                try:
                    self._log_handle.write(f"\n--- YAVIS Mining gestoppt: {time.strftime('%Y-%m-%d %H:%M:%S')} ---\n")
                    self._log_handle.flush()
                    self._log_handle.close()
                except Exception:
                    pass
                self._log_handle = None

    def close(self):
        self.stop()
