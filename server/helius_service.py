"""
Helius Integration Service
Monitors on-chain events for automated posting flows
"""

import os
import logging
import asyncio
from typing import Optional, List, Callable
from datetime import datetime
from dataclasses import dataclass
import httpx
from enum import Enum

logger = logging.getLogger(__name__)

HELIUS_API_KEY = os.getenv("HELIUS_API_KEY", "")
HELIUS_BASE_URL = "https://api.helius.xyz/v0"
HELIUS_WEBHOOK_URL = os.getenv("HELIUS_WEBHOOK_URL", "")  # Your server's webhook endpoint


class TransactionType(str, Enum):
    """Supported transaction types to monitor"""
    ANY = "ANY"
    TRANSFER = "TRANSFER"
    SWAP = "SWAP"
    NFT_SALE = "NFT_SALE"
    NFT_MINT = "NFT_MINT"
    TOKEN_MINT = "TOKEN_MINT"
    STAKE = "STAKE"
    BURN = "BURN"


class WebhookType(str, Enum):
    """Helius webhook types"""
    ENHANCED = "enhanced"
    RAW = "raw"
    DISCORD = "discord"


@dataclass
class WebhookConfig:
    """Configuration for a Helius webhook"""
    webhook_url: str
    transaction_types: List[TransactionType]
    account_addresses: List[str]
    webhook_type: WebhookType = WebhookType.ENHANCED
    auth_header: Optional[str] = None


@dataclass
class OnChainEvent:
    """Parsed on-chain event"""
    event_type: str
    signature: str
    timestamp: datetime
    accounts: List[str]
    amount: Optional[float]
    token_mint: Optional[str]
    raw_data: dict


class HeliusService:
    """Service for Helius webhook management and on-chain monitoring"""
    
    def __init__(self):
        self.api_key = HELIUS_API_KEY
        self.base_url = HELIUS_BASE_URL
        self._event_handlers: dict[str, List[Callable]] = {}
    
    def _get_headers(self) -> dict:
        """Get headers for Helius API requests"""
        return {
            "Content-Type": "application/json"
        }
    
    async def create_webhook(
        self,
        config: WebhookConfig,
        project_id: str
    ) -> dict:
        """
        Create a new Helius webhook for monitoring addresses
        
        Args:
            config: Webhook configuration
            project_id: Project ID for reference
            
        Returns:
            Webhook creation response with webhook ID
        """
        if not self.api_key:
            logger.warning("Helius API key not configured")
            return {"error": "Helius API key not configured"}
        
        try:
            async with httpx.AsyncClient() as client:
                payload = {
                    "webhookURL": config.webhook_url,
                    "transactionTypes": [t.value for t in config.transaction_types],
                    "accountAddresses": config.account_addresses,
                    "webhookType": config.webhook_type.value,
                }
                
                if config.auth_header:
                    payload["authHeader"] = config.auth_header
                
                response = await client.post(
                    f"{self.base_url}/webhooks?api-key={self.api_key}",
                    json=payload,
                    headers=self._get_headers(),
                    timeout=30.0
                )
                response.raise_for_status()
                result = response.json()
                
                logger.info(f"Created webhook {result.get('webhookID')} for project {project_id}")
                return result
                
        except httpx.HTTPError as e:
            logger.error(f"Failed to create webhook: {e}")
            return {"error": str(e)}
    
    async def delete_webhook(self, webhook_id: str) -> bool:
        """Delete a Helius webhook"""
        if not self.api_key:
            return False
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    f"{self.base_url}/webhooks/{webhook_id}?api-key={self.api_key}",
                    headers=self._get_headers(),
                    timeout=30.0
                )
                response.raise_for_status()
                logger.info(f"Deleted webhook {webhook_id}")
                return True
                
        except httpx.HTTPError as e:
            logger.error(f"Failed to delete webhook: {e}")
            return False
    
    async def list_webhooks(self) -> List[dict]:
        """List all webhooks for this API key"""
        if not self.api_key:
            return []
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/webhooks?api-key={self.api_key}",
                    headers=self._get_headers(),
                    timeout=30.0
                )
                response.raise_for_status()
                return response.json()
                
        except httpx.HTTPError as e:
            logger.error(f"Failed to list webhooks: {e}")
            return []
    
    async def update_webhook(
        self,
        webhook_id: str,
        account_addresses: Optional[List[str]] = None,
        transaction_types: Optional[List[TransactionType]] = None
    ) -> dict:
        """Update an existing webhook"""
        if not self.api_key:
            return {"error": "Helius API key not configured"}
        
        try:
            async with httpx.AsyncClient() as client:
                payload = {}
                if account_addresses:
                    payload["accountAddresses"] = account_addresses
                if transaction_types:
                    payload["transactionTypes"] = [t.value for t in transaction_types]
                
                response = await client.put(
                    f"{self.base_url}/webhooks/{webhook_id}?api-key={self.api_key}",
                    json=payload,
                    headers=self._get_headers(),
                    timeout=30.0
                )
                response.raise_for_status()
                return response.json()
                
        except httpx.HTTPError as e:
            logger.error(f"Failed to update webhook: {e}")
            return {"error": str(e)}
    
    def parse_webhook_event(self, raw_event: dict) -> OnChainEvent:
        """Parse raw webhook payload into OnChainEvent"""
        try:
            # Handle enhanced transaction format
            event_type = raw_event.get("type", "UNKNOWN")
            signature = raw_event.get("signature", "")
            timestamp = datetime.fromtimestamp(raw_event.get("timestamp", 0))
            
            # Extract account addresses
            accounts = []
            account_data = raw_event.get("accountData", [])
            for acc in account_data:
                if isinstance(acc, dict):
                    accounts.append(acc.get("account", ""))
                elif isinstance(acc, str):
                    accounts.append(acc)
            
            # Extract amount if transfer
            amount = None
            token_mint = None
            
            if event_type == "TRANSFER":
                native_transfers = raw_event.get("nativeTransfers", [])
                if native_transfers:
                    amount = native_transfers[0].get("amount", 0) / 1e9  # lamports to SOL
                
                token_transfers = raw_event.get("tokenTransfers", [])
                if token_transfers:
                    amount = token_transfers[0].get("tokenAmount", 0)
                    token_mint = token_transfers[0].get("mint", "")
            
            return OnChainEvent(
                event_type=event_type,
                signature=signature,
                timestamp=timestamp,
                accounts=accounts,
                amount=amount,
                token_mint=token_mint,
                raw_data=raw_event
            )
            
        except Exception as e:
            logger.error(f"Failed to parse webhook event: {e}")
            return OnChainEvent(
                event_type="PARSE_ERROR",
                signature="",
                timestamp=datetime.now(),
                accounts=[],
                amount=None,
                token_mint=None,
                raw_data=raw_event
            )
    
    def register_handler(self, event_type: str, handler: Callable):
        """Register a handler for a specific event type"""
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        self._event_handlers[event_type].append(handler)
    
    async def process_event(self, event: OnChainEvent):
        """Process an event through registered handlers"""
        handlers = self._event_handlers.get(event.event_type, [])
        handlers.extend(self._event_handlers.get("ANY", []))
        
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                logger.error(f"Handler error for {event.event_type}: {e}")
    
    async def get_token_price(self, token_mint: str) -> Optional[float]:
        """
        Get token price from Jupiter/Birdeye via Helius DAS API
        """
        if not self.api_key:
            return None
        
        try:
            async with httpx.AsyncClient() as client:
                # Use Jupiter price API (free)
                response = await client.get(
                    f"https://price.jup.ag/v4/price?ids={token_mint}",
                    timeout=10.0
                )
                response.raise_for_status()
                data = response.json()
                
                if token_mint in data.get("data", {}):
                    return data["data"][token_mint].get("price")
                
                return None
                
        except Exception as e:
            logger.error(f"Failed to get token price: {e}")
            return None
    
    async def get_holder_count(self, token_mint: str) -> Optional[int]:
        """Get approximate holder count for a token"""
        if not self.api_key:
            return None
        
        try:
            async with httpx.AsyncClient() as client:
                # Use Helius DAS API for token info
                payload = {
                    "jsonrpc": "2.0",
                    "id": "holder-count",
                    "method": "getAsset",
                    "params": {"id": token_mint}
                }
                
                response = await client.post(
                    f"https://mainnet.helius-rpc.com/?api-key={self.api_key}",
                    json=payload,
                    timeout=30.0
                )
                response.raise_for_status()
                data = response.json()
                
                # Note: This doesn't directly give holder count
                # For accurate holder count, you'd need to use getTokenLargestAccounts
                # and sum up or use a dedicated API
                
                return None  # Placeholder
                
        except Exception as e:
            logger.error(f"Failed to get holder count: {e}")
            return None


# Singleton instance
helius_service = HeliusService()


# Event type constants for flows
class FlowTrigger:
    """Constants for flow trigger types"""
    PRICE_ABOVE = "price_above"
    PRICE_BELOW = "price_below"
    HOLDER_MILESTONE = "holder_milestone"
    WHALE_TRANSFER = "whale_transfer"  # Large transfer detected
    NEW_HOLDER = "new_holder"
    LIQUIDITY_CHANGE = "liquidity_change"
    MARKET_CAP_MILESTONE = "market_cap_milestone"
    TIME_BASED = "time_based"  # Scheduled posts
