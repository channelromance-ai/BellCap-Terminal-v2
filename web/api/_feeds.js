// Headlines from free RSS feeds, tagged with the markets they move.
//
// Fetched live by the site's server when a page asks (cached two minutes), so
// news is minutes old, not hours like the twice-daily data run. Every feed
// was checked on 2026-10-25 to answer a request that honestly says it's
// BellCap. Only these fixed URLs are ever fetched: nothing from the browser
// decides what the server requests.

export const FEEDS = [
  ["InvestingLive", "https://investinglive.com/feed/news"],
  ["FXStreet", "https://www.fxstreet.com/rss/news"],
  ["CNBC Markets", "https://www.cnbc.com/id/10000664/device/rss/rss.html"],
  ["CNBC Economy", "https://www.cnbc.com/id/20910258/device/rss/rss.html"],
  ["CNBC Energy", "https://www.cnbc.com/id/19836768/device/rss/rss.html"],
  ["Oilprice.com", "https://oilprice.com/rss/main"],
  ["Investing.com Commodities", "https://www.investing.com/rss/news_11.rss"],
  ["Google News: oil", "https://news.google.com/rss/search?q=oil+OR+OPEC+OR+crude+OR+Hormuz+when:2d&hl=en-US&gl=US&ceid=US:en"],
  ["EIA", "https://www.eia.gov/rss/todayinenergy.xml"],
  ["Federal Reserve", "https://www.federalreserve.gov/feeds/press_all.xml"],
  ["ECB", "https://www.ecb.europa.eu/rss/press.html"],
  ["Bank of England", "https://www.bankofengland.co.uk/rss/news"],
  ["Bank of Canada", "https://www.bankofcanada.ca/content_type/press-releases/feed/"],
  ["MarketWatch", "https://feeds.content.dowjones.io/public/rss/mw_topstories"],
  ["BBC Business", "https://feeds.bbci.co.uk/news/business/rss.xml"],
];

// Tag -> pattern. Lowercase words are matched case-insensitively; the
// all-caps acronyms (US, UK, CPI...) only in capitals, so "us" the word
// doesn't tag every headline USD.
const W = (words) => new RegExp(`\\b(${words})\\b`, "i");
const C = (words) => new RegExp(`\\b(${words})\\b`);
export const TAGS = {
  OIL: [W("oil|crude|brent|wti|opec\\+?|barrels?|refiner(y|ies)|gasoline|diesel|hormuz|tankers?|petroleum|natural gas|lng|shale"), C("EIA")],
  GOLD: [W("gold|bullion|silver|precious metals?")],
  RISK: [W("war|missiles?|drones?|attacks?|strikes?|sanctions?|iran|israel|russia|ukraine|houthis?|ceasefire|tariffs?|escalat\\w*|geopolitic\\w*")],
  USD: [W("fed|fomc|powell|federal reserve|dollar|greenback|treasur(y|ies)|payrolls|jobless claims|wall street"), C("US|U\\.S\\.|NFP|PCE|DXY")],
  EUR: [W("ecb|lagarde|euro|eurozone|euro area|bunds?|germany|german|france|french|italy|italian")],
  GBP: [W("bank of england|bailey|sterling|pound|gilts?|britain|british"), C("BoE|BOE|UK|U\\.K\\.")],
  JPY: [W("bank of japan|ueda|yen|japan|japanese|jgbs?"), C("BoJ|BOJ")],
  CHF: [W("swiss|franc|switzerland"), C("SNB")],
  CAD: [W("bank of canada|macklem|loonie|canada|canadian"), C("BoC|BOC")],
  AUD: [W("reserve bank of australia|aussie|australia|australian"), C("RBA")],
  NZD: [W("kiwi|new zealand"), C("RBNZ")],
  STOCKS: [W("stocks?|equit(y|ies)|nasdaq|s&p|dow|nikkei|dax|ftsr?e|stoxx|earnings|shares")],
};
const PAIR = /\b(EUR|USD|GBP|JPY|CHF|CAD|AUD|NZD)\/?(EUR|USD|GBP|JPY|CHF|CAD|AUD|NZD)\b/g;

export function tagsFor(title) {
  const tags = new Set(Object.entries(TAGS).filter(([, res]) => res.some((re) => re.test(title))).map(([t]) => t));
  for (const m of title.matchAll(PAIR)) { tags.add(m[1]); tags.add(m[2]); }
  return [...tags];
}

const ENTITIES = { amp: "&", lt: "<", gt: ">", quot: '"', apos: "'", nbsp: " " };
function clean(s) {
  return (s || "").replace(/<!\[CDATA\[([\s\S]*?)\]\]>/g, "$1").replace(/<[^>]+>/g, "")
    .replace(/&(#x[0-9a-f]+|#\d+|\w+);/gi, (m, e) => e[0] === "#"
      ? String.fromCodePoint(e[1] === "x" ? parseInt(e.slice(2), 16) : Number(e.slice(1)))
      : ENTITIES[e] ?? m)
    .replace(/\s+/g, " ").trim();
}
const field = (chunk, names) => {
  for (const n of names) {
    const m = chunk.match(new RegExp(`<${n}[^>]*>([\\s\\S]*?)</${n}>`, "i"));
    if (m) return clean(m[1]);
  }
  return "";
};

// RSS <item> and Atom <entry>, enough of each to read headlines.
export function parse(xml, source) {
  return xml.split(/<item[\s>]|<entry[\s>]/i).slice(1).map((chunk) => {
    let title = field(chunk, ["title"]);
    let src = source;
    if (source.startsWith("Google News")) {          // "Headline - Reuters"
      const cut = title.lastIndexOf(" - ");
      if (cut > 0) { src = title.slice(cut + 3); title = title.slice(0, cut); }
    }
    const link = field(chunk, ["link"]) || (chunk.match(/<link[^>]*href="([^"]+)"/i) || [])[1] || "";
    const time = new Date(field(chunk, ["pubDate", "updated", "published", "dc:date"]));
    return { title, link: /^https?:\/\//.test(link) ? link : null, source: src,
             time: Number.isNaN(time.getTime()) ? null : time.toISOString(), tags: tagsFor(title) };
  }).filter((x) => x.title && x.time);
}

const HEADERS = { "User-Agent": "BellCap-Terminal/2.0 (personal macro research; RSS reader)" };

export async function collect(now = Date.now()) {
  const results = await Promise.all(FEEDS.map(async ([name, url]) => {
    try {
      const res = await fetch(url, { headers: HEADERS, signal: AbortSignal.timeout(8000) });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const items = parse(await res.text(), name);
      return { name, ok: true, count: items.length, items };
    } catch (e) {
      return { name, ok: false, count: 0, error: String(e.message || e), items: [] };
    }
  }));
  const seen = new Set();
  const items = results.flatMap((r) => r.items)
    .filter((x) => now - Date.parse(x.time) < 3 * 86400e3)
    .sort((a, b) => (a.time < b.time ? 1 : -1))
    .filter((x) => {
      const key = x.title.toLowerCase().replace(/[^a-z0-9]/g, "").slice(0, 70);
      return !seen.has(key) && seen.add(key);
    })
    .slice(0, 250);
  return { fetched_at: new Date(now).toISOString(), items,
           feeds: results.map(({ items: _, ...r }) => r) };
}
