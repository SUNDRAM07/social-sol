"""
Token Gating Middleware
Restricts access to features based on user's token tier
"""

import logging
from functools import wraps
from typing import Optional, Callable
from fastapi import HTTPException, Depends, Request
from fastapi.responses import JSONResponse

from auth_routes import get_current_user
from token_service import token_service, get_user_tier
from subscription_tiers import (
    TierLevel,
    check_feature_access,
    get_tier_features,
    TIER_THRESHOLDS
)
from models import UserResponse

logger = logging.getLogger(__name__)


# New tier system mapping (aligns with subscription_service.py)
NEW_TIERS = ["free", "basic", "premium", "agency"]


class TokenGateError(HTTPException):
    """Custom exception for token gating"""
    def __init__(
        self,
        required_tier: TierLevel,
        current_tier: TierLevel,
        feature: str,
        tokens_needed: int = 0
    ):
        detail = {
            "error": "insufficient_tier",
            "message": f"This feature requires {required_tier.value} tier",
            "required_tier": required_tier.value,
            "current_tier": current_tier.value,
            "feature": feature,
            "tokens_needed": tokens_needed,
            "upgrade_url": "/dashboard/tokens"
        }
        super().__init__(status_code=403, detail=detail)


async def get_user_subscription(user_id: str, wallet_address: Optional[str] = None) -> dict:
    """
    Get user's subscription info from database or wallet
    """
    from database import get_db_connection
    
    try:
        conn = await get_db_connection()
        
        # First check if user has subscription record
        subscription = await conn.fetchrow(
            """
            SELECT tier, token_balance, last_balance_check, features_unlocked,
                   posts_used_today, last_post_reset
            FROM user_subscriptions
            WHERE user_id = $1
            """,
            user_id
        )
        
        if subscription:
            return dict(subscription)
        
        # If no subscription record, check wallet balance
        if wallet_address:
            balance = await token_service.get_token_balance(wallet_address)
            
            # Create subscription record
            await conn.execute(
                """
                INSERT INTO user_subscriptions (user_id, tier, token_balance, last_balance_check)
                VALUES ($1, $2, $3, NOW())
                ON CONFLICT (user_id) DO UPDATE SET
                    tier = $2, token_balance = $3, last_balance_check = NOW()
                """,
                user_id, balance.tier.value, int(balance.ui_balance)
            )
            
            return {
                "tier": balance.tier.value,
                "token_balance": int(balance.ui_balance),
                "features_unlocked": balance.features,
                "posts_used_today": 0,
                "last_post_reset": None
            }
        
        # No wallet, return free tier
        return {
            "tier": TierLevel.FREE.value,
            "token_balance": 0,
            "features_unlocked": get_tier_features(TierLevel.FREE).__dict__,
            "posts_used_today": 0,
            "last_post_reset": None
        }
        
    except Exception as e:
        logger.error(f"Error getting subscription: {e}")
        return {
            "tier": TierLevel.FREE.value,
            "token_balance": 0,
            "features_unlocked": get_tier_features(TierLevel.FREE).__dict__,
            "posts_used_today": 0,
            "last_post_reset": None
        }


def require_tier(min_tier: TierLevel):
    """
    Decorator to require minimum tier for an endpoint
    
    Usage:
        @app.get("/premium-feature")
        @require_tier(TierLevel.PRO)
        async def premium_feature(current_user: dict = Depends(get_current_user)):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get current user from kwargs (injected by Depends)
            current_user = kwargs.get("current_user")
            if not current_user:
                raise HTTPException(status_code=401, detail="Not authenticated")
            
            # Get user's wallet address
            wallet_address = getattr(current_user, 'wallet_address', None)
            user_id = str(current_user.id)
            
            # Get subscription info
            subscription = await get_user_subscription(user_id, wallet_address)
            current_tier = TierLevel(subscription["tier"])
            
            # Check tier hierarchy
            tier_order = [TierLevel.FREE, TierLevel.HOLDER, TierLevel.PRO, TierLevel.AGENCY]
            current_index = tier_order.index(current_tier)
            required_index = tier_order.index(min_tier)
            
            if current_index < required_index:
                tokens_needed = TIER_THRESHOLDS[min_tier] - subscription.get("token_balance", 0)
                raise TokenGateError(
                    required_tier=min_tier,
                    current_tier=current_tier,
                    feature=func.__name__,
                    tokens_needed=max(0, tokens_needed)
                )
            
            # Add subscription info to kwargs for use in the function
            kwargs["subscription"] = subscription
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def check_daily_limit(feature: str):
    """
    Decorator to check daily usage limits
    
    Usage:
        @app.post("/create-post")
        @check_daily_limit("posts_per_day")
        async def create_post(current_user: dict = Depends(get_current_user)):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            current_user = kwargs.get("current_user")
            if not current_user:
                raise HTTPException(status_code=401, detail="Not authenticated")
            
            wallet_address = getattr(current_user, 'wallet_address', None)
            user_id = str(current_user.id)
            
            subscription = await get_user_subscription(user_id, wallet_address)
            tier = TierLevel(subscription["tier"])
            features = get_tier_features(tier)
            
            # Get the limit for this feature
            limit = getattr(features, feature, None)
            if limit is None:
                raise HTTPException(status_code=500, detail=f"Unknown feature: {feature}")
            
            # Unlimited = proceed
            if limit == -1:
                kwargs["subscription"] = subscription
                return await func(*args, **kwargs)
            
            # Check usage (for posts_per_day specifically)
            if feature == "posts_per_day":
                current_usage = subscription.get("posts_used_today", 0)
                
                if current_usage >= limit:
                    raise HTTPException(
                        status_code=429,
                        detail={
                            "error": "daily_limit_reached",
                            "message": f"You've reached your daily limit of {limit} posts",
                            "limit": limit,
                            "used": current_usage,
                            "resets_at": "midnight UTC",
                            "upgrade_url": "/dashboard/tokens"
                        }
                    )
            
            kwargs["subscription"] = subscription
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


async def increment_usage(user_id: str, feature: str = "posts_used_today"):
    """Increment usage counter for a feature"""
    from database import get_db_connection
    
    try:
        conn = await get_db_connection()
        
        if feature == "posts_used_today":
            await conn.execute(
                """
                UPDATE user_subscriptions
                SET posts_used_today = posts_used_today + 1
                WHERE user_id = $1
                """,
                user_id
            )
    except Exception as e:
        logger.error(f"Error incrementing usage: {e}")


async def reset_daily_limits():
    """Reset daily limits for all users (run via cron at midnight UTC)"""
    from database import get_db_connection
    
    try:
        conn = await get_db_connection()
        await conn.execute(
            """
            UPDATE user_subscriptions
            SET posts_used_today = 0, last_post_reset = NOW()
            WHERE last_post_reset < CURRENT_DATE OR last_post_reset IS NULL
            """
        )
        logger.info("Daily limits reset for all users")
    except Exception as e:
        logger.error(f"Error resetting daily limits: {e}")


# Feature-specific decorators for convenience
def require_holder(func: Callable):
    """Require at least HOLDER tier"""
    return require_tier(TierLevel.HOLDER)(func)


def require_pro(func: Callable):
    """Require at least PRO tier"""
    return require_tier(TierLevel.PRO)(func)


def require_agency(func: Callable):
    """Require AGENCY tier"""
    return require_tier(TierLevel.AGENCY)(func)


# =========================================================================
# NEW FASTAPI DEPENDENCIES (Use with new subscription system)
# =========================================================================

async def check_post_limit(current_user: UserResponse = Depends(get_current_user)):
    """
    FastAPI dependency to check if user can create posts
    Raises HTTPException if limit reached
    """
    from subscription_service import subscription_service
    
    check = await subscription_service.check_daily_limit(current_user.id, "posts")
    
    if not check["allowed"]:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "daily_limit_reached",
                "message": f"You've reached your daily limit of {check['limit']} posts",
                "limit": check["limit"],
                "used": check["used"],
                "remaining": 0,
                "upgrade_url": "/tokens"
            }
        )
    
    return check


async def check_ai_limit(current_user: UserResponse = Depends(get_current_user)):
    """
    FastAPI dependency to check if user can use AI generation
    Raises HTTPException if limit reached
    """
    from subscription_service import subscription_service
    
    check = await subscription_service.check_daily_limit(current_user.id, "ai_generations")
    
    if not check["allowed"]:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "daily_limit_reached",
                "message": f"You've reached your daily limit of {check['limit']} AI generations",
                "limit": check["limit"],
                "used": check["used"],
                "remaining": 0,
                "upgrade_url": "/tokens"
            }
        )
    
    return check


async def require_premium_tier(current_user: UserResponse = Depends(get_current_user)):
    """
    FastAPI dependency to require Premium or Agency tier
    """
    from subscription_service import subscription_service
    
    status = await subscription_service.get_subscription_status(current_user.id)
    
    if status.tier not in ["premium", "agency"] or not status.subscription_active:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "insufficient_tier",
                "message": "This feature requires Premium or Agency subscription",
                "current_tier": status.tier,
                "required_tier": "premium",
                "upgrade_url": "/tokens"
            }
        )
    
    return status


async def require_agency_tier(current_user: UserResponse = Depends(get_current_user)):
    """
    FastAPI dependency to require Agency tier
    """
    from subscription_service import subscription_service
    
    status = await subscription_service.get_subscription_status(current_user.id)
    
    if status.tier != "agency" or not status.subscription_active:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "insufficient_tier",
                "message": "This feature requires Agency subscription",
                "current_tier": status.tier,
                "required_tier": "agency",
                "upgrade_url": "/tokens"
            }
        )
    
    return status


async def can_auto_post(current_user: UserResponse = Depends(get_current_user)):
    """
    FastAPI dependency to check if user can use auto-posting
    """
    from subscription_service import subscription_service
    
    status = await subscription_service.get_subscription_status(current_user.id)
    
    if not status.can_auto_post:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "feature_locked",
                "message": "Automatic posting requires Premium or Agency subscription",
                "current_tier": status.tier,
                "feature": "auto_post",
                "upgrade_url": "/tokens"
            }
        )
    
    return status


async def increment_post_usage(current_user: UserResponse = Depends(get_current_user)):
    """
    FastAPI dependency to increment post usage after successful post
    Call this AFTER a post is successfully created
    """
    from subscription_service import subscription_service
    
    result = await subscription_service.increment_usage(current_user.id, "posts")
    return result


async def increment_ai_usage(current_user: UserResponse = Depends(get_current_user)):
    """
    FastAPI dependency to increment AI usage after successful generation
    """
    from subscription_service import subscription_service
    
    result = await subscription_service.increment_usage(current_user.id, "ai_generations")
    return result
