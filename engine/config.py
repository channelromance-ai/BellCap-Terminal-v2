"""
Every model setting in one place.

Each weight and threshold here is a hypothesis, not a finding. The score log
(store.py) records every read with the version below, so the edge report can
eventually say which of them earned their place. Change a number, bump
MODEL_VERSION, and the log keeps the old and new reads apart.
"""

MODEL_VERSION = "2.0-macro.3"

CCYS = ["USD", "EUR", "GBP", "JPY", "CHF", "CAD", "AUD", "NZD"]

# Market convention for which currency is quoted first in a pair.
PAIR_PRIORITY = ["EUR", "GBP", "AUD", "NZD", "USD", "CAD", "CHF", "JPY"]

# Central bank inflation targets (midpoint where the target is a range).
INFLATION_TARGET = {"USD": 2.0, "EUR": 2.0, "GBP": 2.0, "JPY": 2.0,
                    "CHF": 1.0, "CAD": 2.0, "AUD": 2.5, "NZD": 2.0}

# The market rate that best shows where each central bank is expected to go,
# best first. 2y yields price the next two years of policy; the 3-month rate
# only the next few months, but it is what exists for AUD, NZD and CHF.
# GBP has no usable front-end series (the OECD's was LIBOR and stopped).
FRONT_END = {
    "USD": ["USD.2Y"], "EUR": ["EUR.2Y"], "JPY": ["JPY.2Y"], "CAD": ["CAD.2Y"],
    "AUD": ["AUD.3M_M"], "NZD": ["NZD.3M_M"], "CHF": ["CHF.3M_M"], "GBP": [],
}
LONG_END = {"USD": "USD.10Y", "EUR": "EUR.10Y", "JPY": "JPY.10Y",
            "CAD": "CAD.10Y", "GBP": "GBP.10Y_M", "AUD": "AUD.10Y_M",
            "NZD": "NZD.10Y_M", "CHF": "CHF.10Y_M"}
INFLATION = {c: f"{c}.CPI" for c in CCYS}
COT = {c: f"COT.{c}" for c in CCYS if c != "USD"}

# Currency score: each component is z-scored across the eight currencies,
# clipped at +/-2, and weighted. A missing component (no front-end rate for
# GBP, no CPI for JPY/CHF) drops out and the rest are reweighted rather than
# scoring it as zero.
CURRENCY_WEIGHTS = {
    "rate_momentum": 0.40,   # 3-month change in the front-end rate
    "policy_path": 0.25,     # front-end rate minus policy rate
    "carry": 0.20,           # policy rate level
    "inflation": 0.15,       # CPI minus target: pressure to stay hawkish
}
MIN_CURRENCIES_PER_COMPONENT = 4

SHORT_DAYS = 28              # "1 month" in calendar days
LONG_DAYS = 91               # "3 months"
TREND_MA = 50                # sessions
EFFICIENCY_SESSIONS = 20     # Kaufman efficiency ratio window

# Rates-vs-price link, only where both legs have daily yields.
LINK_SESSIONS = 60           # correlation of spread changes with pair returns
FAIR_VALUE_SESSIONS = 250    # regression of price on the yield spread
MIN_LINK_SESSIONS = 40

# Z-scores of driver moves are measured against this much of their own history.
Z_HISTORY_SESSIONS = 750
Z_CHANGE_SESSIONS = 20       # driver move = change over 20 sessions

COT_WINDOW_WEEKS = 156       # ~3 years of weekly reports
COT_EXTREME_LOW, COT_EXTREME_HIGH = 10, 90

# Gold's real-yield link: normally strongly negative. Near zero means
# something else (central bank buying, a geopolitical bid) is driving it.
GOLD_LINK_OK, GOLD_LINK_WEAK = -0.30, -0.10

# Risk regime from VIX.
VIX_STRESS_LEVEL = 25.0
VIX_STRESS_PCT, VIX_CALM_PCT = 85, 25
VIX_RISING_POINTS = 4.0

# A macro bias needs at least this much score (difference, for pairs).
# Scores run -100..100.
PAIR_BIAS_MIN = 30
ASSET_BIAS_MIN = 30

# Swing setup template on thesis cards, in multiples of the average daily
# move over 20 sessions. A template for planning, not a tested strategy.
SETUP_ENTRY_PULLBACK = 0.5     # enter on a pullback against the lean
SETUP_STOP_MOVES = 3.0
SETUP_TARGETS_R = (1.5, 3.0)

# Hourly gold RVOL (GLD, US session). Same rule as v1.
RVOL_THRESHOLD = 1.5        # flag an hour at >= 1.5x its usual volume
RVOL_BASELINE_DAYS = 15     # same hour, previous 15 trading days
