import { useEffect, useRef, useState } from "react";
import { ALIASES, ASSET_LABEL, clearCache, daysAgo, fmtTime, getJson, login, logout, NotLoggedIn } from "./data.js";
import { go, href, useRoute } from "./router.js";
import { Failed, Loading } from "./components/ui.jsx";
import Home from "./pages/Home.jsx";
import Pairs from "./pages/Pairs.jsx";
import Pair from "./pages/Pair.jsx";
import Currencies from "./pages/Currencies.jsx";
import Currency from "./pages/Currency.jsx";
import Markets from "./pages/Markets.jsx";
import Market from "./pages/Market.jsx";
import Rates from "./pages/Rates.jsx";
import Calendar from "./pages/Calendar.jsx";
import Track from "./pages/Track.jsx";
import Health from "./pages/Health.jsx";
import News from "./pages/News.jsx";
import Correlations from "./pages/Correlations.jsx";
import Positioning from "./pages/Positioning.jsx";

const MENU = [
  ["home", "Overview"], ["pairs", "Pairs"], ["currencies", "Currencies"], ["markets", "Markets"],
  ["rates", "Rates"], ["calendar", "Calendar"], ["track", "Track record"], ["health", "Data health"], ["news", "News"],
  ["corr", "Correlations"], ["cot", "Positioning"],
];
const TITLES = {
  home: "Macro Overview", pairs: "FX Pairs Monitor", pair: "Pair Analysis", currencies: "Currency Board",
  currency: "Currency Analysis", markets: "Markets Monitor", market: "Market Analysis",
  rates: "World Rates", calendar: "Economic Calendar", track: "Track Record", health: "Data Health",
  news: "News", corr: "Cross-Market Correlations", cot: "Speculative Positioning",
};
const PARENT = { pair: "pairs", currency: "currencies", market: "markets" };
const PAGES = { home: Home, pairs: Pairs, pair: Pair, currencies: Currencies, currency: Currency,
                markets: Markets, market: Market, rates: Rates, calendar: Calendar, track: Track,
                health: Health, news: News, corr: Correlations, cot: Positioning };

// Typed command -> route, Bloomberg style: "EURUSD <GO>".
function resolve(text, snap) {
  const t = text.trim().toUpperCase().replace(/[^A-Z0-9]/g, "");
  if (!t) return null;
  const pairs = new Set(snap.pairs.map((p) => p.pair));
  const ccys = new Set(snap.currencies.map((c) => c.ccy));
  const assets = new Set(snap.assets.map((a) => a.name));
  if (pairs.has(t)) return `pair/${t}`;
  if (t.length === 6 && pairs.has(t.slice(3) + t.slice(0, 3))) return `pair/${t.slice(3)}${t.slice(0, 3)}`;
  if (assets.has(t)) return `market/${t}`;
  if (ALIASES[t]) return `market/${ALIASES[t]}`;
  if (ccys.has(t)) return `currency/${t}`;
  const page = MENU.find(([k, label]) => k.toUpperCase() === t || label.toUpperCase().replace(/ /g, "") === t);
  if (page) return page[0];
  if (/^\d$/.test(t) && MENU[Number(t) - 1]) return MENU[Number(t) - 1][0];
  return null;
}

function CommandLine({ snap }) {
  const [text, setText] = useState("");
  const [err, setErr] = useState("");
  const ref = useRef(null);
  useEffect(() => {
    const onKey = (e) => {
      if (e.target.tagName === "INPUT") return;
      if (e.key === "/") { e.preventDefault(); ref.current?.focus(); }
      else if (/^[0-9]$/.test(e.key) && !e.ctrlKey && !e.metaKey && !e.altKey) go(MENU[(Number(e.key) || 10) - 1][0]);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);
  const submit = (e) => {
    e.preventDefault();
    const to = resolve(text, snap);
    if (to) { go(to); setText(""); setErr(""); ref.current?.blur(); }
    else setErr(`${text.toUpperCase()} not found`);
  };
  return (
    <form className="cmdline" onSubmit={submit}>
      <span className="help">&lt;HELP&gt;</span>
      <input ref={ref} value={text} onChange={(e) => setText(e.target.value)} placeholder="EURUSD, GOLD, USD…"
             aria-label="Go to a pair, currency, market or page" spellCheck={false} />
      <span className="go">&lt;GO&gt;</span>
      {err ? <span className="err">{err}</span> : <span className="dim hint">type a ticker, or press / then 0–9</span>}
      <span className="clock">READ AS OF {snap.asof} · {snap.regime?.state?.toUpperCase()}</span>
    </form>
  );
}

function TitleBar({ route, snap, onRefresh }) {
  const id = route.id;
  const name = id ? (ASSET_LABEL[id] ? `${id} ${ASSET_LABEL[id]}` : id) : "BELLCAP";
  return (
    <div className="titlebar">
      <div className="name">{name}</div>
      <div className="bar">
        <button onClick={onRefresh}>1) Refresh</button>
        <a className="btn blue" href={href("track")}>97) Track record</a>
        <span className="title">{TITLES[route.page] || "BellCap"}</span>
      </div>
    </div>
  );
}

function Band({ snap }) {
  const items = snap.calendar.filter((e) => !e.past && e.impact === "High").slice(0, 14);
  if (!items.length) return null;
  // Rendered twice and scrolled by half its width, so the loop has no gap.
  const row = items.map((e, i) => (
    <span className="item" key={i}><b>{fmtTime(e.time)}</b> {e.currency} {e.title}
      {e.forecast ? ` (f ${e.forecast}, p ${e.previous ?? "-"})` : ""}</span>
  ));
  return (
    <div className="band" aria-label="Upcoming high-impact events">
      <span className="inner">{row}<span aria-hidden="true">{row}</span></span>
    </div>
  );
}

function Login({ onDone }) {
  const [pw, setPw] = useState("");
  const [err, setErr] = useState("");
  const submit = async (e) => {
    e.preventDefault();
    try { await login(pw); onDone(); } catch (x) { setErr(x.message); }
  };
  return (
    <div className="login panel">
      <h2>BELLCAP TERMINAL <span className="aside">sign on</span></h2>
      <form onSubmit={submit}>
        <span className="amber">Password</span>
        <input type="password" value={pw} onChange={(e) => setPw(e.target.value)} autoFocus />
        <button type="submit">Log on &lt;GO&gt;</button>
        {err && <span className="neg">{err}</span>}
      </form>
    </div>
  );
}

export default function App() {
  const route = useRoute();
  const [state, setState] = useState({ snap: null, error: null, needLogin: false });
  const load = () => {
    clearCache();
    setState({ snap: null, error: null, needLogin: false });
    getJson("latest.json").then(
      (snap) => setState({ snap, error: null, needLogin: false }),
      (error) => setState({ snap: null, error, needLogin: error instanceof NotLoggedIn }),
    );
  };
  useEffect(load, []);

  if (state.needLogin) return <Login onDone={load} />;
  if (state.error) return <Failed error={state.error} />;
  if (!state.snap) return <Loading what="Loading the latest read" />;

  const snap = state.snap;
  const Page = PAGES[route.page] || Home;
  const health = snap.data_warnings?.length ? `${snap.data_warnings.length} data warnings` : "all data current";
  return (
    <div className="app">
      <CommandLine snap={snap} />
      <TitleBar route={route} snap={snap} onRefresh={load} />
      <nav className="menu">
        {MENU.map(([key, label], i) => (
          <a key={key} href={href(key)}
             className={route.page === key || PARENT[route.page] === key ? "on" : ""}>
            {i + 1}) {label}
          </a>
        ))}
      </nav>
      <main><Page snap={snap} id={route.id} /></main>
      <Band snap={snap} />
      <div className="status">
        <span>Model {snap.model_version}</span>
        <span>Read as of {snap.asof} ({daysAgo(snap.asof)}d ago)</span>
        <span>Built {snap.generated_at.slice(0, 16).replace("T", " ")} UTC</span>
        <span className={snap.data_warnings?.length ? "warn" : ""}>{health}</span>
        <span>Prices: Twelve Data, FRED, Yahoo · daily closes · not for redistribution</span>
        <a href="#" onClick={async (e) => { e.preventDefault(); await logout(); load(); }}>Log off</a>
      </div>
    </div>
  );
}
