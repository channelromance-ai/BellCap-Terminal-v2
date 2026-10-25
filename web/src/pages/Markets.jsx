import { ASSET_LABEL, fmt } from "../data.js";
import { go } from "../router.js";
import { Lean, Panel, RangeBar, Signed, Spark } from "../components/ui.jsx";

const GROUPS = [["metals", "Metals"], ["indices", "Stock indices"], ["energy", "Energy"]];

export default function Markets({ snap }) {
  const cards = Object.fromEntries(snap.ideas.map((c) => [c.name, c]));
  return (
    <Panel num={4} title="Markets" aside="click a row for drivers and the thesis" bodyClass="scroll">
      <table className="t">
        <thead><tr>
          <th className="l">Market</th><th className="l">Source</th><th>Last</th><th>1D%</th><th>1M%</th><th>3M%</th>
          <th>Score</th><th className="l">Lean</th><th>Eff</th><th className="l">Positioning</th>
          <th>1Y range</th><th className="l">3M</th>
        </tr></thead>
        <tbody>
          {GROUPS.map(([g, label]) => [
            <tr key={g} className="group"><td className="l" colSpan={12}>{label}</td></tr>,
            ...snap.assets.filter((a) => a.group === g).map((a) => {
              const m = snap.markets[a.name] || {};
              return (
                <tr key={a.name} className="click" onClick={() => go(`market/${a.name}`)}>
                  <td className="l name">{a.name} <span className="dim">{ASSET_LABEL[a.name]}</span></td>
                  <td className="l dim">{snap.price_sources[a.name]?.replace("twelvedata", "TD") ?? "-"}</td>
                  <td className="white">{m.last ?? "-"}</td>
                  <td><Signed v={m.chg_1d_pct} /></td>
                  <td><Signed v={a.return_1m_pct} /></td>
                  <td><Signed v={a.return_3m_pct} /></td>
                  <td><Signed v={a.score} d={0} /></td>
                  <td className="l"><Lean lean={cards[a.name]?.lean} bias={cards[a.name]?.bias} /></td>
                  <td>{fmt(a.efficiency)}</td>
                  <td className="l">{a.cot_flag ? <span className="tag hot">{a.cot_flag}</span> : <span className="dim">{a.cot_pct != null ? `${fmt(a.cot_pct, 0)}th pct` : "-"}</span>}</td>
                  <td><RangeBar lo={m.lo_1y} hi={m.hi_1y} avg={m.avg_1y} now={m.last} /></td>
                  <td className="l"><Spark values={m.spark} /></td>
                </tr>
              );
            }),
          ])}
        </tbody>
      </table>
      <div className="note">
        Silver, oil and the indices are priced from US-listed ETFs (Twelve Data free plan); DAX, FTSE and Nikkei
        stand-ins are converted back to EUR, GBP and JPY. EWJ tracks MSCI Japan, not the Nikkei itself.
      </div>
    </Panel>
  );
}
