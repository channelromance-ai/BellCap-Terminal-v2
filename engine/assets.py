"""
Driver reads for gold, silver, the indices and oil, and the risk regime.

Each asset has a short list of macro drivers with a direction taken from
economics, not fitted: rising real yields weigh on gold, a weaker yen lifts
the Nikkei. For each driver the read shows

  move    its change over the last month
  z       how unusual that move is against its own past three years
  push    z times the driver's direction, clipped at +/-2: what it implies
  corr    the asset's actual 60-session correlation with the driver

`corr` is the honesty check. When a textbook driver's correlation has the
wrong sign, the textbook isn't what's moving the market right now, and the
push from that driver deserves less trust. It is shown, not used to re-weight:
a model that drops whatever stopped working last month just chases noise.

The score is the weighted average push, scaled to -100..100. Like the
currency score it is a reading of the drivers, not a forecast.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

import numpy as np
import pandas as pd

from . import config as C
from .macro import cot_read
from .ts import change_z, clip, efficiency_ratio, last, pct_change, percentile, rnd, upto

# (driver key, direction, weight)
DRIVERS = {
    "XAUUSD": [("real10y", -1, .40), ("usd", -1, .30), ("be10y", +1, .15), ("vix", +1, .15)],
    "XAGUSD": [("real10y", -1, .30), ("usd", -1, .30), ("us500", +1, .20), ("be10y", +1, .20)],
    "NAS100": [("real10y", -1, .35), ("vix", -1, .25), ("us2y", -1, .25), ("usd", -1, .15)],
    "US500": [("real10y", -1, .30), ("vix", -1, .30), ("us2y", -1, .20), ("usd", -1, .20)],
    "US30": [("real10y", -1, .30), ("vix", -1, .30), ("us2y", -1, .20), ("usd", -1, .20)],
    "GER40": [("eur2y", -1, .30), ("vix", -1, .30), ("eurusd", -1, .20), ("real10y", -1, .20)],
    "UK100": [("vix", -1, .30), ("gbpusd", -1, .25), ("gbp10y", -1, .25), ("brent", +1, .20)],
    "JP225": [("usdjpy", +1, .40), ("vix", -1, .40), ("jpy10y", -1, .20)],
    "WTI": [("usd", -1, .40), ("us500", +1, .35), ("vix", -1, .25)],
    "BRENT": [("usd", -1, .40), ("us500", +1, .35), ("vix", -1, .25)],
}
GROUP = {"XAUUSD": "metals", "XAGUSD": "metals", "WTI": "energy", "BRENT": "energy"}
COT_OF = {"XAUUSD": "COT.GOLD", "XAGUSD": "COT.SILVER", "WTI": "COT.WTI",
          "BRENT": "COT.WTI", "NAS100": "COT.NDX", "US500": "COT.SPX"}
NOTES = {
    "WTI": "Thin read: no inventory or OPEC data yet. USO stand-in carries roll costs.",
    "BRENT": "Thin read: no inventory or OPEC data yet. BNO stand-in carries roll costs.",
    "JP225": "EWJ stand-in tracks MSCI Japan, not the Nikkei.",
}

# key -> (label, kind). kind: "rate" (bp moves), "price" (% moves), "level" (points)
DRIVER_INFO = {
    "real10y": ("US 10y real yield", "rate"), "us2y": ("US 2y yield", "rate"),
    "be10y": ("US 10y breakeven", "rate"), "vix": ("VIX", "level"),
    "usd": ("Dollar index", "price"), "eurusd": ("EURUSD", "price"),
    "gbpusd": ("GBPUSD", "price"), "usdjpy": ("USDJPY", "price"),
    "us500": ("US500", "price"), "brent": ("Brent", "price"),
    "eur2y": ("German 2y yield", "rate"), "jpy10y": ("Japan 10y yield", "rate"),
    "gbp10y": ("UK 10y yield (monthly)", "rate"),
}


@dataclass
class Driver:
    key: str
    label: str
    direction: int
    weight: float
    move: float | None = None
    move_unit: str = ""
    z: float | None = None
    push: float | None = None
    corr: float | None = None
    monthly: bool = False


@dataclass
class AssetRead:
    name: str
    group: str
    score: float | None = None
    drivers: list[Driver] = field(default_factory=list)
    return_1m_pct: float | None = None
    return_3m_pct: float | None = None
    vs_ma_pct: float | None = None
    efficiency: float | None = None
    cot_net: float | None = None
    cot_pct: float | None = None
    cot_flag: str | None = None
    link_check: dict | None = None     # gold only: is the real-yield link intact?
    note: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def driver_series(macro: pd.DataFrame, bars: dict, usd_index: pd.Series) -> dict:
    close = {k: v["close"] for k, v in bars.items()}
    return {
        "real10y": macro.get("USD.REAL10Y"), "us2y": macro.get("USD.2Y"),
        "be10y": macro.get("USD.BE10Y"), "vix": macro.get("VIX"),
        "eur2y": macro.get("EUR.2Y"), "jpy10y": macro.get("JPY.10Y"),
        "gbp10y": macro.get("GBP.10Y_M"), "usd": usd_index,
        "eurusd": close.get("EURUSD"), "gbpusd": close.get("GBPUSD"),
        "usdjpy": close.get("USDJPY"), "us500": close.get("US500"),
        "brent": close.get("BRENT"),
    }


def _is_monthly(s: pd.Series) -> bool:
    return len(s) > 3 and s.index.to_series().diff().median() > pd.Timedelta(days=20)


def read_driver(key: str, direction: int, weight: float, s: pd.Series | None,
                asset_close: pd.Series, asof) -> Driver:
    label, kind = DRIVER_INFO[key]
    d = Driver(key, label, direction, weight)
    s = upto(s, asof)
    if s.empty:
        return d
    d.monthly = _is_monthly(s)
    is_price = kind == "price"
    if d.monthly:                       # one monthly print vs three years of them
        d.z = change_z(s, asof, 1, 36, log=is_price, min_moves=12)
        days = 31
    else:
        d.z = change_z(s, asof, C.Z_CHANGE_SESSIONS, C.Z_HISTORY_SESSIONS, log=is_price)
        days = C.SHORT_DAYS
    if is_price:
        d.move, d.move_unit = rnd(pct_change(s, days, asof), 2), "%"
    else:
        base = s[s.index <= s.index[-1] - pd.Timedelta(days=days)]
        if len(base):
            mult = 100 if kind == "rate" else 1
            d.move = rnd(mult * (s.iloc[-1] - base.iloc[-1]), 1 if kind == "level" else 0)
            d.move_unit = "bp" if kind == "rate" else "pts"
    d.push = rnd(None if d.z is None else direction * clip(d.z), 2)
    d.z = rnd(d.z, 2)
    if not d.monthly:
        a = np.log(upto(asset_close, asof))
        x = np.log(s) if is_price else s
        both = pd.concat([a.diff(), x.diff()], axis=1).dropna().iloc[-C.LINK_SESSIONS:]
        if len(both) >= C.MIN_LINK_SESSIONS:
            d.corr = rnd(both.iloc[:, 0].corr(both.iloc[:, 1]), 2)
    return d


def gold_link_check(gold: pd.Series, real10y: pd.Series | None, asof) -> dict:
    """Gold's correlation with real yields: normally strongly negative. Three
    states, because 'the check couldn't run' is not the same as 'it passed'."""
    if real10y is None:
        return {"state": "unknown", "corr": None}
    both = pd.concat([np.log(upto(gold, asof)).diff(), upto(real10y, asof).diff()],
                     axis=1).dropna().iloc[-C.LINK_SESSIONS:]
    if len(both) < C.MIN_LINK_SESSIONS:
        return {"state": "unknown", "corr": None}
    corr = float(both.iloc[:, 0].corr(both.iloc[:, 1]))
    state = ("ok" if corr <= C.GOLD_LINK_OK else
             "weak" if corr >= C.GOLD_LINK_WEAK else "fading")
    return {"state": state, "corr": rnd(corr, 2)}


def read_asset(name: str, bars: dict, series: dict, macro: pd.DataFrame, asof) -> AssetRead:
    r = AssetRead(name, GROUP.get(name, "indices"), note=NOTES.get(name))
    if name not in bars:
        return r
    close = upto(bars[name]["close"], asof)
    r.drivers = [read_driver(k, sign, w, series.get(k), close, asof)
                 for k, sign, w in DRIVERS[name]]
    used = [d for d in r.drivers if d.push is not None]
    if used:
        total = sum(d.weight * d.push for d in used) / sum(d.weight for d in used)
        r.score = rnd(max(-100.0, min(100.0, 50 * total)), 0)
    if len(close) > C.TREND_MA:
        r.return_1m_pct = rnd(pct_change(close, C.SHORT_DAYS, asof), 2)
        r.return_3m_pct = rnd(pct_change(close, C.LONG_DAYS, asof), 2)
        r.vs_ma_pct = rnd(100 * (close.iloc[-1] / close.iloc[-C.TREND_MA:].mean() - 1), 2)
        r.efficiency = rnd(efficiency_ratio(close, C.EFFICIENCY_SESSIONS), 2)
    if name in COT_OF:
        net, pct, flag = cot_read(macro.get(COT_OF[name]), asof)
        r.cot_net, r.cot_pct, r.cot_flag = rnd(net, 1), rnd(pct, 0), flag
    if name == "XAUUSD":
        r.link_check = gold_link_check(close, series.get("real10y"), asof)
    return r


def read_all(macro: pd.DataFrame, bars: dict, usd_index: pd.Series, asof) -> list[AssetRead]:
    series = driver_series(macro, bars, usd_index)
    return [read_asset(n, bars, series, macro, asof) for n in DRIVERS]


def risk_regime(macro: pd.DataFrame, asof) -> dict:
    vix = macro.get("VIX")
    got = last(vix, asof)
    if got is None:
        return {"state": "unknown"}
    level = got[1]
    pct = percentile(vix, asof, 252)
    s = upto(vix, asof)
    base = s[s.index <= s.index[-1] - pd.Timedelta(days=C.SHORT_DAYS)]
    move = level - base.iloc[-1] if len(base) else None
    if level >= C.VIX_STRESS_LEVEL or (pct is not None and pct >= C.VIX_STRESS_PCT):
        state = "stressed"
    elif move is not None and move >= C.VIX_RISING_POINTS:
        state = "stress rising"
    elif pct is not None and pct <= C.VIX_CALM_PCT:
        state = "calm"
    else:
        state = "normal"
    curve = None
    two, ten = last(macro.get("USD.2Y"), asof), last(macro.get("USD.10Y"), asof)
    if two and ten:
        curve = rnd(100 * (ten[1] - two[1]), 0)
    return {"state": state, "vix": rnd(level, 2), "vix_pct_1y": rnd(pct, 0),
            "vix_1m_move": rnd(move, 2), "us_2s10s_bp": curve}
