-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- ── OHLCV bars ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS ohlcv (
    ts          TIMESTAMPTZ     NOT NULL,
    symbol      TEXT            NOT NULL,
    timeframe   TEXT            NOT NULL,   -- 1m, 5m, 15m, 1h, 4h, 1d
    open        DOUBLE PRECISION NOT NULL,
    high        DOUBLE PRECISION NOT NULL,
    low         DOUBLE PRECISION NOT NULL,
    close       DOUBLE PRECISION NOT NULL,
    volume      DOUBLE PRECISION,           -- NULL marks a gap row
    PRIMARY KEY (ts, symbol, timeframe)
);
SELECT create_hypertable('ohlcv', 'ts', if_not_exists => TRUE);
CREATE INDEX IF NOT EXISTS idx_ohlcv_symbol_tf ON ohlcv (symbol, timeframe, ts DESC);

-- ── Trades (live + paper) ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS trades (
    id              TEXT            PRIMARY KEY,
    symbol          TEXT            NOT NULL,
    strategy        TEXT            NOT NULL,
    direction       SMALLINT        NOT NULL,   -- 1 long, -1 short
    entry_time      TIMESTAMPTZ     NOT NULL,
    exit_time       TIMESTAMPTZ,
    entry_price     DOUBLE PRECISION NOT NULL,
    exit_price      DOUBLE PRECISION,
    qty             DOUBLE PRECISION NOT NULL,
    pnl             DOUBLE PRECISION,
    pnl_pct         DOUBLE PRECISION,
    exit_reason     TEXT,                       -- tp | sl | watchdog | cro | manual
    confidence      DOUBLE PRECISION,
    lgbm_prob       DOUBLE PRECISION,
    river_prob      DOUBLE PRECISION,
    is_paper        BOOLEAN         NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);
SELECT create_hypertable('trades', 'entry_time', if_not_exists => TRUE);

-- ── News events ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS news_events (
    id              BIGSERIAL       PRIMARY KEY,
    ts              TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    source          TEXT            NOT NULL,
    url             TEXT            UNIQUE,
    headline        TEXT            NOT NULL,
    sentiment       TEXT            NOT NULL,   -- bullish | bearish | neutral
    confidence      DOUBLE PRECISION NOT NULL,
    impact_score    DOUBLE PRECISION NOT NULL,
    high_impact     BOOLEAN         NOT NULL DEFAULT FALSE,
    affected        TEXT[]                      -- array of symbols
);
SELECT create_hypertable('news_events', 'ts', if_not_exists => TRUE);

-- ── Macro data ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS macro_data (
    ts              TIMESTAMPTZ     NOT NULL,
    series_id       TEXT            NOT NULL,   -- FEDFUNDS, CPIAUCSL, M2SL, etc.
    value           DOUBLE PRECISION NOT NULL,
    PRIMARY KEY (ts, series_id)
);
SELECT create_hypertable('macro_data', 'ts', if_not_exists => TRUE);

-- ── COT positioning ───────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS cot_data (
    report_date     DATE            NOT NULL,
    market          TEXT            NOT NULL,
    commercial_long BIGINT,
    commercial_short BIGINT,
    commercial_net  BIGINT,
    large_spec_long BIGINT,
    large_spec_short BIGINT,
    large_spec_net  BIGINT,
    PRIMARY KEY (report_date, market)
);

-- ── Backtest runs ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS backtest_runs (
    id              BIGSERIAL       PRIMARY KEY,
    run_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    symbol          TEXT            NOT NULL,
    strategy        TEXT            NOT NULL,
    timeframe       TEXT            NOT NULL,
    date_from       DATE            NOT NULL,
    date_to         DATE            NOT NULL,
    total_trades    INTEGER,
    win_rate        DOUBLE PRECISION,
    profit_factor   DOUBLE PRECISION,
    net_pnl         DOUBLE PRECISION,
    net_pnl_pct     DOUBLE PRECISION,
    max_drawdown    DOUBLE PRECISION,
    sharpe          DOUBLE PRECISION,
    sortino         DOUBLE PRECISION,
    result_json     JSONB
);

-- ── Agent audit log ───────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS agent_audit (
    id              BIGSERIAL       PRIMARY KEY,
    ts              TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    cycle_id        TEXT            NOT NULL,
    agent           TEXT            NOT NULL,
    action          TEXT            NOT NULL,
    reasoning       TEXT,
    outcome         TEXT,
    metadata        JSONB
);
SELECT create_hypertable('agent_audit', 'ts', if_not_exists => TRUE);

-- ── ML model performance tracking ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS ml_predictions (
    id              BIGSERIAL       PRIMARY KEY,
    ts              TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    trade_id        TEXT,
    lgbm_pred       TEXT,
    river_pred      TEXT,
    actual_label    TEXT,
    lgbm_prob       JSONB,
    river_prob      JSONB,
    blend_weights   JSONB
);
SELECT create_hypertable('ml_predictions', 'ts', if_not_exists => TRUE);

-- ── Watchdog state history ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS watchdog_history (
    id              BIGSERIAL       PRIMARY KEY,
    ts              TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    strategy        TEXT            NOT NULL,
    from_state      TEXT            NOT NULL,
    to_state        TEXT            NOT NULL,
    reason          TEXT            NOT NULL,
    consecutive_count INTEGER
);
