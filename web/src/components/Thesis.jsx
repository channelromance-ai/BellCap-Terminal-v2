// The thesis card: lean, for / against / notes, catalysts, setup template, track record.
import { fmt, fmtTime, isNum } from "../data.js";
import { href } from "../router.js";
import { ImpactTag, Lean, Panel } from "./ui.jsx";

function TrackLine({ record }) {
  const rows = Object.entries(record || {});
  if (!rows.length) return <div className="dim">No track record yet.</div>;
  return (
    <div>
      {rows.map(([h, r]) => (
        <div key={h}>
          <span className="amber">{h === "1m" ? "1 month" : "1 week"}:</span>{" "}
          right {isNum(r.hit) ? `${(r.hit * 100).toFixed(0)}%` : "-"} of {r.signals ?? 0} past leans,
          t = {fmt(r.t)}{" "}
          {r.proven ? <span className="pos">(proven)</span>
            : Math.abs(r.t ?? 0) >= 2 ? <span className="warn">(only in one stretch of history)</span>
            : <span className="neg">(no proven edge)</span>}
        </div>
      ))}
    </div>
  );
}

function TicketLine({ t }) {
  if (!t) return null;
  const what = t.status === "pending"
    ? `waiting for entry at ${t.entry} (issued ${t.issued}, expires after 5 sessions)`
    : `filled at ${t.entry} on ${t.filled}; ` + t.results.map((r, i) =>
        `${t.targets_r[i]}R target ${r == null ? "open" : r > 0 ? `hit (+${r}R)` : `${r}R`}`).join(", ");
  return (
    <div className="note" style={{ padding: "4px 0 0" }}>
      <span className="amber">Logged ticket ({t.side}, {t.basis} basis):</span> {what}.
    </div>
  );
}

export default function Thesis({ card, ticket, num = 2 }) {
  if (!card) return <Panel num={num} title="Thesis"><div className="dim">No card for this market.</div></Panel>;
  const s = card.setup;
  return (
    <Panel num={num} title="Thesis" aside={<Lean lean={card.lean} bias={card.bias} />}>
      {!card.lean && <div className="dim">No macro lean today.</div>}
      {card.lean && !card.bias && (
        <div className="note" style={{ padding: 0 }}>Lean is below the bias threshold: weak, shown for context.</div>
      )}
      {card.for.length > 0 && <><div className="subhead">For</div>
        <ul className="reasons for">{card.for.map((x, i) => <li key={i}>{x}</li>)}</ul></>}
      {card.against.length > 0 && <><div className="subhead">Against</div>
        <ul className="reasons against">{card.against.map((x, i) => <li key={i}>{x}</li>)}</ul></>}
      {card.notes.length > 0 && <><div className="subhead">Watch</div>
        <ul className="reasons notes">{card.notes.map((x, i) => <li key={i}>{x}</li>)}</ul></>}

      <div className="subhead">Catalysts this week</div>
      {card.catalysts.length ? (
        <table className="t"><tbody>
          {card.catalysts.map((e, i) => (
            <tr key={i}>
              <td className="l dim">{fmtTime(e.time)}</td>
              <td className="l amber">{e.currency}</td>
              <td className="l">{e.title}</td>
              <td><ImpactTag impact={e.impact} /></td>
            </tr>
          ))}
        </tbody></table>
      ) : <div className="dim">Nothing scheduled.</div>}

      {s && (
        <>
          <div className="subhead">Swing template ({s.side})</div>
          <div className="kv">
            <span className="k">Entry (pullback)</span><span className="v">{s.entry}</span>
            <span className="k">Stop</span><span className="v neg">{s.stop}</span>
            {s.targets.map((t, i) => (
              <span key={i} style={{ display: "contents" }}>
                <span className="k">Target {s.targets_r[i]}R</span><span className="v pos">{t}</span>
              </span>
            ))}
            <span className="k">Avg daily move</span><span className="v">{s.daily_move}</span>
          </div>
          <div className="note" style={{ padding: "4px 0 0" }}>{s.label}. Sized from volatility, not from the model.</div>
          <TicketLine t={ticket} />
        </>
      )}

      <div className="subhead">Track record of this kind of lean</div>
      <TrackLine record={card.track_record} />
      <div className="note" style={{ padding: "4px 0 0" }}>
        Full details in <a className="amber" href={href("track")}>7) Track record</a>.
      </div>
    </Panel>
  );
}
