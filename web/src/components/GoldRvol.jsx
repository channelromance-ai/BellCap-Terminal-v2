// Hourly gold relative volume: is this hour busier than the same hour usually is?
import { fmtTime, useJson } from "../data.js";
import { Panel } from "./ui.jsx";

export default function GoldRvol({ num }) {
  const { data: r, error } = useJson("rvol.json");
  const title = "Gold volume (RVOL)";
  if (error || !r) {
    return <Panel num={num} title={title}><div className="dim">{error ? "No reading yet: the hourly job hasn't run." : "Loading…"}</div></Panel>;
  }
  if (r.status !== "ok") {
    return (
      <Panel num={num} title={title} aside={`as of ${fmtTime(r.generated_at)}`}>
        <div className="warn">{r.status === "closed" ? "Gold session closed." : "Unavailable: the volume source didn't answer."}</div>
        {r.detail && <div className="note" style={{ padding: "4px 0 0" }}>{r.detail}</div>}
      </Panel>
    );
  }
  const l = r.latest;
  return (
    <Panel num={num} title={title} aside={`flag at ${r.threshold}x`} bodyClass="scroll">
      <div className="headline" style={{ padding: "0 0 4px" }}>
        <span className={`big ${l.flag ? "warn" : "white"}`}>{l.rvol != null ? `${l.rvol}x` : l.status}</span>
        <span className="what">{l.hour} vs the same hour's 15-day average{l.flag ? " · BUSY" : ""}</span>
      </div>
      <table className="t"><tbody>
        {r.hours.slice(-8).reverse().map((h) => (
          <tr key={h.hour_start}>
            <td className="l dim">{h.hour}</td>
            <td className={h.flag ? "warn" : ""}>{h.rvol != null ? `${h.rvol}x` : h.status}</td>
            <td className="dim">{h.volume?.toLocaleString() ?? "-"}</td>
          </tr>
        ))}
      </tbody></table>
      <div className="note">COMEX gold, front two contracts summed ({r.contracts.join(" + ")}). Observation only, not part of any score.</div>
    </Panel>
  );
}
