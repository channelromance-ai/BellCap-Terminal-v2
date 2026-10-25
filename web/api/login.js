import { cookieHeader, makeSession, passwordMatches, SESSION_SECONDS } from "./_auth.js";

export default async function handler(req, res) {
  if (req.method !== "POST") {
    res.setHeader("Allow", "POST");
    return res.status(405).json({ error: "POST only" });
  }
  const { BELLCAP_PASSWORD, SESSION_SECRET } = process.env;
  if (!BELLCAP_PASSWORD || !SESSION_SECRET) {
    return res.status(500).json({ error: "Site not configured: set BELLCAP_PASSWORD and SESSION_SECRET in Vercel" });
  }
  if (!passwordMatches(req.body?.password, BELLCAP_PASSWORD)) {
    await new Promise((r) => setTimeout(r, 800));   // slows guessing down
    return res.status(401).json({ error: "Wrong password" });
  }
  res.setHeader("Set-Cookie", cookieHeader(makeSession(SESSION_SECRET), SESSION_SECONDS));
  return res.status(200).json({ ok: true });
}
