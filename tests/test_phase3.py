"""
History rebuild, track record, forecast and thesis rules.

    python -m unittest discover tests
"""

from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from engine import backtest, edge, forecast, thesis
from engine.catalog import point_in_time
from engine.collect import Collected

DAYS = pd.bdate_range("2023-01-02", "2026-10-21")    # ends on a Wednesday


def flat_bars(level=1.1):
    s = pd.Series(level * np.exp(np.cumsum(np.random.default_rng(2).normal(0, .003, len(DAYS)))),
                  index=DAYS)
    return pd.DataFrame({f: s for f in ("open", "high", "low", "close")})


class Rebuild(unittest.TestCase):
    def test_only_finished_weeks_after_warmup(self):
        majors = {n: flat_bars() for n in ("EURUSD", "GBPUSD", "USDJPY", "USDCHF",
                                           "USDCAD", "AUDUSD", "NZDUSD")}
        dates = backtest.read_dates(Collected(pd.DataFrame(), majors, {}, {}))
        self.assertTrue(all(d.dayofweek == 4 for d in dates[:-1]))
        self.assertLess(dates[-1], pd.Timestamp("2026-10-19"))   # this week left out
        self.assertGreaterEqual(DAYS.get_loc(dates[0]), backtest.WARMUP_SESSIONS)

    def test_point_in_time_delays_monthly_cpi(self):
        macro = pd.DataFrame({"USD.CPI": pd.Series([3.0], index=[pd.Timestamp("2026-09-30")])})
        pit = point_in_time(macro)
        self.assertEqual(pit["USD.CPI"].dropna().index[0], pd.Timestamp("2026-10-15"))  # BLS releases ~15 days after month end


class LiveLog(unittest.TestCase):
    def test_one_read_per_week_current_version_only(self):
        log = [{"asof": "2026-10-20", "model_version": "v2", "n": 1},
               {"asof": "2026-10-22", "model_version": "v2", "n": 2},   # same week, later
               {"asof": "2026-10-22", "model_version": "v1", "n": 3},   # old model
               {"asof": "2026-10-27", "model_version": "v2", "n": 4}]
        self.assertEqual([r["n"] for r in edge.weekly(log, "v2")], [2, 4])


class Proven(unittest.TestCase):
    def test_needs_both_halves(self):
        self.assertTrue(edge.proven({"t": 2.5, "t_halves": [1.8, 1.9]}))
        self.assertFalse(edge.proven({"t": -2.09, "t_halves": [-0.27, -2.38]}))
        self.assertFalse(edge.proven({"t": 2.5, "t_halves": [2.0, -1.6]}))
        self.assertFalse(edge.proven({"t": 1.9, "t_halves": [1.8, 1.9]}))
        self.assertFalse(edge.proven(None))


class Forecast(unittest.TestCase):
    def test_flat_cone_without_proven_signal(self):
        close = flat_bars()["close"]
        f = forecast.forecast("pair", {"macro_diff": 80, "residual_z": -2}, close,
                              DAYS[-1], {"horizons": {"1m": {"pair_score": {"t": 1.0}}}})
        c = f["1m"]
        self.assertEqual(len(c["dates"]), 20)
        self.assertEqual(c["centre"][0], c["centre"][-1])
        self.assertIsNone(c["lean"])
        self.assertLess(c["lo95"][-1], c["lo68"][-1])
        self.assertGreater(c["hi68"][-1] - c["lo68"][-1], c["hi68"][0] - c["lo68"][0])

    def test_proven_signal_tilts_but_is_shrunk(self):
        close = flat_bars()["close"]
        calib = {"horizons": {"1m": {"pair_score": {"t": 4.0, "t_halves": [3, 3], "slope": 0.5}}}}
        drift, why = forecast.lean("pair", {"macro_diff": 100}, calib, "1m")
        self.assertAlmostEqual(drift, 0.5 * 0.75)
        self.assertIn("shrunk to 75%", why[0])
        up = forecast.cone(close, DAYS[-1], 20, drift)
        self.assertGreater(up["centre"][-1], up["centre"][0])


class Thesis(unittest.TestCase):
    def test_setup_is_on_the_right_side(self):
        close = flat_bars()["close"]
        long_ = thesis.setup(close, DAYS[-1], 1)
        short = thesis.setup(close, DAYS[-1], -1)
        self.assertLess(long_["stop"], long_["entry"])
        self.assertLess(long_["entry"], long_["targets"][0])
        self.assertGreater(short["stop"], short["entry"])
        self.assertIsNone(thesis.setup(close, DAYS[-1], 0))

    def test_crowded_positioning_in_the_lean_direction_argues_against(self):
        ccy = {"EUR": {"ccy": "EUR", "score": 40, "quality": "daily", "cot_flag": "crowded long",
                       "cot_pct": 95},
               "USD": {"ccy": "USD", "score": -40, "quality": "daily", "cot_flag": None}}
        p = {"pair": "EURUSD", "base": "EUR", "quote": "USD", "macro_diff": 80, "bias": "long",
             "spread_3m_bp": 20, "spread_quality": "daily", "return_3m_pct": 1.0,
             "residual_z": None, "link_corr": None, "rates_vs_price": "aligned",
             "efficiency": 0.5}
        card = thesis.pair_card(p, ccy, {"state": "normal"}, [], flat_bars()["close"],
                                DAYS[-1], None)
        self.assertEqual(card["lean"], "long")
        self.assertTrue(any("crowded long" in x for x in card["against"]))
        self.assertTrue(any("Rate gap" in x for x in card["for"]))
        self.assertIsNotNone(card["setup"])


if __name__ == "__main__":
    unittest.main()


class PolicyDecisions(unittest.TestCase):
    def test_decision_after_bis_update_marks_rate_stale(self):
        from engine.doctor import decisions_since
        rows = [{"id": "NZD.POLICY", "group": "policy", "status": "ok", "last_date": "2026-10-16", "last_value": 2.75},
                {"id": "AUD.POLICY", "group": "policy", "status": "ok", "last_date": "2026-10-15", "last_value": 4.6}]
        cal = pd.DataFrame({"time": pd.to_datetime(["2026-10-28T01:00:00Z", "2026-11-04T03:30:00Z"]),
                            "currency": ["NZD", "AUD"], "impact": ["High", "High"],
                            "title": ["Official Cash Rate", "Cash Rate"]})
        decisions_since(rows, cal, pd.Timestamp("2026-10-28T12:00:00Z"))
        self.assertEqual(rows[0]["status"], "stale")             # RBNZ decided after BIS's 16 Oct update
        self.assertIn("Official Cash Rate decided 2026-10-28", rows[0]["note"])
        self.assertEqual(rows[1]["status"], "ok")                # RBA's meeting hasn't happened yet


class PolicyMerge(unittest.TestCase):
    def test_official_feed_overrides_bis_and_bis_fills_gaps(self):
        from engine.collect import merge
        days = pd.to_datetime(["2026-10-15", "2026-10-28", "2026-10-29"])
        bis = pd.DataFrame({"USD.POLICY": [3.875, None, None], "NZD.POLICY": [2.75, None, None]}, index=days)
        official = pd.DataFrame({"USD.POLICY": [None, 3.875, 3.625]}, index=days)
        m = merge([bis, official])
        self.assertEqual(list(m.columns), ["USD.POLICY", "NZD.POLICY"])
        self.assertEqual(m["USD.POLICY"].tolist(), [3.875, 3.875, 3.625])     # official newest wins
        self.assertEqual(m["NZD.POLICY"].dropna().index[-1], days[0])          # BIS-only stays as it was
