"""
Solana Token Balance Service
Checks user's $SOCIAL token balance via Solana RPC
"""

import os
import logging
import asyncio
from typing import Optional
from datetime import datetime, timedelta
import httpx
from dataclasses import dataclass

from subscription_tiers import (
    SOCIAL_TOKEN_MINT,
    TierLevel,
    get_tier_from_balance,
    get_tier_features,
    TIER_CONFIG,
    TIER_THRESHOLDS
)

logger = logging.getLogger(__name__)

# Solana RPC endpoints (use Helius for better rate limits)
SOLANA_RPC_URL = os.getenv("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com")
HELIUS_API_KEY = os.getenv("HELIUS_API_KEY", "")

# Cache settings
BALANCE_CACHE_MINUTES = 5


@dataclass
class TokenBalance:
    """Token balance result"""
    wallet_address: str
    token_mint: str
    balance: int  # Raw balance (with decimals)
    ui_balance: float  # Human-readable balance
    decimals: int
    tier: TierLevel
    features: dict
    last_checked: datetime


class TokenService:
    """Service for checking Solana token balances"""
    
    def __init__(self):
        self.rpc_url = self._get_rpc_url()
        self._balance_cache: dict[str, TokenBalance] = {}
    
    def _get_rpc_url(self) -> str:
        """Get the best available RPC URL"""
        if HELIUS_API_KEY:
            return f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"
        return SOLANA_RPC_URL
    
    async def get_token_balance(
        self,
        wallet_address: str,
        token_mint: str = SOCIAL_TOKEN_MINT,
        use_cache: bool = True
    ) -> TokenBalance:
        """
        Get token balance for a wallet
        
        Args:
            wallet_address: Solana wallet address
            token_mint: SPL token mint address
            use_cache: Whether to use cached balance
            
        Returns:
            TokenBalance with balance and tier info
        """
        cache_key = f"{wallet_address}:{token_mint}"
        
        # Check cache
        if use_cache and cache_key in self._balance_cache:
            cached = self._balance_cache[cache_key]
            if datetime.now() - cached.last_checked < timedelta(minutes=BALANCE_CACHE_MINUTES):
                logger.info(f"Using cached balance for {wallet_address[:8]}...")
                return cached
        
        try:
            balance_info = await self._fetch_token_balance(wallet_address, token_mint)
            
            # Calculate tier based on balance
            tier = get_tier_from_balance(int(balance_info["ui_balance"]))
            features = get_tier_features(tier)
            
            result = TokenBalance(
                wallet_address=wallet_address,
                token_mint=token_mint,
                balance=balance_info["balance"],
                ui_balance=balance_info["ui_balance"],
                decimals=balance_info["decimals"],
                tier=tier,
                features=features.__dict__,
                last_checked=datetime.now()
            )
            
            # Cache result
            self._balance_cache[cache_key] = result
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get token balance: {e}")
            # Return free tier on error
            return TokenBalance(
                wallet_address=wallet_address,
                token_mint=token_mint,
                balance=0,
                ui_balance=0.0,
                decimals=9,
                tier=TierLevel.FREE,
                features=TIER_CONFIG[TierLevel.FREE].__dict__,
                last_checked=datetime.now()
            )
    
    async def _fetch_token_balance(
        self,
        wallet_address: str,
        token_mint: str
    ) -> dict:
        """Fetch token balance from Solana RPC"""
        
        async with httpx.AsyncClient() as client:
            # Get token accounts by owner
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getTokenAccountsByOwner",
                "params": [
                    wallet_address,
                    {"mint": token_mint},
                    {"encoding": "jsonParsed"}
                ]
            }
            
            response = await client.post(
                self.rpc_url,
                json=payload,
                timeout=30.0
            )
            response.raise_for_status()
            data = response.json()
            
            if "error" in data:
                raise Exception(f"RPC error: {data['error']}")
            
            accounts = data.get("result", {}).get("value", [])
            
            if not accounts:
                # No token account = 0 balance
                return {
                    "balance": 0,
                    "ui_balance": 0.0,
                    "decimals": 9
                }
            
            # Get the first (usually only) token account
            token_account = accounts[0]
            parsed_info = token_account["account"]["data"]["parsed"]["info"]
            token_amount = parsed_info["tokenAmount"]
            
            return {
                "balance": int(token_amount["amount"]),
                "ui_balance": float(token_amount["uiAmount"] or 0),
                "decimals": token_amount["decimals"]
            }
    
    async def get_sol_balance(self, wallet_address: str) -> float:
        """Get SOL balance for a wallet"""
        async with httpx.AsyncClient() as client:
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getBalance",
                "params": [wallet_address]
            }
            
            response = await client.post(
                self.rpc_url,
                json=payload,
                timeout=30.0
            )
            response.raise_for_status()
            data = response.json()
            
            if "error" in data:
                raise Exception(f"RPC error: {data['error']}")
            
            lamports = data.get("result", {}).get("value", 0)
            return lamports / 1_000_000_000  # Convert lamports to SOL
    
    async def check_tier_eligibility(
        self,
        wallet_address: str,
        required_tier: TierLevel
    ) -> dict:
        """
        Check if wallet is eligible for a specific tier
        
        Returns:
            {
                "eligible": bool,
                "current_tier": str,
                "required_tier": str,
                "current_balance": float,
                "required_balance": int,
                "tokens_needed": int
            }
        """
        balance = await self.get_token_balance(wallet_address)
        required_balance = TIER_THRESHOLDS[required_tier]
        
        return {
            "eligible": balance.tier.value >= required_tier.value or balance.ui_balance >= required_balance,
            "current_tier": balance.tier.value,
            "required_tier": required_tier.value,
            "current_balance": balance.ui_balance,
            "required_balance": required_balance,
            "tokens_needed": max(0, required_balance - int(balance.ui_balance))
        }
    
    def clear_cache(self, wallet_address: Optional[str] = None):
        """Clear balance cache for a wallet or all wallets"""
        if wallet_address:
            keys_to_remove = [k for k in self._balance_cache if k.startswith(wallet_address)]
            for key in keys_to_remove:
                del self._balance_cache[key]
        else:
            self._balance_cache.clear()


# Singleton instance
token_service = TokenService()


# Convenience functions
async def get_user_tier(wallet_address: str) -> TierLevel:
    """Quick helper to get user's tier"""
    balance = await token_service.get_token_balance(wallet_address)
    return balance.tier


async def check_feature_limit(
    wallet_address: str,
    feature: str,
    current_usage: int = 0
) -> dict:
    """Check if user can use a feature based on their tier"""
    from subscription_tiers import check_feature_access
    
    balance = await token_service.get_token_balance(wallet_address)
    return check_feature_access(balance.tier, feature, current_usage)
