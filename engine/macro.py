"""
The macro read for each of the eight currencies.

For a swing trader the question per currency is: which way is its central
bank leaning, and is the market moving that way? So each read answers, in
order:

  policy        where the rate is and the last time it moved
  path          front-end market rate minus policy rate. Positive means the
                market prices hikes, negative means cuts.
  momentum      how far the front-end rate moved over 1 and 3 months. This
                is the main FX swing driver: currencies follow the CHANGE in
                rate expectations far more than the level.
  inflation     CPI against the bank's own target, and its 3-month direction
  real rate     policy minus CPI: how tight policy actually is
  positioning   speculative net position as a percentile of 3 years. Only
                the extremes mean anything (crowded trades unwind).

Each read says how good its rates data is ("daily", "monthly" or "policy
only"), because a 3-month momentum built from monthly averages is not the
same quality as one built from daily closes, and the dashboard shouldn't pretend otherwise.

The score is a weighted blend of cross-sectional z-scores (see config). It
is a ranking of the eight against each other on the day, not a forecast.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

import numpy as np
import pandas as pd

from . import config as C
from .catalog import LAGS
from .ts import change, change_z, clip, last, percentile, rnd, upto, value_at


@dataclass
class CurrencyRead:
    ccy: str
    quality: str                       # daily | monthly | policy only
    policy: float | None = None
    policy_date: str | None = None
    last_move_date: str | None = None
    last_move_bp: float | None = None
    policy_change_12m_bp: float | None = None
    front_end_id: str | None = None
    front_end: float | None = None
    front_end_date: str | None = None
    path_bp: float | None = None
    path_scaled: float | None = None    # path / its own typical size
    momentum_1m_bp: float | None = None
    momentum_3m_bp: float | None = None
    momentum_z: float | None = None     # 3m move vs this rate's own 3m moves
    long_end: float | None = None
    curve_bp: float | None = None
    cpi: float | None = None
    cpi_date: str | None = None         # when the model could first see it
    cpi_period: str | None = None       # the month (or quarter) it describes
    cpi_3m_change: float | None = None
    cpi_gap: float | None = None
    real_policy: float | None = None
    cot_net: float | None = None
    cot_pct: float | None = None
    cot_flag: str | None = None        # crowded long | crowded short | None
    strength_1m_pct: float | None = None
    components: dict = field(default_factory=dict)   # name -> z used
    score: float | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def _d(ts) -> str | None:
    return ts.date().isoformat() if ts is not None else None


def last_policy_move(policy: pd.Series):
    """(date, size in bp) of the most recent change in the policy rate."""
    moves = policy.diff()
    moves = moves[moves.abs() > 1e-9]
    return (moves.index[-1], 100 * float(moves.iloc[-1])) if len(moves) else (None, None)


def cot_read(s: pd.Series | None, asof) -> tuple:
    got = last(s, asof)
    if got is None:
        return None, None, None
    pct = percentile(s, asof, C.COT_WINDOW_WEEKS)
    flag = ("crowded long" if pct is not None and pct >= C.COT_EXTREME_HIGH else
            "crowded short" if pct is not None and pct <= C.COT_EXTREME_LOW else None)
    return got[1], pct, flag


def read_currency(ccy: str, macro: pd.DataFrame, asof: pd.Timestamp,
                  strength: pd.DataFrame | None = None) -> CurrencyRead:
    col = macro.get
    policy = upto(col(f"{ccy}.POLICY"), asof)
    front_id = next((i for i in C.FRONT_END[ccy] if not upto(col(i), asof).empty), None)
    quality = ("policy only" if front_id is None else
               "monthly" if front_id.endswith("_M") else "daily")
    r = CurrencyRead(ccy, quality)

    if len(policy):
        r.policy, r.policy_date = float(policy.iloc[-1]), _d(policy.index[-1])
        when, bp = last_policy_move(policy)
        r.last_move_date, r.last_move_bp = _d(when), rnd(bp, 0)
        ch = change(policy, 365, asof)
        r.policy_change_12m_bp = rnd(None if ch is None else 100 * ch, 0)

    if front_id:
        front = col(front_id)
        d, v = last(front, asof)
        r.front_end_id, r.front_end, r.front_end_date = front_id, rnd(v, 3), _d(d)
        # Compare with the policy rate on the market rate's own date. A
        # monthly average set before a hike, measured against the rate after
        # it, reads as the market pricing cuts that nobody priced.
        policy_then = value_at(policy, d) if len(policy) else None
        if policy_then is not None:
            r.path_bp = rnd(100 * (v - policy_then), 0)
            r.path_scaled = rnd(path_scaled(upto(front, asof), policy), 2)
        for days, attr in ((C.SHORT_DAYS, "momentum_1m_bp"), (C.LONG_DAYS, "momentum_3m_bp")):
            ch = change(front, days, asof)
            setattr(r, attr, rnd(None if ch is None else 100 * ch, 0))
        r.momentum_z = rnd(momentum_z(front, quality, asof), 2)

    long_got = last(col(C.LONG_END[ccy]), asof)
    if long_got:
        r.long_end = rnd(long_got[1], 3)
        if r.front_end is not None and quality == "daily":
            r.curve_bp = rnd(100 * (r.long_end - r.front_end), 0)

    cpi = col(C.INFLATION[ccy])
    cpi_got = last(cpi, asof)
    if cpi_got:
        r.cpi, r.cpi_date = rnd(cpi_got[1], 2), _d(cpi_got[0])
        period_end = cpi_got[0] - pd.Timedelta(days=LAGS.get(C.INFLATION[ccy], 0))
        r.cpi_period = period_end.strftime("%b %Y")
        r.cpi_3m_change = rnd(change(cpi, C.LONG_DAYS, asof), 2)
        r.cpi_gap = rnd(cpi_got[1] - C.INFLATION_TARGET[ccy], 2)
        if r.policy is not None:
            r.real_policy = rnd(r.policy - cpi_got[1], 2)

    if ccy in C.COT:
        net, pct, flag = cot_read(col(C.COT[ccy]), asof)
        r.cot_net, r.cot_pct, r.cot_flag = rnd(net, 1), rnd(pct, 0), flag

    if strength is not None and ccy in strength:
        s = upto(strength[ccy], asof)
        base = s[s.index <= s.index[-1] - pd.Timedelta(days=C.SHORT_DAYS)] if len(s) else s
        if len(base):
            r.strength_1m_pct = rnd(100 * (s.iloc[-1] - base.iloc[-1]), 2)
    return r


def momentum_z(front: pd.Series, quality: str, asof) -> float | None:
    """The 3-month move measured against this same rate's own 3-month moves.

    Raw basis points can't be compared across the eight: a 3-month rate sits
    still between meetings while a 2-year yield reprices daily, so ranking
    raw moves penalises AUD, NZD and CHF for the series we happen to have.
    Against its own history, a move is big or small for that rate."""
    if quality == "monthly":
        return change_z(front, asof, 3, 36, min_moves=12)
    return change_z(front, asof, 60, C.Z_HISTORY_SESSIONS)


def path_scaled(front: pd.Series, policy: pd.Series) -> float | None:
    """Path (front-end minus policy) divided by its own typical size, keeping
    its sign: "pricing hikes" stays positive. Same reason as momentum_z: a
    2y-minus-policy gap is naturally wider than a 3m-minus-policy one."""
    pol = policy.reindex(policy.index.union(front.index)).ffill().reindex(front.index)
    path = (front - pol).dropna()
    if len(path) < 12:
        return None
    typical = path.abs().mean()
    return float(path.iloc[-1] / typical) if typical else None


COMPONENT_INPUTS = {
    "rate_momentum": "momentum_z",
    "policy_path": "path_scaled",
    "carry": "policy",
    "inflation": "cpi_gap",
}


def score(reads: list[CurrencyRead]) -> None:
    """Fill in components and score, in place. Cross-sectional: each input is
    z-scored across the currencies that have it, so a score only says how a
    currency compares with the other seven today."""
    for name, attr in COMPONENT_INPUTS.items():
        have = [(r, getattr(r, attr)) for r in reads if getattr(r, attr) is not None]
        if len(have) < C.MIN_CURRENCIES_PER_COMPONENT:
            continue
        vals = np.array([v for _, v in have], dtype=float)
        sd = vals.std()
        for r, v in have:
            r.components[name] = rnd(clip((v - vals.mean()) / sd) if sd else 0.0, 2)
    for r in reads:
        w = {k: C.CURRENCY_WEIGHTS[k] for k in r.components}
        if w:
            total = sum(C.CURRENCY_WEIGHTS[k] * r.components[k] for k in w) / sum(w.values())
            r.score = rnd(max(-100.0, min(100.0, 50 * total)), 0)


def read_all(macro: pd.DataFrame, asof: pd.Timestamp,
             strength: pd.DataFrame | None = None) -> list[CurrencyRead]:
    reads = [read_currency(c, macro, asof, strength) for c in C.CCYS]
    score(reads)
    return reads
