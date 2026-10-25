// Hash routes (#/pair/EURUSD). Works on any static host and with the back button.
import { useEffect, useState } from "react";

export function parse(hash) {
  const parts = hash.replace(/^#\/?/, "").split("/").filter(Boolean);
  return { page: parts[0] || "home", id: parts[1] ? decodeURIComponent(parts[1]).toUpperCase() : null };
}

export function useRoute() {
  const [route, setRoute] = useState(() => parse(window.location.hash));
  useEffect(() => {
    const on = () => {
      setRoute(parse(window.location.hash));
      window.scrollTo(0, 0);
    };
    window.addEventListener("hashchange", on);
    return () => window.removeEventListener("hashchange", on);
  }, []);
  return route;
}

export function go(path) {
  window.location.hash = `#/${path}`;
}

export const href = (path) => `#/${path}`;
