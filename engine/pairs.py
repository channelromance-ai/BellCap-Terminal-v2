"""
The macro read for each of the 28 pairs.

A pair's macro case is the gap between its two currencies: their score
difference, and above all the gap in their front-end rates and which way it
is moving. Then the question a swing trade turns on: is price following?

  aligned     the rate gap and price moved the same way over 3 months
  diverging   they moved opposite ways. Either price catches up with rates
              (the trade) or rates were wrong (the risk). Worth a look, not
              a signal on its own.

Where both legs have daily yields (pairs among USD, EUR, JPY and CAD) there
are two more checks:

  link        60-session correlation between daily spread changes and pair
              returns. High means the pair is trading on rates right now;
              near zero means something else is in charge and the rate case
              matters less.
  fair value  price regressed on the spread over 250 sessions. The residual
              in standard deviations says how far price sits from where rates
              alone would put it. A big residual with a strong link is the
              classic rates-driven swing setup.

Pairs whose legs have only monthly yields get the rate gap and its 3-month
change but no link or fair value. Where the two legs' rates are different
maturities (a US 2y against a Swiss 3-month) only the change is shown. A monthly average can't support a daily
correlation, and estimating one anyway would be decoration.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd

from . import config as C
from .fx import pair_names
from .macro import CurrencyRead
from .ts import efficiency_ratio, pct_change, rnd, upto


@dataclass
class PairRead:
    pair: str
    base: str
    quote: str
    macro_diff: float | None = None
    bias: str | None = None             # long | short | None
    spread_bp: float | None = None
    spread_quality: str | None = None   # daily | monthly | mixed tenor | None
    spread_1m_bp: float | None = None
    spread_3m_bp: float | None = None
    return_1m_pct: float | None = None
    return_3m_pct: float | None = None
    vs_ma_pct: float | None = None      # distance from the 50-session average
    efficiency: float | None = None
    rates_vs_price: str | None = None   # aligned | diverging | None
    link_corr: float | None = None
    fair_value: float | None = None
    residual_z: float | None = None
    cot_note: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def _tenor(series_id: str) -> str:
    return series_id.split(".")[1].removesuffix("_M")


def _front(read: CurrencyRead, macro: pd.DataFrame, asof) -> pd.Series:
    return upto(macro.get(read.front_end_id), asof) if read.front_end_id else pd.Series(dtype=float)


def rates_link(close: pd.Series, spread: pd.Series) -> tuple:
    """(correlation, fair value, residual z) from daily data, or Nones."""
    df = pd.concat([np.log(close).rename("p"), spread.rename("s")], axis=1).dropna()
    corr = None
    tail = df.iloc[-(C.LINK_SESSIONS + 1):].diff().dropna()
    if len(tail) >= C.MIN_LINK_SESSIONS and tail.std().min() > 0:
        corr = float(tail["p"].corr(tail["s"]))
    fit = df.iloc[-C.FAIR_VALUE_SESSIONS:]
    if len(fit) < C.FAIR_VALUE_SESSIONS // 2 or fit["s"].std() == 0:
        return corr, None, None
    slope, intercept = np.polyfit(fit["s"], fit["p"], 1)
    resid = fit["p"] - (intercept + slope * fit["s"])
    sd = resid.std()
    fair = float(np.exp(intercept + slope * fit["s"].iloc[-1]))
    return corr, fair, (float(resid.iloc[-1] / sd) if sd else None)


def read_pair(base: CurrencyRead, quote: CurrencyRead, close: pd.Series | None,
              macro: pd.DataFrame, asof: pd.Timestamp) -> PairRead:
    r = PairRead(base.ccy + quote.ccy, base.ccy, quote.ccy)
    if base.score is not None and quote.score is not None:
        r.macro_diff = rnd(base.score - quote.score, 0)
        if abs(r.macro_diff) >= C.PAIR_BIAS_MIN:
            r.bias = "long" if r.macro_diff > 0 else "short"

    fb, fq = _front(base, macro, asof), _front(quote, macro, asof)
    if base.front_end is not None and quote.front_end is not None:
        same_tenor = _tenor(base.front_end_id) == _tenor(quote.front_end_id)
        both_daily = base.quality == quote.quality == "daily"
        r.spread_quality = ("daily" if both_daily else
                            "monthly" if same_tenor else "mixed tenor")
        # A 2y yield minus a 3-month rate is mostly the gap between two points
        # on a curve, not between two central banks. Its direction of travel
        # still says something; its level doesn't, so it isn't shown.
        if same_tenor:
            r.spread_bp = rnd(100 * (base.front_end - quote.front_end), 0)
        for attr, a, b in (("spread_1m_bp", base.momentum_1m_bp, quote.momentum_1m_bp),
                           ("spread_3m_bp", base.momentum_3m_bp, quote.momentum_3m_bp)):
            if a is not None and b is not None:
                setattr(r, attr, rnd(a - b, 0))

    if close is not None:
        c = upto(close, asof)
        if len(c) > C.TREND_MA:
            r.return_1m_pct = rnd(pct_change(c, C.SHORT_DAYS, asof), 2)
            r.return_3m_pct = rnd(pct_change(c, C.LONG_DAYS, asof), 2)
            ma = c.iloc[-C.TREND_MA:].mean()
            r.vs_ma_pct = rnd(100 * (c.iloc[-1] / ma - 1), 2)
            r.efficiency = rnd(efficiency_ratio(c, C.EFFICIENCY_SESSIONS), 2)
        if r.spread_3m_bp and r.return_3m_pct:
            r.rates_vs_price = ("aligned" if np.sign(r.spread_3m_bp) == np.sign(r.return_3m_pct)
                                else "diverging")
        if r.spread_quality == "daily":
            corr, fair, z = rates_link(c, (fb - fq).dropna())
            r.link_corr, r.fair_value, r.residual_z = rnd(corr, 2), rnd(fair, 5), rnd(z, 2)

    notes = [f"{x.ccy} {x.cot_flag}" for x in (base, quote) if x.cot_flag]
    r.cot_note = "; ".join(notes) or None
    return r


def read_all(reads: list[CurrencyRead], closes: dict[str, pd.Series],
             macro: pd.DataFrame, asof: pd.Timestamp) -> list[PairRead]:
    by = {r.ccy: r for r in reads}
    out = [read_pair(by[b], by[q], closes.get(b + q), macro, asof)
           for b, q in pair_names()]
    return sorted(out, key=lambda p: -abs(p.macro_diff or 0))
