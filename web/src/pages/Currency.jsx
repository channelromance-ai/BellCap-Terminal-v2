import { fmt, fmtTime, useJson } from "../data.js";
import { go } from "../router.js";
import { LineChart } from "../components/charts.jsx";
import { Failed, ImpactTag, Lean, Loading, Panel, Signed } from "../components/ui.jsx";
import { COMPONENT_LABEL } from "./Currencies.jsx";

export default function Currency({ snap, id }) {
  const c = snap.currencies.find((x) => x.ccy === id);
  const { data: ch, error } = useJson(c ? `charts/ccy/${id}.json` : null);
  if (!c) return <Failed error={`${id} is not one of the 8 currencies`} />;
  const cards = Object.fromEntries(snap.ideas.map((x) => [x.name, x]));
  const pairs = snap.pairs.filter((p) => p.base === id || p.quote === id)
    .map((p) => ({ ...p, mine: p.base === id ? p.macro_diff : -p.macro_diff }))
    .sort((a, b) => b.mine - a.mine);
  const events = snap.calendar.filter((e) => e.currency === id && !e.past);
  const frontLabel = c.front_end_id?.includes("2Y") ? "2y yield" : "3-month rate (monthly avg)";
  return (
    <>
      <div className="headline">
        <span className="big name-amber">{id}</span>
        <span className="big"><Signed v={c.score} d={0} /></span>
        <span className="what">macro score · rates data {c.quality} · policy {fmt(c.policy)}%</span>
      </div>
      <div className="grid cols-2">
        <div className="grid">
          <Panel num={1} title="Policy rate and market rates" bodyClass="">
            {error ? <Failed error={error} /> : !ch ? <Loading /> : (
              <LineChart height={230} unit="%" series={[
                { key: "policy", label: "policy rate", colour: "#ffa028", data: ch.policy, step: true },
                { key: "front", label: frontLabel, colour: "#4fd2ff", data: ch.front_end },
                { key: "long", label: "10y yield", colour: "#ffffff", data: ch.long_end, dash: "4 3" },
              ]} />
            )}
          </Panel>
          <div className="grid cols-2e">
            <Panel num={3} title="Inflation vs target" bodyClass="">
              {ch && (ch.cpi?.dates?.length
                ? <LineChart height={170} unit="%" digits={1}
                    series={[{ key: "cpi", label: "CPI y/y", colour: "#ff4545", data: ch.cpi }]}
                    reference={{ y: ch.cpi_target, label: `target ${ch.cpi_target}%` }} />
                : <div className="note">No current inflation source for {id} yet.</div>)}
            </Panel>
            <Panel num={4} title="Speculative positioning" aside="net % of open interest" bodyClass="">
              {ch && (ch.cot
                ? <LineChart height={170} unit="%" digits={0}
                    series={[{ key: "cot", label: "net long % OI", colour: "#31d158", data: ch.cot }]}
                    reference={{ y: 0, label: "" }} />
                : <div className="note">No futures positioning for USD (it is the other side of every contract).</div>)}
            </Panel>
            <Panel num={5} title="Price strength" aside="vs the other seven, %" bodyClass="">
              {ch && <LineChart height={170} unit="%" digits={1}
                series={[{ key: "s", label: "strength index", colour: "#ffffff", data: ch.strength }]} />}
            </Panel>
            <Panel num={6} title="Macro score" aside="weekly history" bodyClass="">
              {ch && <LineChart height={170} digits={0}
                series={[{ key: "score", label: "score", colour: "#ffa028", data: ch.score }]}
                reference={{ y: 0, label: "" }} />}
            </Panel>
          </div>
        </div>
        <div className="grid">
          <Panel num={2} title="Read">
            <div className="kv">
              <span className="k">Policy rate</span><span className="v white">{fmt(c.policy)}% <span className="dim">({c.policy_date})</span></span>
              <span className="k">Last move</span><span className="v"><Signed v={c.last_move_bp} d={0} unit="bp" /> {c.last_move_date}</span>
              <span className="k">Change over 12 months</span><span className="v"><Signed v={c.policy_change_12m_bp} d={0} unit="bp" /></span>
              <span className="k">{frontLabel}</span><span className="v">{fmt(c.front_end, 3)} <span className="dim">({c.front_end_date ?? "-"})</span></span>
              <span className="k">Market path</span><span className="v"><Signed v={c.path_bp} d={0} unit="bp" /> {c.path_bp > 0 ? "(hikes priced)" : c.path_bp < 0 ? "(cuts priced)" : ""}</span>
              <span className="k">Rate move 1M / 3M</span><span className="v"><Signed v={c.momentum_1m_bp} d={0} unit="bp" /> / <Signed v={c.momentum_3m_bp} d={0} unit="bp" /></span>
              <span className="k">How unusual (3M)</span><span className="v"><Signed v={c.momentum_z} unit=" SD" /></span>
              <span className="k">10y yield / curve</span><span className="v">{fmt(c.long_end, 2)} / {c.curve_bp != null ? `${fmt(c.curve_bp, 0)}bp` : "-"}</span>
              <span className="k">CPI y/y</span><span className="v">{fmt(c.cpi, 1)} <span className="dim">({c.cpi_period ?? "no source"})</span></span>
              <span className="k">CPI 3M change</span><span className="v"><Signed v={c.cpi_3m_change} d={1} /></span>
              <span className="k">Real policy rate</span><span className="v"><Signed v={c.real_policy} d={1} /></span>
              <span className="k">Positioning</span><span className="v">{c.cot_flag ?? (c.cot_pct != null ? `${fmt(c.cot_pct, 0)}th pct` : "-")}</span>
            </div>
            <div className="subhead">Score components (vs the other seven)</div>
            <table className="t"><tbody>
              {Object.entries(COMPONENT_LABEL).map(([k, label]) => (
                <tr key={k}><td className="l amber">{label}</td>
                  <td>{c.components[k] != null ? <Signed v={c.components[k]} /> : <span className="dim">no data</span>}</td></tr>
              ))}
            </tbody></table>
          </Panel>
          <Panel num={7} title={`${id} pairs`} aside={`ranked for ${id}`} bodyClass="scroll">
            <table className="t">
              <thead><tr><th className="l">Pair</th><th>Gap for {id}</th><th className="l">Lean</th><th>1M%</th></tr></thead>
              <tbody>
                {pairs.map((p) => (
                  <tr key={p.pair} className="click" onClick={() => go(`pair/${p.pair}`)}>
                    <td className="l name">{p.pair}</td><td><Signed v={p.mine} d={0} /></td>
                    <td className="l"><Lean lean={cards[p.pair]?.lean} bias={p.bias} /></td>
                    <td><Signed v={p.return_1m_pct} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Panel>
          <Panel num={8} title="Events this week">
            {events.length ? (
              <table className="t"><tbody>
                {events.map((e, i) => (
                  <tr key={i}><td className="l dim">{fmtTime(e.time)}</td><td className="l">{e.title}</td>
                    <td><ImpactTag impact={e.impact} /></td></tr>
                ))}
              </tbody></table>
            ) : <div className="dim">Nothing scheduled.</div>}
          </Panel>
        </div>
      </div>
    </>
  );
}
