import { fmt, isNum } from "../data.js";
import { Panel, Signed, Spark } from "../components/ui.jsx";

const TONE = { "very bullish": "good", bullish: "", normal: "", bearish: "", "very bearish": "bad" };

// Net position as a bar out from the middle: right = net long, left = net short.
function NetBar({ v, max = 50 }) {
  if (!isNum(v)) return <span className="dim">-</span>;
  const w = Math.min(Math.abs(v) / max, 1) * 50;
  return (
    <span className="scorebar" style={{ width: 140 }} title={`${fmt(v, 1)}% of open interest`}>
      <span className="mid" />
      <span className="fill" style={v >= 0 ? { left: "50%", width: `${w}%`, background: "var(--green)" }
                                           : { left: `${50 - w}%`, width: `${w}%`, background: "var(--red)" }} />
    </span>
  );
}

// Where today sits in its own 3-year range: shaded ends are the extremes.
function Gauge({ pct }) {
  if (!isNum(pct)) return <span className="dim">-</span>;
  return (
    <span style={{ position: "relative", display: "inline-block", width: 120, height: 10, verticalAlign: "middle",
                   background: "linear-gradient(90deg, #5a1010 0 10%, #1d1d1d 10% 90%, #104a1d 90% 100%)" }}
          title={`${fmt(pct, 0)} percentile of 3 years`}>
      <span style={{ position: "absolute", left: `calc(${Math.max(1, Math.min(99, pct))}% - 2px)`, top: -1,
                     width: 4, height: 12, background: "var(--cyan)" }} />
    </span>
  );
}

export default function Positioning({ snap }) {
  const rows = snap.positioning || [];
  if (!rows.length) return <div className="dim">No positioning data yet.</div>;
  const notable = rows.filter((r) => r.label.startsWith("very"));
  return (
    <div className="grid">
      <Panel num={11} title="Speculative positioning (CFTC)" bodyClass="scroll"
             aside={`positions as of ${rows[0].as_of}, published ${rows[0].released}`}>
        <table className="t">
          <thead><tr>
            <th className="l">Market</th><th className="l">Who</th><th className="l">Net short ◀ ▶ net long</th>
            <th>Net % of OI</th><th>This week</th><th>4 weeks</th><th className="l">vs last 3 years</th>
            <th className="l">Reading</th><th className="l">1 year</th>
          </tr></thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.series} title={r.text}>
                <td className="l name">{r.market}</td>
                <td className="l dim">{r.who}</td>
                <td className="l"><NetBar v={r.net_pct} /></td>
                <td className="white">{r.net_pct > 0 ? "+" : ""}{fmt(r.net_pct, 1)}%</td>
                <td><Signed v={r.chg_1w} d={1} /></td>
                <td><Signed v={r.chg_4w} d={1} /></td>
                <td className="l"><Gauge pct={r.pct_3y} /> <span className="dim">{fmt(r.pct_3y, 0)}</span></td>
                <td className="l"><span className={`tag ${TONE[r.label] ? TONE[r.label] : ""}`}>{r.label}</span></td>
                <td className="l"><Spark values={r.history} width={110} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </Panel>
      <Panel num={12} title="What it says">
        <ul className="reasons notes">
          {[...notable, ...rows.filter((r) => !r.label.startsWith("very"))].map((r) => (
            <li key={r.series}><span className="amber">{r.market}:</span> {r.text}</li>
          ))}
        </ul>
      </Panel>
      <Panel num={13} title="How to read this">
        <ul className="reasons notes">
          <li>Every Friday the CFTC publishes how the big speculators were positioned in futures as of that Tuesday:
            hedge funds in currencies and stock indices, fund managers in gold, silver and oil.</li>
          <li>Net % of OI: their longs minus shorts, as a share of all contracts open. The bar shows the direction:
            green to the right is net long, red to the left is net short.</li>
          <li>Currency futures are priced against the dollar: long EUR is a bet on EURUSD rising; long JPY, CHF or
            CAD is a bet on USDJPY, USDCHF or USDCAD falling.</li>
          <li>"vs last 3 years" compares today with their own history (red end = most bearish, green end = most
            bullish). Speculators can be net long and still at their most bearish in years, as silver shows.</li>
          <li>The extremes are what matter: very stretched positions can unwind fast when the news turns. In the
            middle of the range, positioning says little.</li>
        </ul>
      </Panel>
    </div>
  );
}
