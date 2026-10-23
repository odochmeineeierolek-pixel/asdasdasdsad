import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from yavis.wallet import lookup_address, validate_address

ADDRESS = "bc1qexampleaddresswithenoughlength1234567890"


def test_validate_public_address_only():
    assert validate_address(ADDRESS) == ADDRESS
    for bad in ("", "seed phrase words should never be accepted", "abc/../def", "short"):
        try:
            validate_address(bad)
            assert False, bad
        except ValueError:
            pass


def test_balance_and_recent_transactions_without_network():
    calls = []
    def fake_get(url):
        calls.append(url)
        if url.endswith("/txs"):
            return [{"txid": "abc123", "status": {"confirmed": True, "block_time": 123}}]
        return {
            "chain_stats": {"funded_txo_sum": 150000000, "spent_txo_sum": 50000000},
            "mempool_stats": {"funded_txo_sum": 25000000, "spent_txo_sum": 0},
        }
    result = lookup_address(ADDRESS, get_json=fake_get)
    assert result["confirmed_sats"] == 100000000
    assert result["unconfirmed_sats"] == 25000000
    assert result["balance_btc"] == 1.25
    assert result["transactions"][0]["txid"] == "abc123"
    assert len(calls) == 2


if __name__ == "__main__":
    test_validate_public_address_only()
    test_balance_and_recent_transactions_without_network()
    print("ok wallet read-only")
