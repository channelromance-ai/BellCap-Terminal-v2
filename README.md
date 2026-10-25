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

## Running it

In the cloud: on GitHub, open **Actions → Data health → Run workflow**. The
run's Summary page shows the full health table.

On your PC (optional):

```
pip install -r requirements.txt
python run.py doctor
python -m unittest discover tests
```

Keys go in `.env` locally (copy `.env.example`) and in **Settings → Secrets
and variables → Actions** on GitHub. `.env` is gitignored and must stay so.
