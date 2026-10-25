// The two chart types: price with forecast cone, and plain line series.
import { useMemo, useState } from "react";
import {
  Area, CartesianGrid, ComposedChart, Line, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { isNum } from "../data.js";
import { Toggle } from "./ui.jsx";

const RANGES = [["3M", 92], ["6M", 183], ["1Y", 365], ["3Y", 1100]];
const AXIS = { stroke: "#555", tick: { fill: "#8a8a8a", fontSize: 11 }, tickLine: false };
const TIP = {
  contentStyle: { background: "#000", border: "1px solid #444", fontSize: 12 },
  labelStyle: { color: "#ffa028" },
};

function cutoff(dates, days) {
  if (!dates?.length) return "";
  const last = new Date(dates[dates.length - 1]);
  last.setDate(last.getDate() - days);
  return last.toISOString().slice(0, 10);
}

const shortDate = (d) => (typeof d === "string" ? d.slice(2) : d);

// Price line, the rates-implied level (dashed) and the 68%/95% cone.
export function PriceChart({ chart, digits = 5, height = 340 }) {
  const [range, setRange] = useState("1Y");
  const [horizon, setHorizon] = useState("1m");
  const rows = useMemo(() => {
    if (!chart?.close) return [];
    const from = cutoff(chart.close.dates, RANGES.find(([k]) => k === range)[1]);
    const byDate = new Map();
    chart.close.dates.forEach((d, i) => d >= from && byDate.set(d, { date: d, close: chart.close.values[i] }));
    chart.fair_value?.dates.forEach((d, i) => {
      if (byDate.has(d)) byDate.get(d).fair = chart.fair_value.values[i];
    });
    const out = [...byDate.values()];
    const cone = chart.forecast?.[horizon];
    if (cone && out.length) {
      const last = out[out.length - 1];
      Object.assign(last, { centre: last.close, band68: [last.close, last.close], band95: [last.close, last.close] });
      cone.dates.forEach((d, i) => out.push({
        date: d, centre: cone.centre[i],
        band68: [cone.lo68[i], cone.hi68[i]], band95: [cone.lo95[i], cone.hi95[i]],
      }));
    }
    return out;
  }, [chart, range, horizon]);

  const cone = chart?.forecast?.[horizon];
  return (
    <div>
      <div className="chart-tools">
        <Toggle options={RANGES.map(([k]) => [k, k])} value={range} onChange={setRange} />
        <span className="dim">forecast</span>
        <Toggle options={[["1w", "1W"], ["1m", "1M"]]} value={horizon} onChange={setHorizon} />
        <span className="legend">
          <span><span className="swatch" style={{ background: "#fff" }} />price</span>
          {chart?.fair_value && <span><span className="swatch" style={{ background: "#ff8c1a" }} />rates-implied</span>}
          <span><span className="swatch" style={{ background: "#4fd2ff" }} />68% / 95% range</span>
        </span>
      </div>
      <ResponsiveContainer width="100%" height={height}>
        <ComposedChart data={rows} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
          <CartesianGrid stroke="#161616" vertical={false} />
          <XAxis dataKey="date" {...AXIS} tickFormatter={shortDate} minTickGap={40} />
          <YAxis {...AXIS} domain={["auto", "auto"]} width={64} orientation="right"
                 tickFormatter={(v) => (isNum(v) ? v.toFixed(digits > 3 ? 4 : digits) : v)} />
          <Tooltip {...TIP} formatter={(v) => (Array.isArray(v) ? v.join(" – ") : v)} />
          <Area dataKey="band95" stroke="none" fill="#4fd2ff" fillOpacity={0.10} isAnimationActive={false} />
          <Area dataKey="band68" stroke="none" fill="#4fd2ff" fillOpacity={0.22} isAnimationActive={false} />
          <Line dataKey="fair" stroke="#ff8c1a" strokeDasharray="5 4" dot={false} strokeWidth={1.2}
                isAnimationActive={false} connectNulls />
          <Line dataKey="close" stroke="#ffffff" dot={false} strokeWidth={1.4} isAnimationActive={false} />
          <Line dataKey="centre" stroke="#4fd2ff" strokeDasharray="2 3" dot={false} strokeWidth={1}
                isAnimationActive={false} />
        </ComposedChart>
      </ResponsiveContainer>
      {cone && (
        <div className="note">
          {horizon === "1m" ? "One-month" : "One-week"} range from recent volatility
          ({cone.daily_vol_pct}% a day).{cone.coverage
            ? ` Past ranges like this held ${Math.round(cone.coverage.inside68 * 100)}% of the time (68% band) and ${Math.round(cone.coverage.inside95 * 100)}% (95% band).`
            : ""} {cone.lean
            ? `Centre tilted by: ${cone.lean.join("; ")}.`
            : "Centre is flat: no signal has passed testing yet (see 7) Track record)."}
        </div>
      )}
    </div>
  );
}

// Several series on one date axis. series: [{ key, label, colour, data: {dates, values}, step, dash }]
export function LineChart({ series, height = 200, unit = "", reference, digits = 2 }) {
  const rows = useMemo(() => {
    const byDate = new Map();
    for (const s of series) {
      if (!s.data?.dates) continue;
      s.data.dates.forEach((d, i) => {
        if (!byDate.has(d)) byDate.set(d, { date: d });
        byDate.get(d)[s.key] = s.data.values[i];
      });
    }
    return [...byDate.values()].sort((a, b) => (a.date < b.date ? -1 : 1));
  }, [series]);
  if (!rows.length) return <div className="note">No data.</div>;
  return (
    <div>
      <div className="chart-tools">
        <span className="legend" style={{ marginLeft: 0 }}>
          {series.filter((s) => s.data?.dates?.length).map((s) => (
            <span key={s.key}><span className="swatch" style={{ background: s.colour }} />{s.label}</span>
          ))}
        </span>
      </div>
      <ResponsiveContainer width="100%" height={height}>
        <ComposedChart data={rows} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
          <CartesianGrid stroke="#161616" vertical={false} />
          <XAxis dataKey="date" {...AXIS} tickFormatter={shortDate} minTickGap={40} />
          <YAxis {...AXIS} domain={["auto", "auto"]} width={52} orientation="right"
                 tickFormatter={(v) => (isNum(v) ? `${v.toFixed(digits)}${unit}` : v)} />
          <Tooltip {...TIP} />
          {reference != null && <ReferenceLine y={reference.y} stroke="#ff8c1a" strokeDasharray="4 4"
                                               label={{ value: reference.label, fill: "#ff8c1a", fontSize: 11, position: "insideTopLeft" }} />}
          {series.map((s) => (
            <Line key={s.key} dataKey={s.key} name={s.label} stroke={s.colour} dot={false}
                  strokeWidth={1.3} strokeDasharray={s.dash} type={s.step ? "stepAfter" : "linear"}
                  connectNulls isAnimationActive={false} />
          ))}
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
