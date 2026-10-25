import { cookieHeader } from "./_auth.js";

export default function handler(req, res) {
  res.setHeader("Set-Cookie", cookieHeader("", 0));
  return res.status(200).json({ ok: true });
}
