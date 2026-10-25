// Small building blocks used on every page.
import { fmt, isNum, signed, tone } from "../data.js";

export function Panel({ num, title, aside, children, className = "", bodyClass = "body" }) {
  return (
    <section className={`panel ${className}`}>
      <h2>
        {num != null && <span className="num">{num})</span>}
        {title}
        {aside && <span className="aside">{aside}</span>}
      </h2>
      <div className={bodyClass}>{children}</div>
    </section>
  );
}

export function Signed({ v, d = 2, unit = "" }) {
  return <span className={tone(v)}>{signed(v, d, unit)}</span>;
}

export function Lean({ lean, bias }) {
  if (!lean) return <span className="dim">none</span>;
  return (
    <span className={`lean ${lean}`} title={bias ? "clears the bias threshold" : "below the bias threshold"}>
      {lean === "long" ? "▲" : "▼"} {lean.toUpperCase()}{bias ? "" : "?"}
    </span>
  );
}

// Inline SVG line: cheap enough to draw dozens of them in one table.
export function Spark({ values, width = 90, height = 18 }) {
  const v = (values || []).filter(isNum);
  if (v.length < 2) return <span className="dim">-</span>;
  const lo = Math.min(...v), hi = Math.max(...v), span = hi - lo || 1;
  const pts = v.map((x, i) => `${(i / (v.length - 1)) * width},${height - 1 - ((x - lo) / span) * (height - 2)}`);
  const colour = v[v.length - 1] >= v[0] ? "var(--green)" : "var(--red)";
  return (
    <svg width={width} height={height} style={{ verticalAlign: "middle" }}>
      <polyline points={pts.join(" ")} fill="none" stroke={colour} strokeWidth="1.2" />
    </svg>
  );
}

// Centre-zero bar for scores that run -100..100.
export function ScoreBar({ v, max = 100 }) {
  if (!isNum(v)) return <span className="dim">-</span>;
  const w = Math.min(Math.abs(v) / max, 1) * 50;
  const style = v >= 0 ? { left: "50%", width: `${w}%`, background: "var(--green)" }
                       : { left: `${50 - w}%`, width: `${w}%`, background: "var(--red)" };
  return (
    <span className="scorebar" title={fmt(v, 0)}>
      <span className="mid" />
      <span className="fill" style={style} />
    </span>
  );
}

// 1-year range: line from low to high, orange diamond = average, cyan dot = now.
export function RangeBar({ lo, hi, avg, now }) {
  if (![lo, hi, now].every(isNum) || hi === lo) return <span className="dim">-</span>;
  const at = (x) => `${Math.max(0, Math.min(1, (x - lo) / (hi - lo))) * 100}%`;
  return (
    <span className="rangebar" title={`1y low ${lo} · avg ${avg} · high ${hi} · now ${now}`}>
      <span className="track" />
      {isNum(avg) && <span className="avg" style={{ left: at(avg) }} />}
      <span className="now" style={{ left: at(now) }} />
    </span>
  );
}

export function Toggle({ options, value, onChange }) {
  return (
    <span className="toggle">
      {options.map(([key, label]) => (
        <button key={key} className={key === value ? "on" : ""} onClick={() => onChange(key)}>{label}</button>
      ))}
    </span>
  );
}

export function Loading({ what = "Loading" }) {
  return <div className="loading">{what}…</div>;
}

export function Failed({ error }) {
  return <div className="error">Couldn't load: {String(error?.message || error)}</div>;
}

export function ImpactTag({ impact }) {
  return <span className={`tag ${impact === "High" ? "bad" : "hot"}`}>{impact}</span>;
}
