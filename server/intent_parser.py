"""
Intent Parser Service - Converts natural language to structured actions

Supported intents:
- create_campaign: Generate posts for a campaign
- generate_ideas: Get viral content ideas
- schedule_posts: Schedule posts for optimal times
- get_analytics: Query performance metrics
- edit_content: Modify specific posts
- connect_platform: Connect social media account
- help: Get assistance
"""

import os
import json
import re
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum
import httpx


class Intent(Enum):
    CREATE_CAMPAIGN = "create_campaign"
    GENERATE_IDEAS = "generate_ideas"
    SCHEDULE_POSTS = "schedule_posts"
    GET_ANALYTICS = "get_analytics"
    EDIT_CONTENT = "edit_content"
    CONNECT_PLATFORM = "connect_platform"
    GENERAL_CHAT = "general_chat"
    HELP = "help"
    UNKNOWN = "unknown"


@dataclass
class ParsedIntent:
    """Structured intent with extracted entities"""
    intent: Intent
    confidence: float
    entities: Dict[str, Any]
    original_message: str
    suggested_response: Optional[str] = None


class IntentParser:
    """
    Parses user messages into structured intents using Groq AI
    with fallback to keyword matching
    """
    
    def __init__(self):
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        self.groq_api_url = "https://api.groq.com/openai/v1/chat/completions"
        self.model = "llama-3.1-8b-instant"
        
        # Keyword patterns for fallback matching
        self.intent_patterns = {
            Intent.CREATE_CAMPAIGN: [
                r"create\s+(\d+)?\s*posts?",
                r"make\s+(\d+)?\s*posts?",
                r"generate\s+(\d+)?\s*posts?",
                r"start\s+(?:a\s+)?campaign",
                r"new\s+campaign",
                r"campaign\s+for",
                r"(\d+)\s+posts?\s+(?:for|about|on)",
            ],
            Intent.GENERATE_IDEAS: [
                r"(?:give|get|show)\s+(?:me\s+)?ideas?",
                r"content\s+ideas?",
                r"viral\s+(?:content|posts?|ideas?)",
                r"suggest\s+(?:content|posts?|topics?)",
                r"what\s+(?:should|can)\s+i\s+post",
                r"trending\s+(?:topics?|content)",
            ],
            Intent.SCHEDULE_POSTS: [
                r"schedule\s+(?:these|my|the)?\s*posts?",
                r"when\s+(?:should|to)\s+post",
                r"best\s+time\s+to\s+post",
                r"optimal\s+(?:time|schedule)",
                r"auto[- ]?schedule",
            ],
            Intent.GET_ANALYTICS: [
                r"(?:how|what)\s+(?:did|are|were)\s+(?:my\s+)?(?:posts?|campaigns?)\s+(?:perform|doing)",
                r"analytics",
                r"performance",
                r"engagement",
                r"(?:show|get)\s+(?:me\s+)?(?:my\s+)?stats",
                r"metrics",
                r"impressions",
                r"reach",
            ],
            Intent.EDIT_CONTENT: [
                r"edit\s+(?:post|content)",
                r"change\s+(?:post|content)",
                r"modify\s+(?:post|content)",
                r"make\s+(?:it|post|this)\s+(?:more\s+)?(?:casual|professional|funny|serious)",
                r"rewrite",
                r"rephrase",
            ],
            Intent.CONNECT_PLATFORM: [
                r"connect\s+(?:my\s+)?(?:twitter|x|facebook|instagram|linkedin|reddit)",
                r"link\s+(?:my\s+)?(?:twitter|x|facebook|instagram|linkedin|reddit)",
                r"add\s+(?:twitter|x|facebook|instagram|linkedin|reddit)",
                r"setup?\s+(?:twitter|x|facebook|instagram|linkedin|reddit)",
            ],
            Intent.HELP: [
                r"^help$",
                r"how\s+(?:do|can)\s+i",
                r"what\s+can\s+you\s+do",
                r"tutorial",
                r"guide",
            ],
        }
        
        # Platform name normalization
        self.platform_aliases = {
            "x": "twitter",
            "ig": "instagram",
            "fb": "facebook",
            "li": "linkedin",
        }
        
    async def parse(self, message: str, context: Optional[Dict] = None) -> ParsedIntent:
        """
        Parse a user message into a structured intent
        
        Args:
            message: User's natural language message
            context: Optional conversation context
            
        Returns:
            ParsedIntent with intent type, confidence, and extracted entities
        """
        message_lower = message.lower().strip()
        
        # Try AI-powered parsing first if API key available
        if self.groq_api_key:
            try:
                return await self._parse_with_ai(message, context)
            except Exception as e:
                print(f"AI parsing failed, falling back to keywords: {e}")
        
        # Fallback to keyword matching
        return self._parse_with_keywords(message_lower)
    
    async def _parse_with_ai(self, message: str, context: Optional[Dict] = None) -> ParsedIntent:
        """Use Groq AI to parse intent and extract entities"""
        
        system_prompt = """You are an intent parser for a social media management AI agent.
        
Your job is to:
1. Identify the user's intent from their message
2. Extract relevant entities (numbers, platforms, topics, timeframes, etc.)
3. Return a structured JSON response

Available intents:
- create_campaign: User wants to create posts/content campaign
- generate_ideas: User wants content ideas or suggestions
- schedule_posts: User wants to schedule posts or find optimal times
- get_analytics: User wants to see performance metrics
- edit_content: User wants to modify existing content
- connect_platform: User wants to connect a social media account
- general_chat: General conversation, greetings, or casual chat
- help: User needs assistance

Extract these entities when present:
- post_count: Number of posts requested (integer)
- platforms: List of social platforms mentioned (twitter, instagram, facebook, linkedin, reddit)
- topic: Main topic or subject matter
- duration: Time period (e.g., "2 weeks", "1 month")
- tone: Desired tone (casual, professional, funny, etc.)
- post_id: Specific post reference if editing

ALWAYS respond with valid JSON only, no other text:
{
    "intent": "intent_name",
    "confidence": 0.0-1.0,
    "entities": {...},
    "suggested_action": "Brief description of what to do"
}"""

        user_prompt = f"Parse this message: \"{message}\""
        
        if context:
            user_prompt += f"\n\nContext: {json.dumps(context)}"
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.groq_api_url,
                headers={
                    "Authorization": f"Bearer {self.groq_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "temperature": 0.1,
                    "max_tokens": 500,
                },
                timeout=10.0
            )
            response.raise_for_status()
            
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            
            # Parse JSON from response
            parsed = json.loads(content)
            
            return ParsedIntent(
                intent=Intent(parsed.get("intent", "unknown")),
                confidence=float(parsed.get("confidence", 0.8)),
                entities=parsed.get("entities", {}),
                original_message=message,
                suggested_response=parsed.get("suggested_action")
            )
    
    def _parse_with_keywords(self, message: str) -> ParsedIntent:
        """Fallback keyword-based parsing"""
        
        best_intent = Intent.GENERAL_CHAT
        best_confidence = 0.3
        entities = {}
        
        # Check each intent's patterns
        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, message, re.IGNORECASE)
                if match:
                    # Higher confidence for more specific matches
                    confidence = 0.7 + (0.1 * len(match.groups()))
                    if confidence > best_confidence:
                        best_intent = intent
                        best_confidence = min(confidence, 0.95)
                        
                        # Extract captured groups as entities
                        for i, group in enumerate(match.groups()):
                            if group and group.isdigit():
                                entities["post_count"] = int(group)
        
        # Extract additional entities
        entities.update(self._extract_entities(message))
        
        return ParsedIntent(
            intent=best_intent,
            confidence=best_confidence,
            entities=entities,
            original_message=message,
            suggested_response=self._get_suggested_response(best_intent)
        )
    
    def _extract_entities(self, message: str) -> Dict[str, Any]:
        """Extract common entities from message"""
        entities = {}
        
        # Extract platforms
        platforms = []
        platform_pattern = r"\b(twitter|x|instagram|ig|facebook|fb|linkedin|li|reddit)\b"
        for match in re.finditer(platform_pattern, message, re.IGNORECASE):
            platform = match.group(1).lower()
            platform = self.platform_aliases.get(platform, platform)
            if platform not in platforms:
                platforms.append(platform)
        if platforms:
            entities["platforms"] = platforms
        
        # Extract numbers (post count)
        number_match = re.search(r"\b(\d+)\s*(?:posts?|pieces?|content)", message, re.IGNORECASE)
        if number_match:
            entities["post_count"] = int(number_match.group(1))
        
        # Extract duration
        duration_match = re.search(r"(\d+)\s*(days?|weeks?|months?)", message, re.IGNORECASE)
        if duration_match:
            entities["duration"] = f"{duration_match.group(1)} {duration_match.group(2)}"
        
        # Extract tone
        tone_match = re.search(r"\b(casual|professional|funny|serious|friendly|formal|playful)\b", message, re.IGNORECASE)
        if tone_match:
            entities["tone"] = tone_match.group(1).lower()
        
        return entities
    
    def _get_suggested_response(self, intent: Intent) -> str:
        """Get a suggested response template for the intent"""
        responses = {
            Intent.CREATE_CAMPAIGN: "I'll help you create a content campaign. Let me generate some posts based on your requirements.",
            Intent.GENERATE_IDEAS: "Let me generate some viral content ideas for you!",
            Intent.SCHEDULE_POSTS: "I'll find the optimal posting times based on your audience and platform.",
            Intent.GET_ANALYTICS: "Let me pull up your performance metrics.",
            Intent.EDIT_CONTENT: "Sure, I'll help you modify that content.",
            Intent.CONNECT_PLATFORM: "Let me help you connect your social media account.",
            Intent.HELP: "I'm here to help! I can create campaigns, generate content ideas, schedule posts, show analytics, and more.",
            Intent.GENERAL_CHAT: "How can I assist you with your social media today?",
            Intent.UNKNOWN: "I'm not sure I understood that. Could you rephrase or ask for help to see what I can do?",
        }
        return responses.get(intent, responses[Intent.UNKNOWN])


# Singleton instance
intent_parser = IntentParser()


