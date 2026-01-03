-- Migration: Add unified social_media_accounts table
-- This table stores all social media platform accounts (Facebook, Instagram, Twitter, Reddit, LinkedIn)
-- in a flexible, platform-agnostic way

CREATE TABLE IF NOT EXISTS social_media_accounts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    platform VARCHAR(50) NOT NULL, -- 'facebook', 'instagram', 'twitter', 'reddit', 'linkedin'
    
    -- Platform-specific identifiers
    account_id VARCHAR(255) NOT NULL, -- Platform account ID (e.g., Facebook Page ID, Instagram Business Account ID, Twitter User ID, Reddit Username)
    username VARCHAR(255), -- Platform username (for display)
    display_name VARCHAR(255), -- Display name (e.g., Page name, Twitter name)
    
    -- Authentication tokens
    access_token TEXT NOT NULL,
    refresh_token TEXT, -- For platforms that support token refresh
    token_type VARCHAR(50) DEFAULT 'Bearer',
    expires_at TIMESTAMP WITH TIME ZONE, -- Token expiration time
    
    -- Platform-specific metadata (stored as JSONB for flexibility)
    metadata JSONB DEFAULT '{}', -- Store platform-specific data like:
                                 -- Facebook: page_id, page_access_token, user_id
                                 -- Instagram: instagram_account_id, facebook_page_id
                                 -- Twitter: twitter_user_id, screen_name
                                 -- Reddit: reddit_user_id, subreddit preferences
                                 -- LinkedIn: person_id, organization_id
    
    -- Scopes and permissions
    scopes TEXT[], -- Array of granted permissions/scopes
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    is_primary BOOLEAN DEFAULT FALSE, -- Primary account for the platform (user can have multiple)
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Ensure one account per user per platform per account_id
    UNIQUE(user_id, platform, account_id)
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_social_media_accounts_user_id ON social_media_accounts(user_id);
CREATE INDEX IF NOT EXISTS idx_social_media_accounts_platform ON social_media_accounts(platform);
CREATE INDEX IF NOT EXISTS idx_social_media_accounts_user_platform ON social_media_accounts(user_id, platform);
CREATE INDEX IF NOT EXISTS idx_social_media_accounts_active ON social_media_accounts(is_active) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_social_media_accounts_primary ON social_media_accounts(user_id, platform, is_primary) WHERE is_primary = TRUE;

-- Create trigger to automatically update updated_at
CREATE TRIGGER update_social_media_accounts_updated_at BEFORE UPDATE ON social_media_accounts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Migrate existing Instagram accounts if table exists
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'instagram_accounts') THEN
        INSERT INTO social_media_accounts (
            user_id, platform, account_id, username, access_token, refresh_token,
            expires_at, metadata, scopes, is_active, created_at, updated_at
        )
        SELECT 
            user_id,
            'instagram',
            instagram_account_id,
            instagram_username,
            access_token,
            NULL as refresh_token,
            expires_at,
            jsonb_build_object(
                'facebook_page_id', facebook_page_id,
                'instagram_account_id', instagram_account_id
            ) as metadata,
            scopes,
            is_active,
            created_at,
            updated_at
        FROM instagram_accounts
        ON CONFLICT (user_id, platform, account_id) DO NOTHING;
    END IF;
END $$;




