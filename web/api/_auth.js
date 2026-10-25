// Session handling shared by the API routes.
//
// One user, one password (BELLCAP_PASSWORD). A successful login sets an
// HttpOnly cookie holding an expiry time and an HMAC of it, signed with
// SESSION_SECRET. Nothing is stored server-side; changing SESSION_SECRET
// logs every device out.

import { createHash, createHmac, timingSafeEqual } from "node:crypto";

export const COOKIE = "bc_session";
const DAYS = 30;

function sign(value, secret) {
  return createHmac("sha256", secret).update(value).digest("hex");
}

// Hashing both sides first makes the comparison constant-time regardless of
// how long the guess is.
export function passwordMatches(given, expected) {
  if (typeof given !== "string" || !expected) return false;
  const a = createHash("sha256").update(given).digest();
  const b = createHash("sha256").update(expected).digest();
  return timingSafeEqual(a, b);
}

export function makeSession(secret, now = Date.now()) {
  const expires = String(now + DAYS * 86400 * 1000);
  return `${expires}.${sign(expires, secret)}`;
}

export function sessionValid(token, secret, now = Date.now()) {
  if (!token || !secret) return false;
  const [expires, mac] = token.split(".");
  if (!expires || !mac || Number(expires) < now) return false;
  const want = Buffer.from(sign(expires, secret));
  const got = Buffer.from(mac);
  return want.length === got.length && timingSafeEqual(want, got);
}

export function readCookie(req, name = COOKIE) {
  const header = req.headers?.cookie || "";
  for (const part of header.split(";")) {
    const [k, ...v] = part.trim().split("=");
    if (k === name) return decodeURIComponent(v.join("="));
  }
  return null;
}

export function cookieHeader(value, maxAgeSeconds) {
  return `${COOKIE}=${encodeURIComponent(value)}; Path=/; HttpOnly; Secure; ` +
         `SameSite=Strict; Max-Age=${maxAgeSeconds}`;
}

export const SESSION_SECONDS = DAYS * 86400;
