-- Migration: Add password_hash field to users table for email/password authentication
-- This allows users to register and login with email/password in addition to Google OAuth

-- Add password_hash column (nullable to support existing Google OAuth users)
ALTER TABLE users 
ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255);

-- Add index for email lookups (if not already exists)
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- Make google_id nullable (users can register with email/password without Google)
ALTER TABLE users 
ALTER COLUMN google_id DROP NOT NULL;

-- Add constraint: user must have either google_id OR password_hash
-- Note: This is enforced at application level, not database level for flexibility

