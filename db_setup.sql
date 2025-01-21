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

-- Add indexes for common queries
CREATE INDEX IF NOT EXISTS idx_interactions_created_at ON interactions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_research_cache_topic ON research_cache(topic);
CREATE INDEX IF NOT EXISTS idx_article_queue_status ON article_queue(status);

-- Grant necessary permissions
DO $$ BEGIN
    IF EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'interactions') THEN
        ALTER TABLE interactions ENABLE ROW LEVEL SECURITY;
        DROP POLICY IF EXISTS "Enable all access for authenticated users" ON interactions;
        CREATE POLICY "Enable all access for authenticated users" ON interactions
            FOR ALL USING (auth.role() = 'authenticated');
    END IF;

    IF EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'research_cache') THEN
        ALTER TABLE research_cache ENABLE ROW LEVEL SECURITY;
        DROP POLICY IF EXISTS "Enable all access for authenticated users" ON research_cache;
        CREATE POLICY "Enable all access for authenticated users" ON research_cache
            FOR ALL USING (auth.role() = 'authenticated');
    END IF;

    IF EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'article_queue') THEN
        ALTER TABLE article_queue ENABLE ROW LEVEL SECURITY;
        DROP POLICY IF EXISTS "Enable all access for authenticated users" ON article_queue;
        CREATE POLICY "Enable all access for authenticated users" ON article_queue
            FOR ALL USING (auth.role() = 'authenticated');
    END IF;
END $$;