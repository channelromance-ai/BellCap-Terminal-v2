import { fmt, useJson } from "../data.js";
import { Failed, Loading, Panel } from "../components/ui.jsx";

const ICON = { ok: ["●", "pos"], stale: ["●", "warn"], missing: ["○", "dim"], fail: ["✕", "neg"] };

export default function Health() {
  const { data: h, error } = useJson("health.json");
  if (error) return <Failed error={error} />;
  if (!h) return <Loading />;
  const failed = h.sources.filter((s) => !s.ok);
  return (
    <div className="grid cols-2">
      <Panel num={8} title="Data health" aside={`checked ${h.checked_at.replace("T", " ").slice(0, 16)} UTC`} bodyClass="scroll">
        <table className="t">
          <thead><tr><th className="l"></th><th className="l">Series</th><th className="l">Source</th>
            <th>Last date</th><th>Age</th><th>Allowed</th><th>Points</th></tr></thead>
          <tbody>
            {h.series.map((r) => {
              const [icon, cls] = ICON[r.status];
              return (
                <tr key={r.id}>
                  <td className={`l ${cls}`}>{icon}</td>
                  <td className="l">{r.name}</td><td className="l dim">{r.source}</td>
                  <td>{r.last_date ?? "-"}</td><td className={cls}>{r.age_days ?? "-"}d</td>
                  <td className="dim">{r.max_age}d</td><td className="dim">{r.points}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </Panel>
      <div className="grid">
        <Panel num={9} title="Summary">
          <div className="kv">
            {Object.entries(h.summary).map(([k, v]) => (
              <span key={k} style={{ display: "contents" }}><span className="k">{k}</span><span className="v">{v}</span></span>
            ))}
            <span className="k">calendar</span>
            <span className="v">{h.calendar.ok ? `${h.calendar.events} events` : h.calendar.error}</span>
          </div>
          {failed.length > 0 && <><div className="subhead">Failed sources</div>
            <ul className="reasons against">{failed.map((s) => <li key={s.source}>{s.source}: {s.error}</li>)}</ul></>}
          <div className="subhead">Fetch times</div>
          <table className="t"><tbody>
            {h.sources.map((s) => <tr key={s.source}><td className="l amber">{s.source}</td><td>{fmt(s.seconds, 1)}s</td></tr>)}
          </tbody></table>
        </Panel>
        <Panel num={10} title="Known gaps">
          <ul className="reasons notes">
            {Object.entries(h.gaps).map(([k, v]) => <li key={k}><span className="amber">{k}:</span> {v}</li>)}
          </ul>
        </Panel>
      </div>
    </div>
  );
}
