-- Drop existing triggers first (if they exist)
DO $$ BEGIN
    IF EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_article_queue_updated_at') THEN
        DROP TRIGGER update_article_queue_updated_at ON article_queue;
    END IF;
END $$;

-- Drop existing functions (if they exist)
DO $$ BEGIN
    IF EXISTS (SELECT 1 FROM pg_proc WHERE proname = 'update_updated_at_column') THEN
        DROP FUNCTION update_updated_at_column();
    END IF;
END $$;

-- Drop existing tables (if they exist)
DO $$ BEGIN
    IF EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'article_queue') THEN
        DROP TABLE article_queue;
    END IF;
    IF EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'research_cache') THEN
        DROP TABLE research_cache;
    END IF;
    IF EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'interactions') THEN
        DROP TABLE interactions;
    END IF;
    IF EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'rate_limits') THEN
        DROP TABLE rate_limits;
    END IF;
END $$;

-- Create interactions table
CREATE TABLE IF NOT EXISTS interactions (
    id SERIAL PRIMARY KEY,
    tweet_id TEXT,
    query_text TEXT,
    query_type TEXT,
    response_text TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB
);

-- Create research_cache table with summary field
CREATE TABLE IF NOT EXISTS research_cache (
    id SERIAL PRIMARY KEY,
    topic TEXT NOT NULL,
    content TEXT NOT NULL,
    summary VARCHAR(255),
    expires_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create article_queue table
CREATE TABLE IF NOT EXISTS article_queue (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    url TEXT NOT NULL,
    tweet_content TEXT NOT NULL,
    source_feed TEXT NOT NULL,
    is_weekly BOOLEAN DEFAULT FALSE,
    queued_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    scheduled_for TIMESTAMP WITH TIME ZONE,
    posted_at TIMESTAMP WITH TIME ZONE,
    status TEXT CHECK (status IN ('queued', 'posted', 'failed')) DEFAULT 'queued',
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Add index for article queue scheduling
CREATE INDEX IF NOT EXISTS idx_article_queue_scheduling 
ON article_queue(status, scheduled_for) 
WHERE status = 'queued';

-- Add function to update timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Add trigger for updating timestamp
CREATE TRIGGER update_article_queue_updated_at
    BEFORE UPDATE ON article_queue
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Create rate_limits table
CREATE TABLE IF NOT EXISTS rate_limits (
    domain VARCHAR PRIMARY KEY,
    last_request TIMESTAMP WITH TIME ZONE,
    request_count INTEGER DEFAULT 0,
    reset_time TIMESTAMP WITH TIME ZONE,
    backoff_period INTEGER DEFAULT 0,
    CONSTRAINT rate_limits_request_count_check CHECK (request_count >= 0),
    CONSTRAINT rate_limits_backoff_period_check CHECK (backoff_period >= 0)
);

-- Add indexes for common queries
CREATE INDEX IF NOT EXISTS idx_interactions_created_at ON interactions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_research_cache_topic ON research_cache(topic);
CREATE INDEX IF NOT EXISTS idx_article_queue_status ON article_queue(status);
CREATE INDEX IF NOT EXISTS idx_rate_limits_last_request ON rate_limits(last_request);
CREATE INDEX IF NOT EXISTS idx_rate_limits_reset_time ON rate_limits(reset_time);

-- Enable RLS on tables
ALTER TABLE interactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE research_cache ENABLE ROW LEVEL SECURITY;
ALTER TABLE article_queue ENABLE ROW LEVEL SECURITY;
ALTER TABLE rate_limits ENABLE ROW LEVEL SECURITY;

-- Drop existing policies
DROP POLICY IF EXISTS "Enable all access for service role" ON interactions;
DROP POLICY IF EXISTS "Enable all access for service role" ON research_cache;
DROP POLICY IF EXISTS "Enable all access for service role" ON article_queue;
DROP POLICY IF EXISTS "Enable all access for service role" ON rate_limits;

-- Create policies for service role access
CREATE POLICY "Enable all access for service role" ON interactions
    FOR ALL
    TO authenticated, anon, service_role
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Enable all access for service role" ON research_cache
    FOR ALL
    TO authenticated, anon, service_role
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Enable all access for service role" ON article_queue
    FOR ALL
    TO authenticated, anon, service_role
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Enable all access for service role" ON rate_limits
    FOR ALL
    TO authenticated, anon, service_role
    USING (true)
    WITH CHECK (true);

-- Grant permissions to public schema
GRANT USAGE ON SCHEMA public TO anon, authenticated, service_role;

-- Grant table permissions
GRANT ALL ON ALL TABLES IN SCHEMA public TO anon, authenticated, service_role;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO anon, authenticated, service_role;