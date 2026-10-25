// node --test api/
import assert from "node:assert/strict";
import { test } from "node:test";
import { makeSession, passwordMatches, readCookie, sessionValid } from "./_auth.js";
import { allowed } from "./data.js";

test("sessions verify, expire and can't be forged", () => {
  const s = makeSession("secret", 1000);
  assert.ok(sessionValid(s, "secret", 2000));
  assert.ok(!sessionValid(s, "other-secret", 2000));
  assert.ok(!sessionValid(s, "secret", 1000 + 31 * 86400 * 1000));
  const [exp] = s.split(".");
  assert.ok(!sessionValid(`${Number(exp) + 1}.${s.split(".")[1]}`, "secret", 2000));
  assert.ok(!sessionValid("", "secret"));
  assert.ok(!sessionValid("garbage", "secret"));
});

test("password check", () => {
  assert.ok(passwordMatches("hunter2", "hunter2"));
  assert.ok(!passwordMatches("hunter", "hunter2"));
  assert.ok(!passwordMatches(undefined, "hunter2"));
  assert.ok(!passwordMatches("x", ""));
});

test("cookie parsing", () => {
  assert.equal(readCookie({ headers: { cookie: "a=1; bc_session=abc.def" } }), "abc.def");
  assert.equal(readCookie({ headers: {} }), null);
});

test("only the site's files can be read", () => {
  for (const ok of ["latest.json", "edge.json", "health.json", "rvol.json", "charts/EURUSD.json",
                    "charts/XAUUSD.json", "charts/ccy/USD.json", "snapshots/2026-10-23.json"]) {
    assert.ok(allowed(ok), ok);
  }
  for (const bad of ["log/reads.jsonl", "history/2.0-macro.2.json", "../secrets",
                     "charts/../log/reads.jsonl", ".git/config", "README.md", undefined]) {
    assert.ok(!allowed(bad), String(bad));
  }
});

import { parse, tagsFor } from "./_feeds.js";

test("headlines are tagged with the markets they move", () => {
  assert.deepEqual(tagsFor("Oil jumps as Iran missiles hit Saudi facility").sort(), ["OIL", "RISK"]);
  assert.ok(tagsFor("EUR/USD slips after ECB's Lagarde").includes("EUR"));
  assert.ok(tagsFor("EUR/USD slips after ECB's Lagarde").includes("USD"));
  assert.ok(tagsFor("BoJ holds, yen weakens").includes("JPY"));
  assert.deepEqual(tagsFor("Let us know what you think"), []);   // "us" isn't USD
});

test("RSS and Google News items parse, unsafe links dropped", () => {
  const xml = `<rss><item><title><![CDATA[Crude rises &amp; OPEC meets - Reuters]]></title>
    <link>https://example.com/a</link><pubDate>Sun, 25 Oct 2026 12:00:00 GMT</pubDate></item>
    <item><title>Bad link</title><link>javascript:alert(1)</link><pubDate>Sun, 25 Oct 2026 12:00:00 GMT</pubDate></item></rss>`;
  const [a, b] = parse(xml, "Google News: oil");
  assert.equal(a.title, "Crude rises & OPEC meets");
  assert.equal(a.source, "Reuters");
  assert.ok(a.tags.includes("OIL"));
  assert.equal(b.link, null);
});
