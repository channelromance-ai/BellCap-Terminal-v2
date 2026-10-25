import { fmt, priceDigits, useJson } from "../data.js";
import { href } from "../router.js";
import { LineChart, PriceChart } from "../components/charts.jsx";
import Thesis from "../components/Thesis.jsx";
import { Failed, Loading, Panel, Signed } from "../components/ui.jsx";

export default function Pair({ snap, id }) {
  const p = snap.pairs.find((x) => x.pair === id);
  const { data: chart, error } = useJson(p ? `charts/${id}.json` : null);
  if (!p) return <Failed error={`${id} is not one of the 28 pairs`} />;
  const m = snap.markets[id] || {};
  const card = snap.ideas.find((c) => c.name === id);
  const ccy = Object.fromEntries(snap.currencies.map((c) => [c.ccy, c]));
  const digits = priceDigits(m.last);
  return (
    <>
      <div className="headline">
        <span className="big name-amber">{id}</span>
        <span className="big white">{m.last ?? "-"}</span>
        <Signed v={m.chg_1d_pct} unit="% 1D" />
        <Signed v={p.return_1m_pct} unit="% 1M" />
        <Signed v={p.return_3m_pct} unit="% 3M" />
        <span className="what">
          <a className="amber" href={href(`currency/${p.base}`)}>{p.base}</a> score {fmt(ccy[p.base]?.score, 0)} ·{" "}
          <a className="amber" href={href(`currency/${p.quote}`)}>{p.quote}</a> score {fmt(ccy[p.quote]?.score, 0)}
        </span>
      </div>
      <div className="grid cols-2">
        <div className="grid">
          <Panel num={1} title="Price, rates-implied level and forecast range" bodyClass="">
            {error ? <Failed error={error} /> : chart ? <PriceChart chart={chart} digits={digits} /> : <Loading />}
          </Panel>
          <div className="grid cols-2e">
            <Panel num={3} title="Rate gap" aside={p.spread_quality || "no rate data"} bodyClass="">
              {chart && <LineChart height={170} unit="bp" digits={0}
                series={[{ key: "gap", label: `${p.base} minus ${p.quote} front-end rate`, colour: "#4fd2ff",
                           data: chart.spread_bp }]} />}
            </Panel>
            <Panel num={4} title="Macro score gap" aside="weekly history" bodyClass="">
              {chart && <LineChart height={170} digits={0}
                series={[{ key: "score", label: "score gap", colour: "#ffa028", data: chart.score }]}
                reference={{ y: 0, label: "" }} />}
            </Panel>
          </div>
          <Panel num={5} title="Read">
            <div className="kv">
              <span className="k">Rate gap</span><span className="v">{p.spread_bp != null ? `${fmt(p.spread_bp, 0)} bp` : p.spread_quality === "mixed tenor" ? "mixed maturities" : "-"}</span>
              <span className="k">Rate gap 1M / 3M</span><span className="v"><Signed v={p.spread_1m_bp} d={0} unit="bp" /> / <Signed v={p.spread_3m_bp} d={0} unit="bp" /></span>
              <span className="k">Rates vs price (3M)</span><span className="v">{p.rates_vs_price ?? "-"}</span>
              <span className="k">Rates-implied level</span><span className="v">{p.fair_value ?? "-"}</span>
              <span className="k">Price vs that level</span><span className="v"><Signed v={p.residual_z} unit=" SD" /></span>
              <span className="k">Link to rates (60d corr)</span><span className="v">{fmt(p.link_corr)}</span>
              <span className="k">Distance from 50-day avg</span><span className="v"><Signed v={p.vs_ma_pct} unit="%" /></span>
              <span className="k">Efficiency (20d)</span><span className="v">{fmt(p.efficiency)}</span>
              <span className="k">Positioning</span><span className="v">{p.cot_note ?? "-"}</span>
            </div>
          </Panel>
        </div>
        <Thesis card={card} />
      </div>
    </>
  );
}
