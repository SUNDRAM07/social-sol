"""
Subscription Tier Definitions for SocialAnywhere.ai
Token-gated features based on $SOCIAL token holdings
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional

# Token contract address (replace with actual when deployed)
SOCIAL_TOKEN_MINT = "SoCiaLxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"  # Placeholder


class TierLevel(str, Enum):
    FREE = "free"
    HOLDER = "holder"  # Any amount of tokens
    PRO = "pro"  # 1,000+ tokens
    AGENCY = "agency"  # 10,000+ tokens


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


# Tier definitions
TIER_CONFIG = {
    TierLevel.FREE: TierFeatures(
        posts_per_day=3,
        platforms_allowed=2,
        ai_generations_per_day=10,
        scheduled_posts=10,
        campaigns=1,
        analytics_days=7,
        multi_project=False,
        white_label=False,
        priority_support=False,
        custom_ai_voice=False,
        flow_automations=0,
        webhook_integrations=False,
    ),
    TierLevel.HOLDER: TierFeatures(
        posts_per_day=10,
        platforms_allowed=4,
        ai_generations_per_day=50,
        scheduled_posts=50,
        campaigns=5,
        analytics_days=30,
        multi_project=False,
        white_label=False,
        priority_support=False,
        custom_ai_voice=True,
        flow_automations=2,
        webhook_integrations=False,
    ),
    TierLevel.PRO: TierFeatures(
        posts_per_day=-1,  # Unlimited
        platforms_allowed=-1,  # All platforms
        ai_generations_per_day=-1,
        scheduled_posts=-1,
        campaigns=-1,
        analytics_days=90,
        multi_project=True,
        white_label=False,
        priority_support=True,
        custom_ai_voice=True,
        flow_automations=10,
        webhook_integrations=True,
    ),
    TierLevel.AGENCY: TierFeatures(
        posts_per_day=-1,
        platforms_allowed=-1,
        ai_generations_per_day=-1,
        scheduled_posts=-1,
        campaigns=-1,
        analytics_days=365,
        multi_project=True,
        white_label=True,
        priority_support=True,
        custom_ai_voice=True,
        flow_automations=-1,  # Unlimited
        webhook_integrations=True,
    ),
}

# Token thresholds (in token units, not lamports)
TIER_THRESHOLDS = {
    TierLevel.FREE: 0,
    TierLevel.HOLDER: 1,  # Any amount
    TierLevel.PRO: 1_000,
    TierLevel.AGENCY: 10_000,
}


def get_tier_from_balance(token_balance: int) -> TierLevel:
    """Determine user tier based on token balance"""
    if token_balance >= TIER_THRESHOLDS[TierLevel.AGENCY]:
        return TierLevel.AGENCY
    elif token_balance >= TIER_THRESHOLDS[TierLevel.PRO]:
        return TierLevel.PRO
    elif token_balance >= TIER_THRESHOLDS[TierLevel.HOLDER]:
        return TierLevel.HOLDER
    else:
        return TierLevel.FREE


def get_tier_features(tier: TierLevel) -> TierFeatures:
    """Get features for a specific tier"""
    return TIER_CONFIG[tier]


def check_feature_access(tier: TierLevel, feature: str, current_usage: int = 0) -> dict:
    """
    Check if user has access to a feature
    Returns: {"allowed": bool, "limit": int, "remaining": int, "upgrade_tier": TierLevel|None}
    """
    features = TIER_CONFIG[tier]
    feature_value = getattr(features, feature, None)
    
    if feature_value is None:
        return {"allowed": False, "error": f"Unknown feature: {feature}"}
    
    if isinstance(feature_value, bool):
        if feature_value:
            return {"allowed": True}
        else:
            # Find which tier unlocks this
            for check_tier in [TierLevel.HOLDER, TierLevel.PRO, TierLevel.AGENCY]:
                if getattr(TIER_CONFIG[check_tier], feature, False):
                    return {
                        "allowed": False,
                        "upgrade_tier": check_tier,
                        "message": f"Upgrade to {check_tier.value} to unlock {feature}"
                    }
            return {"allowed": False}
    
    if isinstance(feature_value, int):
        if feature_value == -1:  # Unlimited
            return {"allowed": True, "limit": -1, "remaining": -1}
        
        remaining = feature_value - current_usage
        if remaining > 0:
            return {
                "allowed": True,
                "limit": feature_value,
                "remaining": remaining
            }
        else:
            # Find next tier with higher limit
            for check_tier in [TierLevel.HOLDER, TierLevel.PRO, TierLevel.AGENCY]:
                check_value = getattr(TIER_CONFIG[check_tier], feature, 0)
                if check_value == -1 or check_value > feature_value:
                    return {
                        "allowed": False,
                        "limit": feature_value,
                        "remaining": 0,
                        "upgrade_tier": check_tier,
                        "message": f"Daily limit reached. Upgrade to {check_tier.value} for more."
                    }
            return {"allowed": False, "limit": feature_value, "remaining": 0}
    
    return {"allowed": False, "error": "Invalid feature configuration"}


def get_tier_comparison() -> list[dict]:
    """Get comparison table of all tiers for UI display"""
    comparison = []
    
    for tier in TierLevel:
        features = TIER_CONFIG[tier]
        threshold = TIER_THRESHOLDS[tier]
        
        comparison.append({
            "tier": tier.value,
            "min_tokens": threshold,
            "posts_per_day": "Unlimited" if features.posts_per_day == -1 else features.posts_per_day,
            "platforms": "All" if features.platforms_allowed == -1 else features.platforms_allowed,
            "ai_generations": "Unlimited" if features.ai_generations_per_day == -1 else features.ai_generations_per_day,
            "analytics_days": features.analytics_days,
            "multi_project": features.multi_project,
            "white_label": features.white_label,
            "flow_automations": "Unlimited" if features.flow_automations == -1 else features.flow_automations,
            "webhooks": features.webhook_integrations,
        })
    
    return comparison
