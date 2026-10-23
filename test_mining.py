import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from yavis.mining import estimate_economics


def test_gpu_cost_and_profit():
    r = estimate_economics(190, 0.34, 0.60, 100, 1)
    assert round(r["kwh_day"], 2) == 4.56
    assert round(r["electricity_day"], 2) == 1.55
    assert r["net_day"] < 0
    assert round(r["break_even_gross_day"], 2) == 1.57


def test_uptime_and_bounds():
    r = estimate_economics(190, 0.34, 0.60, 50, 101)
    assert round(r["kwh_day"], 2) == 2.28
    assert r["pool_fee_day"] <= r["gross_day"]
    assert r["net_month"] == r["net_day"] * 30


if __name__ == "__main__":
    test_gpu_cost_and_profit()
    test_uptime_and_bounds()
    print("ok mining economics")


def test_peakminer_argument_builder():
    from yavis.mining import build_peakminer_arguments
    args = build_peakminer_arguments("Pearl (PRL)", "prl1" + "a" * 45, "yavis-rig1")
    assert args[:6] == ["--coin", "pearl", "--url", "de.pearl.herominers.com:1200", "--user", "prl1" + "a" * 45 + ".yavis-rig1"]
    assert "--gpu-temp-stop" in args and "80" in args
    try:
        build_peakminer_arguments("Pearl (PRL)", "seed phrase words must never be accepted")
        assert False, "seed phrase must be rejected"
    except ValueError:
        pass
    try:
        build_peakminer_arguments("Pearl (PRL)", "prl1" + "a" * 45, "worker;bad")
        assert False, "unsafe worker should be rejected"
    except ValueError:
        pass


def test_peakminer_download_is_pinned_and_checksum_verified():
    from yavis.mining import PEAKMINER_URL, PEAKMINER_SHA256, PEAKMINER_VERSION
    assert PEAKMINER_VERSION == "2.20.0"
    assert PEAKMINER_URL.endswith("peakminer-2.20.0-windows-x86_64.zip")
    assert len(PEAKMINER_SHA256) == 64
    assert all(ch in "0123456789abcdef" for ch in PEAKMINER_SHA256)
