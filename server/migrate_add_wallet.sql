-- Migration: Add wallet_address column to users table
-- Date: 2026-01-11
-- Description: Adds Solana wallet address support for wallet-based authentication

-- Add wallet_address column (nullable, unique)
ALTER TABLE users 
ADD COLUMN IF NOT EXISTS wallet_address VARCHAR(44) UNIQUE;

-- Make email nullable for wallet-only users
ALTER TABLE users 
ALTER COLUMN email DROP NOT NULL;

-- Create index for faster wallet lookups
CREATE INDEX IF NOT EXISTS idx_users_wallet_address ON users(wallet_address);

-- Add comment for documentation
COMMENT ON COLUMN users.wallet_address IS 'Solana wallet address (base58 encoded, 32-44 characters)';

