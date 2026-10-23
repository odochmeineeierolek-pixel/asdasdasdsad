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
