# BellCap Terminal v2

A macro research terminal for swing trading FX, gold and silver, stock
indices and oil. It runs entirely in the cloud: GitHub's free scheduled
machines fetch and score the data, and Vercel serves the web app. Nothing
needs to run on your PC.

## Why v2

v1 could only fetch reliably from your own computer, because its price source
(Yahoo) blocks GitHub's cloud machines. v2 is built on official sources that
publish openly to anyone who identifies themselves honestly, so the whole
pipeline can live in the cloud.

## Where the data comes from

| What | Source | How often |
|---|---|---|
| US yields, real yields, breakevens | US Treasury | daily |
| Fed funds (EFFR), SOFR | New York Fed | daily |
| German 2y and 10y | Bundesbank | daily |
| Euro short-term rate | ECB | daily |
| Japan 2y and 10y | Japan Ministry of Finance | daily |
| Canada 2y and 10y | Bank of Canada | daily |
| Policy rates, all 8 central banks | BIS | daily |
| Euro-area inflation (headline, core, services) | Eurostat | monthly |
| US, UK, Canada, Australia, NZ inflation | OECD | monthly / quarterly |
| UK, Swiss, Australian, NZ yields | OECD | monthly (see below) |
| Speculative positioning (COT) | CFTC | weekly |
| VIX | Cboe | daily |
| FX and gold prices | Twelve Data (free plan) | daily |
| Silver, oil, index prices | Twelve Data ETF stand-ins | daily |
| Backup for any price | Yahoo via yfinance | daily |
| Economic calendar | Forex Factory export | this week |

**Stand-ins.** The free Twelve Data plan has no silver, oil or index data, so
ETFs that track them stand in: SLV, USO, BNO, QQQ, SPY, DIA, and DAX / EWU /
EWJ converted back to euros, pounds and yen so dollar moves don't read as
index moves. EWJ tracks MSCI Japan, not the Nikkei. ETF bars close at the US
4pm close. If Twelve Data fails for an instrument, that instrument's whole
history comes from Yahoo instead, never stitched onto the ETF's, and the
health report says which source each one used.

**Monthly yields for GBP, AUD, NZD and CHF.** The Bank of England, RBA and
RBNZ refuse requests that don't come from a web browser, and the SNB stopped
publishing daily yields in 2025. Rather than disguise requests, these four
use monthly OECD yields alongside their daily policy rates.

**What stays private.** Twelve Data and Yahoo prices are personal-use data,
so they are never committed here, and health reports show their dates but not
their values. Trade ideas and the score log are kept out of this public repo
too.

Every series has a maximum age. `python run.py doctor` checks each one by
its latest date, not just whether the download worked, because two sources
during setup downloaded perfectly and had stopped updating months earlier.
The known gaps are listed in `engine/catalog.py` and printed in every health
report.

## The read

Every run builds one read, as of the latest closed session:

- **Currencies (8):** policy rate and last move; what the market prices next
  (front-end rate minus policy rate); how fast that's moving; inflation
  against the bank's own target; real policy rate; positioning extremes.
  Rate moves are judged against each rate's own normal moves, because a
  3-month rate and a 2-year yield move by very different amounts.
- **Pairs (28):** score gap, rate gap and its momentum, and whether price is
  following rates. Where both legs have daily yields: how tightly the pair
  is trading on rates, and where rates alone would put it (fair value).
- **Gold, silver, indices, oil:** each driver's push, plus its actual recent
  correlation, so a textbook driver that has stopped working is visible.
- **Risk regime** from VIX, and **this week's events**.

Every weight is in `engine/config.py`, and every one is a hypothesis.

## Track record and forecasts

Every run also re-runs the model on the last session of every past week
(about 4.5 years of history), using only what was public at the time: macro
figures are held back until their national release date. Each past read is
then set next to what prices did over the following week and month
(`engine/edge.py`).

A signal counts as proven only if t ≥ 2 overall and t ≥ 1.5, pointing the
same way, in each half of the history. As of 2026-10-25 nothing passes. The
forecast cone therefore shows the likely range (68% and 95%, from recent
volatility) with a flat centre. If a signal ever passes, the cone leans on it
automatically, shrunk according to how strong the evidence is.

## The website (`web/`)

A Bloomberg-style React app on Vercel with these pages: Overview, Pairs,
Currencies, Markets, Rates, Calendar, Track record and Data health. Each
pair, currency and market also has its own page. The page code is public;
the data isn't. The site asks for a password, and its server reads the
private data repo with a read-only token. Type a ticker into the yellow
command line (`EURUSD`, `GOLD`, `USD`), or press 1–8.

Vercel settings: Root Directory `web`, framework Vite. Environment
variables:

| Name | What |
|---|---|
| `BELLCAP_PASSWORD` | the password you type to log on |
| `SESSION_SECRET` | any long random text; changing it logs every device out |
| `GITHUB_DATA_TOKEN` | fine-grained token, **Contents: Read-only**, on `bellcap-v2-data` only |
| `DATA_REPO` | `channelromance-ai/bellcap-v2-data` |

To preview locally without a login (it reads `data/private`, which
`python run.py update` writes): `cd web && npm install && npm run dev`.

## Running it

In the cloud, **Update** runs on its own: weekdays at 06:00 Winnipeg time,
Saturdays for Friday's closes, and each weekday evening. Each read is saved
to the private repo `bellcap-v2-data`. You can also start it from
**Actions → Update → Run workflow**. **Data health** is a manual source check
that saves nothing.

On your PC (optional):

```
pip install -r requirements.txt
python run.py update      # fetch, score, save to data/private, print the read
python run.py show        # print the last saved read again
python run.py doctor      # source check only
python -m unittest discover tests
```

Keys go in `.env` locally (copy `.env.example`) and in **Settings → Secrets
and variables → Actions** on GitHub. `.env` is gitignored and must stay so.
