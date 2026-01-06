"""
Chat Routes - API endpoints for the conversational AI interface

Handles:
- Message processing and intent routing
- Streaming responses (SSE)
- Conversation history
- Action execution
"""

import os
import json
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import httpx
import asyncio

from intent_parser import intent_parser, Intent, ParsedIntent
from database import db_manager
from auth_routes import get_current_user
from optimal_times_service import optimal_times_service

router = APIRouter(prefix="/chat", tags=["Chat"])


# ============= Request/Response Models =============

class ChatMessage(BaseModel):
    content: str
    conversation_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    message_id: str
    content: str
    intent: str
    entities: Dict[str, Any]
    actions: Optional[List[Dict[str, Any]]] = None
    conversation_id: str
    timestamp: str


class ConversationHistory(BaseModel):
    conversation_id: str
    messages: List[Dict[str, Any]]
    created_at: str
    updated_at: str


# ============= Chat Service =============

class ChatService:
    """Handles chat processing, intent routing, and response generation"""
    
    def __init__(self):
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        self.groq_api_url = "https://api.groq.com/openai/v1/chat/completions"
        self.model = "llama-3.1-8b-instant"
        
    async def process_message(
        self, 
        message: str, 
        user_id: str,
        conversation_id: Optional[str] = None,
        context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Process a chat message:
        1. Parse intent
        2. Execute relevant action
        3. Generate AI response
        """
        # Parse intent
        parsed = await intent_parser.parse(message, context)
        
        # Create or get conversation
        if not conversation_id:
            conversation_id = str(uuid.uuid4())
        
        # Route to appropriate handler based on intent
        action_result = await self._execute_action(parsed, user_id)
        
        # Generate conversational response
        response_content = await self._generate_response(
            message=message,
            parsed_intent=parsed,
            action_result=action_result,
            user_id=user_id
        )
        
        # Save to conversation history
        await self._save_message(
            conversation_id=conversation_id,
            user_id=user_id,
            role="user",
            content=message,
            metadata={"intent": parsed.intent.value}
        )
        
        await self._save_message(
            conversation_id=conversation_id,
            user_id=user_id,
            role="assistant",
            content=response_content,
            metadata={"action_result": action_result}
        )
        
        return {
            "message_id": str(uuid.uuid4()),
            "content": response_content,
            "intent": parsed.intent.value,
            "entities": parsed.entities,
            "actions": action_result.get("actions") if action_result else None,
            "conversation_id": conversation_id,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def _execute_action(self, parsed: ParsedIntent, user_id: str) -> Optional[Dict]:
        """Execute the appropriate action based on intent"""
        
        handlers = {
            Intent.CREATE_CAMPAIGN: self._handle_create_campaign,
            Intent.GENERATE_IDEAS: self._handle_generate_ideas,
            Intent.SCHEDULE_POSTS: self._handle_schedule_posts,
            Intent.GET_ANALYTICS: self._handle_get_analytics,
            Intent.CONNECT_PLATFORM: self._handle_connect_platform,
            Intent.HELP: self._handle_help,
        }
        
        handler = handlers.get(parsed.intent)
        if handler:
            return await handler(parsed.entities, user_id)
        
        return None
    
    async def _handle_create_campaign(self, entities: Dict, user_id: str) -> Dict:
        """Handle campaign creation intent"""
        post_count = entities.get("post_count", 5)
        platforms = entities.get("platforms", ["twitter"])
        topic = entities.get("topic", "general")
        duration = entities.get("duration", "1 week")
        tone = entities.get("tone", "professional")
        
        return {
            "action": "create_campaign",
            "status": "ready",
            "preview": {
                "post_count": post_count,
                "platforms": platforms,
                "topic": topic,
                "duration": duration,
                "tone": tone
            },
            "actions": [
                {
                    "type": "generate_posts",
                    "label": "Generate Posts",
                    "data": entities
                },
                {
                    "type": "customize",
                    "label": "Customize Settings"
                }
            ]
        }
    
    async def _handle_generate_ideas(self, entities: Dict, user_id: str) -> Dict:
        """Handle idea generation intent"""
        platforms = entities.get("platforms", ["twitter", "linkedin"])
        topic = entities.get("topic")
        
        return {
            "action": "generate_ideas",
            "status": "ready",
            "params": {
                "platforms": platforms,
                "topic": topic
            },
            "actions": [
                {
                    "type": "generate_ideas",
                    "label": "Generate Ideas"
                }
            ]
        }
    
    async def _handle_schedule_posts(self, entities: Dict, user_id: str) -> Dict:
        """Handle scheduling intent with AI-powered optimal times"""
        platforms = entities.get("platforms", ["twitter", "instagram", "linkedin"])
        industry = entities.get("industry")
        
        # Get intelligent recommendations from optimal times service
        recommendations = optimal_times_service.get_optimal_times(
            platforms=platforms,
            industry=industry
        )
        
        # Format optimal times for response
        optimal_times = {}
        platform_tips = {}
        
        for platform, rec in recommendations.items():
            optimal_times[platform] = [
                {
                    "time": slot.time,
                    "day": slot.day,
                    "score": slot.engagement_score,
                    "reason": slot.reason
                }
                for slot in rec.best_times[:3]
            ]
            platform_tips[platform] = rec.tips[:2]
        
        # Generate weekly schedule suggestion
        weekly_schedule = optimal_times_service.get_weekly_schedule(
            platforms=platforms,
            posts_per_week=7,
            industry=industry
        )
        
        # Format recommendation text for AI to include
        recommendation_text = optimal_times_service.format_recommendation_text(recommendations)
        
        return {
            "action": "schedule_posts",
            "status": "ready",
            "optimal_times": optimal_times,
            "platform_tips": platform_tips,
            "weekly_schedule": weekly_schedule,
            "recommendation_text": recommendation_text,
            "note": "AI-analyzed optimal times based on 2024 engagement data",
            "actions": [
                {
                    "type": "auto_schedule",
                    "label": "Auto-Schedule All"
                },
                {
                    "type": "custom_schedule",
                    "label": "Choose Times Manually"
                },
                {
                    "type": "view_weekly",
                    "label": "View Weekly Plan"
                }
            ]
        }
    
    async def _handle_get_analytics(self, entities: Dict, user_id: str) -> Dict:
        """Handle analytics request"""
        # Fetch actual analytics from database
        try:
            query = """
                SELECT 
                    COUNT(*) as total_posts,
                    SUM(CASE WHEN status = 'posted' THEN 1 ELSE 0 END) as posted,
                    SUM(CASE WHEN status = 'scheduled' THEN 1 ELSE 0 END) as scheduled
                FROM posts 
                WHERE user_id = :user_id
            """
            result = await db_manager.fetch_one(query, {"user_id": user_id})
            
            return {
                "action": "show_analytics",
                "status": "ready",
                "summary": {
                    "total_posts": result["total_posts"] if result else 0,
                    "posted": result["posted"] if result else 0,
                    "scheduled": result["scheduled"] if result else 0
                },
                "actions": [
                    {
                        "type": "view_detailed",
                        "label": "View Detailed Analytics"
                    }
                ]
            }
        except Exception as e:
            return {
                "action": "show_analytics",
                "status": "error",
                "message": "Could not fetch analytics",
                "actions": []
            }
    
    async def _handle_connect_platform(self, entities: Dict, user_id: str) -> Dict:
        """Handle platform connection intent"""
        platforms = entities.get("platforms", [])
        
        return {
            "action": "connect_platform",
            "status": "ready",
            "platforms": platforms,
            "message": f"Ready to connect: {', '.join(platforms)}" if platforms else "Which platform would you like to connect?",
            "actions": [
                {"type": "connect_twitter", "label": "Connect Twitter/X"},
                {"type": "connect_instagram", "label": "Connect Instagram"},
                {"type": "connect_linkedin", "label": "Connect LinkedIn"},
                {"type": "connect_facebook", "label": "Connect Facebook"},
            ]
        }
    
    async def _handle_help(self, entities: Dict, user_id: str) -> Dict:
        """Handle help intent"""
        return {
            "action": "show_help",
            "status": "ready",
            "capabilities": [
                "🚀 Create content campaigns with AI-generated posts",
                "💡 Generate viral content ideas for any platform",
                "📅 Schedule posts at optimal times",
                "📊 View analytics and performance metrics",
                "🔗 Connect your social media accounts",
                "✏️ Edit and refine generated content"
            ],
            "examples": [
                "Create 10 posts about Solana for 2 weeks",
                "Give me viral content ideas for Twitter",
                "Schedule my posts for optimal engagement",
                "How did my posts perform last week?",
                "Connect my Instagram account"
            ]
        }
    
    async def _generate_response(
        self,
        message: str,
        parsed_intent: ParsedIntent,
        action_result: Optional[Dict],
        user_id: str
    ) -> str:
        """Generate a conversational AI response"""
        
        if not self.groq_api_key:
            # Return simple response without AI
            return parsed_intent.suggested_response or "How can I help you today?"
        
        system_prompt = """You are a friendly, helpful AI social media assistant called "SocialAgent".
Your personality:
- Enthusiastic but professional
- Concise (2-3 sentences max for simple queries)
- Use emojis sparingly but effectively
- Action-oriented - always suggest next steps

You help users:
- Create and manage social media campaigns
- Generate content ideas
- Schedule posts at optimal times
- Analyze performance

IMPORTANT: Be conversational and helpful. Don't be robotic."""

        # Build context for response
        context_parts = [f"User's message: {message}"]
        context_parts.append(f"Detected intent: {parsed_intent.intent.value}")
        
        if parsed_intent.entities:
            context_parts.append(f"Extracted info: {json.dumps(parsed_intent.entities)}")
        
        if action_result:
            context_parts.append(f"Action result: {json.dumps(action_result)}")
        
        user_prompt = "\n".join(context_parts)
        user_prompt += "\n\nGenerate a helpful, conversational response. Keep it concise."
        
        try:
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
                        "temperature": 0.7,
                        "max_tokens": 300,
                    },
                    timeout=15.0
                )
                response.raise_for_status()
                
                result = response.json()
                return result["choices"][0]["message"]["content"]
                
        except Exception as e:
            print(f"AI response generation failed: {e}")
            return parsed_intent.suggested_response or "I'm here to help! What would you like to do?"
    
    async def _save_message(
        self,
        conversation_id: str,
        user_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict] = None
    ):
        """Save message to conversation history"""
        try:
            # Check if conversations table exists, create if not
            await db_manager.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    conversation_id VARCHAR(255) NOT NULL,
                    user_id UUID NOT NULL,
                    role VARCHAR(20) NOT NULL,
                    content TEXT NOT NULL,
                    metadata JSONB,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
            await db_manager.execute("""
                INSERT INTO conversations (conversation_id, user_id, role, content, metadata)
                VALUES (:conversation_id, :user_id, :role, :content, :metadata)
            """, {
                "conversation_id": conversation_id,
                "user_id": user_id,
                "role": role,
                "content": content,
                "metadata": json.dumps(metadata) if metadata else None
            })
        except Exception as e:
            print(f"Failed to save message: {e}")


# Singleton
chat_service = ChatService()


# ============= API Endpoints =============

@router.post("/message", response_model=ChatResponse)
async def send_message(
    message: ChatMessage,
    current_user: dict = Depends(get_current_user)
):
    """
    Send a message to the AI agent and get a response
    """
    try:
        result = await chat_service.process_message(
            message=message.content,
            user_id=str(current_user["id"]),
            conversation_id=message.conversation_id,
            context=message.context
        )
        return ChatResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stream")
async def stream_response(
    message: ChatMessage,
    current_user: dict = Depends(get_current_user)
):
    """
    Stream a response using Server-Sent Events (SSE)
    for ChatGPT-like typing effect with real Groq streaming
    """
    async def generate():
        try:
            user_id = str(current_user["id"])
            conversation_id = message.conversation_id or str(uuid.uuid4())
            
            # Parse intent first
            parsed = await intent_parser.parse(message.content)
            
            # Yield intent info
            yield f"data: {json.dumps({'type': 'intent', 'data': {'intent': parsed.intent.value, 'entities': parsed.entities}})}\n\n"
            
            # Execute action
            action_result = await chat_service._execute_action(parsed, user_id)
            
            if action_result:
                yield f"data: {json.dumps({'type': 'action', 'data': action_result})}\n\n"
            
            # Stream from Groq API
            full_response = ""
            
            if chat_service.groq_api_key:
                system_prompt = """You are Social Sol AI, a friendly AI social media assistant.
Be conversational, helpful, and concise. Use markdown formatting for structure.
Help users create content, schedule posts, analyze performance, and generate ideas."""
                
                context_parts = [f"User message: {message.content}"]
                context_parts.append(f"Intent: {parsed.intent.value}")
                if parsed.entities:
                    context_parts.append(f"Entities: {json.dumps(parsed.entities)}")
                if action_result:
                    context_parts.append(f"Action result: {json.dumps(action_result)}")
                
                user_prompt = "\n".join(context_parts)
                
                try:
                    async with httpx.AsyncClient() as client:
                        async with client.stream(
                            "POST",
                            chat_service.groq_api_url,
                            headers={
                                "Authorization": f"Bearer {chat_service.groq_api_key}",
                                "Content-Type": "application/json"
                            },
                            json={
                                "model": chat_service.model,
                                "messages": [
                                    {"role": "system", "content": system_prompt},
                                    {"role": "user", "content": user_prompt}
                                ],
                                "temperature": 0.7,
                                "max_tokens": 500,
                                "stream": True
                            },
                            timeout=30.0
                        ) as response:
                            async for line in response.aiter_lines():
                                if line.startswith("data: "):
                                    data = line[6:]
                                    if data == "[DONE]":
                                        break
                                    try:
                                        chunk = json.loads(data)
                                        if "choices" in chunk and len(chunk["choices"]) > 0:
                                            delta = chunk["choices"][0].get("delta", {})
                                            content = delta.get("content", "")
                                            if content:
                                                full_response += content
                                                yield f"data: {json.dumps({'type': 'content', 'data': content})}\n\n"
                                    except json.JSONDecodeError:
                                        pass
                except Exception as e:
                    print(f"Groq streaming error: {e}")
                    # Fallback to non-streaming
                    full_response = parsed.suggested_response or "I'm here to help with your social media needs!"
                    yield f"data: {json.dumps({'type': 'content', 'data': full_response})}\n\n"
            else:
                # No API key - use fallback
                full_response = parsed.suggested_response or "I'm here to help with your social media needs!"
                # Stream character by character for effect
                for char in full_response:
                    yield f"data: {json.dumps({'type': 'content', 'data': char})}\n\n"
                    await asyncio.sleep(0.01)
            
            # Save messages
            await chat_service._save_message(conversation_id, user_id, "user", message.content)
            await chat_service._save_message(conversation_id, user_id, "assistant", full_response)
            
            # Done
            yield f"data: {json.dumps({'type': 'done', 'conversation_id': conversation_id})}\n\n"
            
        except Exception as e:
            print(f"Stream error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'data': str(e)})}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@router.get("/history/{conversation_id}")
async def get_conversation_history(
    conversation_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get conversation history"""
    try:
        messages = await db_manager.fetch_all("""
            SELECT role, content, metadata, created_at
            FROM conversations
            WHERE conversation_id = :conversation_id AND user_id = :user_id
            ORDER BY created_at ASC
        """, {
            "conversation_id": conversation_id,
            "user_id": str(current_user["id"])
        })
        
        return {
            "conversation_id": conversation_id,
            "messages": [dict(m) for m in messages] if messages else [],
            "created_at": messages[0]["created_at"].isoformat() if messages else None,
            "updated_at": messages[-1]["created_at"].isoformat() if messages else None
        }
    except Exception as e:
        return {
            "conversation_id": conversation_id,
            "messages": [],
            "created_at": None,
            "updated_at": None
        }


@router.get("/conversations")
async def list_conversations(
    current_user: dict = Depends(get_current_user),
    limit: int = 20
):
    """List user's recent conversations"""
    try:
        conversations = await db_manager.fetch_all("""
            SELECT DISTINCT ON (conversation_id) 
                conversation_id,
                content as last_message,
                created_at
            FROM conversations
            WHERE user_id = :user_id AND role = 'user'
            ORDER BY conversation_id, created_at DESC
            LIMIT :limit
        """, {
            "user_id": str(current_user["id"]),
            "limit": limit
        })
        
        return {
            "conversations": [
                {
                    "id": c["conversation_id"],
                    "preview": c["last_message"][:50] + "..." if len(c["last_message"]) > 50 else c["last_message"],
                    "timestamp": c["created_at"].isoformat()
                }
                for c in conversations
            ] if conversations else []
        }
    except Exception as e:
        return {"conversations": []}


@router.delete("/conversation/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a conversation"""
    try:
        await db_manager.execute("""
            DELETE FROM conversations
            WHERE conversation_id = :conversation_id AND user_id = :user_id
        """, {
            "conversation_id": conversation_id,
            "user_id": str(current_user["id"])
        })
        return {"status": "deleted", "conversation_id": conversation_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

