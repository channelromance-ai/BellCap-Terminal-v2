import { useState } from "react";
import { HeadlineRows, useNews } from "../components/Headlines.jsx";
import { Panel } from "../components/ui.jsx";

const FILTERS = ["ALL", "OIL", "GOLD", "RISK", "STOCKS", "USD", "EUR", "GBP", "JPY", "CHF", "CAD", "AUD", "NZD"];

export default function News() {
  const { news, error } = useNews();
  const [tag, setTag] = useState("ALL");
  const items = (news?.items || []).filter((x) => tag === "ALL" || x.tags.includes(tag));
  return (
    <div className="grid">
      <Panel num={9} title="News" bodyClass="scroll"
             aside={news ? `${items.length} headlines · refreshed ${new Date(news.fetched_at).toLocaleTimeString()} · updates every 2 min` : ""}>
        <div className="toggle" style={{ marginBottom: 6, flexWrap: "wrap" }}>
          {FILTERS.map((t) => <button key={t} className={t === tag ? "on" : ""} onClick={() => setTag(t)}>{t}</button>)}
        </div>
        {error && !news ? <div className="neg">Headlines unavailable: {error.message}</div>
          : !news ? <div className="dim">Loading headlines…</div> : <HeadlineRows items={items.slice(0, 150)} />}
      </Panel>
      {news && (
        <Panel num={10} title="Feeds" bodyClass="scroll">
          <div className="dim">
            {news.feeds.map((f) => (
              <span key={f.name} style={{ marginRight: 14 }} className={f.ok ? "" : "neg"}>
                {f.name} {f.ok ? f.count : `(${f.error})`}
              </span>
            ))}
          </div>
          <div className="note">Headlines amber when under an hour old. Tags come from keywords in the headline, so
            treat them as a filter, not a judgement. Links open the publisher's site.</div>
        </Panel>
      )}
    </div>
  );
}
