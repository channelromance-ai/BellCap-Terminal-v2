"""
Model rules on synthetic data, where the right answer is known in advance.

    python -m unittest discover tests
"""

from __future__ import annotations

import json
import unittest

import numpy as np
import pandas as pd

from engine import assets, fx, macro, model, pairs
from engine.collect import Collected
from engine.ts import change, change_z, last

DAYS = pd.bdate_range("2024-01-01", "2026-10-23")
ASOF = DAYS[-1]


def bars_from(close: pd.Series) -> pd.DataFrame:
    return pd.DataFrame({f: close for f in ("open", "high", "low", "close")})


def fake_majors(seed: int = 1) -> dict:
    rng = np.random.default_rng(seed)
    start = {"EURUSD": 1.10, "GBPUSD": 1.30, "USDJPY": 150.0, "USDCHF": 0.85,
             "USDCAD": 1.38, "AUDUSD": 0.66, "NZDUSD": 0.60}
    return {k: bars_from(pd.Series(v * np.exp(np.cumsum(rng.normal(0, .004, len(DAYS)))),
                                   index=DAYS)) for k, v in start.items()}


class TimeSeries(unittest.TestCase):
    def test_change_is_measured_from_the_latest_print(self):
        monthly = pd.Series([1.0, 2.0, 3.0, 4.0],
                            index=pd.to_datetime(["2026-06-30", "2026-07-31",
                                                  "2026-08-31", "2026-09-30"]))
        # Read on 23 Oct: latest is Sep, three months back is Jun -> +3.
        self.assertEqual(change(monthly, 91, pd.Timestamp("2026-10-23")), 3.0)

    def test_nothing_after_asof_is_seen(self):
        s = pd.Series([1.0, 99.0], index=pd.to_datetime(["2026-10-22", "2026-10-26"]))
        self.assertEqual(last(s, pd.Timestamp("2026-10-23"))[1], 1.0)

    def test_change_z_flags_an_unusual_move(self):
        quiet = pd.Series(np.sin(np.arange(len(DAYS)) / 5) * 0.01, index=DAYS)
        jolted = quiet.copy()
        jolted.iloc[-1] += 0.5
        self.assertGreater(change_z(jolted, ASOF, 20, 750), 5)


class Fx(unittest.TestCase):
    def test_crosses_and_names(self):
        majors = fake_majors()
        values = fx.usd_value(majors)
        closes = fx.pair_closes(values)
        self.assertEqual(len(closes), 28)
        self.assertIn("EURJPY", closes)
        self.assertNotIn("JPYEUR", closes)
        self.assertIn("AUDNZD", closes)
        eurjpy = majors["EURUSD"]["close"] * majors["USDJPY"]["close"]
        self.assertAlmostEqual(closes["EURJPY"].iloc[-1], eurjpy.iloc[-1])
        eurgbp = majors["EURUSD"]["close"] / majors["GBPUSD"]["close"]
        self.assertAlmostEqual(closes["EURGBP"].iloc[-1], eurgbp.iloc[-1])

    def test_cross_only_on_days_both_legs_exist(self):
        majors = fake_majors()
        majors["GBPUSD"] = majors["GBPUSD"].drop(DAYS[-1])
        closes = fx.pair_closes(fx.usd_value(majors))
        self.assertEqual(closes["EURGBP"].index[-1], DAYS[-2])
        self.assertEqual(closes["EURUSD"].index[-1], DAYS[-1])

    def test_strength_sums_to_zero(self):
        st = fx.strength(fx.usd_value(fake_majors()))
        self.assertAlmostEqual(float(st.iloc[-1].sum()), 0.0, places=9)


class Currencies(unittest.TestCase):
    def test_path_uses_policy_on_the_market_rate_date(self):
        # 3m rate averaged 4.50 in Sep; the bank hiked 4.35 -> 4.60 on 30 Sep.
        macro_df = pd.DataFrame({
            "AUD.POLICY": pd.Series([4.35, 4.60], index=pd.to_datetime(["2026-09-01", "2026-10-01"])),
            "AUD.3M_M": pd.Series([4.50], index=pd.to_datetime(["2026-09-30"])),
        })
        r = macro.read_currency("AUD", macro_df, ASOF)
        self.assertEqual(r.quality, "monthly")
        self.assertEqual(r.path_bp, 15.0)            # vs 4.35, not -10 vs 4.60

    def test_missing_components_are_reweighted_not_zeroed(self):
        reads = [macro.CurrencyRead(c, "daily") for c in "ABCDE"]
        for i, r in enumerate(reads):
            r.momentum_z, r.policy = float(i), float(i)
        macro.score(reads)
        self.assertEqual(set(reads[-1].components), {"rate_momentum", "carry"})
        self.assertEqual(reads[-1].score, -reads[0].score)
        self.assertGreater(reads[-1].score, 0)

    def test_component_skipped_when_too_few_currencies_have_it(self):
        reads = [macro.CurrencyRead(c, "daily") for c in "ABCDE"]
        for r in reads:
            r.policy = 1.0
        reads[0].cpi_gap, reads[1].cpi_gap = 1.0, -1.0
        macro.score(reads)
        self.assertNotIn("inflation", reads[0].components)

    def test_cot_extremes(self):
        weekly = pd.Series(np.arange(200.0), index=pd.date_range("2023-01-06", periods=200, freq="W-FRI"))
        net, pct, flag = macro.cot_read(weekly, weekly.index[-1])
        self.assertEqual(flag, "crowded long")
        net, pct, flag = macro.cot_read(-weekly, weekly.index[-1])
        self.assertEqual(flag, "crowded short")


class Pairs(unittest.TestCase):
    def test_fair_value_sits_on_the_line_when_price_follows_rates(self):
        spread = pd.Series(np.linspace(1.0, 2.0, len(DAYS)) + np.sin(np.arange(len(DAYS)) / 9) * .1,
                           index=DAYS)
        price = np.exp(0.05 * spread + 0.1)
        noise = np.random.default_rng(3).normal(0, 1e-4, len(DAYS))
        corr, fair, z = pairs.rates_link(price * np.exp(noise), spread)
        self.assertGreater(corr, 0.9)
        self.assertAlmostEqual(fair, price.iloc[-1], places=3)
        self.assertLess(abs(z), 3)

    def test_price_far_below_rates_shows_a_negative_residual(self):
        spread = pd.Series(np.linspace(1.0, 2.0, len(DAYS)), index=DAYS)
        noise = np.random.default_rng(4).normal(0, 1e-3, len(DAYS))
        price = pd.Series(np.exp(0.05 * spread + noise), index=DAYS)
        price.iloc[-1] *= 0.97
        _, _, z = pairs.rates_link(price, spread)
        self.assertLess(z, -5)

    def test_mixed_tenor_spread_hides_the_level(self):
        a = macro.CurrencyRead("USD", "daily", front_end_id="USD.2Y", front_end=4.0,
                               momentum_1m_bp=10, momentum_3m_bp=20, score=40)
        b = macro.CurrencyRead("CHF", "monthly", front_end_id="CHF.3M_M", front_end=0.0,
                               momentum_1m_bp=0, momentum_3m_bp=0, score=-40)
        p = pairs.read_pair(a, b, None, pd.DataFrame(), ASOF)
        self.assertEqual(p.spread_quality, "mixed tenor")
        self.assertIsNone(p.spread_bp)
        self.assertEqual(p.spread_3m_bp, 20)
        self.assertEqual(p.bias, "long")


class Assets(unittest.TestCase):
    def vix(self, last_value: float, base: float = 15.0) -> pd.DataFrame:
        s = pd.Series(base + np.sin(np.arange(len(DAYS)) / 7), index=DAYS)
        s.iloc[-1] = last_value
        return pd.DataFrame({"VIX": s})

    def test_regime_states(self):
        self.assertEqual(assets.risk_regime(self.vix(30), ASOF)["state"], "stressed")
        self.assertEqual(assets.risk_regime(self.vix(14.1), ASOF)["state"], "calm")
        self.assertEqual(assets.risk_regime(pd.DataFrame(), ASOF)["state"], "unknown")

    def test_gold_link_unknown_is_not_ok(self):
        gold = pd.Series(np.linspace(2000, 2100, len(DAYS)), index=DAYS)
        self.assertEqual(assets.gold_link_check(gold, None, ASOF)["state"], "unknown")


class Snapshot(unittest.TestCase):
    def test_build_is_complete_and_json_clean(self):
        majors = fake_majors()
        rng = np.random.default_rng(9)
        walk = lambda lvl: pd.Series(lvl + np.cumsum(rng.normal(0, .02, len(DAYS))), index=DAYS)
        macro_df = pd.DataFrame({
            **{f"{c}.POLICY": pd.Series(r, index=DAYS) for c, r in
               {"USD": 4.0, "EUR": 2.5, "GBP": 4.0, "JPY": 0.5, "CHF": 0.5,
                "CAD": 3.0, "AUD": 4.1, "NZD": 4.0}.items()},
            "USD.2Y": walk(4.2), "EUR.2Y": walk(2.6), "JPY.2Y": walk(0.8), "CAD.2Y": walk(3.1),
            "USD.10Y": walk(4.5), "USD.REAL10Y": walk(2.0), "USD.BE10Y": walk(2.3),
            "VIX": walk(16).abs(),
        })
        allbars = {**majors, "XAUUSD": bars_from(majors["EURUSD"]["close"] * 3000)}
        data = Collected(macro_df, allbars, {k: "test" for k in allbars}, {})
        snap, record = model.build(data)
        self.assertEqual(snap["asof"], ASOF.date().isoformat())
        self.assertEqual(len(snap["pairs"]), 28)
        self.assertEqual(len(snap["currencies"]), 8)
        json.dumps(snap, allow_nan=False)
        json.dumps(record, allow_nan=False)
        self.assertIn("EURJPY", record["closes"])


if __name__ == "__main__":
    unittest.main()
