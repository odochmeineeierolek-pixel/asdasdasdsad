"""Read-only Bitcoin address lookup via Blockstream Esplora API.

This module never asks for seed phrases/private keys and cannot broadcast transactions.
"""
from __future__ import annotations
import json
import re
import urllib.parse
import urllib.request

BASE_URL = "https://blockstream.info/api"


def validate_address(address: str) -> str:
    address = str(address or "").strip()
    if not 26 <= len(address) <= 90 or not re.fullmatch(r"[A-Za-z0-9]+", address):
        raise ValueError("Bitte eine gültige Bitcoin-Adresse eingeben (keinen Seed/Private Key).")
    return address


def _get_json(url: str, timeout: float = 12):
    request = urllib.request.Request(url, headers={"User-Agent": "YAVIS-Wallet-Viewer/1.0"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def lookup_address(address: str, get_json=None) -> dict:
    """Return confirmed/unconfirmed BTC balance and recent txs for a public address."""
    address = validate_address(address)
    getter = get_json or _get_json
    encoded = urllib.parse.quote(address, safe="")
    details = getter(f"{BASE_URL}/address/{encoded}")
    chain = details.get("chain_stats", {})
    mempool = details.get("mempool_stats", {})
    confirmed = int(chain.get("funded_txo_sum", 0)) - int(chain.get("spent_txo_sum", 0))
    unconfirmed = (
        int(mempool.get("funded_txo_sum", 0)) - int(mempool.get("spent_txo_sum", 0))
    )
    txs = getter(f"{BASE_URL}/address/{encoded}/txs")
    if not isinstance(txs, list):
        raise ValueError("Unerwartete Antwort vom Bitcoin-Explorer.")
    return {
        "address": address,
        "confirmed_sats": confirmed,
        "unconfirmed_sats": unconfirmed,
        "balance_btc": (confirmed + unconfirmed) / 100_000_000,
        "transactions": txs[:10],
    }


def format_tx(tx: dict) -> str:
    txid = str(tx.get("txid", "unbekannt"))
    status = tx.get("status", {})
    if status.get("confirmed"):
        stamp = status.get("block_time")
        when = f"Blockzeit Unix: {stamp}" if stamp else "bestätigt"
    else:
        when = "unbestätigt"
    return f"{txid} · {when}"
