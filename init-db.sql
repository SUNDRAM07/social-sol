-- Database initialization script for Social Media Agent
-- This script will be run automatically when the database container starts

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create users table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    google_id VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    picture_url VARCHAR(500),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE
);

-- Create campaigns table with user_id
CREATE TABLE IF NOT EXISTS campaigns (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE
);

-- Create posts table with user_id
CREATE TABLE IF NOT EXISTS posts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    campaign_id UUID REFERENCES campaigns(id) ON DELETE SET NULL,
    campaign_name VARCHAR(255),
    original_description TEXT NOT NULL,
    caption TEXT,
    image_path VARCHAR(500),
    image_url VARCHAR(500),
    scheduled_at TIMESTAMP WITH TIME ZONE,
    posted_at TIMESTAMP WITH TIME ZONE,
    platforms TEXT[],
    subreddit VARCHAR(255),
    status VARCHAR(50) DEFAULT 'draft',
    batch_id UUID,
    engagement_metrics JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create batch_operations table with user_id
CREATE TABLE IF NOT EXISTS batch_operations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    description TEXT NOT NULL,
    num_posts INTEGER NOT NULL,
    days_duration INTEGER NOT NULL,
    posts_generated INTEGER DEFAULT 0,
    posts_failed INTEGER DEFAULT 0,
    status VARCHAR(50) DEFAULT 'pending',
    error_messages TEXT[],
    created_by VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create calendar_events table with user_id
CREATE TABLE IF NOT EXISTS calendar_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    start_time TIMESTAMP WITH TIME ZONE NOT NULL,
    end_time TIMESTAMP WITH TIME ZONE,
    all_day BOOLEAN DEFAULT FALSE,
    location VARCHAR(255),
    color VARCHAR(7) DEFAULT '#3174ad',
    reminder_minutes INTEGER DEFAULT 15,
    recurrence_rule VARCHAR(200),
    status VARCHAR(50) DEFAULT 'scheduled',
    google_event_id VARCHAR(200),
    google_event_link VARCHAR(500),
    drive_folder_id VARCHAR(200),
    drive_file_urls JSONB DEFAULT '{}'::jsonb,
    event_metadata JSONB DEFAULT '{}'::jsonb,
    post_id UUID REFERENCES posts(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create API usage tracking table
CREATE TABLE IF NOT EXISTS api_usage (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    service VARCHAR(50) NOT NULL, -- 'groq', 'chatgpt', 'stability', 'piapi'
    operation VARCHAR(50) NOT NULL, -- 'caption', 'image', 'batch_caption'
    tokens_used INTEGER DEFAULT 0,
    credits_used INTEGER DEFAULT 0,
    cost_usd DECIMAL(10, 6) DEFAULT 0.0,
    request_data JSONB,
    response_data JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_api_usage_user_id ON api_usage(user_id);
CREATE INDEX IF NOT EXISTS idx_api_usage_service ON api_usage(service);
CREATE INDEX IF NOT EXISTS idx_api_usage_created_at ON api_usage(created_at);
CREATE INDEX IF NOT EXISTS idx_api_usage_user_service ON api_usage(user_id, service);

-- Create other tables (existing schema)
CREATE TABLE IF NOT EXISTS images (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    post_id UUID REFERENCES posts(id) ON DELETE CASCADE,
    file_path VARCHAR(500) NOT NULL,
    generation_method VARCHAR(100),
    generation_prompt TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS captions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    post_id UUID REFERENCES posts(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    generation_method VARCHAR(100),
    generation_prompt TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS posting_schedules (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    post_id UUID REFERENCES posts(id) ON DELETE CASCADE,
    platform VARCHAR(50) NOT NULL,
    scheduled_at TIMESTAMP WITH TIME ZONE NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_users_google_id ON users(google_id);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_campaigns_user_id ON campaigns(user_id);
CREATE INDEX IF NOT EXISTS idx_posts_user_id ON posts(user_id);
CREATE INDEX IF NOT EXISTS idx_posts_campaign_id ON posts(campaign_id);
CREATE INDEX IF NOT EXISTS idx_posts_scheduled_at ON posts(scheduled_at);
CREATE INDEX IF NOT EXISTS idx_batch_operations_user_id ON batch_operations(user_id);
CREATE INDEX IF NOT EXISTS idx_calendar_events_user_id ON calendar_events(user_id);
CREATE INDEX IF NOT EXISTS idx_calendar_events_start_time ON calendar_events(start_time);

-- Create trigger for updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply triggers
DROP TRIGGER IF EXISTS update_users_updated_at ON users;
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_campaigns_updated_at ON campaigns;
CREATE TRIGGER update_campaigns_updated_at BEFORE UPDATE ON campaigns FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_posts_updated_at ON posts;
CREATE TRIGGER update_posts_updated_at BEFORE UPDATE ON posts FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_batch_operations_updated_at ON batch_operations;
CREATE TRIGGER update_batch_operations_updated_at BEFORE UPDATE ON batch_operations FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_calendar_events_updated_at ON calendar_events;
CREATE TRIGGER update_calendar_events_updated_at BEFORE UPDATE ON calendar_events FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Auto-create calendar events when posts are scheduled
CREATE OR REPLACE FUNCTION create_calendar_event_for_scheduled_post()
RETURNS TRIGGER AS $$
BEGIN
    -- Only create calendar event if post is being set to scheduled status
    -- and it has a scheduled_at time and user_id
    IF NEW.status = 'scheduled' 
       AND NEW.scheduled_at IS NOT NULL 
       AND NEW.user_id IS NOT NULL 
       AND (OLD.status IS NULL OR OLD.status != 'scheduled') THEN
        
        -- Check if calendar event already exists for this post
        IF NOT EXISTS (SELECT 1 FROM calendar_events WHERE post_id = NEW.id) THEN
            INSERT INTO calendar_events (
                id, 
                user_id, 
                post_id, 
                title, 
                description, 
                start_time, 
                end_time, 
                status
            )
            VALUES (
                uuid_generate_v4(),
                NEW.user_id,
                NEW.id,
                CASE 
                    WHEN NEW.campaign_name IS NOT NULL AND NEW.campaign_name != '' THEN NEW.campaign_name
                    WHEN length(NEW.original_description) > 10 THEN substring(NEW.original_description, 1, 50) || '...'
                    ELSE 'Social Media Post'
                END,
                COALESCE(NEW.caption, NEW.original_description, ''),
                NEW.scheduled_at,
                NEW.scheduled_at,
                'scheduled'
            );
        END IF;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create the triggers for auto calendar event creation
DROP TRIGGER IF EXISTS auto_create_calendar_event ON posts;
CREATE TRIGGER auto_create_calendar_event
    AFTER UPDATE ON posts
    FOR EACH ROW
    EXECUTE FUNCTION create_calendar_event_for_scheduled_post();

DROP TRIGGER IF EXISTS auto_create_calendar_event_insert ON posts;
CREATE TRIGGER auto_create_calendar_event_insert
    AFTER INSERT ON posts
    FOR EACH ROW
    EXECUTE FUNCTION create_calendar_event_for_scheduled_post();

-- Insert default campaign for existing posts (if any)
INSERT INTO campaigns (id, name, description, user_id)
SELECT 
    '00000000-0000-0000-0000-000000000000'::uuid,
    'Default Campaign',
    'Default campaign for posts without a specific campaign',
    NULL
WHERE NOT EXISTS (SELECT 1 FROM campaigns WHERE id = '00000000-0000-0000-0000-000000000000'::uuid);

-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO smedia_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO smedia_user;
GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO smedia_user;
