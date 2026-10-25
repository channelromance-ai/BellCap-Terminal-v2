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
          <li>Research ledger: on 2026-10-25, 13 further pre-registered signals (3- and 12-month trend,
            rates-confirmed trend, weekly rate-gap change, fair value) were tested with a held-back period and
            all failed. Next up: positioning extremes, rates only when a pair is linked, and a 3-month horizon.</li>
        </ul>
      </Panel>
    </div>
  );
}
