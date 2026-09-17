CREATE TABLE IF NOT EXISTS mentions (
  id TEXT PRIMARY KEY,
  external_id TEXT,
  source TEXT NOT NULL,
  platform TEXT NOT NULL,
  source_type TEXT NOT NULL DEFAULT 'news',
  author TEXT,
  url TEXT,
  title TEXT,
  content TEXT,
  published_at TIMESTAMPTZ NOT NULL,
  collected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  engagement BIGINT NOT NULL DEFAULT 0,
  reach_estimate BIGINT NOT NULL DEFAULT 0,
  sentiment TEXT NOT NULL DEFAULT 'neutral',
  sentiment_score DOUBLE PRECISION NOT NULL DEFAULT 0,
  emotion TEXT,
  topic TEXT,
  narrative TEXT,
  keywords JSONB NOT NULL DEFAULT '[]'::jsonb,
  entities JSONB NOT NULL DEFAULT '[]'::jsonb,
  virality_score DOUBLE PRECISION NOT NULL DEFAULT 0,
  risk_score DOUBLE PRECISION NOT NULL DEFAULT 0,
  ai_enriched BOOLEAN NOT NULL DEFAULT FALSE,
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_mentions_published_at ON mentions (published_at DESC);
CREATE INDEX IF NOT EXISTS idx_mentions_platform ON mentions (platform);
CREATE INDEX IF NOT EXISTS idx_mentions_sentiment ON mentions (sentiment);
CREATE INDEX IF NOT EXISTS idx_mentions_topic ON mentions (topic);
CREATE INDEX IF NOT EXISTS idx_mentions_risk_score ON mentions (risk_score DESC);
