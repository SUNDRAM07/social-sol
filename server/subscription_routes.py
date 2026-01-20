"""
Subscription API Routes
Handles tier management, subscription actions, and usage tracking
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, Literal
from uuid import UUID

from auth_service import get_current_user
from models import UserResponse
from subscription_service import subscription_service

router = APIRouter(prefix="/subscription", tags=["subscription"])


# =========================================================================
# REQUEST MODELS
# =========================================================================

class SubscribeRequest(BaseModel):
    tier: Literal["premium", "agency"]
    wallet_address: str
    auto_renew: bool = True


class RefreshBalanceRequest(BaseModel):
    wallet_address: str


class UseCreditRequest(BaseModel):
    amount: int
    reason: str


class AddCreditRequest(BaseModel):
    amount: int
    reason: str = "purchase"


# =========================================================================
# SUBSCRIPTION STATUS
# =========================================================================

@router.get("/status")
async def get_subscription_status(current_user: UserResponse = Depends(get_current_user)):
    """Get current user's subscription status"""
    try:
        status = await subscription_service.get_subscription_status(current_user.id)
        
        return {
            "tier": status.tier,
            "token_balance": status.token_balance,
            "is_subscribed": status.is_subscribed,
            "subscription_active": status.subscription_active,
            "renews_at": status.renews_at.isoformat() if status.renews_at else None,
            "auto_renew": status.auto_renew,
            "posts_used_today": status.posts_used_today,
            "posts_limit": status.posts_limit,
            "ai_generations_today": status.ai_generations_today,
            "ai_generations_limit": status.ai_generations_limit,
            "credits_balance": status.credits_balance,
            "tokens_burned_total": status.tokens_burned_total,
            "can_auto_post": status.can_auto_post,
            "days_until_renewal": status.days_until_renewal,
            "grace_period": status.grace_period,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tiers")
async def get_tier_comparison():
    """Get tier comparison for pricing display"""
    from subscription_tiers import get_tier_comparison
    return get_tier_comparison()


# =========================================================================
# SUBSCRIPTION MANAGEMENT
# =========================================================================

@router.post("/subscribe")
async def subscribe(
    request: SubscribeRequest,
    current_user: UserResponse = Depends(get_current_user)
):
    """Subscribe to a paid tier (Premium or Agency)"""
    try:
        result = await subscription_service.subscribe(
            user_id=current_user.id,
            tier=request.tier,
            wallet_address=request.wallet_address,
            auto_renew=request.auto_renew
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cancel")
async def cancel_subscription(current_user: UserResponse = Depends(get_current_user)):
    """Cancel subscription auto-renewal"""
    try:
        result = await subscription_service.cancel_subscription(current_user.id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/refresh-balance")
async def refresh_balance(
    request: RefreshBalanceRequest,
    current_user: UserResponse = Depends(get_current_user)
):
    """Refresh token balance from blockchain"""
    try:
        result = await subscription_service.update_tier_from_balance(
            user_id=current_user.id,
            wallet_address=request.wallet_address
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =========================================================================
# USAGE TRACKING
# =========================================================================

@router.get("/usage/posts")
async def check_post_limit(current_user: UserResponse = Depends(get_current_user)):
    """Check remaining post quota for today"""
    try:
        return await subscription_service.check_daily_limit(current_user.id, "posts")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/usage/ai")
async def check_ai_limit(current_user: UserResponse = Depends(get_current_user)):
    """Check remaining AI generation quota for today"""
    try:
        return await subscription_service.check_daily_limit(current_user.id, "ai_generations")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/usage/increment-posts")
async def increment_post_usage(current_user: UserResponse = Depends(get_current_user)):
    """Increment post usage (called after successful post)"""
    try:
        return await subscription_service.increment_usage(current_user.id, "posts")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/usage/increment-ai")
async def increment_ai_usage(current_user: UserResponse = Depends(get_current_user)):
    """Increment AI generation usage"""
    try:
        return await subscription_service.increment_usage(current_user.id, "ai_generations")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =========================================================================
# CREDITS
# =========================================================================

@router.get("/credits")
async def get_credits(current_user: UserResponse = Depends(get_current_user)):
    """Get user's credit balance"""
    try:
        return await subscription_service.get_credits(current_user.id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/credits/use")
async def use_credits(
    request: UseCreditRequest,
    current_user: UserResponse = Depends(get_current_user)
):
    """Use credits for a feature"""
    try:
        return await subscription_service.use_credits(
            user_id=current_user.id,
            amount=request.amount,
            reason=request.reason
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/credits/add")
async def add_credits(
    request: AddCreditRequest,
    current_user: UserResponse = Depends(get_current_user)
):
    """Add credits (after token burn)"""
    try:
        return await subscription_service.add_credits(
            user_id=current_user.id,
            amount=request.amount,
            reason=request.reason
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =========================================================================
# BURN STATS
# =========================================================================

@router.get("/burn-stats")
async def get_burn_stats(current_user: UserResponse = Depends(get_current_user)):
    """Get platform-wide burn statistics"""
    try:
        return await subscription_service.get_platform_burn_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/burn-history")
async def get_burn_history(
    limit: int = 20,
    current_user: UserResponse = Depends(get_current_user)
):
    """Get user's burn history"""
    try:
        burns = await subscription_service.get_burn_history(current_user.id, limit)
        return {"burns": burns}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =========================================================================
# FEATURE ACCESS
# =========================================================================

@router.get("/can-use/{feature}")
async def can_use_feature(
    feature: str,
    current_user: UserResponse = Depends(get_current_user)
):
    """Check if user can use a specific feature"""
    try:
        return await subscription_service.can_use_feature(current_user.id, feature)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
