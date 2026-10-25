import { fmt } from "../data.js";
import { go } from "../router.js";
import { Panel, Signed } from "../components/ui.jsx";

const REGIONS = [["Americas", ["USD", "CAD"]], ["Europe", ["EUR", "GBP", "CHF"]],
                 ["Asia / Pacific", ["JPY", "AUD", "NZD"]]];
const NAMES = { USD: "United States", CAD: "Canada", EUR: "Euro area (Germany)", GBP: "United Kingdom",
                CHF: "Switzerland", JPY: "Japan", AUD: "Australia", NZD: "New Zealand" };

export default function Rates({ snap }) {
  const by = Object.fromEntries(snap.currencies.map((c) => [c.ccy, c]));
  return (
    <Panel num={5} title="World rates" aside="policy, front end, 10y and what the market prices" bodyClass="scroll">
      <table className="t">
        <thead><tr>
          <th className="l">Country</th><th>Policy</th><th>Front end</th><th className="l">Tenor</th>
          <th>Mkt path</th><th>1M</th><th>3M</th><th>3M (SD)</th><th>10Y</th><th>2s10s</th>
          <th>CPI</th><th>Real</th><th className="l">Data</th>
        </tr></thead>
        <tbody>
          {REGIONS.map(([region, ccys]) => [
            <tr key={region} className="group"><td className="l" colSpan={13}>{region}</td></tr>,
            ...ccys.map((k) => {
              const c = by[k];
              return (
                <tr key={k} className="click" onClick={() => go(`currency/${k}`)}>
                  <td className="l name">{NAMES[k]} <span className="dim">{k}</span></td>
                  <td className="white">{fmt(c.policy)}</td>
                  <td>{fmt(c.front_end, 3)}</td>
                  <td className="l dim">{c.front_end_id ? (c.front_end_id.includes("2Y") ? "2y daily" : "3m monthly") : "none"}</td>
                  <td><Signed v={c.path_bp} d={0} unit="bp" /></td>
                  <td><Signed v={c.momentum_1m_bp} d={0} unit="bp" /></td>
                  <td><Signed v={c.momentum_3m_bp} d={0} unit="bp" /></td>
                  <td><Signed v={c.momentum_z} /></td>
                  <td>{fmt(c.long_end, 2)}</td>
                  <td>{c.curve_bp != null ? `${fmt(c.curve_bp, 0)}bp` : <span className="dim">-</span>}</td>
                  <td>{fmt(c.cpi, 1)}</td>
                  <td><Signed v={c.real_policy} d={1} /></td>
                  <td className={`l ${c.quality === "daily" ? "dim" : "warn"}`}>{c.quality}</td>
                </tr>
              );
            }),
          ])}
        </tbody>
      </table>
      <div className="note">
        Mkt path = front-end rate minus policy rate: positive means hikes are priced, negative means cuts.
        3M (SD) = the 3-month move measured against this rate's own usual 3-month moves. UK, Swiss, Australian
        and NZ yields are monthly OECD figures: their central banks don't serve data to scripts, and the SNB
        stopped publishing daily yields in 2025.
      </div>
    </Panel>
  );
}
