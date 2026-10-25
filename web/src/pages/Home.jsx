import { ASSET_LABEL, fmt, fmtTime, isNum } from "../data.js";
import { go, href } from "../router.js";
import { Lean, Panel, ScoreBar, Signed, Spark } from "../components/ui.jsx";

// Every pair and asset with a bias, strongest first.
export function leans(snap) {
  const cards = Object.fromEntries(snap.ideas.map((c) => [c.name, c]));
  const rows = [
    ...snap.pairs.map((p) => ({ name: p.pair, kind: "pair", score: p.macro_diff })),
    ...snap.assets.map((a) => ({ name: a.name, kind: "market", score: a.score })),
  ];
  return rows
    .map((r) => ({ ...r, card: cards[r.name], market: snap.markets[r.name] || {},
                   cone: snap.forecasts[r.name]?.["1m"] }))
    .filter((r) => r.card?.bias)
    .sort((a, b) => Math.abs(b.score) - Math.abs(a.score));
}

function MainSignals({ snap }) {
  const rows = leans(snap).slice(0, 14);
  const record = snap.track_record?.horizons?.["1m"]?.pair_score;
  return (
    <Panel num={1} title="Macro leans" className="span-2"
           aside={`${rows.length} shown · none has a proven edge yet`} bodyClass="scroll">
      <table className="t">
        <thead><tr>
          <th className="l">Market</th><th className="l">Lean</th><th>Score</th><th>For / against</th>
          <th className="l">3M</th><th>Last</th><th>1M likely range (68%)</th><th className="l">Next catalyst</th>
        </tr></thead>
        <tbody>
          {rows.map((r) => {
            const next = r.card.catalysts.find((e) => e.impact === "High") || r.card.catalysts[0];
            return (
              <tr key={r.name} className="click" onClick={() => go(`${r.kind}/${r.name}`)}>
                <td className="l name">{r.name}</td>
                <td className="l"><Lean lean={r.card.lean} bias={r.card.bias} /></td>
                <td><Signed v={r.score} d={0} /></td>
                <td><span className="pos">{r.card.for.length}</span> / <span className="neg">{r.card.against.length}</span></td>
                <td className="l"><Spark values={r.market.spark} /></td>
                <td className="white">{r.market.last ?? "-"}</td>
                <td className="cyan">{r.cone ? `${r.cone.lo68} – ${r.cone.hi68}` : "-"}</td>
                <td className="l dim">{next ? `${next.currency} ${next.title.slice(0, 26)}` : "-"}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <div className="note">
        Leans are what the macro read points to, not forecasts. Pair leans were right{" "}
        {isNum(record?.hit) ? `${(record.hit * 100).toFixed(0)}%` : "-"} of the time over 1 month in the
        history test (t = {fmt(record?.t)}): no better than a coin so far. See <a className="amber" href={href("track")}>7) Track record</a>.
      </div>
    </Panel>
  );
}

function Regime({ r }) {
  const tone = { stressed: "neg", "stress rising": "warn", calm: "pos" }[r.state] || "white";
  return (
    <Panel num={2} title="Risk regime">
      <div className={`big ${tone}`}>{r.state?.toUpperCase()}</div>
      <div className="kv" style={{ marginTop: 6 }}>
        <span className="k">VIX</span><span className="v">{fmt(r.vix)}</span>
        <span className="k">VIX 1y percentile</span><span className="v">{fmt(r.vix_pct_1y, 0)}</span>
        <span className="k">VIX 1m change</span><span className="v"><Signed v={r.vix_1m_move} /></span>
        <span className="k">US 2s10s curve</span><span className="v">{fmt(r.us_2s10s_bp, 0)} bp</span>
      </div>
    </Panel>
  );
}

function CurrencyBoard({ snap }) {
  const rows = [...snap.currencies].sort((a, b) => (b.score ?? -999) - (a.score ?? -999));
  return (
    <Panel num={3} title="Currency board" aside="ranked by macro score" bodyClass="scroll">
      <table className="t">
        <thead><tr>
          <th className="l">Ccy</th><th className="l">Score</th><th>Policy</th><th>Mkt path</th>
          <th>3M move</th><th>CPI</th><th className="l">Positioning</th>
        </tr></thead>
        <tbody>
          {rows.map((c) => (
            <tr key={c.ccy} className="click" onClick={() => go(`currency/${c.ccy}`)}>
              <td className="l name">{c.ccy}</td>
              <td className="l"><ScoreBar v={c.score} /> <Signed v={c.score} d={0} /></td>
              <td>{fmt(c.policy)}</td>
              <td><Signed v={c.path_bp} d={0} unit="bp" /></td>
              <td><Signed v={c.momentum_3m_bp} d={0} unit="bp" /></td>
              <td title={`target ${c.cpi_gap != null ? fmt(c.cpi - c.cpi_gap) : "-"}`}>{fmt(c.cpi, 1)}</td>
              <td className="l">{c.cot_flag ? <span className="tag hot">{c.cot_flag}</span> : <span className="dim">-</span>}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="note">Mkt path: front-end rate minus policy rate (+ = market prices hikes).</div>
    </Panel>
  );
}

function MarketsPanel({ snap }) {
  return (
    <Panel num={4} title="Markets" bodyClass="scroll">
      <table className="t">
        <thead><tr><th className="l">Market</th><th>Last</th><th>1D</th><th>1M</th><th>Score</th><th className="l">3M</th></tr></thead>
        <tbody>
          {snap.assets.map((a) => {
            const m = snap.markets[a.name] || {};
            return (
              <tr key={a.name} className="click" onClick={() => go(`market/${a.name}`)}>
                <td className="l name" title={ASSET_LABEL[a.name]}>{a.name}</td>
                <td className="white">{m.last ?? "-"}</td>
                <td><Signed v={m.chg_1d_pct} unit="%" /></td>
                <td><Signed v={a.return_1m_pct} unit="%" /></td>
                <td><Signed v={a.score} d={0} /></td>
                <td className="l"><Spark values={m.spark} width={70} /></td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </Panel>
  );
}

function WeekAhead({ snap }) {
  const rows = snap.calendar.filter((e) => !e.past && e.impact === "High").slice(0, 12);
  return (
    <Panel num={5} title="Week ahead" aside="high impact" bodyClass="scroll">
      {rows.length ? (
        <table className="t"><tbody>
          {rows.map((e, i) => (
            <tr key={i}>
              <td className="l dim">{fmtTime(e.time)}</td><td className="l amber">{e.currency}</td>
              <td className="l">{e.title}</td><td className="dim">{e.forecast ?? ""}</td>
            </tr>
          ))}
        </tbody></table>
      ) : <div className="dim">No high-impact events left this week.</div>}
      <div className="note"><a className="amber" href={href("calendar")}>6) Calendar</a> for everything.</div>
    </Panel>
  );
}

function DataPanel({ snap }) {
  const w = snap.data_warnings || [];
  return (
    <Panel num={6} title="Data">
      {w.length ? <ul className="reasons notes">{w.map((x) => <li key={x}>{x}</li>)}</ul>
                : <div className="pos">Every series is current.</div>}
      <div className="note" style={{ padding: "4px 0 0" }}>
        <a className="amber" href={href("health")}>8) Data health</a> · prices are daily closes, not live.
      </div>
    </Panel>
  );
}

export default function Home({ snap }) {
  return (
    <div className="grid cols-3">
      <MainSignals snap={snap} />
      <div className="grid">
        <Regime r={snap.regime} />
        <DataPanel snap={snap} />
      </div>
      <CurrencyBoard snap={snap} />
      <MarketsPanel snap={snap} />
      <WeekAhead snap={snap} />
    </div>
  );
}
