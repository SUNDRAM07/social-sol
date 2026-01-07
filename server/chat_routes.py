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
from trend_analyzer_service import trend_analyzer
from deep_research_engine import deep_research_engine
from real_time_research_service import real_time_research
from free_research_service import free_research

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
        """
        Handle scheduling intent with DEEP RESEARCH.
        
        Full analysis:
        - Content topic & audience detection
        - Real-time trend analysis
        - Timezone-aware optimal timing
        - Viral potential scoring
        - Competitor timing analysis
        """
        platforms = entities.get("platforms", ["twitter"])
        content = entities.get("content", "")  # Content to schedule if provided
        timezone = entities.get("timezone", "UTC")
        
        # If we have content, run DEEP RESEARCH
        if content:
            research_result = await deep_research_engine.research_optimal_posting(
                content=content,
                platform=platforms[0] if platforms else "twitter",
                user_timezone=timezone,
                user_id=user_id
            )
            
            formatted = deep_research_engine.format_research_for_display(research_result)
            
            return {
                "action": "schedule_with_research",
                "status": "researched",
                "research_summary": formatted,
                "timing": {
                    "optimal_time": research_result.timing_recommendation.optimal_time.isoformat(),
                    "timezone": research_result.timing_recommendation.timezone,
                    "confidence": research_result.timing_recommendation.confidence_score,
                    "viral_potential": research_result.timing_recommendation.viral_potential,
                    "reasoning": research_result.timing_recommendation.reasoning,
                },
                "content_analysis": {
                    "category": research_result.content_analysis.get("category"),
                    "type": research_result.content_analysis.get("content_type"),
                    "hook_strength": research_result.content_analysis.get("hook_strength", {}).get("score", 0),
                },
                "audience": {
                    "who": research_result.audience_profile.primary_demographic,
                    "timezones": research_result.audience_profile.primary_timezones,
                },
                "trends": [t.topic for t in research_result.trending_data[:3]],
                "suggested_hashtags": research_result.hashtag_suggestions,
                "improvements": research_result.content_improvements,
                "actions": [
                    {
                        "type": "schedule_optimal",
                        "label": f"📅 Schedule for {research_result.timing_recommendation.optimal_time.strftime('%a %I:%M %p')}"
                    },
                    {
                        "type": "post_now",
                        "label": "🚀 Post Now"
                    },
                    {
                        "type": "edit_first",
                        "label": "✏️ Edit Content First"
                    }
                ]
            }
        
        # No content - provide general timing guidance
        # Get current trending topics
        trending = await trend_analyzer.get_trending_topics(platforms=platforms)
        
        # Get personalized times if we have user data
        personalized_times = {}
        for platform in platforms:
            user_optimal = await trend_analyzer.get_personalized_optimal_times(user_id, platform)
            personalized_times[platform] = user_optimal
        
        # Fallback to research-based times
        research_recommendations = optimal_times_service.get_optimal_times(
            platforms=platforms,
            industry=entities.get("industry")
        )
        
        return {
            "action": "schedule_posts",
            "status": "need_content",
            "message": "Share the content you want to schedule, and I'll do deep research to find the PERFECT time!",
            "general_optimal_times": {
                platform: {
                    "best_times": [
                        {"time": slot.time, "day": slot.day, "score": slot.engagement_score}
                        for slot in rec.best_times[:3]
                    ]
                }
                for platform, rec in research_recommendations.items()
            },
            "trending_now": [
                {"topic": t.get("name"), "hashtags": t.get("hashtags", [])}
                for t in trending.get("trends", [])[:5]
            ],
            "tip": "💡 Paste your tweet/post and I'll analyze: topic, audience timezone, trend alignment, competitor timing, and viral potential!",
            "actions": [
                {
                    "type": "paste_content",
                    "label": "📝 Paste Content for Deep Research"
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
            user_id=str(current_user.id),
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
            user_id = str(current_user.id)
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
            "user_id": str(current_user.id)
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
            "user_id": str(current_user.id),
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
            "user_id": str(current_user.id)
        })
        return {"status": "deleted", "conversation_id": conversation_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============= Trend & Timing Endpoints =============

@router.get("/trends")
async def get_trending_topics(
    platforms: str = "twitter,instagram",
    category: str = None,
    limit: int = 10,
    current_user: dict = Depends(get_current_user)
):
    """
    Get real-time trending topics across platforms.
    Use this to create timely, relevant content.
    """
    platform_list = [p.strip() for p in platforms.split(",")]
    
    try:
        trends = await trend_analyzer.get_trending_topics(
            platforms=platform_list,
            category=category,
            limit=limit
        )
        return trends
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/optimal-times/{platform}")
async def get_optimal_times(
    platform: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get PERSONALIZED optimal posting times based on YOUR engagement data.
    Falls back to industry research if you don't have enough posts yet.
    """
    user_id = str(current_user.id)
    
    try:
        # Get personalized times from user's actual data
        personalized = await trend_analyzer.get_personalized_optimal_times(user_id, platform)
        
        if personalized.get("status") == "personalized":
            return {
                "source": "your_engagement_data",
                "confidence": personalized.get("confidence"),
                "based_on": personalized.get("based_on"),
                "best_times": [
                    {
                        "time": slot.time,
                        "day": slot.day,
                        "engagement_rate": slot.engagement_rate,
                        "sample_size": slot.sample_size,
                        "reason": slot.reason
                    }
                    for slot in personalized.get("best_times", [])
                ],
                "worst_times": personalized.get("worst_times", []),
                "insights": personalized.get("insights", [])
            }
        else:
            # Return fallback with research-based times
            research = optimal_times_service.get_optimal_times([platform])
            rec = research.get(platform)
            
            return {
                "source": "industry_research",
                "message": personalized.get("message"),
                "recommendation": personalized.get("recommendation"),
                "best_times": [
                    {
                        "time": slot.time,
                        "day": slot.day,
                        "score": slot.engagement_score,
                        "reason": slot.reason
                    }
                    for slot in rec.best_times[:5]
                ] if rec else personalized.get("fallback_times", []),
                "tips": rec.tips if rec else []
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/smart-schedule")
async def get_smart_scheduling(
    content: str,
    platforms: str = "twitter",
    current_user: dict = Depends(get_current_user)
):
    """
    Get smart scheduling recommendation based on:
    - Your audience's engagement patterns
    - Current trending topics
    - Content-trend alignment
    """
    user_id = str(current_user.id)
    platform_list = [p.strip() for p in platforms.split(",")]
    
    try:
        recommendation = await trend_analyzer.get_smart_posting_recommendation(
            user_id=user_id,
            content=content,
            platforms=platform_list
        )
        return recommendation
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============= Deep Research Endpoint =============

class DeepResearchRequest(BaseModel):
    content: str
    platform: str = "twitter"
    timezone: str = "UTC"


@router.post("/deep-research")
async def run_deep_research(
    request: DeepResearchRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    🔬 DEEP RESEARCH - The full package!
    
    Comprehensive analysis before posting:
    1. Content Analysis (topic, keywords, sentiment, hook strength)
    2. Audience Intelligence (who, timezone, when they're active)
    3. Real-time Trends (what's hot, related hashtags)
    4. Competitor Insights (when top accounts post)
    5. Optimal Timing (exact time with confidence score)
    6. Viral Potential Score
    7. Content Improvement Suggestions
    8. Hashtag Recommendations
    """
    user_id = str(current_user.id)
    
    try:
        # Run comprehensive research
        result = await deep_research_engine.research_optimal_posting(
            content=request.content,
            platform=request.platform,
            user_timezone=request.timezone,
            user_id=user_id
        )
        
        # Format for display
        formatted_result = deep_research_engine.format_research_for_display(result)
        
        # Return both raw data and formatted
        return {
            "status": "complete",
            "formatted": formatted_result,
            "data": {
                "content_analysis": result.content_analysis,
                "audience": {
                    "demographic": result.audience_profile.primary_demographic,
                    "age_range": result.audience_profile.age_range,
                    "timezones": result.audience_profile.primary_timezones,
                    "peak_hours": result.audience_profile.peak_activity_hours,
                    "device": result.audience_profile.device_preference,
                },
                "timing": {
                    "optimal_time": result.timing_recommendation.optimal_time.isoformat(),
                    "timezone": result.timing_recommendation.timezone,
                    "confidence": result.timing_recommendation.confidence_score,
                    "viral_potential": result.timing_recommendation.viral_potential,
                    "reasoning": result.timing_recommendation.reasoning,
                    "warnings": result.timing_recommendation.warnings,
                    "action_items": result.timing_recommendation.action_items,
                    "alternatives": [
                        {"time": t.isoformat(), "score": s}
                        for t, s in result.timing_recommendation.alternative_times
                    ]
                },
                "trends": [
                    {
                        "topic": t.topic,
                        "hashtags": t.related_hashtags,
                        "is_growing": not t.is_peak,
                        "news": t.news_events
                    }
                    for t in result.trending_data[:5]
                ],
                "hashtags": result.hashtag_suggestions,
                "improvements": result.content_improvements,
                "competitors": result.competitor_insights
            },
            "research_timestamp": result.research_timestamp
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============= Raw Real-Time Data Endpoints =============

@router.get("/realtime/twitter-trends")
async def get_live_twitter_trends(
    woeid: int = 1,  # 1=Worldwide, 23424977=US
    current_user: dict = Depends(get_current_user)
):
    """
    Get LIVE Twitter trending topics.
    
    WOEID locations:
    - 1 = Worldwide
    - 23424977 = United States
    - 23424975 = United Kingdom
    - 23424848 = India
    - 23424768 = Brazil
    """
    try:
        trends = await real_time_research.get_twitter_trends(woeid)
        return {
            "source": "twitter",
            "is_real_data": trends[0].is_real_data if trends else False,
            "trends": [
                {
                    "name": t.name,
                    "volume": t.volume,
                    "velocity": t.velocity,
                    "hashtags": t.hashtags,
                    "url": t.url
                }
                for t in trends
            ],
            "fetched_at": trends[0].fetched_at if trends else None,
            "api_status": "🟢 LIVE" if (trends and trends[0].is_real_data) else "🟡 Fallback"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/realtime/reddit/{category}")
async def get_live_reddit_trends(
    category: str,  # crypto, ai, tech, defi, startup
    current_user: dict = Depends(get_current_user)
):
    """
    Get LIVE hot posts from relevant subreddits.
    
    Categories: crypto, ai, tech, defi, startup
    """
    try:
        trends = await real_time_research.get_reddit_hot(category)
        return {
            "source": "reddit",
            "category": category,
            "is_real_data": trends[0].is_real_data if trends else False,
            "posts": [
                {
                    "title": t.name,
                    "score": t.volume,
                    "velocity": t.velocity,
                    "subreddit": t.related_topics[0] if t.related_topics else "",
                    "url": t.url,
                    "sentiment": t.sentiment
                }
                for t in trends
            ],
            "fetched_at": trends[0].fetched_at if trends else None,
            "api_status": "🟢 LIVE" if (trends and trends[0].is_real_data) else "🟡 Fallback"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/realtime/news/{topic}")
async def get_live_news(
    topic: str,
    hours: int = 24,
    current_user: dict = Depends(get_current_user)
):
    """
    Get LIVE news articles about a topic from the last N hours.
    """
    try:
        news = await real_time_research.get_news_for_topic(topic, hours)
        return {
            "source": "newsapi",
            "topic": topic,
            "is_real_data": news[0].get("is_real_data", False) if news else False,
            "articles": news,
            "api_status": "🟢 LIVE" if (news and news[0].get("is_real_data")) else "🔴 No API Key"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/realtime/google-trends/{keyword}")
async def get_google_trends_data(
    keyword: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get Google Trends data for a keyword.
    """
    try:
        data = await real_time_research.get_google_trends(keyword)
        return {
            "source": "google_trends",
            "keyword": keyword,
            **data,
            "api_status": "🟢 LIVE" if data.get("is_real_data") else "🔴 No API Key"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/realtime/competitor/{username}")
async def analyze_competitor(
    username: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Analyze a competitor's posting patterns (Twitter).
    
    Returns:
    - Recent posting times
    - Posting frequency
    - Average engagement
    - Best performing content
    """
    try:
        insight = await real_time_research.get_competitor_posting_times(username)
        return {
            "source": "twitter",
            "handle": f"@{insight.handle}",
            "is_real_data": insight.is_real_data,
            "posting_frequency": insight.posting_frequency,
            "recent_post_times": insight.recent_post_times,
            "avg_engagement": insight.avg_engagement,
            "best_performing_content": insight.best_performing_content,
            "api_status": "🟢 LIVE" if insight.is_real_data else "🔴 No API Key"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/realtime/comprehensive")
async def comprehensive_realtime_research(
    topic: str,
    category: str = "crypto",
    competitors: str = "",  # Comma-separated usernames
    current_user: dict = Depends(get_current_user)
):
    """
    🔬 COMPREHENSIVE REAL-TIME RESEARCH
    
    Fetches data from ALL sources:
    - Twitter trending topics
    - Twitter hashtag volume
    - Reddit hot posts
    - News articles
    - Google Trends
    - Competitor analysis
    
    Returns data quality score showing what % is real vs fallback.
    """
    try:
        competitor_list = [c.strip() for c in competitors.split(",") if c.strip()]
        
        result = await real_time_research.comprehensive_research(
            topic=topic,
            category=category,
            competitors=competitor_list or None
        )
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/realtime/status")
async def check_api_status(
    current_user: dict = Depends(get_current_user)
):
    """
    Check which real-time APIs are configured and working.
    """
    import os
    
    return {
        "apis": {
            "twitter": {
                "configured": bool(os.getenv("TWITTER_BEARER_TOKEN")),
                "key_name": "TWITTER_BEARER_TOKEN",
                "get_key_at": "https://developer.twitter.com/en/portal/dashboard"
            },
            "reddit": {
                "configured": bool(os.getenv("REDDIT_CLIENT_ID") and os.getenv("REDDIT_CLIENT_SECRET")),
                "key_names": ["REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET"],
                "get_key_at": "https://www.reddit.com/prefs/apps"
            },
            "news_api": {
                "configured": bool(os.getenv("NEWS_API_KEY")),
                "key_name": "NEWS_API_KEY",
                "get_key_at": "https://newsapi.org/register"
            },
            "google_trends": {
                "configured": bool(os.getenv("SERP_API_KEY")),
                "key_name": "SERP_API_KEY",
                "get_key_at": "https://serpapi.com/"
            },
            "groq_ai": {
                "configured": bool(os.getenv("GROQ_API_KEY")),
                "key_name": "GROQ_API_KEY",
                "get_key_at": "https://console.groq.com/"
            }
        },
        "recommendation": "Add missing API keys to Railway environment variables for full real-time research capabilities."
    }


# ============= FREE Research Endpoints (No API Keys Needed!) =============

@router.get("/free/twitter/{country}")
async def get_free_twitter_trends(
    country: str = "us",  # us, uk, india, worldwide, etc.
    current_user: dict = Depends(get_current_user)
):
    """
    🆓 FREE - Get REAL Twitter trending topics!
    
    No Twitter API key required! Uses TrendsTools free API.
    
    Countries: us, uk, india, brazil, worldwide, canada, australia, germany, france, japan
    """
    try:
        trends = await free_research.get_twitter_trends_free(country)
        return {
            "source": "trendstools_api",
            "platform": "twitter",
            "country": country,
            "cost": "FREE",
            "is_real_data": trends[0].is_real_data if trends else False,
            "trends": [
                {
                    "topic": t.topic,
                    "volume": t.volume,
                    "velocity": round(t.velocity, 2),
                    "url": t.url
                }
                for t in trends
            ],
            "fetched_at": trends[0].fetched_at if trends else None,
            "note": "Real Twitter trends without $100/mo API cost!"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/free/google-trends-trendstools/{country}")
async def get_free_google_trends_trendstools(
    country: str = "us",
    current_user: dict = Depends(get_current_user)
):
    """
    🆓 FREE - Get Google Trends via TrendsTools.
    
    No API key required!
    """
    try:
        trends = await free_research.get_google_trends_via_trendstools(country)
        return {
            "source": "trendstools_api",
            "platform": "google_trends",
            "country": country,
            "cost": "FREE",
            "is_real_data": trends[0].is_real_data if trends else False,
            "trends": [
                {
                    "topic": t.topic,
                    "traffic": t.volume,
                    "url": t.url
                }
                for t in trends
            ],
            "fetched_at": trends[0].fetched_at if trends else None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/free/youtube/{country}")
async def get_free_youtube_trends(
    country: str = "us",
    current_user: dict = Depends(get_current_user)
):
    """
    🆓 FREE - Get YouTube trending videos.
    
    No API key required! Uses TrendsTools free API.
    """
    try:
        videos = await free_research.get_youtube_trends_free(country)
        return {
            "source": "trendstools_api",
            "platform": "youtube",
            "country": country,
            "cost": "FREE",
            "is_real_data": len(videos) > 0,
            "videos": videos,
            "note": "Free YouTube trends without YouTube API quota!"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/free/reddit/{category}")
async def get_free_reddit_trends(
    category: str,  # crypto, ai, tech, defi, startup, nft
    current_user: dict = Depends(get_current_user)
):
    """
    🆓 FREE - Get trending posts from Reddit.
    
    No API key required! Uses Reddit's public JSON endpoints.
    
    Categories: crypto, ai, tech, defi, startup, nft
    """
    try:
        trends = await free_research.get_reddit_trends(category)
        return {
            "source": "reddit_public_api",
            "category": category,
            "cost": "FREE",
            "is_real_data": trends[0].is_real_data if trends else False,
            "posts": [
                {
                    "title": t.topic,
                    "score": t.volume,
                    "velocity": round(t.velocity, 2),
                    "subreddit": t.related_topics[0] if t.related_topics else "",
                    "url": t.url,
                    "sentiment": t.sentiment
                }
                for t in trends
            ],
            "fetched_at": trends[0].fetched_at if trends else None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/free/news/{category}")
async def get_free_news(
    category: str,  # crypto, ai, tech, startup
    limit: int = 10,
    current_user: dict = Depends(get_current_user)
):
    """
    🆓 FREE - Get news from RSS feeds.
    
    No API key required! Works in production (unlike NewsAPI free tier).
    
    Categories: crypto, ai, tech, startup
    """
    try:
        news = await free_research.get_news_from_rss(category, limit)
        return {
            "source": "rss_feeds",
            "category": category,
            "cost": "FREE",
            "is_real_data": len(news) > 0,
            "articles": news,
            "note": "RSS feeds - works in production (unlike NewsAPI free tier)"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/free/crypto")
async def get_free_crypto_trends(
    current_user: dict = Depends(get_current_user)
):
    """
    🆓 FREE - Get crypto market trends from CoinGecko.
    
    No API key required!
    Returns: trending coins, market cap, BTC dominance, etc.
    """
    try:
        data = await free_research.get_crypto_trends()
        return {
            "source": "coingecko_api",
            "cost": "FREE",
            **data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/free/google-trends/{keyword}")
async def get_free_google_trends(
    keyword: str,
    current_user: dict = Depends(get_current_user)
):
    """
    🆓 FREE - Get Google Trends data using PyTrends.
    
    No API key required! Uses Google's public interface.
    May be rate limited if overused.
    """
    try:
        data = await free_research.get_google_trends_free(keyword)
        return {
            "source": "pytrends_library",
            "cost": "FREE",
            **data,
            "note": "Uses web scraping, may be rate limited"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/free/comprehensive")
async def comprehensive_free_research_endpoint(
    topic: str,
    category: str = "crypto",
    country: str = "us",
    current_user: dict = Depends(get_current_user)
):
    """
    🆓 FREE COMPREHENSIVE RESEARCH - THE FULL PACKAGE!
    
    Fetches from ALL free sources:
    - 🐦 Twitter Trends (via TrendsTools - FREE!)
    - 📈 Google Trends (via TrendsTools - FREE!)
    - 📺 YouTube Trends (via TrendsTools - FREE!)
    - 🟠 Reddit Hot Posts (public API - FREE!)
    - 📰 RSS News Feeds (FREE!)
    - 💰 CoinGecko crypto data (FREE!)
    - 🤖 Groq AI analysis (FREE tier!)
    
    ZERO paid APIs required! Total cost: $0.00
    """
    try:
        result = await free_research.comprehensive_free_research(topic, category, country)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/free/status")
async def check_free_api_status():
    """
    Check status of FREE data sources.
    No authentication required for this endpoint.
    """
    import os
    
    return {
        "free_sources": {
            "twitter_trends": {
                "status": "✅ FREE via TrendsTools!",
                "api_key_required": False,
                "endpoint": "/chat/free/twitter/{country}",
                "note": "REAL Twitter trends without $100/mo API cost!"
            },
            "google_trends": {
                "status": "✅ FREE via TrendsTools!",
                "api_key_required": False,
                "endpoint": "/chat/free/google-trends-trendstools/{country}",
                "note": "No SerpAPI needed!"
            },
            "youtube_trends": {
                "status": "✅ FREE via TrendsTools!",
                "api_key_required": False,
                "endpoint": "/chat/free/youtube/{country}",
                "note": "Trending videos without YouTube API quota"
            },
            "reddit": {
                "status": "✅ Always FREE",
                "api_key_required": False,
                "endpoint": "/chat/free/reddit/{category}",
                "note": "Uses public JSON endpoints"
            },
            "rss_news": {
                "status": "✅ Always FREE", 
                "api_key_required": False,
                "endpoint": "/chat/free/news/{category}",
                "note": "RSS feeds work in production (unlike NewsAPI)"
            },
            "coingecko": {
                "status": "✅ Always FREE",
                "api_key_required": False,
                "endpoint": "/chat/free/crypto",
                "note": "Great for crypto market data"
            },
            "groq_ai": {
                "status": "✅ FREE tier" if os.getenv("GROQ_API_KEY") else "⚠️ Need GROQ_API_KEY",
                "api_key_required": True,
                "endpoint": "Used in comprehensive research",
                "get_key_at": "https://console.groq.com/",
                "note": "Generous free tier - 30 RPM"
            }
        },
        "paid_sources_bypassed": {
            "twitter_api": {
                "official_cost": "$100-5000/month",
                "our_solution": "TrendsTools API (FREE)",
                "savings": "100%"
            },
            "newsapi": {
                "official_cost": "$449/month for production",
                "our_solution": "RSS Feeds (FREE)",
                "savings": "100%"
            },
            "serpapi": {
                "official_cost": "$75+/month",
                "our_solution": "TrendsTools + PyTrends (FREE)",
                "savings": "100%"
            },
            "youtube_api": {
                "official_cost": "Quota limited",
                "our_solution": "TrendsTools API (FREE)",
                "savings": "100%"
            }
        },
        "total_monthly_savings": "$624+ (Twitter $100 + NewsAPI $449 + SerpAPI $75)",
        "recommendation": "Only GROQ_API_KEY is needed for full functionality!",
        "comprehensive_endpoint": "POST /chat/free/comprehensive - Gets ALL data at once!"
    }

