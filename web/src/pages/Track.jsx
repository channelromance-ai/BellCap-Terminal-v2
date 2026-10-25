import { fmt, isNum } from "../data.js";
import { Panel } from "../components/ui.jsx";

const SIGNALS = {
  pair_score: "Pair macro score",
  pair_fair_value: "Pair rates fair value",
  asset_score: "Market driver score",
};

function verdict(s, req, half) {
  if (!isNum(s?.t)) return ["not enough data", "dim"];
  const halves = s.t_halves || [];
  const consistent = halves.every((h) => isNum(h) && Math.sign(h) === Math.sign(s.t) && Math.abs(h) >= half);
  if (Math.abs(s.t) >= req && consistent) return ["PROVEN: tilts forecasts", "pos"];
  if (Math.abs(s.t) >= req) return ["only in one stretch of history", "warn"];
  return ["no edge", "neg"];
}

// Reads the site actually published, graded once a week or month has passed.
function Live({ live }) {
  const rows = live ? Object.entries(live.horizons || {}).flatMap(([h, sigs]) =>
    ["pair_score", "asset_score"].map((k) => [h, k, sigs[k] || {}])) : [];
  const graded = rows.some(([, , s]) => s.signals);
  return (
    <Panel num={10} title="Live record" aside={live ? `${live.reads} published weeks since ${live.from}` : "nothing graded yet"}
           bodyClass="scroll">
      {graded ? (
        <table className="t">
          <thead><tr><th className="l">Signal</th><th className="l">Horizon</th><th>Right</th><th>Leans graded</th>
            <th>Inside 68% range</th></tr></thead>
          <tbody>
            {rows.map(([h, k, s]) => (
              <tr key={h + k}>
                <td className="l amber">{SIGNALS[k]}</td>
                <td className="l">{h === "1m" ? "1 month" : "1 week"}</td>
                <td className="white">{isNum(s.hit) ? `${(s.hit * 100).toFixed(1)}%` : "-"}</td>
                <td>{s.signals ?? 0}</td>
                <td>{isNum(live.cone?.[h]?.inside68) ? `${(live.cone[h].inside68 * 100).toFixed(1)}%` : "-"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : <div className="dim">Every run is logged. A lean can only be graded once its week or month has passed, so this fills in over time.</div>}
      <div className="note">These are the leans the site actually showed, never refit, so this is the record to trust most once it grows.</div>
    </Panel>
  );
}

// The swing template tickets the cards showed, graded like real orders.
function Tickets({ s }) {
  const r = s?.record;
  return (
    <Panel num={11} title="Swing template record"
           aside={r ? `${r.tickets} tickets · ${r.filled} filled · ${r.pending} waiting · ${r.expired} expired` : "none yet"}
           bodyClass="scroll">
      {r?.targets?.some((x) => x.resolved) ? (
        <table className="t">
          <thead><tr><th className="l">Target</th><th>Resolved</th><th>Reached before stop</th><th>Average R</th></tr></thead>
          <tbody>{r.targets.map((x) => (
            <tr key={x.r}><td className="l amber">{x.r}R</td><td>{x.resolved}</td>
              <td className="white">{isNum(x.hit) ? `${(x.hit * 100).toFixed(1)}%` : "-"}</td>
              <td className={x.avg_r > 0 ? "pos" : "neg"}>{fmt(x.avg_r)}</td></tr>))}
          </tbody>
        </table>
      ) : <div className="dim">Every ticket shown on a thesis card is logged. Results appear once tickets fill and hit a stop or target.</div>}
      {s?.live?.length > 0 && (
        <table className="t" style={{ marginTop: 6 }}>
          <thead><tr><th className="l">Live ticket</th><th className="l">Side</th><th className="l">Issued</th>
            <th>Entry</th><th>Stop</th><th className="l">Status</th></tr></thead>
          <tbody>{s.live.map((t) => (
            <tr key={t.name + t.issued}><td className="l name">{t.name}</td><td className="l">{t.side}</td>
              <td className="l dim">{t.issued}</td><td>{t.entry}</td><td className="neg">{t.stop}</td>
              <td className="l">{t.status}{t.basis === "close" ? " (close basis)" : ""}</td></tr>))}
          </tbody>
        </table>
      )}
      <div className="note">Entry is a limit at the pullback level (expires after 5 sessions). Each target is graded
        on its own against the stop; a bar touching both counts as the stop; anything open 20 sessions after
        filling closes at that day's price. Crosses are graded on closing prices only.</div>
    </Panel>
  );
}

export default function Track({ snap }) {
  const tr = snap.track_record || {};
  const req = tr.t_required ?? 2;
  return (
    <div className="grid">
      <Panel num={7} title="Track record" aside={`${tr.reads ?? 0} weekly reads, ${tr.from ?? "-"} to ${tr.to ?? "-"}`} bodyClass="scroll">
        <table className="t">
          <thead><tr>
            <th className="l">Signal</th><th className="l">Horizon</th><th>Slope</th><th>t</th>
            <th>t 1st half</th><th>t 2nd half</th><th>Right</th><th>Leans</th><th>Avg (SD)</th><th className="l">Verdict</th>
          </tr></thead>
          <tbody>
            {Object.entries(tr.horizons || {}).flatMap(([h, sigs]) =>
              Object.entries(sigs).map(([k, s]) => {
                const [text, cls] = verdict(s, req, 1.5);
                return (
                  <tr key={h + k}>
                    <td className="l amber">{SIGNALS[k] ?? k}</td>
                    <td className="l">{h === "1m" ? "1 month" : "1 week"}</td>
                    <td>{fmt(s.slope, 3)}</td>
                    <td className="white">{fmt(s.t)}</td>
                    <td>{fmt(s.t_halves?.[0])}</td><td>{fmt(s.t_halves?.[1])}</td>
                    <td>{isNum(s.hit) ? `${(s.hit * 100).toFixed(1)}%` : "-"}</td>
                    <td>{s.signals ?? "-"}</td>
                    <td>{fmt(s.avg_return_sd, 3)}</td>
                    <td className={`l ${cls}`}>{text}</td>
                  </tr>
                );
              }))}
          </tbody>
        </table>
      </Panel>
      <Live live={tr.live} />
      <Tickets s={snap.setups} />
      <Panel num={9} title="Forecast range check" aside="did price finish inside the cone?" bodyClass="scroll">
        <table className="t">
          <thead><tr><th className="l">Horizon</th><th>Inside 68% band</th><th>Inside 95% band</th><th>Outcomes</th></tr></thead>
          <tbody>
            {Object.entries(tr.cone || {}).map(([h, c]) => (
              <tr key={h}>
                <td className="l amber">{h === "1m" ? "1 month" : "1 week"}</td>
                <td className="white">{(c.inside68 * 100).toFixed(1)}%</td>
                <td className="white">{(c.inside95 * 100).toFixed(1)}%</td>
                <td>{c.n}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="note">Close to 68% and 95% means the ranges are honest. Measured over the same history as the table above.</div>
      </Panel>
      <Panel num={8} title="How to read this">
        <ul className="reasons notes">
          <li>Each week of history the model was re-run using only what was known then (macro data is held back
            until its real publication date), and each read was set next to what prices did over the next week
            and month.</li>
          <li>t measures whether the effect is distinguishable from luck. Below 2 it isn't. A signal must reach 2
            overall and at least 1.5 the same way in each half of the history before the forecast cone is
            allowed to lean on it, because a run of luck in one stretch isn't an edge.</li>
          <li>Right = how often price moved the way the lean pointed (50% is a coin). Avg (SD) = average move in
            the lean's direction, in units of that market's own volatility.</li>
          <li>Research ledger (rules fixed before each test; a signal needs t ≥ 2 before July 2024 and t ≥ 1.5
            the same way after it). Round 1, 13 signals: 3- and 12-month trend, rates-confirmed trend, weekly
            rate-gap change, fair value. Round 2, 9 signals: positioning extremes (pairs and markets),
            rates only when a pair is linked to them, and a 3-month horizon. Round 3 re-tested the core
            signals over 23 years (2003–2026, split mid-2015): all 7 failed; the asset score worked before
            2015 (t 2.7) and not after (t 0.0). Round 4 tested drift after 415 central bank rate moves (2002–2026): whether currencies keep moving the way they first reacted, the way 2-year yields reacted, or the way of the hike or cut. All 6 failed. In total 41 tests, none adopted.</li>
          <li>What did hold up: the forecast cone's ranges. Over those 23 years of weekly reads, price
            finished inside the 68% band 70% of the time and inside the 95% band 94% of the time.</li>
        </ul>
      </Panel>
    </div>
  );
}
