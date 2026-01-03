-- Database Migration Script
-- This script adds user_id columns to existing tables

-- Add user_id column to campaigns table if it doesn't exist
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'campaigns' AND column_name = 'user_id') THEN
        ALTER TABLE campaigns ADD COLUMN user_id VARCHAR(255);
    END IF;
END $$;

-- Add user_id column to posts table if it doesn't exist
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'posts' AND column_name = 'user_id') THEN
        ALTER TABLE posts ADD COLUMN user_id VARCHAR(255);
    END IF;
END $$;

-- Add user_id column to batch_operations table if it doesn't exist
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'batch_operations' AND column_name = 'user_id') THEN
        ALTER TABLE batch_operations ADD COLUMN user_id VARCHAR(255);
    END IF;
END $$;

-- Add user_id column to calendar_events table if it doesn't exist
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'calendar_events' AND column_name = 'user_id') THEN
        ALTER TABLE calendar_events ADD COLUMN user_id VARCHAR(255);
    END IF;
END $$;

-- Create indexes for user_id columns if they don't exist
CREATE INDEX IF NOT EXISTS idx_campaigns_user_id ON campaigns(user_id);
CREATE INDEX IF NOT EXISTS idx_posts_user_id ON posts(user_id);
CREATE INDEX IF NOT EXISTS idx_batch_operations_user_id ON batch_operations(user_id);
CREATE INDEX IF NOT EXISTS idx_calendar_events_user_id ON calendar_events(user_id);

-- Add missing columns to posts table
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'posts' AND column_name = 'image_url') THEN
        ALTER TABLE posts ADD COLUMN image_url VARCHAR(500);
    END IF;
END $$;

DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'posts' AND column_name = 'posted_at') THEN
        ALTER TABLE posts ADD COLUMN posted_at TIMESTAMP WITH TIME ZONE;
    END IF;
END $$;

DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'posts' AND column_name = 'engagement_metrics') THEN
        ALTER TABLE posts ADD COLUMN engagement_metrics JSONB;
    END IF;
END $$;

-- Add missing columns to calendar_events table
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'calendar_events' AND column_name = 'recurrence_rule') THEN
        ALTER TABLE calendar_events ADD COLUMN recurrence_rule VARCHAR(200);
    END IF;
END $$;

DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'calendar_events' AND column_name = 'google_event_id') THEN
        ALTER TABLE calendar_events ADD COLUMN google_event_id VARCHAR(200);
    END IF;
END $$;

DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'calendar_events' AND column_name = 'google_event_link') THEN
        ALTER TABLE calendar_events ADD COLUMN google_event_link VARCHAR(500);
    END IF;
END $$;

DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'calendar_events' AND column_name = 'drive_folder_id') THEN
        ALTER TABLE calendar_events ADD COLUMN drive_folder_id VARCHAR(200);
    END IF;
END $$;

DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'calendar_events' AND column_name = 'drive_file_urls') THEN
        ALTER TABLE calendar_events ADD COLUMN drive_file_urls JSONB DEFAULT '{}'::jsonb;
    END IF;
END $$;

DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'calendar_events' AND column_name = 'event_metadata') THEN
        ALTER TABLE calendar_events ADD COLUMN event_metadata JSONB DEFAULT '{}'::jsonb;
    END IF;
END $$;

-- Update existing records to have a default user_id (for existing data)
-- This ensures existing data doesn't break
UPDATE campaigns SET user_id = 'legacy-user' WHERE user_id IS NULL;
UPDATE posts SET user_id = 'legacy-user' WHERE user_id IS NULL;
UPDATE batch_operations SET user_id = 'legacy-user' WHERE user_id IS NULL;
UPDATE calendar_events SET user_id = 'legacy-user' WHERE user_id IS NULL;

-- Create calendar events for any existing scheduled posts that don't have them
INSERT INTO calendar_events (id, user_id, post_id, title, description, start_time, end_time, status)
SELECT 
    uuid_generate_v4(),
    user_id,
    id,
    CASE 
        WHEN campaign_name IS NOT NULL AND campaign_name != '' THEN campaign_name
        WHEN length(original_description) > 10 THEN substring(original_description, 1, 50) || '...'
        ELSE 'Social Media Post'
    END,
    COALESCE(caption, original_description, ''),
    scheduled_at,
    scheduled_at,
    'scheduled'
FROM posts 
WHERE status = 'scheduled' 
    AND user_id IS NOT NULL 
    AND scheduled_at IS NOT NULL
    AND NOT EXISTS (
        SELECT 1 FROM calendar_events ce WHERE ce.post_id = posts.id
    );

-- Auto-create calendar events when posts are scheduled (database triggers)
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
