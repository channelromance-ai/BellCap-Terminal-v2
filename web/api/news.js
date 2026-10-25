// Live headlines for a logged-in browser. Cached two minutes per server
// instance so page refreshes don't hammer the feeds.
import { readCookie, sessionValid } from "./_auth.js";
import { collect } from "./_feeds.js";

let cached = null;

export default async function handler(req, res) {
  if (!sessionValid(readCookie(req), process.env.SESSION_SECRET)) {
    return res.status(401).json({ error: "Not logged in" });
  }
  if (!cached || Date.now() - cached.at > 120e3) {
    cached = { at: Date.now(), body: await collect() };
  }
  res.setHeader("Cache-Control", "private, max-age=120");
  return res.status(200).json(cached.body);
}
