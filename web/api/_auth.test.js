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
  for (const ok of ["latest.json", "edge.json", "health.json", "charts/EURUSD.json",
                    "charts/XAUUSD.json", "charts/ccy/USD.json", "snapshots/2026-10-23.json"]) {
    assert.ok(allowed(ok), ok);
  }
  for (const bad of ["log/reads.jsonl", "history/2.0-macro.2.json", "../secrets",
                     "charts/../log/reads.jsonl", ".git/config", "README.md", undefined]) {
    assert.ok(!allowed(bad), String(bad));
  }
});
