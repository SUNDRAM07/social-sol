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

from database import Database
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
        self.db = Database()
    
    # =========================================================================
    # SUBSCRIPTION STATUS
    # =========================================================================
    
    async def get_subscription_status(self, user_id: UUID) -> SubscriptionStatus:
        """
        Get complete subscription status for a user
        Includes tier, limits, usage, and renewal info
        """
        # Get subscription record
        sub = await self.db.fetch_one(
            """
            SELECT * FROM subscriptions WHERE user_id = $1
            """,
            str(user_id)
        )
        
        # Get credit balance
        credits = await self.db.fetch_one(
            """
            SELECT * FROM credit_balances WHERE user_id = $1
            """,
            str(user_id)
        )
        
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
        
        tier = sub["tier"]
        limits = DAILY_LIMITS.get(tier, DAILY_LIMITS["free"])
        
        # Calculate days until renewal
        days_until_renewal = None
        if sub["renews_at"]:
            delta = sub["renews_at"] - datetime.now()
            days_until_renewal = max(0, delta.days)
        
        # Check grace period
        grace_period = False
        if sub.get("grace_period_ends"):
            grace_period = datetime.now() < sub["grace_period_ends"]
        
        # Is subscription actually active?
        subscription_active = tier in ["premium", "agency"]
        if subscription_active and sub["renews_at"]:
            subscription_active = datetime.now() < sub["renews_at"] or grace_period
        
        return SubscriptionStatus(
            user_id=user_id,
            tier=tier,
            token_balance=sub.get("token_balance", 0),
            is_subscribed=tier in ["premium", "agency"],
            subscription_active=subscription_active,
            renews_at=sub.get("renews_at"),
            auto_renew=sub.get("auto_renew", False),
            posts_used_today=sub.get("posts_used_today", 0),
            posts_limit=limits["posts"],
            ai_generations_today=sub.get("ai_generations_today", 0),
            ai_generations_limit=limits["ai_generations"],
            credits_balance=credits["credits_balance"] if credits else 0,
            tokens_burned_total=sub.get("tokens_burned_total", 0),
            can_auto_post=tier in ["premium", "agency"] and subscription_active,
            days_until_renewal=days_until_renewal,
            grace_period=grace_period
        )
    
    async def get_or_create_subscription(self, user_id: UUID) -> dict:
        """Get or create subscription record for user"""
        sub = await self.db.fetch_one(
            "SELECT * FROM subscriptions WHERE user_id = $1",
            str(user_id)
        )
        
        if not sub:
            # Create default subscription
            await self.db.execute(
                """
                INSERT INTO subscriptions (user_id, tier, posts_used_today, ai_generations_today)
                VALUES ($1, 'free', 0, 0)
                """,
                str(user_id)
            )
            sub = await self.db.fetch_one(
                "SELECT * FROM subscriptions WHERE user_id = $1",
                str(user_id)
            )
        
        return dict(sub)
    
    # =========================================================================
    # TIER MANAGEMENT
    # =========================================================================
    
    async def update_tier_from_balance(
        self, 
        user_id: UUID, 
        wallet_address: str
    ) -> dict:
        """
        Update user's tier based on their current token balance
        Called after wallet verification or balance check
        """
        # Get fresh balance from blockchain
        balance = await token_service.get_token_balance(wallet_address)
        token_balance = int(balance.ui_balance)
        
        # Get current subscription
        sub = await self.get_or_create_subscription(user_id)
        current_tier = sub["tier"]
        
        # Determine tier based on balance
        # Note: For premium/agency, user must also have active subscription
        if token_balance >= MINIMUM_HOLD["agency"]:
            eligible_tier = "agency" if current_tier == "agency" else "basic"
        elif token_balance >= MINIMUM_HOLD["basic"]:
            eligible_tier = "basic"
        else:
            eligible_tier = "free"
        
        # If they have an active paid subscription, keep it
        if current_tier in ["premium", "agency"]:
            if sub.get("renews_at") and datetime.now() < sub["renews_at"]:
                eligible_tier = current_tier
        
        # Update subscription
        await self.db.execute(
            """
            UPDATE subscriptions 
            SET token_balance = $1, tier = $2, updated_at = NOW()
            WHERE user_id = $3
            """,
            token_balance, eligible_tier, str(user_id)
        )
        
        logger.info(f"Updated tier for user {user_id}: {current_tier} -> {eligible_tier} (balance: {token_balance})")
        
        return {
            "previous_tier": current_tier,
            "new_tier": eligible_tier,
            "token_balance": token_balance,
            "can_upgrade_to": self._get_upgrade_options(eligible_tier, token_balance)
        }
    
    def _get_upgrade_options(self, current_tier: str, balance: int) -> list[dict]:
        """Get available upgrade options for user"""
        options = []
        
        if current_tier == "free":
            options.append({
                "tier": "basic",
                "required_hold": MINIMUM_HOLD["basic"],
                "monthly_burn": 0,
                "tokens_needed": max(0, MINIMUM_HOLD["basic"] - balance),
                "description": "Hold 100 $SOCIAL for Basic access"
            })
        
        if current_tier in ["free", "basic"]:
            options.append({
                "tier": "premium",
                "required_hold": MINIMUM_HOLD["premium"],
                "monthly_burn": SUBSCRIPTION_BURN_AMOUNTS["premium"],
                "tokens_needed": max(0, MINIMUM_HOLD["premium"] - balance),
                "description": "Hold 100 + burn 25/month for Premium"
            })
        
        if current_tier in ["free", "basic", "premium"]:
            options.append({
                "tier": "agency",
                "required_hold": MINIMUM_HOLD["agency"],
                "monthly_burn": SUBSCRIPTION_BURN_AMOUNTS["agency"],
                "tokens_needed": max(0, MINIMUM_HOLD["agency"] - balance),
                "description": "Hold 500 + burn 100/month for Agency"
            })
        
        return options
    
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
        """
        Subscribe user to a paid tier
        This will record the burn (actual blockchain burn done separately)
        """
        if tier not in ["premium", "agency"]:
            return {"success": False, "error": "Invalid tier"}
        
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
        
        # Check if they have enough for the burn (after holding)
        if token_balance < required_hold + burn_amount:
            return {
                "success": False,
                "error": f"Need {required_hold + burn_amount} tokens total ({required_hold} to hold + {burn_amount} to burn)"
            }
        
        # Calculate renewal date (30 days from now)
        renews_at = datetime.now() + timedelta(days=30)
        
        # Update subscription
        await self.db.execute(
            """
            UPDATE subscriptions 
            SET tier = $1, 
                started_at = COALESCE(started_at, NOW()),
                renews_at = $2,
                auto_renew = $3,
                tokens_burned_total = COALESCE(tokens_burned_total, 0) + $4,
                updated_at = NOW()
            WHERE user_id = $5
            """,
            tier, renews_at, auto_renew, burn_amount, str(user_id)
        )
        
        # Record the burn
        await self._record_burn(user_id, burn_amount, "subscription", tier)
        
        # Grant free credits for the month
        await self._grant_monthly_credits(user_id, tier)
        
        logger.info(f"User {user_id} subscribed to {tier}. Burned {burn_amount} tokens.")
        
        return {
            "success": True,
            "tier": tier,
            "burn_amount": burn_amount,
            "renews_at": renews_at.isoformat(),
            "auto_renew": auto_renew,
            "message": f"Successfully subscribed to {tier}! {burn_amount} tokens will be burned."
        }
    
    async def cancel_subscription(self, user_id: UUID) -> dict:
        """
        Cancel auto-renewal (subscription stays active until renewal date)
        """
        sub = await self.get_or_create_subscription(user_id)
        
        if sub["tier"] not in ["premium", "agency"]:
            return {"success": False, "error": "No active subscription"}
        
        await self.db.execute(
            """
            UPDATE subscriptions 
            SET auto_renew = FALSE, updated_at = NOW()
            WHERE user_id = $1
            """,
            str(user_id)
        )
        
        return {
            "success": True,
            "message": f"Auto-renewal cancelled. Your {sub['tier']} subscription will remain active until {sub['renews_at']}"
        }
    
    async def process_renewal(self, user_id: UUID, wallet_address: str) -> dict:
        """
        Process subscription renewal
        Called by background job or manually
        """
        sub = await self.get_or_create_subscription(user_id)
        
        if sub["tier"] not in ["premium", "agency"]:
            return {"success": False, "error": "No subscription to renew"}
        
        if not sub.get("auto_renew"):
            return {"success": False, "error": "Auto-renewal disabled"}
        
        # Check if it's time to renew
        if sub.get("renews_at") and datetime.now() < sub["renews_at"]:
            return {"success": False, "error": "Not yet due for renewal"}
        
        # Check balance
        balance = await token_service.get_token_balance(wallet_address)
        token_balance = int(balance.ui_balance)
        tier = sub["tier"]
        burn_amount = SUBSCRIPTION_BURN_AMOUNTS[tier]
        required_hold = MINIMUM_HOLD[tier]
        
        if token_balance < required_hold + burn_amount:
            # Enter grace period
            grace_period_ends = datetime.now() + timedelta(days=3)
            await self.db.execute(
                """
                UPDATE subscriptions 
                SET grace_period_ends = $1, updated_at = NOW()
                WHERE user_id = $2
                """,
                grace_period_ends, str(user_id)
            )
            return {
                "success": False,
                "error": "Insufficient balance for renewal",
                "grace_period_ends": grace_period_ends.isoformat(),
                "tokens_needed": required_hold + burn_amount - token_balance
            }
        
        # Process renewal
        new_renews_at = datetime.now() + timedelta(days=30)
        
        await self.db.execute(
            """
            UPDATE subscriptions 
            SET renews_at = $1,
                tokens_burned_total = tokens_burned_total + $2,
                grace_period_ends = NULL,
                updated_at = NOW()
            WHERE user_id = $3
            """,
            new_renews_at, burn_amount, str(user_id)
        )
        
        # Record burn
        await self._record_burn(user_id, burn_amount, "subscription", tier)
        
        # Grant new month's credits
        await self._grant_monthly_credits(user_id, tier)
        
        logger.info(f"Renewed {tier} subscription for user {user_id}")
        
        return {
            "success": True,
            "tier": tier,
            "burn_amount": burn_amount,
            "renews_at": new_renews_at.isoformat()
        }
    
    async def downgrade_expired(self, user_id: UUID) -> dict:
        """
        Downgrade user from paid tier after grace period
        Called by background job
        """
        sub = await self.get_or_create_subscription(user_id)
        
        if sub["tier"] not in ["premium", "agency"]:
            return {"success": False, "error": "Not on a paid tier"}
        
        # Check grace period
        if sub.get("grace_period_ends") and datetime.now() < sub["grace_period_ends"]:
            return {"success": False, "error": "Still in grace period"}
        
        # Downgrade to basic (they still hold tokens)
        await self.db.execute(
            """
            UPDATE subscriptions 
            SET tier = 'basic',
                renews_at = NULL,
                auto_renew = FALSE,
                grace_period_ends = NULL,
                updated_at = NOW()
            WHERE user_id = $1
            """,
            str(user_id)
        )
        
        logger.info(f"Downgraded user {user_id} to basic tier")
        
        return {
            "success": True,
            "previous_tier": sub["tier"],
            "new_tier": "basic"
        }
    
    # =========================================================================
    # USAGE TRACKING
    # =========================================================================
    
    async def check_daily_limit(
        self,
        user_id: UUID,
        limit_type: Literal["posts", "ai_generations"]
    ) -> dict:
        """
        Check if user has remaining daily quota
        Returns: {"allowed": bool, "used": int, "limit": int, "remaining": int}
        """
        sub = await self.get_or_create_subscription(user_id)
        tier = sub["tier"]
        limits = DAILY_LIMITS.get(tier, DAILY_LIMITS["free"])
        limit = limits[limit_type]
        
        # Reset if needed
        await self._check_daily_reset(user_id, sub)
        
        # Get fresh usage
        sub = await self.db.fetch_one(
            "SELECT * FROM subscriptions WHERE user_id = $1",
            str(user_id)
        )
        
        if limit_type == "posts":
            used = sub.get("posts_used_today", 0)
        else:
            used = sub.get("ai_generations_today", 0)
        
        if limit == -1:  # Unlimited
            return {
                "allowed": True,
                "used": used,
                "limit": -1,
                "remaining": -1
            }
        
        remaining = max(0, limit - used)
        
        return {
            "allowed": remaining > 0,
            "used": used,
            "limit": limit,
            "remaining": remaining
        }
    
    async def increment_usage(
        self,
        user_id: UUID,
        limit_type: Literal["posts", "ai_generations"],
        amount: int = 1
    ) -> dict:
        """Increment daily usage counter"""
        # Check limit first
        check = await self.check_daily_limit(user_id, limit_type)
        
        if not check["allowed"]:
            return {
                "success": False,
                "error": f"Daily {limit_type} limit reached",
                **check
            }
        
        column = "posts_used_today" if limit_type == "posts" else "ai_generations_today"
        
        await self.db.execute(
            f"""
            UPDATE subscriptions 
            SET {column} = {column} + $1, updated_at = NOW()
            WHERE user_id = $2
            """,
            amount, str(user_id)
        )
        
        return {
            "success": True,
            "used": check["used"] + amount,
            "limit": check["limit"],
            "remaining": check["remaining"] - amount if check["remaining"] != -1 else -1
        }
    
    async def _check_daily_reset(self, user_id: UUID, sub: dict):
        """Reset daily counters if needed"""
        last_reset = sub.get("last_post_reset")
        
        if last_reset and last_reset.date() < datetime.now().date():
            await self.db.execute(
                """
                UPDATE subscriptions 
                SET posts_used_today = 0, 
                    ai_generations_today = 0,
                    last_post_reset = NOW()
                WHERE user_id = $1
                """,
                str(user_id)
            )
    
    # =========================================================================
    # CREDITS
    # =========================================================================
    
    async def get_credits(self, user_id: UUID) -> dict:
        """Get user's credit balance"""
        credits = await self.db.fetch_one(
            "SELECT * FROM credit_balances WHERE user_id = $1",
            str(user_id)
        )
        
        if not credits:
            # Create credit balance record
            await self.db.execute(
                """
                INSERT INTO credit_balances (user_id, credits_balance, free_credits_remaining)
                VALUES ($1, 0, 0)
                """,
                str(user_id)
            )
            return {
                "credits_balance": 0,
                "credits_used_this_month": 0,
                "free_credits_remaining": 0
            }
        
        return dict(credits)
    
    async def use_credits(self, user_id: UUID, amount: int, reason: str) -> dict:
        """
        Use credits for a feature
        Returns: {"success": bool, "remaining": int, "error": str?}
        """
        credits = await self.get_credits(user_id)
        total_available = credits["credits_balance"] + credits.get("free_credits_remaining", 0)
        
        if total_available < amount:
            return {
                "success": False,
                "error": f"Insufficient credits. Need {amount}, have {total_available}",
                "remaining": total_available
            }
        
        # Use free credits first, then paid credits
        free_to_use = min(credits.get("free_credits_remaining", 0), amount)
        paid_to_use = amount - free_to_use
        
        await self.db.execute(
            """
            UPDATE credit_balances 
            SET free_credits_remaining = free_credits_remaining - $1,
                credits_balance = credits_balance - $2,
                credits_used_this_month = credits_used_this_month + $3
            WHERE user_id = $4
            """,
            free_to_use, paid_to_use, amount, str(user_id)
        )
        
        logger.info(f"User {user_id} used {amount} credits for {reason}")
        
        return {
            "success": True,
            "used": amount,
            "remaining": total_available - amount
        }
    
    async def add_credits(self, user_id: UUID, amount: int, reason: str = "purchase") -> dict:
        """Add credits to user's balance (from token burn)"""
        await self.db.execute(
            """
            INSERT INTO credit_balances (user_id, credits_balance)
            VALUES ($1, $2)
            ON CONFLICT (user_id) 
            DO UPDATE SET credits_balance = credit_balances.credits_balance + $2
            """,
            str(user_id), amount
        )
        
        credits = await self.get_credits(user_id)
        
        return {
            "success": True,
            "added": amount,
            "new_balance": credits["credits_balance"]
        }
    
    async def _grant_monthly_credits(self, user_id: UUID, tier: str):
        """Grant free monthly credits based on tier"""
        free_credits = FREE_CREDITS.get(tier, 0)
        
        if free_credits > 0:
            await self.db.execute(
                """
                INSERT INTO credit_balances (user_id, free_credits_remaining)
                VALUES ($1, $2)
                ON CONFLICT (user_id) 
                DO UPDATE SET free_credits_remaining = $2, last_reset = NOW()
                """,
                str(user_id), free_credits
            )
    
    # =========================================================================
    # BURN TRACKING
    # =========================================================================
    
    async def _record_burn(
        self,
        user_id: UUID,
        amount: int,
        reason: str,
        tier: Optional[str] = None,
        tx_signature: Optional[str] = None
    ):
        """Record a token burn for transparency"""
        await self.db.execute(
            """
            INSERT INTO token_burns (user_id, amount, reason, tier, tx_signature)
            VALUES ($1, $2, $3, $4, $5)
            """,
            str(user_id), amount, reason, tier, tx_signature
        )
    
    async def get_burn_history(self, user_id: UUID, limit: int = 20) -> list[dict]:
        """Get user's burn history"""
        burns = await self.db.fetch_many(
            """
            SELECT * FROM token_burns 
            WHERE user_id = $1 
            ORDER BY burned_at DESC 
            LIMIT $2
            """,
            str(user_id), limit
        )
        return [dict(b) for b in burns]
    
    async def get_platform_burn_stats(self) -> dict:
        """Get platform-wide burn statistics for transparency dashboard"""
        stats = await self.db.fetch_one(
            """
            SELECT 
                SUM(amount) as total_burned,
                COUNT(*) as total_burns,
                COUNT(DISTINCT user_id) as unique_burners
            FROM token_burns
            """
        )
        
        monthly = await self.db.fetch_many(
            """
            SELECT * FROM platform_burn_stats LIMIT 12
            """
        )
        
        return {
            "total_burned": stats["total_burned"] or 0,
            "total_burns": stats["total_burns"] or 0,
            "unique_burners": stats["unique_burners"] or 0,
            "monthly_breakdown": [dict(m) for m in monthly]
        }
    
    # =========================================================================
    # FEATURE ACCESS CHECKS
    # =========================================================================
    
    async def can_use_feature(
        self,
        user_id: UUID,
        feature: str
    ) -> dict:
        """
        Check if user can use a specific feature
        Features: auto_post, evergreen, brand_voice, flows, competitor_tracking, etc.
        """
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
            # Feature available to all
            return {"allowed": True}
        
        if status.tier in required_tiers and status.subscription_active:
            return {"allowed": True}
        
        # Find minimum tier needed
        tier_order = ["free", "basic", "premium", "agency"]
        min_tier = None
        for t in required_tiers:
            if min_tier is None or tier_order.index(t) < tier_order.index(min_tier):
                min_tier = t
        
        return {
            "allowed": False,
            "required_tier": min_tier,
            "current_tier": status.tier,
            "message": f"Upgrade to {min_tier} to unlock {feature}"
        }


# Singleton instance
subscription_service = SubscriptionService()
