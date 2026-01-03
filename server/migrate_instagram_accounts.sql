-- Migration: Add Instagram accounts table
-- This table stores Instagram Business account credentials connected via OAuth

CREATE TABLE IF NOT EXISTS instagram_accounts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    instagram_account_id VARCHAR(255) NOT NULL,
    instagram_username VARCHAR(255),
    facebook_page_id VARCHAR(255), -- The Facebook page that owns this Instagram account
    access_token TEXT NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE,
    token_type VARCHAR(50) DEFAULT 'Bearer',
    scopes TEXT[], -- Array of granted permissions
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, instagram_account_id)
);

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_instagram_accounts_user_id ON instagram_accounts(user_id);
CREATE INDEX IF NOT EXISTS idx_instagram_accounts_account_id ON instagram_accounts(instagram_account_id);
CREATE INDEX IF NOT EXISTS idx_instagram_accounts_active ON instagram_accounts(is_active) WHERE is_active = TRUE;

-- Create trigger to automatically update updated_at
CREATE TRIGGER update_instagram_accounts_updated_at BEFORE UPDATE ON instagram_accounts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();




