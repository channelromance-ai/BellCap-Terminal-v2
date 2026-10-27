import { ASSET_LABEL, fmt, priceDigits, useJson } from "../data.js";
import { LineChart, PriceChart } from "../components/charts.jsx";
import Thesis from "../components/Thesis.jsx";
import GoldRvol from "../components/GoldRvol.jsx";
import Headlines, { newsTags } from "../components/Headlines.jsx";
import { MovesWith } from "./Correlations.jsx";
import { Failed, Loading, Panel, Signed } from "../components/ui.jsx";

function PushBar({ v }) {
  if (v == null) return <span className="dim">-</span>;
  const w = Math.min(Math.abs(v) / 2, 1) * 40;
  return (
    <span style={{ display: "inline-block", width: 80, height: 8, position: "relative", background: "#151515" }}>
      <span style={{ position: "absolute", left: "50%", top: 0, bottom: 0, width: 1, background: "#444" }} />
      <span style={{ position: "absolute", top: 1, bottom: 1, background: v >= 0 ? "var(--green)" : "var(--red)",
                     left: v >= 0 ? "50%" : `${50 - w}%`, width: `${w}%` }} />
    </span>
  );
}

export default function Market({ snap, id }) {
  const a = snap.assets.find((x) => x.name === id);
  const { data: chart, error } = useJson(a ? `charts/${id}.json` : null);
  if (!a) return <Failed error={`${id} is not one of the covered markets`} />;
  const m = snap.markets[id] || {};
  const card = snap.ideas.find((c) => c.name === id);
  return (
    <>
      <div className="headline">
        <span className="big name-amber">{id}</span>
        <span className="what">{ASSET_LABEL[id]}</span>
        <span className="big white">{m.last ?? "-"}</span>
        <Signed v={m.chg_1d_pct} unit="% 1D" />
        <Signed v={a.return_1m_pct} unit="% 1M" />
        <Signed v={a.return_3m_pct} unit="% 3M" />
        <span className={snap.price_sources[id]?.includes("ETF") ? "warn" : "what"}>
          {snap.price_sources[id]?.includes("ETF") ? "⚠ " : ""}source: {snap.price_sources[id] ?? "-"}</span>
      </div>
      <div className="grid cols-2">
        <div className="grid">
          <Panel num={1} title="Price and forecast range" bodyClass="">
            {error ? <Failed error={error} /> : chart ? <PriceChart chart={chart} digits={priceDigits(m.last)} /> : <Loading />}
          </Panel>
          <Panel num={3} title="Drivers" aside={`driver score ${fmt(a.score, 0)}`} bodyClass="scroll">
            <table className="t">
              <thead><tr>
                <th className="l">Driver</th><th>Should push</th><th>1M move</th><th>How unusual</th>
                <th className="l">Push now</th><th>Actual 60d corr</th>
              </tr></thead>
              <tbody>
                {a.drivers.map((d) => {
                  const working = d.corr == null ? null : d.direction * d.corr > -0.2;
                  return (
                    <tr key={d.key}>
                      <td className="l amber">{d.label}{d.monthly ? <span className="dim"> (monthly)</span> : ""}</td>
                      <td className="dim">{d.direction > 0 ? "same way" : "opposite"} · {Math.round(d.weight * 100)}%</td>
                      <td>{d.move != null ? <Signed v={d.move} d={{ "%": 2, pts: 1 }[d.move_unit] ?? 0} unit={d.move_unit} /> : "-"}</td>
                      <td><Signed v={d.z} unit=" SD" /></td>
                      <td className="l"><PushBar v={d.push} /> <Signed v={d.push} /></td>
                      <td className={working === false ? "warn" : ""}>{fmt(d.corr)}{working === false ? " ⚠" : ""}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
            <div className="note">
              Push = how unusual the driver's move is, times the direction it should push. ⚠ = the market has
              recently been moving against the textbook relationship, so trust that driver less.
              {a.link_check && ` Gold's real-yield link: ${a.link_check.state} (corr ${fmt(a.link_check.corr)}).`}
            </div>
          </Panel>
          <MovesWith snap={snap} id={id} num={7} />
          <Panel num={4} title="Driver score" aside="weekly history" bodyClass="">
            {chart && <LineChart height={160} digits={0}
              series={[{ key: "score", label: "driver score", colour: "#ffa028", data: chart.score }]}
              reference={{ y: 0, label: "" }} />}
          </Panel>
        </div>
        <div className="grid">
          <Thesis card={card} ticket={snap.setups?.live.find((x) => x.name === id)} />
          {id === "XAUUSD" && <GoldRvol num={5} />}
          <Headlines num={6} tags={newsTags("market", id)} limit={10} />
        </div>
      </div>
    </>
  );
}
