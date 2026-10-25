import { useState } from "react";
import { ImpactTag, Panel, Toggle } from "../components/ui.jsx";

const day = (iso) => new Date(iso).toLocaleDateString(undefined, { weekday: "long", month: "short", day: "numeric" });
const time = (iso) => new Date(iso).toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });

export default function Calendar({ snap }) {
  const [which, setWhich] = useState("upcoming");
  const [impact, setImpact] = useState("all");
  const rows = snap.calendar.filter((e) => (which === "all" || !e.past) && (impact === "all" || e.impact === "High"));
  const days = [];
  for (const e of rows) {
    const d = day(e.time);
    if (!days.length || days[days.length - 1][0] !== d) days.push([d, []]);
    days[days.length - 1][1].push(e);
  }
  return (
    <Panel num={6} title="Economic calendar"
           aside={<span style={{ display: "inline-flex", gap: 10 }}>
             <Toggle options={[["upcoming", "Upcoming"], ["all", "Whole week"]]} value={which} onChange={setWhich} />
             <Toggle options={[["all", "High + medium"], ["high", "High only"]]} value={impact} onChange={setImpact} />
           </span>} bodyClass="scroll">
      <table className="t">
        <thead><tr><th className="l">Time (your clock)</th><th className="l">Ccy</th><th className="l">Event</th>
          <th className="l">Impact</th><th>Forecast</th><th>Previous</th></tr></thead>
        <tbody>
          {days.map(([d, events]) => [
            <tr key={d} className="group"><td className="l" colSpan={6}>{d}</td></tr>,
            ...events.map((e, i) => (
              <tr key={d + i} className={e.past ? "dim" : ""}>
                <td className="l">{time(e.time)}</td><td className="l amber">{e.currency}</td>
                <td className="l">{e.title}</td><td className="l"><ImpactTag impact={e.impact} /></td>
                <td>{e.forecast ?? ""}</td><td>{e.previous ?? ""}</td>
              </tr>
            )),
          ])}
        </tbody>
      </table>
      <div className="note">Source: Forex Factory's weekly export. It covers this week only and has no actual figures.</div>
    </Panel>
  );
}
