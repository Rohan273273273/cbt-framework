// Unique constraints
CREATE CONSTRAINT strategy_name IF NOT EXISTS FOR (s:Strategy) REQUIRE s.name IS UNIQUE;
CREATE CONSTRAINT trade_id IF NOT EXISTS FOR (t:Trade) REQUIRE t.id IS UNIQUE;
CREATE CONSTRAINT news_url IF NOT EXISTS FOR (n:NewsEvent) REQUIRE n.url IS UNIQUE;
CREATE CONSTRAINT concept_name IF NOT EXISTS FOR (c:Concept) REQUIRE c.name IS UNIQUE;
CREATE CONSTRAINT regime_label IF NOT EXISTS FOR (r:MacroRegime) REQUIRE r.label IS UNIQUE;
CREATE CONSTRAINT condition_key IF NOT EXISTS FOR (m:MarketCondition) REQUIRE m.key IS UNIQUE;

// Indexes for fast lookup
CREATE INDEX trade_ts IF NOT EXISTS FOR (t:Trade) ON (t.entry_time);
CREATE INDEX trade_symbol IF NOT EXISTS FOR (t:Trade) ON (t.symbol);
CREATE INDEX trade_outcome IF NOT EXISTS FOR (t:Trade) ON (t.outcome);
CREATE INDEX news_ts IF NOT EXISTS FOR (n:NewsEvent) ON (n.ts);
CREATE INDEX condition_session IF NOT EXISTS FOR (m:MarketCondition) ON (m.session);
