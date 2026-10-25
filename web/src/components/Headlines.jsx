// Live headlines, optionally only those tagged with given markets.
import { useEffect, useState } from "react";
import { href } from "../router.js";
import { Panel } from "./ui.jsx";

let shared = null;          // one fetch shared by every panel on the page
async function load(force = false) {
  if (!force && shared && Date.now() - shared.at < 120e3) return shared.body;
  const res = await fetch("/api/news", { credentials: "same-origin" });
  if (!res.ok) throw new Error(`news: HTTP ${res.status}`);
  shared = { at: Date.now(), body: await res.json() };
  return shared.body;
}

export function useNews() {
  const [state, setState] = useState({ news: shared?.body ?? null, error: null });
  useEffect(() => {
    let live = true;
    const get = (force) => load(force).then((news) => live && setState({ news, error: null }),
                                           (error) => live && setState((s) => ({ ...s, error })));
    get(false);
    const timer = setInterval(() => get(true), 120e3);      // keep refreshing while open
    return () => { live = false; clearInterval(timer); };
  }, []);
  return state;
}

// Which tags a page cares about. CAD moves with oil; JPY and CHF with risk.
export function newsTags(kind, id) {
  if (kind === "market") {
    return { XAUUSD: ["GOLD", "RISK"], XAGUSD: ["GOLD"], WTI: ["OIL", "RISK"], BRENT: ["OIL", "RISK"],
             NAS100: ["STOCKS"], US500: ["STOCKS"], US30: ["STOCKS"], GER40: ["STOCKS", "EUR"],
             UK100: ["STOCKS", "GBP"], JP225: ["STOCKS", "JPY"] }[id] || [];
  }
  const ccys = kind === "pair" ? [id.slice(0, 3), id.slice(3)] : [id];
  return [...ccys, ...(ccys.includes("CAD") ? ["OIL"] : []),
          ...(ccys.some((c) => c === "JPY" || c === "CHF") ? ["RISK"] : [])];
}

const ago = (iso) => {
  const m = Math.round((Date.now() - Date.parse(iso)) / 60000);
  return m < 60 ? `${m}m` : m < 1440 ? `${Math.round(m / 60)}h` : `${Math.round(m / 1440)}d`;
};

export function HeadlineRows({ items }) {
  return (
    <table className="t"><tbody>
      {items.map((x) => (
        <tr key={x.link || x.title}>
          <td className={`l ${Date.now() - Date.parse(x.time) < 3600e3 ? "warn" : "dim"}`}>{ago(x.time)}</td>
          <td className="l" style={{ whiteSpace: "normal" }}>
            {x.link ? <a href={x.link} target="_blank" rel="noopener noreferrer">{x.title}</a> : x.title}
          </td>
          <td className="l dim">{x.source.slice(0, 18)}</td>
          <td className="l">{x.tags.slice(0, 3).map((t) => <span key={t} className="tag" style={{ marginRight: 2 }}>{t}</span>)}</td>
        </tr>
      ))}
    </tbody></table>
  );
}

export default function Headlines({ num, tags, limit = 12, className = "", title = "Headlines" }) {
  const { news, error } = useNews();
  const items = (news?.items || []).filter((x) => !tags || x.tags.some((t) => tags.includes(t))).slice(0, limit);
  return (
    <Panel num={num} title={title} className={className} bodyClass="scroll"
           aside={tags ? tags.join(" · ") : <a className="amber" href={href("news")}>9) News for everything</a>}>
      {error && !news ? <div className="neg">Headlines unavailable: {error.message}</div>
        : !news ? <div className="dim">Loading headlines…</div>
        : items.length ? <HeadlineRows items={items} /> : <div className="dim">Nothing tagged {tags?.join("/")} in the last 3 days.</div>}
    </Panel>
  );
}
