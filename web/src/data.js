// Fetching and formatting shared by every page.
import { useEffect, useState } from "react";

const cache = new Map();

export class NotLoggedIn extends Error {}

export async function getJson(path) {
  if (cache.has(path)) return cache.get(path);
  const res = await fetch(`/api/data?path=${encodeURIComponent(path)}`, { credentials: "same-origin" });
  if (res.status === 401) throw new NotLoggedIn();
  if (!res.ok) throw new Error((await res.json().catch(() => ({}))).error || `HTTP ${res.status}`);
  const body = await res.json();
  cache.set(path, body);
  return body;
}

export function clearCache() {
  cache.clear();
}

// { data, error } for one file; re-fetches when the path changes.
export function useJson(path) {
  const [state, setState] = useState({ data: cache.get(path) ?? null, error: null });
  useEffect(() => {
    if (!path) return;
    let live = true;
    if (!cache.has(path)) setState({ data: null, error: null });
    getJson(path).then(
      (data) => live && setState({ data, error: null }),
      (error) => live && setState({ data: null, error }),
    );
    return () => { live = false; };
  }, [path]);
  return state;
}

export async function login(password) {
  const res = await fetch("/api/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ password }),
  });
  if (!res.ok) throw new Error((await res.json().catch(() => ({}))).error || "Login failed");
}

export async function logout() {
  await fetch("/api/logout", { method: "POST" });
  clearCache();
}

// ---- formatting -----------------------------------------------------------
export const isNum = (x) => typeof x === "number" && Number.isFinite(x);

export function fmt(x, digits = 2) {
  return isNum(x) ? x.toFixed(digits) : "-";
}

export function signed(x, digits = 2, unit = "") {
  if (!isNum(x)) return "-";
  return `${x > 0 ? "+" : ""}${x.toFixed(digits)}${unit}`;
}

export function ordinal(x) {
  const n = Math.max(1, Math.round(x));
  const s = n % 100 >= 11 && n % 100 <= 13 ? "th" : { 1: "st", 2: "nd", 3: "rd" }[n % 10] || "th";
  return `${n}${s}`;
}

export const tone = (x) => (!isNum(x) || x === 0 ? "" : x > 0 ? "pos" : "neg");

export function priceDigits(x) {
  return isNum(x) && Math.abs(x) < 20 ? (Math.abs(x) < 2 ? 5 : 3) : 2;
}

export function fmtTime(iso) {
  const d = new Date(iso);
  return d.toLocaleString(undefined, { weekday: "short", hour: "2-digit", minute: "2-digit" });
}

export function daysAgo(isoDate) {
  return Math.round((Date.now() - new Date(isoDate).getTime()) / 86400000);
}

// Instruments the command line understands besides the 28 pairs and 8 currencies.
export const ALIASES = {
  GOLD: "XAUUSD", XAU: "XAUUSD", SILVER: "XAGUSD", XAG: "XAGUSD", NAS: "NAS100", NDX: "NAS100",
  NASDAQ: "NAS100", SPX: "US500", SP500: "US500", DOW: "US30", DJI: "US30", DAX: "GER40",
  FTSE: "UK100", NIKKEI: "JP225", NKY: "JP225", OIL: "WTI", CL: "WTI", BRENT: "BRENT",
};

export const ASSET_LABEL = {
  XAUUSD: "Gold", XAGUSD: "Silver", NAS100: "Nasdaq 100", US500: "S&P 500", US30: "Dow 30",
  GER40: "DAX 40", UK100: "FTSE 100", JP225: "Nikkei 225", WTI: "WTI crude", BRENT: "Brent crude",
};
