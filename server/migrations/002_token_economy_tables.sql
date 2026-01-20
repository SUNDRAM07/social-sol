-- Migration 002: Token Economy Tables
-- Run this migration to add subscription, credits, and burn tracking

-- =====================================================
-- SUBSCRIPTIONS TABLE (Enhanced from user_subscriptions)
-- =====================================================

-- Add subscription-specific columns to user_subscriptions if it exists
-- Or create a proper subscriptions table

CREATE TABLE IF NOT EXISTS subscriptions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE UNIQUE,
    tier VARCHAR(20) DEFAULT 'free', -- free, basic, premium, agency
    token_balance BIGINT DEFAULT 0, -- cached balance
    started_at TIMESTAMP WITH TIME ZONE,
    renews_at TIMESTAMP WITH TIME ZONE,
    auto_renew BOOLEAN DEFAULT true,
    tokens_burned_total BIGINT DEFAULT 0,
    posts_used_today INTEGER DEFAULT 0,
    ai_generations_today INTEGER DEFAULT 0,
    last_post_reset TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    grace_period_ends TIMESTAMP WITH TIME ZONE, -- 3-day grace after failed renewal
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =====================================================
-- CREDIT BALANCES TABLE
-- =====================================================

CREATE TABLE IF NOT EXISTS credit_balances (
    user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    credits_balance INTEGER DEFAULT 0,
    credits_used_this_month INTEGER DEFAULT 0,
    free_credits_remaining INTEGER DEFAULT 0, -- monthly free credits from tier
    last_reset TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =====================================================
-- TOKEN BURNS TABLE (Transparency & History)
-- =====================================================

CREATE TABLE IF NOT EXISTS token_burns (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    amount BIGINT NOT NULL,
    reason VARCHAR(50) NOT NULL, -- subscription, credits, manual
    tier VARCHAR(20), -- which tier was burned for (if subscription)
    tx_signature VARCHAR(100), -- Solana transaction signature
    burned_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =====================================================
-- EVERGREEN POSTS TABLE
-- =====================================================

CREATE TABLE IF NOT EXISTS evergreen_posts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    original_post_id UUID REFERENCES posts(id) ON DELETE SET NULL,
    content TEXT NOT NULL,
    platforms TEXT[],
    variations JSONB DEFAULT '[]', -- AI-generated variations
    repost_frequency_days INTEGER DEFAULT 7,
    last_posted_at TIMESTAMP WITH TIME ZONE,
    next_post_at TIMESTAMP WITH TIME ZONE,
    post_count INTEGER DEFAULT 0,
    avg_engagement FLOAT DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =====================================================
-- USER STREAKS TABLE (Gamification)
-- =====================================================

CREATE TABLE IF NOT EXISTS user_streaks (
    user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    current_streak INTEGER DEFAULT 0,
    longest_streak INTEGER DEFAULT 0,
    last_post_date DATE,
    total_posts INTEGER DEFAULT 0,
    total_ai_generations INTEGER DEFAULT 0,
    xp_points INTEGER DEFAULT 0,
    level INTEGER DEFAULT 1,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =====================================================
-- ACHIEVEMENTS TABLE
-- =====================================================

CREATE TABLE IF NOT EXISTS achievements (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    achievement_type VARCHAR(50) NOT NULL, -- first_post, streak_7, posts_100, etc.
    achieved_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'
);

-- =====================================================
-- INDEXES
-- =====================================================

CREATE INDEX IF NOT EXISTS idx_subscriptions_user_id ON subscriptions(user_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_tier ON subscriptions(tier);
CREATE INDEX IF NOT EXISTS idx_subscriptions_renews_at ON subscriptions(renews_at);

CREATE INDEX IF NOT EXISTS idx_credit_balances_user_id ON credit_balances(user_id);

CREATE INDEX IF NOT EXISTS idx_token_burns_user_id ON token_burns(user_id);
CREATE INDEX IF NOT EXISTS idx_token_burns_reason ON token_burns(reason);
CREATE INDEX IF NOT EXISTS idx_token_burns_burned_at ON token_burns(burned_at);

CREATE INDEX IF NOT EXISTS idx_evergreen_posts_user_id ON evergreen_posts(user_id);
CREATE INDEX IF NOT EXISTS idx_evergreen_posts_is_active ON evergreen_posts(is_active);
CREATE INDEX IF NOT EXISTS idx_evergreen_posts_next_post ON evergreen_posts(next_post_at);

CREATE INDEX IF NOT EXISTS idx_user_streaks_user_id ON user_streaks(user_id);
CREATE INDEX IF NOT EXISTS idx_user_streaks_level ON user_streaks(level);

CREATE INDEX IF NOT EXISTS idx_achievements_user_id ON achievements(user_id);
CREATE INDEX IF NOT EXISTS idx_achievements_type ON achievements(achievement_type);

-- =====================================================
-- TRIGGERS
-- =====================================================

-- Trigger for subscriptions updated_at
DROP TRIGGER IF EXISTS update_subscriptions_updated_at ON subscriptions;
CREATE TRIGGER update_subscriptions_updated_at 
    BEFORE UPDATE ON subscriptions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Trigger for user_streaks updated_at
DROP TRIGGER IF EXISTS update_user_streaks_updated_at ON user_streaks;
CREATE TRIGGER update_user_streaks_updated_at 
    BEFORE UPDATE ON user_streaks
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- USEFUL VIEWS
-- =====================================================

-- View: Total platform burns (for transparency dashboard)
CREATE OR REPLACE VIEW platform_burn_stats AS
SELECT 
    DATE_TRUNC('month', burned_at) as month,
    reason,
    SUM(amount) as total_burned,
    COUNT(*) as burn_count
FROM token_burns
GROUP BY DATE_TRUNC('month', burned_at), reason
ORDER BY month DESC;

-- View: User subscription summary
CREATE OR REPLACE VIEW user_subscription_summary AS
SELECT 
    u.id as user_id,
    u.email,
    u.name,
    COALESCE(s.tier, 'free') as tier,
    COALESCE(s.token_balance, 0) as token_balance,
    s.renews_at,
    s.auto_renew,
    COALESCE(s.tokens_burned_total, 0) as lifetime_burns,
    COALESCE(cb.credits_balance, 0) as credits,
    COALESCE(us.current_streak, 0) as streak,
    COALESCE(us.level, 1) as level
FROM users u
LEFT JOIN subscriptions s ON u.id = s.user_id
LEFT JOIN credit_balances cb ON u.id = cb.user_id
LEFT JOIN user_streaks us ON u.id = us.user_id;

-- =====================================================
-- FUNCTIONS
-- =====================================================

-- Function: Reset daily limits (run via cron at midnight UTC)
CREATE OR REPLACE FUNCTION reset_daily_limits()
RETURNS void AS $$
BEGIN
    UPDATE subscriptions 
    SET posts_used_today = 0, 
        ai_generations_today = 0,
        last_post_reset = NOW()
    WHERE last_post_reset < CURRENT_DATE;
END;
$$ LANGUAGE plpgsql;

-- Function: Reset monthly credits (run via cron on 1st of month)
CREATE OR REPLACE FUNCTION reset_monthly_credits()
RETURNS void AS $$
BEGIN
    -- Reset usage counter
    UPDATE credit_balances 
    SET credits_used_this_month = 0,
        last_reset = NOW()
    WHERE last_reset < DATE_TRUNC('month', CURRENT_DATE);
    
    -- Grant free credits based on tier
    UPDATE credit_balances cb
    SET free_credits_remaining = CASE 
        WHEN s.tier = 'premium' THEN 500
        WHEN s.tier = 'agency' THEN 2000
        ELSE 0
    END
    FROM subscriptions s
    WHERE cb.user_id = s.user_id;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- DONE
-- =====================================================
