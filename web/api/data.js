// Serves one file from the private data repo to a logged-in browser.
//
// The page code is public; the data is not. This route checks the session
// cookie, then reads the file from bellcap-v2-data through GitHub's API using
// a read-only token (GITHUB_DATA_TOKEN) that never leaves the server.
//
// Only the files the site draws are allowed. The score log and the history
// rebuild stay readable on GitHub only, and no path can climb out of the repo.

import { readCookie, sessionValid } from "./_auth.js";

export const ALLOWED = [
  /^latest\.json$/,
  /^edge\.json$/,
  /^health\.json$/,
  /^charts\/[A-Z0-9]{2,8}\.json$/,
  /^charts\/ccy\/[A-Z]{3}\.json$/,
  /^snapshots\/\d{4}-\d{2}-\d{2}\.json$/,
];

export function allowed(path) {
  return typeof path === "string" && ALLOWED.some((re) => re.test(path));
}

export default async function handler(req, res) {
  const { SESSION_SECRET, GITHUB_DATA_TOKEN, DATA_REPO } = process.env;
  if (!sessionValid(readCookie(req), SESSION_SECRET)) {
    return res.status(401).json({ error: "Not logged in" });
  }
  const path = req.query?.path;
  if (!allowed(path)) {
    return res.status(400).json({ error: "Unknown file" });
  }
  if (!GITHUB_DATA_TOKEN || !DATA_REPO) {
    return res.status(500).json({ error: "Site not configured: set GITHUB_DATA_TOKEN and DATA_REPO in Vercel" });
  }
  const upstream = await fetch(`https://api.github.com/repos/${DATA_REPO}/contents/${path}`, {
    headers: {
      Authorization: `Bearer ${GITHUB_DATA_TOKEN}`,
      Accept: "application/vnd.github.raw+json",
      "User-Agent": "bellcap-terminal-v2",
    },
  });
  if (upstream.status === 404) return res.status(404).json({ error: "Not found" });
  if (!upstream.ok) return res.status(502).json({ error: `GitHub answered ${upstream.status}` });
  res.setHeader("Content-Type", "application/json");
  res.setHeader("Cache-Control", "private, max-age=300");
  return res.status(200).send(await upstream.text());
}
