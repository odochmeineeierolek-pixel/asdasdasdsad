"""Sichere Hilfsfunktionen für das optionale Mining-Modul von YAVIS.

Keine Miner werden heruntergeladen oder automatisch installiert. Es wird ausschließlich
vom Benutzer ausgewählte Software gestartet, ohne Shell-Ausführung.
"""
from __future__ import annotations

import os
import subprocess
import threading
import time
from pathlib import Path
from typing import Optional


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
