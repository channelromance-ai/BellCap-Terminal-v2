import { useState } from "react";
import { fmt, isNum } from "../data.js";
import { go } from "../router.js";
import { Lean, Panel, RangeBar, Signed, Spark } from "../components/ui.jsx";

// [key, header, value getter, render]
const COLS = [
  ["pair", "Pair", (r) => r.pair, (r) => <span className="name">{r.pair}</span>, "l"],
  ["last", "Last", (r) => r.m.last, (r) => <span className="white">{r.m.last ?? "-"}</span>],
  ["d1", "1D%", (r) => r.m.chg_1d_pct, (r) => <Signed v={r.m.chg_1d_pct} />],
  ["m1", "1M%", (r) => r.return_1m_pct, (r) => <Signed v={r.return_1m_pct} />],
  ["m3", "3M%", (r) => r.return_3m_pct, (r) => <Signed v={r.return_3m_pct} />],
  ["gap", "Rate gap", (r) => r.spread_bp, (r) => (isNum(r.spread_bp) ? `${fmt(r.spread_bp, 0)}bp` : <span className="dim">{r.spread_quality === "mixed tenor" ? "mixed" : "-"}</span>)],
  ["gap3", "Gap 3M", (r) => r.spread_3m_bp, (r) => <Signed v={r.spread_3m_bp} d={0} unit="bp" />],
  ["score", "Score gap", (r) => r.macro_diff, (r) => <Signed v={r.macro_diff} d={0} />],
  ["lean", "Lean", (r) => r.card?.lean, (r) => <Lean lean={r.card?.lean} bias={r.bias} />, "l"],
  ["rvp", "Rates vs price", (r) => r.rates_vs_price, (r) => <span className={r.rates_vs_price === "diverging" ? "warn" : "dim"}>{r.rates_vs_price ?? "-"}</span>, "l"],
  ["fv", "FV z", (r) => r.residual_z, (r) => <Signed v={r.residual_z} />],
  ["link", "Link", (r) => r.link_corr, (r) => fmt(r.link_corr)],
  ["eff", "Eff", (r) => r.efficiency, (r) => fmt(r.efficiency)],
  ["range", "1Y range", (r) => (isNum(r.m.lo_1y) ? (r.m.last - r.m.lo_1y) / (r.m.hi_1y - r.m.lo_1y) : null),
   (r) => <RangeBar lo={r.m.lo_1y} hi={r.m.hi_1y} avg={r.m.avg_1y} now={r.m.last} />],
  ["spark", "3M", null, (r) => <Spark values={r.m.spark} />, "l"],
];

export default function Pairs({ snap }) {
  const [sort, setSort] = useState({ key: "score", dir: -1, abs: true });
  const cards = Object.fromEntries(snap.ideas.map((c) => [c.name, c]));
  const rows = snap.pairs.map((p) => ({ ...p, m: snap.markets[p.pair] || {}, card: cards[p.pair] }));
  const col = COLS.find((c) => c[0] === sort.key);
  const val = (r) => {
    const v = col[2](r);
    return isNum(v) && sort.abs ? Math.abs(v) : v;
  };
  rows.sort((a, b) => {
    const x = val(a), y = val(b);
    if (x == null) return 1;
    if (y == null) return -1;
    return (x < y ? -1 : x > y ? 1 : 0) * sort.dir;
  });
  const click = (key) => setSort((s) => (s.key === key ? { ...s, dir: -s.dir, abs: false }
                                                       : { key, dir: -1, abs: false }));
  return (
    <Panel num={2} title="FX pairs" aside="click a header to sort, a row to open" bodyClass="scroll">
      <table className="t">
        <thead><tr>
          {COLS.map(([key, label, get, , align]) => (
            <th key={key} className={`${align || ""} ${get ? "sort" : ""}`} onClick={() => get && click(key)}>
              {label}{sort.key === key ? (sort.dir < 0 ? " ▼" : " ▲") : ""}
            </th>
          ))}
        </tr></thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.pair} className="click" onClick={() => go(`pair/${r.pair}`)}>
              {COLS.map(([key, , , render, align]) => <td key={key} className={align || ""}>{render(r)}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
      <div className="note">
        Rate gap: base front-end rate minus quote ("mixed" when the two are different maturities, where only
        the change is meaningful). FV z: price vs where rates put it, in standard deviations (daily-rate pairs
        only). Link: 60-day correlation of the pair with its rate gap. Eff: how directly price has travelled
        lately (1 = straight line, 0 = chop). Range bar: 1-year low to high, ◆ average, ● now.
      </div>
    </Panel>
  );
}
