"""
The thesis card for each pair and asset: the macro lean, what supports it,
what argues against it, what's coming up, and a volatility-based template.

Built from the read itself, no new judgement: every line points at a number
on the page. The lean is the sign of the macro score (gap); `bias` is set
only when it clears the threshold in config. Each card also carries the
measured track record of that kind of lean. On 2026-10-25 that record says
"no proven edge", and the card shows it next to the lean on purpose.

The setup is a template sized by recent volatility (entry on a pullback,
stop and targets in multiples of the average daily move), labelled as such.
It is not a tested strategy.
"""

from __future__ import annotations

import pandas as pd

from . import config as C
from . import edge
from .correlations import family
from .ts import ordinal, rnd, upto

RISK_CCYS, HAVEN_CCYS = {"AUD", "NZD", "CAD"}, {"JPY", "CHF", "USD"}
ASSET_CCYS = {"XAUUSD": ["USD"], "XAGUSD": ["USD"], "NAS100": ["USD"], "US500": ["USD"],
              "US30": ["USD"], "GER40": ["EUR"], "UK100": ["GBP"], "JP225": ["JPY"],
              "WTI": ["USD"], "BRENT": ["USD"]}
OIL_WORDS = ("crude", "oil", "opec")


def _sign(x) -> int:
    return 0 if x is None or x == 0 else (1 if x > 0 else -1)


def daily_move(close: pd.Series, asof) -> float | None:
    c = upto(close, asof).iloc[-21:]
    return float(c.diff().abs().mean()) if len(c) >= 21 else None


def setup(close: pd.Series, asof, lean: int) -> dict | None:
    dm = daily_move(close, asof)
    c = upto(close, asof)
    if not lean or dm is None or c.empty:
        return None
    last = float(c.iloc[-1])
    entry = last - lean * C.SETUP_ENTRY_PULLBACK * dm
    stop = entry - lean * C.SETUP_STOP_MOVES * dm
    risk = abs(entry - stop)
    digits = 5 if last < 20 else 2
    return {"side": "long" if lean > 0 else "short", "last": rnd(last, digits),
            "entry": rnd(entry, digits), "stop": rnd(stop, digits),
            "targets": [rnd(entry + lean * r * risk, digits) for r in C.SETUP_TARGETS_R],
            "targets_r": list(C.SETUP_TARGETS_R), "daily_move": rnd(dm, digits),
            "label": "volatility template - not a tested strategy"}


def catalysts(calendar: list[dict], ccys: list[str], oil: bool = False) -> list[dict]:
    keep = []
    for e in calendar:
        if e["past"]:
            continue
        if e["currency"] in ccys or (oil and any(w in e["title"].lower() for w in OIL_WORDS)):
            keep.append(e)
    return keep[:8]


def track(calib: dict | None, key: str) -> dict:
    out = {}
    for h, stats in ((calib or {}).get("horizons") or {}).items():
        st = stats.get(key) or {}
        out[h] = {"hit": st.get("hit"), "t": st.get("t"), "t_halves": st.get("t_halves"),
                  "signals": st.get("signals"), "proven": edge.proven(st)}
    return out


def pair_card(p: dict, ccy: dict, regime: dict, calendar: list, close, asof, calib) -> dict:
    b, q = ccy[p["base"]], ccy[p["quote"]]
    lean = _sign(p["macro_diff"])
    pro, con, notes = [], [], []
    side = lambda s: pro if s == lean else con
    if lean:
        pro.append(f"{b['ccy']} scores {b['score']:+.0f} vs {q['ccy']} {q['score']:+.0f}")
        if p["spread_3m_bp"]:
            winner = b["ccy"] if p["spread_3m_bp"] > 0 else q["ccy"]
            data = "" if p["spread_quality"] == "daily" else f" ({p['spread_quality']} data)"
            side(_sign(p["spread_3m_bp"])).append(
                f"Rate gap moved {p['spread_3m_bp']:+.0f}bp in 3 months, toward {winner}{data}")
        if p["return_3m_pct"]:
            side(_sign(p["return_3m_pct"])).append(f"Price {p['return_3m_pct']:+.2f}% over 3 months")
        if p["residual_z"] is not None and abs(p["residual_z"]) >= 1:
            where = "below" if p["residual_z"] < 0 else "above"
            side(-_sign(p["residual_z"])).append(
                f"Price is {abs(p['residual_z']):.1f} SD {where} where rates put it")
        if p["link_corr"] is not None:
            if p["link_corr"] < 0.2:
                con.append(f"Pair isn't trading on rates right now (60-day link {p['link_corr']:+.2f})")
            elif p["link_corr"] >= 0.5:
                pro.append(f"Pair is trading closely on rates (60-day link {p['link_corr']:+.2f})")
        for leg, direction in ((b, lean), (q, -lean)):
            if leg.get("cot_flag"):
                crowded = 1 if "long" in leg["cot_flag"] else -1
                (con if crowded == direction else pro).append(
                    f"{leg['ccy']} speculators {leg['cot_flag']} ({ordinal(max(leg['cot_pct'], 1))} percentile of 3 years)")
        if regime.get("state") in ("stressed", "stress rising"):
            long_ccy, short_ccy = (b["ccy"], q["ccy"]) if lean > 0 else (q["ccy"], b["ccy"])
            if long_ccy in RISK_CCYS and short_ccy in HAVEN_CCYS:
                con.append(f"Risk regime is '{regime['state']}' and this is long a risk currency")
            elif long_ccy in HAVEN_CCYS and short_ccy in RISK_CCYS:
                pro.append(f"Risk regime is '{regime['state']}' and this is long a haven")
    if p["rates_vs_price"] == "diverging":
        notes.append("Price hasn't followed the rate gap over 3 months")
    if p["efficiency"] is not None and p["efficiency"] < 0.15:
        notes.append(f"Choppy: price has gone nowhere lately (efficiency {p['efficiency']:.2f})")
    for leg in (b, q):
        if leg["quality"] != "daily":
            notes.append(f"{leg['ccy']} rates are {leg['quality']}")
    return _card(p["pair"], "pair", p["bias"], lean, pro, con, notes,
                 catalysts(calendar, [b["ccy"], q["ccy"]]), close, asof,
                 track(calib, "pair_score"))


def asset_card(a: dict, regime: dict, calendar: list, close, asof, calib) -> dict:
    lean = _sign(a["score"]) if a["score"] is not None and abs(a["score"]) >= 5 else 0
    bias = (("long" if a["score"] > 0 else "short")
            if a["score"] is not None and abs(a["score"]) >= C.ASSET_BIAS_MIN else None)
    pro, con, notes = [], [], []
    for d in a["drivers"]:
        if d["push"] is None or not lean:
            continue
        text = f"{d['label']} {d['move']:+}{d['move_unit']} ({d['z']:+.1f} SD move)"
        if d["push"] * lean > 0.3:
            pro.append(text)
        elif d["push"] * lean < -0.3:
            con.append(text)
        if d["corr"] is not None and d["direction"] * d["corr"] < -0.2:
            notes.append(f"{d['label']} isn't behaving as usual (60-day corr {d['corr']:+.2f})")
    if lean and a["return_3m_pct"]:
        (pro if _sign(a["return_3m_pct"]) == lean else con).append(
            f"Price {a['return_3m_pct']:+.2f}% over 3 months")
    if a["cot_flag"] and lean:
        crowded = 1 if "long" in a["cot_flag"] else -1
        (con if crowded == lean else pro).append(
            f"Speculators {a['cot_flag']} ({ordinal(max(a['cot_pct'], 1))} percentile of 3 years)")
    if a.get("link_check") and a["link_check"]["state"] != "ok":
        notes.append(f"Gold's real-yield link is {a['link_check']['state']} "
                     f"(corr {a['link_check']['corr']})")
    if a.get("note"):
        notes.append(a["note"])
    if regime.get("state") in ("stressed", "stress rising") and a["group"] == "indices" and lean > 0:
        con.append(f"Risk regime is '{regime['state']}'")
    cal = catalysts(calendar, ASSET_CCYS.get(a["name"], []), oil=a["group"] == "energy")
    return _card(a["name"], "asset", bias, lean, pro, con, notes, cal, close, asof,
                 track(calib, "asset_score"))


def _card(name, kind, bias, lean, pro, con, notes, cal, close, asof, record) -> dict:
    return {"name": name, "kind": kind, "bias": bias,
            "lean": {1: "long", -1: "short"}.get(lean), "for": pro, "against": con,
            "notes": notes, "catalysts": cal,
            "setup": setup(close, asof, lean) if bias else None,
            "track_record": record}


def partner_note(name: str, corr: dict | None) -> str | None:
    """The market this one moves with most, and what that partner's month
    implies here if the usual relationship held, against what happened."""
    top = (corr or {}).get("top", {}).get(name)
    # Skip siblings (pairs sharing a currency, Brent for WTI, silver for gold):
    # they say little. The useful partner is the strongest one from elsewhere.
    p = next((x for x in (top or {}).get("partners", [])
              if not family(name) & family(x["name"])), None)
    if not p or abs(p["corr"]) < 0.5 or p["implied_1m"] is None or top["actual_1m"] is None:
        return None
    return (f"Moving with {p['name']} this month (corr {p['corr']:+.2f}, {p['explained']:.0%} of moves): "
            f"its {p['other_1m']:+.1f}{p['other_unit']} month implies {p['implied_1m']:+.2f}% here; "
            f"actual {top['actual_1m']:+.2f}%")


def asia_block(card: dict, snapshot: dict) -> dict | None:
    """The card's Asia-session view: how this market behaves in the user's
    hours, and which of its catalysts fall inside them."""
    a = snapshot.get("asia") or {}
    prof = a.get("markets", {}).get(card["name"])
    ccys = ({card["name"][:3], card["name"][3:]} if card["kind"] == "pair"
            else set(ASSET_CCYS.get(card["name"], [])))
    events = [e for e in a.get("events", []) if not e["past"] and e["currency"] in ccys]
    if not prof and not events:
        return None
    return {**(prof or {}), "events": events[:6]}


def build_cards(snapshot: dict, closes: dict, asof, calib: dict | None,
                corr: dict | None = None) -> list[dict]:
    ccy = {c["ccy"]: c for c in snapshot["currencies"]}
    cards = [pair_card(p, ccy, snapshot["regime"], snapshot["calendar"],
                       closes.get(p["pair"]), asof, calib)
             for p in snapshot["pairs"] if p["pair"] in closes]
    cards += [asset_card(a, snapshot["regime"], snapshot["calendar"], closes.get(a["name"]),
                         asof, calib)
              for a in snapshot["assets"] if a["name"] in closes]
    for card in cards:
        card["asia"] = asia_block(card, snapshot)
        note = partner_note(card["name"], corr)
        if note:
            card["notes"].insert(0, note)
    return cards
