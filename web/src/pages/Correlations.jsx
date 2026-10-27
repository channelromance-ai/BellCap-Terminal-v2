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
    <Panel num={num} title="Moving with it now" aside="last 20 sessions · co-movement, not cause" bodyClass="scroll">
      <table className="t">
        <thead><tr><th className="l">Market</th><th>This month</th><th>3 months</th><th>1 year</th><th>Typical move here</th>
          <th>Share of moves</th><th>Its 1M move</th><th>Implies here</th></tr></thead>
        <tbody>
          {t.partners.map((p) => {
            const to = pageFor(p.name);
            return (
              <tr key={p.name} className={to ? "click" : ""} onClick={() => to && go(to)}>
                <td className="l name">{LABEL[p.name] ?? p.name}</td>
                <td className={Math.abs(p.corr) < 0.45 ? "dim" : ""}><Signed v={p.corr} /></td>
                <td className="dim">{fmt(p.corr_60)}</td>
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
        "implies here" means it's moving on something other than that partner. With 20 days of data, links weaker
        than ±0.45 (greyed) can be chance.</div>
    </Panel>
  );
}

const name = (n) => LABEL[n] ?? n;

function LinkTable({ rows, shift }) {
  return (
    <table className="t">
      <thead><tr><th className="l">Markets</th><th>This month</th><th>1 year</th>{shift && <th>Change</th>}</tr></thead>
      <tbody>{rows.map((l) => (
        <tr key={l.a + l.b} className={pageFor(l.a) ? "click" : ""} onClick={() => pageFor(l.a) && go(pageFor(l.a))}>
          <td className="l"><span className="name">{name(l.a)}</span> <span className="dim">&</span> <span className="name">{name(l.b)}</span></td>
          <td><Signed v={l.corr} /></td><td className="dim">{fmt(l.corr_1y)}</td>
          {shift && <td><Signed v={l.shift} /></td>}
        </tr>))}
      </tbody>
    </table>
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
    <div className="grid">
    <div className="grid cols-2e">
      <Panel num={1} title="Moving together right now" aside={`last 20 sessions to ${c.asof}`} bodyClass="scroll">
        {c.links?.length ? <LinkTable rows={c.links} /> : <div className="dim">No strong cross-market links this month.</div>}
        <div className="note">Strongest links between different markets (siblings like WTI/Brent or two USD pairs left out). Green = move together, red = opposite.</div>
      </Panel>
      <Panel num={2} title="Links forming or breaking" aside="this month vs the last year" bodyClass="scroll">
        {c.shifts?.length ? <LinkTable rows={c.shifts} shift /> : <div className="dim">Nothing unusual this month.</div>}
        <div className="note">Where this month's relationship differs most from the usual one: often the first sign that a new story (like an oil shock) is driving markets.</div>
      </Panel>
    </div>
    <Panel num={10} title="Cross-market correlations" bodyClass="scroll"
           aside={<span style={{ display: "inline-flex", gap: 10 }}>
             <Toggle options={[["corr", "This month"], ["corr_60", "3 months"], ["corr_1y", "1 year"]]} value={win} onChange={setWin} />
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
      <div className="note">Correlation of daily moves: +1 = always together, -1 = always opposite, 0 = unrelated.
        "This month" is the last 20 sessions, where anything weaker than ±0.45 can be chance. Open any pair or market for
        what's moving with it and what those moves imply. Co-movement, not cause.</div>
    </Panel>
    </div>
  );
}
