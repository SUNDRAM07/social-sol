"""
Subscription Tier Definitions for SocialAnywhere.ai
Token-gated features based on $SOCIAL token holdings
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional, List, Dict, Any

# Token contract address (replace with actual when deployed)
SOCIAL_TOKEN_MINT = "SoCiaLxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"  # Placeholder


class TierLevel(str, Enum):
    FREE = "free"
    BASIC = "basic"      # Hold 100 tokens
    PREMIUM = "premium"  # Hold 100 + burn 25/month
    AGENCY = "agency"    # Hold 500 + burn 100/month


@dataclass
class TierFeatures:
    """Features available at each tier"""
    posts_per_day: int  # -1 = unlimited
    platforms_allowed: int  # -1 = all
    ai_generations_per_day: int
    scheduled_posts: int  # max scheduled posts at once
    campaigns: int  # max campaigns
    analytics_days: int  # how many days of analytics
    multi_project: bool
    white_label: bool
    priority_support: bool
    custom_ai_voice: bool
    flow_automations: int  # -1 = unlimited
    webhook_integrations: bool
    auto_posting: bool  # Can posts go out automatically?
    evergreen_content: bool
    brand_voice: bool
    thread_creator: bool
    team_members: int  # 0 = solo only


# Tier definitions aligned with master plan
TIER_CONFIG = {
    TierLevel.FREE: TierFeatures(
        posts_per_day=3,
        platforms_allowed=2,
        ai_generations_per_day=5,
        scheduled_posts=5,
        campaigns=1,
        analytics_days=7,
        multi_project=False,
        white_label=False,
        priority_support=False,
        custom_ai_voice=False,
        flow_automations=0,
        webhook_integrations=False,
        auto_posting=False,
        evergreen_content=False,
        brand_voice=False,
        thread_creator=False,
        team_members=0,
    ),
    TierLevel.BASIC: TierFeatures(
        posts_per_day=5,
        platforms_allowed=3,
        ai_generations_per_day=10,
        scheduled_posts=20,
        campaigns=3,
        analytics_days=7,
        multi_project=False,
        white_label=False,
        priority_support=False,
        custom_ai_voice=False,
        flow_automations=0,
        webhook_integrations=False,
        auto_posting=False,  # Manual only
        evergreen_content=False,
        brand_voice=False,
        thread_creator=False,
        team_members=0,
    ),
    TierLevel.PREMIUM: TierFeatures(
        posts_per_day=-1,  # Unlimited
        platforms_allowed=-1,  # All platforms
        ai_generations_per_day=-1,
        scheduled_posts=-1,
        campaigns=-1,
        analytics_days=90,
        multi_project=False,
        white_label=False,
        priority_support=True,
        custom_ai_voice=True,
        flow_automations=5,
        webhook_integrations=True,
        auto_posting=True,  # THE killer feature
        evergreen_content=True,
        brand_voice=True,
        thread_creator=True,
        team_members=0,
    ),
    TierLevel.AGENCY: TierFeatures(
        posts_per_day=-1,
        platforms_allowed=-1,
        ai_generations_per_day=-1,
        scheduled_posts=-1,
        campaigns=-1,
        analytics_days=365,
        multi_project=True,  # Up to 10 brands
        white_label=True,
        priority_support=True,
        custom_ai_voice=True,
        flow_automations=-1,  # Unlimited
        webhook_integrations=True,
        auto_posting=True,
        evergreen_content=True,
        brand_voice=True,
        thread_creator=True,
        team_members=5,
    ),
}

# Token thresholds (minimum tokens to HOLD for tier access)
TIER_THRESHOLDS = {
    TierLevel.FREE: 0,
    TierLevel.BASIC: 100,     # Hold 100 tokens
    TierLevel.PREMIUM: 100,   # Hold 100 + monthly burn
    TierLevel.AGENCY: 500,    # Hold 500 + monthly burn
}

# Monthly burn amounts for subscription tiers
MONTHLY_BURNS = {
    TierLevel.FREE: 0,
    TierLevel.BASIC: 0,       # Hold only, no burn
    TierLevel.PREMIUM: 25,    # 25 tokens burned/month
    TierLevel.AGENCY: 100,    # 100 tokens burned/month
}


def get_tier_from_balance(token_balance: int, has_active_subscription: bool = False, subscription_tier: str = None) -> TierLevel:
    """
    Determine tier based on token balance and subscription status
    
    - BASIC: Just need to hold 100 tokens
    - PREMIUM/AGENCY: Need tokens AND active subscription (monthly burn)
    """
    if has_active_subscription and subscription_tier:
        # User has active subscription, return that tier
        try:
            return TierLevel(subscription_tier)
        except ValueError:
            pass
    
    # Otherwise, determine by balance alone (for BASIC tier)
    if token_balance >= TIER_THRESHOLDS[TierLevel.BASIC]:
        return TierLevel.BASIC
    
    return TierLevel.FREE


def get_tier_features(tier: TierLevel) -> TierFeatures:
    """Get features for a specific tier"""
    return TIER_CONFIG.get(tier, TIER_CONFIG[TierLevel.FREE])


def check_feature_access(tier: TierLevel, feature: str) -> bool:
    """Check if a tier has access to a specific feature"""
    features = get_tier_features(tier)
    feature_value = getattr(features, feature, None)
    
    if feature_value is None:
        return False
    
    if isinstance(feature_value, bool):
        return feature_value
    
    if isinstance(feature_value, int):
        return feature_value != 0
    
    return True


def get_tier_comparison() -> List[Dict[str, Any]]:
    """Get comparison data for all tiers (for UI display)"""
    comparison = []
    
    for tier in TierLevel:
        features = get_tier_features(tier)
        comparison.append({
            "tier": tier.value,
            "min_tokens": TIER_THRESHOLDS[tier],
            "monthly_burn": MONTHLY_BURNS[tier],
            "posts_per_day": features.posts_per_day if features.posts_per_day != -1 else "Unlimited",
            "platforms": features.platforms_allowed if features.platforms_allowed != -1 else "All",
            "ai_generations": features.ai_generations_per_day if features.ai_generations_per_day != -1 else "Unlimited",
            "analytics_days": features.analytics_days,
            "auto_posting": features.auto_posting,
            "evergreen_content": features.evergreen_content,
            "brand_voice": features.brand_voice,
            "multi_project": features.multi_project,
            "white_label": features.white_label,
            "flow_automations": features.flow_automations if features.flow_automations != -1 else "Unlimited",
            "webhooks": features.webhook_integrations,
            "team_members": features.team_members if features.team_members > 0 else "Solo",
        })
    
    return comparison


# Tier hierarchy for comparison
TIER_ORDER = [TierLevel.FREE, TierLevel.BASIC, TierLevel.PREMIUM, TierLevel.AGENCY]


def tier_meets_requirement(user_tier: TierLevel, required_tier: TierLevel) -> bool:
    """Check if user's tier meets or exceeds the required tier"""
    user_index = TIER_ORDER.index(user_tier)
    required_index = TIER_ORDER.index(required_tier)
    return user_index >= required_index
