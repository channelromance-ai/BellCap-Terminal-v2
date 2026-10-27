"""
Speculative positioning (CFTC Commitments of Traders), in plain terms.

Every Friday the CFTC publishes how the big speculators were positioned in
futures as of that Tuesday: hedge funds ("leveraged funds") in currencies
and stock indices, fund managers ("managed money") in gold, silver and oil.
For each market this says which way they lean, how hard compared with the
last three years, and whether they added or cut this week.

Currency futures are quoted against the dollar, so "long EUR" is a bet on
EUR rising against USD (EURUSD up), and "long JPY" a bet on USDJPY falling.
Extremes matter most: a crowded position can unwind fast when news turns.
"""

from __future__ import annotations

import pandas as pd

from . import config as C
from .ts import ordinal, percentile, rnd, upto

MARKETS = [  # (series, name, who, what the long side is betting on)
    ("COT.EUR", "EUR", "hedge funds", "EUR rising vs USD"),
    ("COT.GBP", "GBP", "hedge funds", "GBP rising vs USD"),
    ("COT.JPY", "JPY", "hedge funds", "JPY rising vs USD (USDJPY down)"),
    ("COT.CHF", "CHF", "hedge funds", "CHF rising vs USD (USDCHF down)"),
    ("COT.CAD", "CAD", "hedge funds", "CAD rising vs USD (USDCAD down)"),
    ("COT.AUD", "AUD", "hedge funds", "AUD rising vs USD"),
    ("COT.NZD", "NZD", "hedge funds", "NZD rising vs USD"),
    ("COT.GOLD", "Gold", "fund managers", "gold rising"),
    ("COT.SILVER", "Silver", "fund managers", "silver rising"),
    ("COT.WTI", "WTI crude", "fund managers", "oil rising"),
    ("COT.SPX", "S&P 500", "hedge funds", "the S&P 500 rising"),
    ("COT.NDX", "Nasdaq 100", "hedge funds", "the Nasdaq 100 rising"),
]
FLOW_PP = 2.0      # a weekly change smaller than this (in % of open interest) is "little changed"


# Judged against their own last 3 years, not against zero: net long silver
# can still be the most bearish speculators have been in years.
LABELS = [(C.COT_EXTREME_HIGH, "very bullish", "near their most bullish in 3 years"),
          (70, "bullish", "more bullish than usual"),
          (30.0001, "normal", "about normal for them"),
          (C.COT_EXTREME_LOW + 0.0001, "bearish", "more bearish than usual"),
          (-1, "very bearish", "near their most bearish in 3 years")]


def label(pct: float | None) -> tuple[str, str]:
    if pct is None:
        return "no data", "no history to compare"
    return next((short, words) for floor, short, words in LABELS if pct >= floor)


def flow(net: float, change: float | None) -> str:
    if change is None or abs(change) < FLOW_PP:
        return "little changed this week"
    if change > 0:
        return "adding to longs" if net > 0 else "covering shorts"
    return "cutting longs" if net > 0 else "adding to shorts"


def read(macro: pd.DataFrame, asof) -> list[dict]:
    out = []
    for col, name, who, bet in MARKETS:
        s = upto(macro.get(col), asof)
        if s.empty:
            continue
        window = s.iloc[-C.COT_WINDOW_WEEKS:]
        net = float(s.iloc[-1])
        wk = net - float(s.iloc[-2]) if len(s) > 1 else None
        pct = percentile(s, asof, C.COT_WINDOW_WEEKS)
        side = "long" if net > 0 else "short"
        lab, words = label(pct)
        what = name if name.isupper() else name.lower().replace("s&p", "S&P").replace("nasdaq", "Nasdaq").replace("wti", "WTI")
        text = (f"{who.capitalize()} are net {side} {what} ({abs(net):.0f}% of open interest), "
                f"{words} ({ordinal(max(pct, 1))} percentile); {flow(net, wk)}.")
        if lab.startswith("very"):
            text += " Positions this stretched can unwind fast if the news turns."
        out.append({"market": name, "series": col, "who": who, "long_means": bet,
                    "released": s.index[-1].date().isoformat(),
                    "as_of": (s.index[-1] - pd.Timedelta(days=3)).date().isoformat(),
                    "net_pct": rnd(net, 1), "chg_1w": rnd(wk, 1),
                    "chg_4w": rnd(net - float(s.iloc[-5]), 1) if len(s) > 4 else None,
                    "pct_3y": rnd(pct, 0), "min_3y": rnd(window.min(), 1), "max_3y": rnd(window.max(), 1),
                    "label": lab, "text": text,
                    "history": [rnd(v, 1) for v in s.iloc[-52:]]})
    return out


if __name__ == "__main__":
    weeks = pd.date_range("2023-10-06", periods=160, freq="W-FRI")
    rising = pd.Series([float(i) / 4 - 20 for i in range(160)], index=weeks)   # ends at its 3y high
    rows = read(pd.DataFrame({"COT.EUR": rising, "COT.JPY": -rising}), weeks[-1])
    eur, jpy = rows
    assert eur["label"] == "very bullish" and eur["chg_1w"] == 0.2, eur
    assert jpy["label"] == "very bearish" and "net short JPY" in jpy["text"], jpy["text"]
    assert "1st percentile" in jpy["text"], jpy["text"]          # 3-year low reads 1st, not 0th
    assert [ordinal(n) for n in (1, 2, 3, 11, 12, 82, 93, 100)] ==         ["1st", "2nd", "3rd", "11th", "12th", "82nd", "93rd", "100th"]
    assert label(50)[0] == "normal" and label(80)[0] == "bullish" and label(20)[0] == "bearish"
    assert flow(10, 3) == "adding to longs" and flow(-10, 3) == "covering shorts"
    assert flow(-10, -3) == "adding to shorts" and flow(10, 0.5) == "little changed this week"
    print("positioning: ok")
