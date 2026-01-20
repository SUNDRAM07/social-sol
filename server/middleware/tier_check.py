"""
Tier Check Dependencies for FastAPI Routes
Simple, clean way to enforce tier limits on routes
"""

import logging
from typing import Optional
from fastapi import HTTPException, Depends

from auth_routes import get_current_user
from models import UserResponse
from subscription_service import subscription_service
from subscription_tiers import TierLevel, TIER_ORDER, get_tier_features

logger = logging.getLogger(__name__)


class TierError(HTTPException):
    """Raised when user doesn't meet tier requirements"""
    def __init__(self, required_tier: str, current_tier: str, feature: str = None):
        detail = {
            "error": "tier_required",
            "message": f"This feature requires {required_tier.upper()} tier or higher",
            "required_tier": required_tier,
            "current_tier": current_tier,
            "feature": feature,
            "upgrade_url": "/tokens"
        }
        super().__init__(status_code=403, detail=detail)


class LimitReachedError(HTTPException):
    """Raised when user has reached their daily limit"""
    def __init__(self, limit_type: str, used: int, limit: int, tier: str):
        detail = {
            "error": "limit_reached",
            "message": f"Daily {limit_type} limit reached ({used}/{limit}). Upgrade for more.",
            "limit_type": limit_type,
            "used": used,
            "limit": limit,
            "current_tier": tier,
            "upgrade_url": "/tokens"
        }
        super().__init__(status_code=429, detail=detail)


async def get_user_tier(current_user: UserResponse = Depends(get_current_user)) -> dict:
    """
    Get user's current tier and subscription status
    Returns dict with tier info for use in routes
    """
    try:
        status = await subscription_service.get_subscription_status(current_user.id)
        return {
            "user_id": current_user.id,
            "tier": status.tier,
            "subscription_active": status.subscription_active,
            "posts_used_today": status.posts_used_today,
            "posts_limit": status.posts_limit,
            "ai_generations_today": status.ai_generations_today,
            "ai_generations_limit": status.ai_generations_limit,
            "can_auto_post": status.can_auto_post,
        }
    except Exception as e:
        logger.error(f"Error getting tier: {e}")
        # Default to free tier on error
        return {
            "user_id": current_user.id,
            "tier": "free",
            "subscription_active": False,
            "posts_used_today": 0,
            "posts_limit": 3,
            "ai_generations_today": 0,
            "ai_generations_limit": 5,
            "can_auto_post": False,
        }


async def check_post_limit(current_user: UserResponse = Depends(get_current_user)) -> dict:
    """
    Check if user can create a post (hasn't hit daily limit)
    Use as dependency: Depends(check_post_limit)
    """
    try:
        result = await subscription_service.check_daily_limit(current_user.id, "posts")
        
        if not result["allowed"]:
            status = await subscription_service.get_subscription_status(current_user.id)
            raise LimitReachedError(
                limit_type="posts",
                used=result["used"],
                limit=result["limit"],
                tier=status.tier
            )
        
        return {
            "user_id": current_user.id,
            "posts_remaining": result["remaining"],
            "posts_used": result["used"],
            "posts_limit": result["limit"]
        }
    except LimitReachedError:
        raise
    except Exception as e:
        logger.error(f"Error checking post limit: {e}")
        # Allow on error to not block users
        return {"user_id": current_user.id, "posts_remaining": -1, "posts_used": 0, "posts_limit": -1}


async def check_ai_limit(current_user: UserResponse = Depends(get_current_user)) -> dict:
    """
    Check if user can use AI generation (hasn't hit daily limit)
    Use as dependency: Depends(check_ai_limit)
    """
    try:
        result = await subscription_service.check_daily_limit(current_user.id, "ai_generations")
        
        if not result["allowed"]:
            status = await subscription_service.get_subscription_status(current_user.id)
            raise LimitReachedError(
                limit_type="AI generations",
                used=result["used"],
                limit=result["limit"],
                tier=status.tier
            )
        
        return {
            "user_id": current_user.id,
            "ai_remaining": result["remaining"],
            "ai_used": result["used"],
            "ai_limit": result["limit"]
        }
    except LimitReachedError:
        raise
    except Exception as e:
        logger.error(f"Error checking AI limit: {e}")
        return {"user_id": current_user.id, "ai_remaining": -1, "ai_used": 0, "ai_limit": -1}


def require_tier(min_tier: str):
    """
    Factory for tier requirement dependency
    
    Usage:
        @router.post("/premium-feature")
        async def premium_feature(
            current_user = Depends(get_current_user),
            _tier = Depends(require_tier("premium"))
        ):
            ...
    """
    async def dependency(current_user: UserResponse = Depends(get_current_user)) -> dict:
        try:
            status = await subscription_service.get_subscription_status(current_user.id)
            user_tier = status.tier
            
            # Check tier hierarchy
            tier_order = ["free", "basic", "premium", "agency"]
            user_index = tier_order.index(user_tier) if user_tier in tier_order else 0
            required_index = tier_order.index(min_tier) if min_tier in tier_order else 0
            
            if user_index < required_index:
                raise TierError(
                    required_tier=min_tier,
                    current_tier=user_tier
                )
            
            return {"tier": user_tier, "user_id": current_user.id}
        except TierError:
            raise
        except Exception as e:
            logger.error(f"Error checking tier: {e}")
            raise TierError(required_tier=min_tier, current_tier="free")
    
    return dependency


def require_feature(feature_name: str):
    """
    Factory for feature requirement dependency
    
    Usage:
        @router.post("/auto-post")
        async def auto_post(
            current_user = Depends(get_current_user),
            _feature = Depends(require_feature("auto_posting"))
        ):
            ...
    """
    async def dependency(current_user: UserResponse = Depends(get_current_user)) -> dict:
        try:
            status = await subscription_service.get_subscription_status(current_user.id)
            user_tier = TierLevel(status.tier) if status.tier in [t.value for t in TierLevel] else TierLevel.FREE
            features = get_tier_features(user_tier)
            
            has_feature = getattr(features, feature_name, None)
            
            if has_feature is None or has_feature is False or has_feature == 0:
                # Find minimum tier that has this feature
                min_tier_for_feature = "premium"  # Default
                for tier in TierLevel:
                    tier_features = get_tier_features(tier)
                    if getattr(tier_features, feature_name, None):
                        min_tier_for_feature = tier.value
                        break
                
                raise TierError(
                    required_tier=min_tier_for_feature,
                    current_tier=status.tier,
                    feature=feature_name
                )
            
            return {"feature": feature_name, "tier": status.tier, "user_id": current_user.id}
        except TierError:
            raise
        except Exception as e:
            logger.error(f"Error checking feature: {e}")
            raise TierError(required_tier="premium", current_tier="free", feature=feature_name)
    
    return dependency


async def increment_post_usage(user_id) -> dict:
    """Call after successful post creation to increment usage counter"""
    return await subscription_service.increment_usage(user_id, "posts")


async def increment_ai_usage(user_id) -> dict:
    """Call after successful AI generation to increment usage counter"""
    return await subscription_service.increment_usage(user_id, "ai_generations")
