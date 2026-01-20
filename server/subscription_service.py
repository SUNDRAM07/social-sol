"""
Subscription Service for SocialAnywhere.ai
Handles tier management, subscription burns, renewals, and usage tracking
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Optional, Literal
from uuid import UUID
from enum import Enum
from dataclasses import dataclass

from database import db_manager
from token_service import token_service, TokenBalance
from subscription_tiers import (
    TierLevel, 
    TIER_CONFIG, 
    TIER_THRESHOLDS,
    get_tier_from_balance,
    get_tier_features,
    TierFeatures
)

logger = logging.getLogger(__name__)

# Subscription burn amounts (tokens burned per month)
SUBSCRIPTION_BURN_AMOUNTS = {
    "basic": 0,      # Hold only, no burn
    "premium": 25,   # 25 tokens/month
    "agency": 100,   # 100 tokens/month
}

# Minimum hold requirements
MINIMUM_HOLD = {
    "basic": 100,    # Hold 100 tokens for basic
    "premium": 100,  # Hold 100 + burn 25/month
    "agency": 500,   # Hold 500 + burn 100/month
}

# Free credits per tier (monthly)
FREE_CREDITS = {
    "free": 0,
    "basic": 0,
    "premium": 500,
    "agency": 2000,
}

# Daily limits per tier
DAILY_LIMITS = {
    "free": {"posts": 3, "ai_generations": 5},
    "basic": {"posts": 5, "ai_generations": 10},
    "premium": {"posts": -1, "ai_generations": -1},  # Unlimited
    "agency": {"posts": -1, "ai_generations": -1},
}


def _row_to_dict(row):
    """Convert database row to dictionary"""
    if row is None:
        return None
    if isinstance(row, dict):
        return row
    mapping = getattr(row, "_mapping", None)
    if mapping is not None:
        return dict(mapping)
    try:
        return dict(row)
    except:
        return None


@dataclass
class SubscriptionStatus:
    """Current subscription status for a user"""
    user_id: UUID
    tier: str
    token_balance: int
    is_subscribed: bool
    subscription_active: bool
    renews_at: Optional[datetime]
    auto_renew: bool
    posts_used_today: int
    posts_limit: int  # -1 = unlimited
    ai_generations_today: int
    ai_generations_limit: int
    credits_balance: int
    tokens_burned_total: int
    can_auto_post: bool
    days_until_renewal: Optional[int]
    grace_period: bool


class SubscriptionService:
    """Service for managing subscriptions and tier access"""
    
    def __init__(self):
        pass  # Uses db_manager for all database operations
    
    # =========================================================================
    # SUBSCRIPTION STATUS
    # =========================================================================
    
    async def get_subscription_status(self, user_id: UUID) -> SubscriptionStatus:
        """Get complete subscription status for a user"""
        try:
            # Get subscription record
            sub = _row_to_dict(await db_manager.fetch_one(
                "SELECT * FROM subscriptions WHERE user_id = :user_id",
                {"user_id": str(user_id)}
            ))
            
            # Get credit balance
            credits = _row_to_dict(await db_manager.fetch_one(
                "SELECT * FROM credit_balances WHERE user_id = :user_id",
                {"user_id": str(user_id)}
            ))
        except Exception as e:
            logger.error(f"Error fetching subscription: {e}")
            sub = None
            credits = None
        
        # Default values if no subscription exists
        if not sub:
            return SubscriptionStatus(
                user_id=user_id,
                tier="free",
                token_balance=0,
                is_subscribed=False,
                subscription_active=False,
                renews_at=None,
                auto_renew=False,
                posts_used_today=0,
                posts_limit=DAILY_LIMITS["free"]["posts"],
                ai_generations_today=0,
                ai_generations_limit=DAILY_LIMITS["free"]["ai_generations"],
                credits_balance=0,
                tokens_burned_total=0,
                can_auto_post=False,
                days_until_renewal=None,
                grace_period=False
            )
        
        tier = sub.get("tier", "free")
        limits = DAILY_LIMITS.get(tier, DAILY_LIMITS["free"])
        
        # Calculate days until renewal
        days_until_renewal = None
        renews_at = sub.get("renews_at")
        if renews_at:
            delta = renews_at - datetime.now()
            days_until_renewal = max(0, delta.days)
        
        # Check grace period
        grace_period = False
        grace_period_ends = sub.get("grace_period_ends")
        if grace_period_ends:
            grace_period = datetime.now() < grace_period_ends
        
        # Is subscription actually active?
        subscription_active = tier in ["premium", "agency"]
        if subscription_active and renews_at:
            subscription_active = datetime.now() < renews_at or grace_period
        
        return SubscriptionStatus(
            user_id=user_id,
            tier=tier,
            token_balance=sub.get("token_balance", 0),
            is_subscribed=tier in ["premium", "agency"],
            subscription_active=subscription_active,
            renews_at=renews_at,
            auto_renew=sub.get("auto_renew", False),
            posts_used_today=sub.get("posts_used_today", 0),
            posts_limit=limits["posts"],
            ai_generations_today=sub.get("ai_generations_today", 0),
            ai_generations_limit=limits["ai_generations"],
            credits_balance=credits.get("credits_balance", 0) if credits else 0,
            tokens_burned_total=sub.get("tokens_burned_total", 0),
            can_auto_post=tier in ["premium", "agency"] and subscription_active,
            days_until_renewal=days_until_renewal,
            grace_period=grace_period
        )
    
    async def get_or_create_subscription(self, user_id: UUID) -> dict:
        """Get or create subscription record for user"""
        try:
            sub = _row_to_dict(await db_manager.fetch_one(
                "SELECT * FROM subscriptions WHERE user_id = :user_id",
                {"user_id": str(user_id)}
            ))
            
            if not sub:
                # Create default subscription
                await db_manager.execute_query(
                    """INSERT INTO subscriptions (user_id, tier, posts_used_today, ai_generations_today)
                       VALUES (:user_id, 'free', 0, 0)
                       ON CONFLICT (user_id) DO NOTHING""",
                    {"user_id": str(user_id)}
                )
                sub = _row_to_dict(await db_manager.fetch_one(
                    "SELECT * FROM subscriptions WHERE user_id = :user_id",
                    {"user_id": str(user_id)}
                ))
            
            return sub or {"tier": "free", "token_balance": 0}
        except Exception as e:
            logger.error(f"Error in get_or_create_subscription: {e}")
            return {"tier": "free", "token_balance": 0}
    
    # =========================================================================
    # TIER MANAGEMENT
    # =========================================================================
    
    async def update_tier_from_balance(self, user_id: UUID, wallet_address: str) -> dict:
        """Update user's tier based on their current token balance"""
        try:
            # Get fresh balance from blockchain
            balance = await token_service.get_token_balance(wallet_address)
            token_balance = int(balance.ui_balance)
            
            # Get current subscription
            sub = await self.get_or_create_subscription(user_id)
            current_tier = sub.get("tier", "free")
            
            # Determine tier based on balance
            if token_balance >= MINIMUM_HOLD["agency"]:
                eligible_tier = "agency" if current_tier == "agency" else "basic"
            elif token_balance >= MINIMUM_HOLD["basic"]:
                eligible_tier = "basic"
            else:
                eligible_tier = "free"
            
            # If they have an active paid subscription, keep it
            if current_tier in ["premium", "agency"]:
                renews_at = sub.get("renews_at")
                if renews_at and datetime.now() < renews_at:
                    eligible_tier = current_tier
            
            # Update subscription
            await db_manager.execute_query(
                """UPDATE subscriptions 
                   SET token_balance = :token_balance, tier = :tier, updated_at = NOW()
                   WHERE user_id = :user_id""",
                {"token_balance": token_balance, "tier": eligible_tier, "user_id": str(user_id)}
            )
            
            logger.info(f"Updated tier for user {user_id}: {current_tier} -> {eligible_tier}")
            
            return {
                "previous_tier": current_tier,
                "new_tier": eligible_tier,
                "token_balance": token_balance,
            }
        except Exception as e:
            logger.error(f"Error updating tier: {e}")
            return {"error": str(e)}
    
    # =========================================================================
    # SUBSCRIPTION MANAGEMENT (BURNS)
    # =========================================================================
    
    async def subscribe(
        self,
        user_id: UUID,
        tier: Literal["premium", "agency"],
        wallet_address: str,
        auto_renew: bool = True
    ) -> dict:
        """Subscribe user to a paid tier"""
        if tier not in ["premium", "agency"]:
            return {"success": False, "error": "Invalid tier"}
        
        try:
            # Check balance
            balance = await token_service.get_token_balance(wallet_address)
            token_balance = int(balance.ui_balance)
            required_hold = MINIMUM_HOLD[tier]
            burn_amount = SUBSCRIPTION_BURN_AMOUNTS[tier]
            
            # Verify requirements
            if token_balance < required_hold:
                return {
                    "success": False,
                    "error": f"Insufficient balance. Need {required_hold} tokens, have {token_balance}"
                }
            
            if token_balance < required_hold + burn_amount:
                return {
                    "success": False,
                    "error": f"Need {required_hold + burn_amount} tokens total"
                }
            
            # Calculate renewal date (30 days from now)
            renews_at = datetime.now() + timedelta(days=30)
            
            # Update subscription
            await db_manager.execute_query(
                """INSERT INTO subscriptions (user_id, tier, started_at, renews_at, auto_renew, tokens_burned_total)
                   VALUES (:user_id, :tier, NOW(), :renews_at, :auto_renew, :burn_amount)
                   ON CONFLICT (user_id) DO UPDATE SET
                     tier = :tier,
                     started_at = COALESCE(subscriptions.started_at, NOW()),
                     renews_at = :renews_at,
                     auto_renew = :auto_renew,
                     tokens_burned_total = COALESCE(subscriptions.tokens_burned_total, 0) + :burn_amount,
                     updated_at = NOW()""",
                {
                    "user_id": str(user_id),
                    "tier": tier,
                    "renews_at": renews_at,
                    "auto_renew": auto_renew,
                    "burn_amount": burn_amount
                }
            )
            
            # Record the burn
            await self._record_burn(user_id, burn_amount, "subscription", tier)
            
            # Grant free credits
            await self._grant_monthly_credits(user_id, tier)
            
            logger.info(f"User {user_id} subscribed to {tier}. Burned {burn_amount} tokens.")
            
            return {
                "success": True,
                "tier": tier,
                "burn_amount": burn_amount,
                "renews_at": renews_at.isoformat(),
                "auto_renew": auto_renew,
            }
        except Exception as e:
            logger.error(f"Error subscribing: {e}")
            return {"success": False, "error": str(e)}
    
    async def cancel_subscription(self, user_id: UUID) -> dict:
        """Cancel auto-renewal"""
        try:
            await db_manager.execute_query(
                "UPDATE subscriptions SET auto_renew = FALSE, updated_at = NOW() WHERE user_id = :user_id",
                {"user_id": str(user_id)}
            )
            return {"success": True, "message": "Auto-renewal cancelled"}
        except Exception as e:
            logger.error(f"Error cancelling subscription: {e}")
            return {"success": False, "error": str(e)}
    
    # =========================================================================
    # USAGE TRACKING
    # =========================================================================
    
    async def check_daily_limit(self, user_id: UUID, limit_type: Literal["posts", "ai_generations"]) -> dict:
        """Check if user has remaining daily quota"""
        try:
            sub = await self.get_or_create_subscription(user_id)
            tier = sub.get("tier", "free")
            limits = DAILY_LIMITS.get(tier, DAILY_LIMITS["free"])
            limit = limits[limit_type]
            
            if limit_type == "posts":
                used = sub.get("posts_used_today", 0)
            else:
                used = sub.get("ai_generations_today", 0)
            
            if limit == -1:  # Unlimited
                return {"allowed": True, "used": used, "limit": -1, "remaining": -1}
            
            remaining = max(0, limit - used)
            
            return {
                "allowed": remaining > 0,
                "used": used,
                "limit": limit,
                "remaining": remaining
            }
        except Exception as e:
            logger.error(f"Error checking limit: {e}")
            return {"allowed": True, "used": 0, "limit": -1, "remaining": -1}
    
    async def increment_usage(self, user_id: UUID, limit_type: Literal["posts", "ai_generations"], amount: int = 1) -> dict:
        """Increment daily usage counter"""
        try:
            # Check limit first
            check = await self.check_daily_limit(user_id, limit_type)
            
            if not check["allowed"]:
                return {"success": False, "error": f"Daily {limit_type} limit reached", **check}
            
            column = "posts_used_today" if limit_type == "posts" else "ai_generations_today"
            
            await db_manager.execute_query(
                f"UPDATE subscriptions SET {column} = {column} + :amount, updated_at = NOW() WHERE user_id = :user_id",
                {"amount": amount, "user_id": str(user_id)}
            )
            
            return {
                "success": True,
                "used": check["used"] + amount,
                "limit": check["limit"],
                "remaining": check["remaining"] - amount if check["remaining"] != -1 else -1
            }
        except Exception as e:
            logger.error(f"Error incrementing usage: {e}")
            return {"success": False, "error": str(e)}
    
    # =========================================================================
    # CREDITS
    # =========================================================================
    
    async def get_credits(self, user_id: UUID) -> dict:
        """Get user's credit balance"""
        try:
            credits = _row_to_dict(await db_manager.fetch_one(
                "SELECT * FROM credit_balances WHERE user_id = :user_id",
                {"user_id": str(user_id)}
            ))
            
            if not credits:
                # Create credit balance record
                await db_manager.execute_query(
                    "INSERT INTO credit_balances (user_id, credits_balance, free_credits_remaining) VALUES (:user_id, 0, 0) ON CONFLICT DO NOTHING",
                    {"user_id": str(user_id)}
                )
                return {"credits_balance": 0, "credits_used_this_month": 0, "free_credits_remaining": 0}
            
            return credits
        except Exception as e:
            logger.error(f"Error getting credits: {e}")
            return {"credits_balance": 0, "credits_used_this_month": 0, "free_credits_remaining": 0}
    
    async def use_credits(self, user_id: UUID, amount: int, reason: str) -> dict:
        """Use credits for a feature"""
        try:
            credits = await self.get_credits(user_id)
            total_available = credits.get("credits_balance", 0) + credits.get("free_credits_remaining", 0)
            
            if total_available < amount:
                return {"success": False, "error": f"Insufficient credits. Need {amount}, have {total_available}", "remaining": total_available}
            
            free_to_use = min(credits.get("free_credits_remaining", 0), amount)
            paid_to_use = amount - free_to_use
            
            await db_manager.execute_query(
                """UPDATE credit_balances 
                   SET free_credits_remaining = free_credits_remaining - :free,
                       credits_balance = credits_balance - :paid,
                       credits_used_this_month = credits_used_this_month + :amount
                   WHERE user_id = :user_id""",
                {"free": free_to_use, "paid": paid_to_use, "amount": amount, "user_id": str(user_id)}
            )
            
            return {"success": True, "used": amount, "remaining": total_available - amount}
        except Exception as e:
            logger.error(f"Error using credits: {e}")
            return {"success": False, "error": str(e)}
    
    async def add_credits(self, user_id: UUID, amount: int, reason: str = "purchase") -> dict:
        """Add credits to user's balance"""
        try:
            await db_manager.execute_query(
                """INSERT INTO credit_balances (user_id, credits_balance)
                   VALUES (:user_id, :amount)
                   ON CONFLICT (user_id) DO UPDATE SET credits_balance = credit_balances.credits_balance + :amount""",
                {"user_id": str(user_id), "amount": amount}
            )
            credits = await self.get_credits(user_id)
            return {"success": True, "added": amount, "new_balance": credits.get("credits_balance", 0)}
        except Exception as e:
            logger.error(f"Error adding credits: {e}")
            return {"success": False, "error": str(e)}
    
    async def _grant_monthly_credits(self, user_id: UUID, tier: str):
        """Grant free monthly credits based on tier"""
        free_credits = FREE_CREDITS.get(tier, 0)
        if free_credits > 0:
            try:
                await db_manager.execute_query(
                    """INSERT INTO credit_balances (user_id, free_credits_remaining)
                       VALUES (:user_id, :credits)
                       ON CONFLICT (user_id) DO UPDATE SET free_credits_remaining = :credits, last_reset = NOW()""",
                    {"user_id": str(user_id), "credits": free_credits}
                )
            except Exception as e:
                logger.error(f"Error granting credits: {e}")
    
    # =========================================================================
    # BURN TRACKING
    # =========================================================================
    
    async def _record_burn(self, user_id: UUID, amount: int, reason: str, tier: Optional[str] = None, tx_signature: Optional[str] = None):
        """Record a token burn for transparency"""
        try:
            await db_manager.execute_query(
                """INSERT INTO token_burns (user_id, amount, reason, tier, tx_signature)
                   VALUES (:user_id, :amount, :reason, :tier, :tx_signature)""",
                {"user_id": str(user_id), "amount": amount, "reason": reason, "tier": tier, "tx_signature": tx_signature}
            )
        except Exception as e:
            logger.error(f"Error recording burn: {e}")
    
    async def get_burn_history(self, user_id: UUID, limit: int = 20) -> list:
        """Get user's burn history"""
        try:
            burns = await db_manager.fetch_all(
                "SELECT * FROM token_burns WHERE user_id = :user_id ORDER BY burned_at DESC LIMIT :limit",
                {"user_id": str(user_id), "limit": limit}
            )
            return [_row_to_dict(b) for b in (burns or [])]
        except Exception as e:
            logger.error(f"Error getting burn history: {e}")
            return []
    
    async def get_platform_burn_stats(self) -> dict:
        """Get platform-wide burn statistics"""
        try:
            stats = _row_to_dict(await db_manager.fetch_one(
                """SELECT 
                     COALESCE(SUM(amount), 0) as total_burned,
                     COUNT(*) as total_burns,
                     COUNT(DISTINCT user_id) as unique_burners
                   FROM token_burns"""
            ))
            return stats or {"total_burned": 0, "total_burns": 0, "unique_burners": 0}
        except Exception as e:
            logger.error(f"Error getting burn stats: {e}")
            return {"total_burned": 0, "total_burns": 0, "unique_burners": 0}
    
    # =========================================================================
    # FEATURE ACCESS CHECKS
    # =========================================================================
    
    async def can_use_feature(self, user_id: UUID, feature: str) -> dict:
        """Check if user can use a specific feature"""
        status = await self.get_subscription_status(user_id)
        
        feature_requirements = {
            "auto_post": ["premium", "agency"],
            "evergreen": ["premium", "agency"],
            "brand_voice": ["premium", "agency"],
            "thread_creator": ["premium", "agency"],
            "bulk_operations": ["premium", "agency"],
            "flows": ["premium", "agency"],
            "unlimited_flows": ["agency"],
            "multi_project": ["agency"],
            "white_label": ["agency"],
            "api_access": ["agency"],
            "onchain_triggers": ["agency"],
            "competitor_tracking": ["agency"],
            "ab_testing": ["agency"],
        }
        
        required_tiers = feature_requirements.get(feature, [])
        
        if not required_tiers:
            return {"allowed": True}
        
        if status.tier in required_tiers and status.subscription_active:
            return {"allowed": True}
        
        tier_order = ["free", "basic", "premium", "agency"]
        min_tier = required_tiers[0] if required_tiers else "premium"
        
        return {
            "allowed": False,
            "required_tier": min_tier,
            "current_tier": status.tier,
            "message": f"Upgrade to {min_tier} to unlock {feature}"
        }


# Singleton instance
subscription_service = SubscriptionService()
