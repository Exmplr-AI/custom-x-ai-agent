-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Drop existing policies if they exist
DO $$ 
BEGIN
    -- Drop policies for interactions
    IF EXISTS (SELECT 1 FROM pg_policy WHERE polrelid = 'interactions'::regclass) THEN
        DROP POLICY IF EXISTS "Enable read access for all users" ON interactions;
        DROP POLICY IF EXISTS "Enable insert access for authenticated users" ON interactions;
    END IF;

    -- Drop policies for research_cache
    IF EXISTS (SELECT 1 FROM pg_policy WHERE polrelid = 'research_cache'::regclass) THEN
        DROP POLICY IF EXISTS "Enable read access for all users" ON research_cache;
        DROP POLICY IF EXISTS "Enable insert access for authenticated users" ON research_cache;
    END IF;

    -- Drop policies for rate_limits
    IF EXISTS (SELECT 1 FROM pg_policy WHERE polrelid = 'rate_limits'::regclass) THEN
        DROP POLICY IF EXISTS "Enable read access for all users" ON rate_limits;
        DROP POLICY IF EXISTS "Enable insert access for authenticated users" ON rate_limits;
        DROP POLICY IF EXISTS "Enable update access for authenticated users" ON rate_limits;
    END IF;
EXCEPTION
    WHEN undefined_table THEN NULL;
END $$;

-- Drop existing tables if they exist
DROP TABLE IF EXISTS interactions CASCADE;
DROP TABLE IF EXISTS research_cache CASCADE;
DROP TABLE IF EXISTS rate_limits CASCADE;

-- Create interactions table
CREATE TABLE interactions (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    tweet_id VARCHAR NOT NULL,
    query_text TEXT NOT NULL,
    query_type VARCHAR(50) NOT NULL,
    response_text TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb,
    UNIQUE(tweet_id)
);

-- Create research_cache table
CREATE TABLE research_cache (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    topic VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Create rate_limits table
CREATE TABLE rate_limits (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    domain VARCHAR(255) NOT NULL,
    last_attempt_at TIMESTAMPTZ DEFAULT NOW(),
    success BOOLEAN NOT NULL,
    consecutive_failures INTEGER DEFAULT 0,
    next_retry_at TIMESTAMPTZ DEFAULT NOW(),
    backoff_period INTEGER DEFAULT 0,  -- in minutes
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(domain)
);

-- Create indexes
CREATE INDEX idx_interactions_tweet_id ON interactions(tweet_id);
CREATE INDEX idx_interactions_created ON interactions(created_at DESC);
CREATE INDEX idx_research_topic ON research_cache(topic);
CREATE INDEX idx_research_expires ON research_cache(expires_at);
CREATE INDEX idx_interactions_metadata ON interactions USING gin (metadata);
CREATE INDEX idx_research_metadata ON research_cache USING gin (metadata);
CREATE INDEX idx_rate_limits_domain ON rate_limits(domain);
CREATE INDEX idx_rate_limits_next_retry ON rate_limits(next_retry_at);
CREATE INDEX idx_rate_limits_metadata ON rate_limits USING gin (metadata);

-- Add RLS (Row Level Security) policies
ALTER TABLE interactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE research_cache ENABLE ROW LEVEL SECURITY;
ALTER TABLE rate_limits ENABLE ROW LEVEL SECURITY;

-- Create policies for interactions
CREATE POLICY "Enable read access for all users" ON interactions FOR SELECT USING (true);
CREATE POLICY "Enable insert access for authenticated users" ON interactions FOR INSERT WITH CHECK (true);

-- Create policies for research_cache
CREATE POLICY "Enable read access for all users" ON research_cache FOR SELECT USING (true);
CREATE POLICY "Enable insert access for authenticated users" ON research_cache FOR INSERT WITH CHECK (true);

-- Create policies for rate_limits
CREATE POLICY "Enable read access for all users" ON rate_limits FOR SELECT USING (true);
CREATE POLICY "Enable insert access for authenticated users" ON rate_limits FOR INSERT WITH CHECK (true);
CREATE POLICY "Enable update access for authenticated users" ON rate_limits FOR UPDATE USING (true) WITH CHECK (true);