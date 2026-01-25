"""
Flow Service - Automation flow management for SocialAnywhere
Handles WHEN → IF → DO automation logic with Helius webhook integration
"""

import logging
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from uuid import UUID
import asyncio

from database import db_manager

logger = logging.getLogger(__name__)

# ============================================
# TRIGGER TYPES
# ============================================

TRIGGER_TYPES = {
    # On-Chain Triggers (Agency only)
    "price_above": {
        "name": "Price Above",
        "description": "When token price goes above a threshold",
        "tier": "AGENCY",
        "category": "onchain",
        "config_schema": {
            "token_address": {"type": "string", "required": True},
            "threshold": {"type": "number", "required": True},
            "currency": {"type": "string", "default": "USD"}
        }
    },
    "price_below": {
        "name": "Price Below", 
        "description": "When token price drops below a threshold",
        "tier": "AGENCY",
        "category": "onchain",
        "config_schema": {
            "token_address": {"type": "string", "required": True},
            "threshold": {"type": "number", "required": True},
            "currency": {"type": "string", "default": "USD"}
        }
    },
    "holder_milestone": {
        "name": "Holder Milestone",
        "description": "When holder count reaches a milestone",
        "tier": "AGENCY", 
        "category": "onchain",
        "config_schema": {
            "token_address": {"type": "string", "required": True},
            "milestone": {"type": "number", "required": True}
        }
    },
    "whale_transfer": {
        "name": "Whale Transfer",
        "description": "When a large transaction is detected",
        "tier": "AGENCY",
        "category": "onchain",
        "config_schema": {
            "token_address": {"type": "string", "required": True},
            "min_amount": {"type": "number", "required": True}
        }
    },
    "new_holder": {
        "name": "New Holder",
        "description": "When a new wallet buys the token",
        "tier": "AGENCY",
        "category": "onchain",
        "config_schema": {
            "token_address": {"type": "string", "required": True}
        }
    },
    
    # Time-Based Triggers (Premium+)
    "scheduled": {
        "name": "Scheduled Time",
        "description": "At a specific date and time",
        "tier": "PREMIUM",
        "category": "time",
        "config_schema": {
            "datetime": {"type": "datetime", "required": True},
            "timezone": {"type": "string", "default": "UTC"}
        }
    },
    "recurring": {
        "name": "Recurring Schedule",
        "description": "Daily, weekly, or monthly at set time",
        "tier": "PREMIUM",
        "category": "time",
        "config_schema": {
            "frequency": {"type": "string", "enum": ["daily", "weekly", "monthly"], "required": True},
            "time": {"type": "time", "required": True},
            "day_of_week": {"type": "number", "min": 0, "max": 6},  # For weekly
            "day_of_month": {"type": "number", "min": 1, "max": 31}  # For monthly
        }
    },
    
    # Platform Triggers (Premium+)
    "engagement_spike": {
        "name": "Engagement Spike",
        "description": "When a post gets unusually high engagement",
        "tier": "PREMIUM",
        "category": "platform",
        "config_schema": {
            "platform": {"type": "string", "required": True},
            "threshold_percent": {"type": "number", "default": 200}
        }
    },
    "follower_milestone": {
        "name": "Follower Milestone",
        "description": "When follower count reaches a milestone",
        "tier": "PREMIUM",
        "category": "platform",
        "config_schema": {
            "platform": {"type": "string", "required": True},
            "milestone": {"type": "number", "required": True}
        }
    }
}

# ============================================
# ACTION TYPES
# ============================================

ACTION_TYPES = {
    "post_twitter": {
        "name": "Post to Twitter/X",
        "description": "Create and publish a tweet",
        "config_schema": {
            "content": {"type": "string", "required": False},
            "use_ai": {"type": "boolean", "default": True},
            "ai_prompt": {"type": "string", "required": False},
            "include_image": {"type": "boolean", "default": False}
        }
    },
    "post_discord": {
        "name": "Post to Discord",
        "description": "Send message to Discord channel",
        "config_schema": {
            "channel_id": {"type": "string", "required": True},
            "content": {"type": "string", "required": False},
            "use_ai": {"type": "boolean", "default": True},
            "ai_prompt": {"type": "string", "required": False}
        }
    },
    "post_telegram": {
        "name": "Post to Telegram",
        "description": "Send message to Telegram channel",
        "config_schema": {
            "chat_id": {"type": "string", "required": True},
            "content": {"type": "string", "required": False},
            "use_ai": {"type": "boolean", "default": True}
        }
    },
    "post_all": {
        "name": "Post to All Platforms",
        "description": "Post to all connected platforms",
        "config_schema": {
            "content": {"type": "string", "required": False},
            "use_ai": {"type": "boolean", "default": True},
            "ai_prompt": {"type": "string", "required": False},
            "platforms": {"type": "array", "default": ["twitter", "discord", "telegram"]}
        }
    },
    "send_notification": {
        "name": "Send Notification",
        "description": "Send alert notification",
        "config_schema": {
            "title": {"type": "string", "required": True},
            "message": {"type": "string", "required": True},
            "channels": {"type": "array", "default": ["email", "push"]}
        }
    },
    "generate_content": {
        "name": "Generate AI Content",
        "description": "Generate content with AI and save as draft",
        "config_schema": {
            "prompt": {"type": "string", "required": True},
            "content_type": {"type": "string", "default": "tweet"},
            "save_as_draft": {"type": "boolean", "default": True}
        }
    },
    "schedule_optimal": {
        "name": "Schedule for Optimal Time",
        "description": "Schedule a post for the next optimal engagement time",
        "config_schema": {
            "content": {"type": "string", "required": False},
            "use_ai": {"type": "boolean", "default": True},
            "platforms": {"type": "array", "required": True}
        }
    }
}

# ============================================
# CONDITION OPERATORS
# ============================================

CONDITION_OPERATORS = {
    "equals": "=",
    "not_equals": "!=",
    "greater_than": ">",
    "less_than": "<",
    "greater_or_equal": ">=",
    "less_or_equal": "<=",
    "contains": "contains",
    "not_contains": "not contains",
    "between": "between"
}


class FlowService:
    """Service for managing automation flows"""
    
    def __init__(self):
        self.db = db_manager
    
    # ============================================
    # FLOW CRUD OPERATIONS
    # ============================================
    
    async def create_flow(
        self,
        user_id: str,
        name: str,
        trigger_type: str,
        trigger_config: Dict,
        actions: List[Dict],
        conditions: Optional[List[Dict]] = None,
        description: Optional[str] = None
    ) -> Dict:
        """Create a new automation flow"""
        try:
            # Validate trigger type
            if trigger_type not in TRIGGER_TYPES:
                return {"success": False, "error": f"Invalid trigger type: {trigger_type}"}
            
            # Validate actions
            for action in actions:
                if action.get("type") not in ACTION_TYPES:
                    return {"success": False, "error": f"Invalid action type: {action.get('type')}"}
            
            query = """
                INSERT INTO flows (user_id, name, description, trigger_type, trigger_config, conditions, actions)
                VALUES (:user_id, :name, :description, :trigger_type, :trigger_config, :conditions, :actions)
                RETURNING id, name, trigger_type, is_active, created_at
            """
            
            result = await self.db.fetch_one(query, {
                "user_id": user_id,
                "name": name,
                "description": description,
                "trigger_type": trigger_type,
                "trigger_config": json.dumps(trigger_config),
                "conditions": json.dumps(conditions) if conditions else None,
                "actions": json.dumps(actions)
            })
            
            if result:
                logger.info(f"✅ Flow created: {name} for user {user_id}")
                return {
                    "success": True,
                    "flow": dict(result)
                }
            
            return {"success": False, "error": "Failed to create flow"}
            
        except Exception as e:
            logger.error(f"❌ Error creating flow: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_user_flows(self, user_id: str) -> List[Dict]:
        """Get all flows for a user"""
        try:
            query = """
                SELECT id, name, description, trigger_type, trigger_config, 
                       conditions, actions, is_active, last_triggered_at, 
                       trigger_count, created_at, updated_at
                FROM flows 
                WHERE user_id = :user_id
                ORDER BY created_at DESC
            """
            
            results = await self.db.fetch_all(query, {"user_id": user_id})
            
            flows = []
            for row in results:
                flow = dict(row)
                # Parse JSON fields
                flow["trigger_config"] = json.loads(flow["trigger_config"]) if flow.get("trigger_config") else {}
                flow["conditions"] = json.loads(flow["conditions"]) if flow.get("conditions") else []
                flow["actions"] = json.loads(flow["actions"]) if flow.get("actions") else []
                flows.append(flow)
            
            return flows
            
        except Exception as e:
            logger.error(f"❌ Error fetching flows: {e}")
            return []
    
    async def get_flow(self, flow_id: str, user_id: str) -> Optional[Dict]:
        """Get a specific flow by ID"""
        try:
            query = """
                SELECT * FROM flows 
                WHERE id = :flow_id AND user_id = :user_id
            """
            
            result = await self.db.fetch_one(query, {
                "flow_id": flow_id,
                "user_id": user_id
            })
            
            if result:
                flow = dict(result)
                flow["trigger_config"] = json.loads(flow["trigger_config"]) if flow.get("trigger_config") else {}
                flow["conditions"] = json.loads(flow["conditions"]) if flow.get("conditions") else []
                flow["actions"] = json.loads(flow["actions"]) if flow.get("actions") else []
                return flow
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Error fetching flow: {e}")
            return None
    
    async def update_flow(
        self,
        flow_id: str,
        user_id: str,
        updates: Dict
    ) -> Dict:
        """Update an existing flow"""
        try:
            # Build update query dynamically
            allowed_fields = ["name", "description", "trigger_type", "trigger_config", 
                           "conditions", "actions", "is_active"]
            
            set_clauses = []
            params = {"flow_id": flow_id, "user_id": user_id}
            
            for field in allowed_fields:
                if field in updates:
                    value = updates[field]
                    if field in ["trigger_config", "conditions", "actions"]:
                        value = json.dumps(value)
                    set_clauses.append(f"{field} = :{field}")
                    params[field] = value
            
            if not set_clauses:
                return {"success": False, "error": "No valid fields to update"}
            
            set_clauses.append("updated_at = CURRENT_TIMESTAMP")
            
            query = f"""
                UPDATE flows 
                SET {", ".join(set_clauses)}
                WHERE id = :flow_id AND user_id = :user_id
                RETURNING id, name, is_active, updated_at
            """
            
            result = await self.db.fetch_one(query, params)
            
            if result:
                logger.info(f"✅ Flow updated: {flow_id}")
                return {"success": True, "flow": dict(result)}
            
            return {"success": False, "error": "Flow not found"}
            
        except Exception as e:
            logger.error(f"❌ Error updating flow: {e}")
            return {"success": False, "error": str(e)}
    
    async def delete_flow(self, flow_id: str, user_id: str) -> Dict:
        """Delete a flow"""
        try:
            query = """
                DELETE FROM flows 
                WHERE id = :flow_id AND user_id = :user_id
                RETURNING id
            """
            
            result = await self.db.fetch_one(query, {
                "flow_id": flow_id,
                "user_id": user_id
            })
            
            if result:
                logger.info(f"✅ Flow deleted: {flow_id}")
                return {"success": True}
            
            return {"success": False, "error": "Flow not found"}
            
        except Exception as e:
            logger.error(f"❌ Error deleting flow: {e}")
            return {"success": False, "error": str(e)}
    
    async def toggle_flow(self, flow_id: str, user_id: str, is_active: bool) -> Dict:
        """Toggle flow active status"""
        return await self.update_flow(flow_id, user_id, {"is_active": is_active})
    
    # ============================================
    # FLOW EXECUTION
    # ============================================
    
    async def check_conditions(self, conditions: List[Dict], context: Dict) -> bool:
        """Check if all conditions are met"""
        if not conditions:
            return True
        
        for condition in conditions:
            field = condition.get("field")
            operator = condition.get("operator")
            value = condition.get("value")
            
            actual_value = context.get(field)
            
            if operator == "equals" and actual_value != value:
                return False
            elif operator == "not_equals" and actual_value == value:
                return False
            elif operator == "greater_than" and not (actual_value > value):
                return False
            elif operator == "less_than" and not (actual_value < value):
                return False
            elif operator == "greater_or_equal" and not (actual_value >= value):
                return False
            elif operator == "less_or_equal" and not (actual_value <= value):
                return False
            elif operator == "contains" and value not in str(actual_value):
                return False
            elif operator == "between":
                min_val, max_val = value
                if not (min_val <= actual_value <= max_val):
                    return False
        
        return True
    
    async def execute_flow(self, flow_id: str, trigger_context: Dict) -> Dict:
        """Execute a flow's actions"""
        try:
            # Get flow from database
            query = """
                SELECT f.*, u.id as owner_id
                FROM flows f
                JOIN users u ON f.user_id = u.id
                WHERE f.id = :flow_id AND f.is_active = true
            """
            
            flow = await self.db.fetch_one(query, {"flow_id": flow_id})
            
            if not flow:
                return {"success": False, "error": "Flow not found or inactive"}
            
            flow = dict(flow)
            conditions = json.loads(flow["conditions"]) if flow.get("conditions") else []
            actions = json.loads(flow["actions"]) if flow.get("actions") else []
            
            # Check conditions
            if not await self.check_conditions(conditions, trigger_context):
                logger.info(f"⏸️ Flow {flow_id} conditions not met, skipping")
                return {"success": True, "skipped": True, "reason": "Conditions not met"}
            
            # Execute actions
            results = []
            for action in actions:
                action_result = await self._execute_action(action, trigger_context, flow["owner_id"])
                results.append(action_result)
            
            # Update flow stats
            await self.db.execute_query("""
                UPDATE flows 
                SET last_triggered_at = CURRENT_TIMESTAMP, 
                    trigger_count = trigger_count + 1
                WHERE id = :flow_id
            """, {"flow_id": flow_id})
            
            logger.info(f"✅ Flow executed: {flow_id}")
            return {"success": True, "results": results}
            
        except Exception as e:
            logger.error(f"❌ Error executing flow {flow_id}: {e}")
            return {"success": False, "error": str(e)}
    
    async def _execute_action(self, action: Dict, context: Dict, user_id: str) -> Dict:
        """Execute a single action"""
        action_type = action.get("type")
        config = action.get("config", {})
        
        try:
            if action_type == "post_twitter":
                return await self._post_to_twitter(config, context, user_id)
            elif action_type == "post_discord":
                return await self._post_to_discord(config, context, user_id)
            elif action_type == "post_telegram":
                return await self._post_to_telegram(config, context, user_id)
            elif action_type == "post_all":
                return await self._post_to_all(config, context, user_id)
            elif action_type == "send_notification":
                return await self._send_notification(config, context, user_id)
            elif action_type == "generate_content":
                return await self._generate_content(config, context, user_id)
            elif action_type == "schedule_optimal":
                return await self._schedule_optimal(config, context, user_id)
            else:
                return {"success": False, "error": f"Unknown action type: {action_type}"}
                
        except Exception as e:
            logger.error(f"❌ Error executing action {action_type}: {e}")
            return {"success": False, "action": action_type, "error": str(e)}
    
    # ============================================
    # ACTION IMPLEMENTATIONS
    # ============================================
    
    async def _post_to_twitter(self, config: Dict, context: Dict, user_id: str) -> Dict:
        """Post to Twitter/X"""
        from twitter_service import twitter_service
        
        content = config.get("content")
        
        # Generate content with AI if needed
        if config.get("use_ai") and not content:
            content = await self._generate_ai_content(
                config.get("ai_prompt", "Create an engaging tweet about: {trigger_event}"),
                context
            )
        
        if not content:
            return {"success": False, "error": "No content to post"}
        
        # Post to Twitter
        result = await twitter_service.post_tweet(content)
        return {"success": True, "action": "post_twitter", "result": result}
    
    async def _post_to_discord(self, config: Dict, context: Dict, user_id: str) -> Dict:
        """Post to Discord (placeholder)"""
        # TODO: Implement Discord posting
        return {"success": True, "action": "post_discord", "result": "Discord integration pending"}
    
    async def _post_to_telegram(self, config: Dict, context: Dict, user_id: str) -> Dict:
        """Post to Telegram (placeholder)"""
        # TODO: Implement Telegram posting
        return {"success": True, "action": "post_telegram", "result": "Telegram integration pending"}
    
    async def _post_to_all(self, config: Dict, context: Dict, user_id: str) -> Dict:
        """Post to all selected platforms"""
        platforms = config.get("platforms", ["twitter"])
        results = []
        
        for platform in platforms:
            if platform == "twitter":
                result = await self._post_to_twitter(config, context, user_id)
            elif platform == "discord":
                result = await self._post_to_discord(config, context, user_id)
            elif platform == "telegram":
                result = await self._post_to_telegram(config, context, user_id)
            else:
                result = {"success": False, "error": f"Unknown platform: {platform}"}
            results.append(result)
        
        return {"success": True, "action": "post_all", "results": results}
    
    async def _send_notification(self, config: Dict, context: Dict, user_id: str) -> Dict:
        """Send notification"""
        # TODO: Implement notification service
        return {
            "success": True, 
            "action": "send_notification",
            "title": config.get("title"),
            "message": config.get("message")
        }
    
    async def _generate_content(self, config: Dict, context: Dict, user_id: str) -> Dict:
        """Generate AI content"""
        content = await self._generate_ai_content(config.get("prompt", ""), context)
        
        if config.get("save_as_draft"):
            # Save as draft post
            # TODO: Implement draft saving
            pass
        
        return {"success": True, "action": "generate_content", "content": content}
    
    async def _schedule_optimal(self, config: Dict, context: Dict, user_id: str) -> Dict:
        """Schedule post for optimal time"""
        from optimal_times_service import optimal_times_service
        
        # Get optimal times
        platforms = config.get("platforms", ["twitter"])
        optimal_time = await optimal_times_service.get_next_optimal_time(platforms[0])
        
        content = config.get("content")
        if config.get("use_ai") and not content:
            content = await self._generate_ai_content(
                config.get("ai_prompt", "Create an engaging post"),
                context
            )
        
        # TODO: Schedule the post
        return {
            "success": True,
            "action": "schedule_optimal",
            "scheduled_for": optimal_time,
            "content": content
        }
    
    async def _generate_ai_content(self, prompt: str, context: Dict) -> str:
        """Generate content using AI"""
        try:
            from ai_service import generate_social_post
            
            # Replace context variables in prompt
            for key, value in context.items():
                prompt = prompt.replace(f"{{{key}}}", str(value))
            
            result = await generate_social_post(prompt)
            return result.get("content", "")
            
        except Exception as e:
            logger.error(f"❌ Error generating AI content: {e}")
            return ""
    
    # ============================================
    # UTILITY METHODS
    # ============================================
    
    def get_trigger_types(self, tier: str = "FREE") -> Dict:
        """Get available trigger types for a tier"""
        tier_order = {"FREE": 0, "BASIC": 1, "PREMIUM": 2, "AGENCY": 3}
        user_tier_level = tier_order.get(tier.upper(), 0)
        
        available = {}
        for key, trigger in TRIGGER_TYPES.items():
            trigger_tier_level = tier_order.get(trigger["tier"], 3)
            if user_tier_level >= trigger_tier_level:
                available[key] = trigger
        
        return available
    
    def get_action_types(self) -> Dict:
        """Get all available action types"""
        return ACTION_TYPES
    
    def get_condition_operators(self) -> Dict:
        """Get all condition operators"""
        return CONDITION_OPERATORS
    
    async def get_flow_stats(self, user_id: str) -> Dict:
        """Get flow statistics for a user"""
        try:
            query = """
                SELECT 
                    COUNT(*) as total_flows,
                    COUNT(*) FILTER (WHERE is_active = true) as active_flows,
                    SUM(trigger_count) as total_triggers,
                    MAX(last_triggered_at) as last_trigger
                FROM flows
                WHERE user_id = :user_id
            """
            
            result = await self.db.fetch_one(query, {"user_id": user_id})
            
            if result:
                return dict(result)
            return {"total_flows": 0, "active_flows": 0, "total_triggers": 0}
            
        except Exception as e:
            logger.error(f"❌ Error getting flow stats: {e}")
            return {"total_flows": 0, "active_flows": 0, "total_triggers": 0}


# Global instance
flow_service = FlowService()
