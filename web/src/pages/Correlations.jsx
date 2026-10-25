import { useState } from "react";
import { fmt, isNum } from "../data.js";
import { go } from "../router.js";
import { Panel, Signed, Toggle } from "../components/ui.jsx";

const CORE = ["EURUSD", "GBPUSD", "USDJPY", "USDCHF", "USDCAD", "AUDUSD", "NZDUSD", "XAUUSD", "XAGUSD",
              "WTI", "BRENT", "NAS100", "US500", "US30", "GER40", "UK100", "JP225", "USDIDX", "US10Y", "VIX"];
const LABEL = { USDIDX: "Dollar index", US10Y: "US 10y yield", VIX: "VIX" };
export const pageFor = (n) => (n.length === 6 && !["XAUUSD", "XAGUSD", "NAS100", "UK100", "JP225", "GER40"].includes(n)
  ? `pair/${n}` : ["USDIDX", "US10Y", "VIX"].includes(n) ? null : `market/${n}`);

// Green = move together, red = move opposite; stronger colour = tighter link.
const shade = (c) => !isNum(c) ? "transparent"
  : `rgba(${c > 0 ? "49,209,88" : "255,69,69"},${Math.min(Math.abs(c), 1) * 0.85})`;

// For a pair or market page: its strongest partners and what they imply.
export function MovesWith({ snap, id, num }) {
  const t = snap.correlations?.top?.[id];
  if (!t) return null;
  return (
    <Panel num={num} title="Moves with" aside="last 60 sessions · co-movement, not cause" bodyClass="scroll">
      <table className="t">
        <thead><tr><th className="l">Market</th><th>Corr</th><th>1y corr</th><th>Typical move here</th>
          <th>Share of moves</th><th>Its 1M move</th><th>Implies here</th></tr></thead>
        <tbody>
          {t.partners.map((p) => {
            const to = pageFor(p.name);
            return (
              <tr key={p.name} className={to ? "click" : ""} onClick={() => to && go(to)}>
                <td className="l name">{LABEL[p.name] ?? p.name}</td>
                <td><Signed v={p.corr} /></td>
                <td className="dim">{fmt(p.corr_1y)}</td>
                <td>{isNum(p.beta) ? `${p.beta > 0 ? "+" : ""}${p.beta.toFixed(2)}% per ${p.per}` : "-"}</td>
                <td>{isNum(p.explained) ? `${Math.round(p.explained * 100)}%` : "-"}</td>
                <td><Signed v={p.other_1m} unit={p.other_unit} /></td>
                <td><Signed v={p.implied_1m} unit="%" /></td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <div className="note">This market's actual 1-month move: <Signed v={t.actual_1m} unit={t.unit} />. Far from
        "implies here" means it's moving on something other than that partner.</div>
    </Panel>
  );
}

export default function Correlations({ snap }) {
  const [win, setWin] = useState("corr");
  const [set, setSet] = useState("core");
  const c = snap.correlations;
  if (!c) return <div className="dim">No correlation data yet.</div>;
  const at = Object.fromEntries(c.names.map((n, i) => [n, i]));
  const names = set === "core" ? CORE.filter((n) => n in at) : c.names;
  const m = c[win];
  return (
    <Panel num={10} title="Cross-market correlations" bodyClass="scroll"
           aside={<span style={{ display: "inline-flex", gap: 10 }}>
             <Toggle options={[["corr", "60 days"], ["corr_1y", "1 year"]]} value={win} onChange={setWin} />
             <Toggle options={[["core", "Core"], ["all", "All 28 pairs"]]} value={set} onChange={setSet} />
           </span>}>
      <table className="t" style={{ width: "auto", fontSize: 11 }}>
        <thead><tr><th />{names.map((n) => (
          <th key={n} style={{ writingMode: "vertical-rl", transform: "rotate(180deg)", textAlign: "left", padding: "4px 1px" }}>
            {LABEL[n] ?? n}</th>))}</tr></thead>
        <tbody>
          {names.map((a) => (
            <tr key={a}>
              <td className="l name">{LABEL[a] ?? a}</td>
              {names.map((b) => {
                const v = m[at[a]][at[b]];
                return (
                  <td key={b} title={`${a} vs ${b}: ${fmt(v)}`}
                      style={{ background: a === b ? "#222" : shade(v), color: "#fff", textAlign: "center", padding: "2px 3px" }}>
                    {a === b ? "" : isNum(v) ? v.toFixed(1).replace("0.", ".") : ""}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
      <div className="note">Correlation of daily moves: +1 = always together, -1 = always opposite, 0 = unrelated. Compare
        60 days with 1 year to see links strengthening or breaking (oil vs stocks this month, for example). Open any pair
        or market for its strongest partners and what their moves imply. Co-movement, not cause.</div>
    </Panel>
  );
}
