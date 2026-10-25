"""
Offline parser tests against saved responses in tests/fixtures.

A source changing its format should fail here, loudly, rather than turn into
a quietly wrong number on the dashboard. No network needed:

    python -m unittest discover tests
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

import pandas as pd

from unittest import mock

from engine.sources import (bis, boc, bundesbank, cboe, cftc, eurostat,
                            forexfactory, mof, nyfed, oecd, prices, treasury,
                            twelvedata)

FIX = Path(__file__).parent / "fixtures"


def raw(name: str) -> bytes:
    return (FIX / name).read_bytes()


class Rates(unittest.TestCase):
    def test_treasury_nominal(self):
        df = treasury.parse(raw("treasury_nominal.csv"), treasury.NOMINAL)
        self.assertEqual(df.loc["2026-10-23", "USD.2Y"], 4.69)
        self.assertEqual(df.loc["2026-10-23", "USD.10Y"], 5.00)
        self.assertTrue(df.index.is_monotonic_increasing)

    def test_treasury_real(self):
        df = treasury.parse(raw("treasury_real.csv"), treasury.REAL)
        self.assertEqual(df.loc["2026-10-23", "USD.REAL10Y"], 2.66)

    def test_bundesbank_german_number_format(self):
        s = bundesbank.parse(raw("bundesbank.csv"), "EUR.2Y")
        self.assertEqual(s.loc["2026-10-23"], 3.02)     # written "3,02"
        self.assertEqual(len(s), 5)                     # metadata rows skipped

    def test_mof_history_and_current_month(self):
        hist = mof.parse(raw("mof_all.csv"))
        cur = mof.parse(raw("mof_current.csv"))         # has a Shift-JIS footer
        self.assertEqual(hist.loc["2026-09-30", "JPY.2Y"], 1.952)
        self.assertEqual(cur.loc["2026-10-01", "JPY.10Y"], 3.092)
        self.assertTrue(pd.isna(hist.loc["1974-09-24", "JPY.10Y"]))  # "-"

    def test_boc(self):
        df = boc.parse(raw("boc.json"))
        self.assertEqual(df.loc["2026-10-20", "CAD.2Y"], 3.32)

    def test_nyfed(self):
        s = nyfed.parse(raw("nyfed.json"), "USD.SOFR")
        self.assertEqual(s.loc["2026-10-22"], 3.90)

    def test_bis_policy_rates(self):
        df = bis.parse(raw("bis.csv"))
        self.assertEqual(set(df.columns), {"USD.POLICY", "EUR.POLICY", "AUD.POLICY"})
        self.assertEqual(df["USD.POLICY"].dropna().iloc[-1], 3.875)   # range midpoint
        self.assertEqual(df["EUR.POLICY"].dropna().iloc[-1], 2.5)


class Inflation(unittest.TestCase):
    def test_eurostat_stamps_month_end(self):
        s = eurostat.parse(raw("eurostat.json"), "EUR.CPI")
        self.assertEqual(s.index[-1], pd.Timestamp("2026-09-30"))
        self.assertEqual(s.iloc[-1], 3.8)

    def test_oecd_cpi_prefers_monthly(self):
        df = oecd.parse_cpi(raw("oecd_cpi.csv"))
        self.assertEqual(df["USD.CPI"].dropna().index[-1], pd.Timestamp("2026-09-30"))
        # New Zealand only publishes quarterly: stamped on the quarter's end.
        self.assertEqual(df["NZD.CPI"].dropna().index[-1].month % 3, 0)

    def test_oecd_rates_drop_discontinued(self):
        df = oecd.parse_rates(raw("oecd_rates.csv"))
        self.assertNotIn("GBP.3M_M", df.columns)
        self.assertIn("AUD.10Y_M", df.columns)


class Markets(unittest.TestCase):
    def test_vix(self):
        df = cboe.parse(raw("cboe_vix.csv"))
        self.assertEqual(df.loc["2026-10-23", "VIX"], 19.45)

    def test_cftc_net_pct_and_friday_stamp(self):
        df = cftc.parse(raw("cftc_tff.json"), cftc.TFF)
        rows = json.loads(raw("cftc_tff.json"))
        r = rows[0]
        expect = 100 * (int(r["lev_money_positions_long"]) -
                        int(r["lev_money_positions_short"])) / int(r["open_interest_all"])
        # Tuesday 2026-10-20 positions became public Friday 2026-10-23.
        self.assertAlmostEqual(df.loc["2026-10-23", "099741"], expect)

    def test_cftc_disaggregated(self):
        df = cftc.parse(raw("cftc_disagg.json"), cftc.DISAGG)
        self.assertIn("088691", df.columns)

    def test_twelvedata_drops_unclosed_and_weekend_bars(self):
        body = {"status": "ok", "values": [
            {"datetime": d, "open": "1", "high": "2", "low": "0.5", "close": "1.5"}
            for d in ["2026-10-26", "2026-10-25", "2026-10-23", "2026-10-23", "2026-10-22"]]}
        df = twelvedata.parse(json.dumps(body).encode(), "EURUSD",
                              today=pd.Timestamp("2026-10-26", tz="UTC"))
        self.assertEqual(list(df.index.strftime("%Y-%m-%d")), ["2026-10-22", "2026-10-23"])
        self.assertEqual(df["close"].iloc[-1], 1.5)

    def test_twelvedata_error_is_raised_not_parsed(self):
        body = {"status": "error", "message": "plan limit"}
        with self.assertRaises(Exception):
            twelvedata.parse(json.dumps(body).encode(), "XAGUSD")

    def test_usd_listed_etf_converted_to_home_currency(self):
        days = pd.to_datetime(["2026-10-21", "2026-10-22", "2026-10-23"])
        etf = pd.DataFrame({f: [44.0, 44.0, 44.0] for f in
                            ("open", "high", "low", "close")}, index=days)
        eurusd = pd.Series([1.10, 1.10], index=days[1:])     # 21st missing
        out = prices.to_home_currency(etf, eurusd, "div")
        self.assertEqual(len(out), 2)                       # no guessed FX day
        self.assertAlmostEqual(out["close"].iloc[-1], 40.0)

    def test_backup_replaces_whole_history_and_is_labelled(self):
        idx = pd.to_datetime(["2026-10-22", "2026-10-23"])
        bar = pd.DataFrame({f: [1.0, 1.0] for f in ("open", "high", "low", "close")},
                           index=idx)
        td = ({i.name: bar for i in prices.INSTRUMENTS if i.name != "NAS100"},
              {"NAS100": "Twelve Data NAS100: plan limit"})
        yh = ({"NAS100": bar * 20000}, {})
        with mock.patch.object(prices.twelvedata, "fetch", return_value=td), \
             mock.patch.object(prices.yahoo, "fetch", return_value=yh) as backup:
            bars, sources, errors = prices.fetch()
        backup.assert_called_once_with({"^NDX": "NAS100"})
        self.assertEqual(sources["NAS100"], "yahoo (^NDX)")
        self.assertEqual(bars["NAS100"]["close"].iloc[-1], 20000)
        self.assertEqual(sources["US500"], "twelvedata (SPY ETF)")
        self.assertEqual(errors, {})

    def test_calendar(self):
        df = forexfactory.parse(raw("ff.json"))
        self.assertEqual(list(df.columns),
                         ["time", "currency", "impact", "title", "forecast", "previous"])
        self.assertEqual(str(df["time"].dt.tz), "UTC")


if __name__ == "__main__":
    unittest.main()
