import { fmt } from "../data.js";
import { go } from "../router.js";
import { Panel, ScoreBar, Signed } from "../components/ui.jsx";

export const COMPONENT_LABEL = {
  rate_momentum: "Rate momentum", policy_path: "Market path", carry: "Carry", inflation: "Inflation",
};

export default function Currencies({ snap }) {
  const rows = [...snap.currencies].sort((a, b) => (b.score ?? -999) - (a.score ?? -999));
  return (
    <Panel num={3} title="Currency board" aside="click a row for the full read" bodyClass="scroll">
      <table className="t">
        <thead><tr>
          <th className="l">Ccy</th><th className="l">Score</th><th>Rates data</th><th>Policy</th>
          <th>Last move</th><th>12M chg</th><th>Front end</th><th>Mkt path</th><th>1M move</th><th>3M move</th>
          <th>CPI</th><th>vs target</th><th>Real rate</th><th>Strength 1M</th><th className="l">Positioning</th>
        </tr></thead>
        <tbody>
          {rows.map((c) => (
            <tr key={c.ccy} className="click" onClick={() => go(`currency/${c.ccy}`)}>
              <td className="l name">{c.ccy}</td>
              <td className="l"><ScoreBar v={c.score} /> <Signed v={c.score} d={0} /></td>
              <td className={c.quality === "daily" ? "dim" : "warn"}>{c.quality}</td>
              <td className="white">{fmt(c.policy, 2)}</td>
              <td>{c.last_move_date ? <><Signed v={c.last_move_bp} d={0} unit="bp" /> <span className="dim">{c.last_move_date}</span></> : "-"}</td>
              <td><Signed v={c.policy_change_12m_bp} d={0} unit="bp" /></td>
              <td>{fmt(c.front_end, 2)} <span className="dim">{c.front_end_id?.split(".")[1]?.replace("_M", " m") ?? ""}</span></td>
              <td><Signed v={c.path_bp} d={0} unit="bp" /></td>
              <td><Signed v={c.momentum_1m_bp} d={0} unit="bp" /></td>
              <td><Signed v={c.momentum_3m_bp} d={0} unit="bp" /></td>
              <td>{fmt(c.cpi, 1)}</td>
              <td><Signed v={c.cpi_gap} d={1} /></td>
              <td><Signed v={c.real_policy} d={1} /></td>
              <td><Signed v={c.strength_1m_pct} unit="%" /></td>
              <td className="l">{c.cot_flag ? <span className="tag hot">{c.cot_flag}</span> : <span className="dim">{c.cot_pct != null ? `${fmt(c.cot_pct, 0)}th pct` : "-"}</span>}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="note">
        Score: rate momentum 40%, market path 25%, carry 20%, inflation vs target 15%, each ranked against the
        other seven. Front end: 2y yield where it exists daily, otherwise the monthly 3-month rate ("m").
        Positioning: speculators' net position as a percentile of 3 years; only extremes are flagged.
      </div>
    </Panel>
  );
}
