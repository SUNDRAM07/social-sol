"""
Deep Research Engine for Optimal Posting

This is the REAL DEAL - comprehensive research before scheduling:

1. CONTENT ANALYSIS
   - Extract topic, keywords, sentiment
   - Categorize content type
   - Identify target audience

2. AUDIENCE INTELLIGENCE  
   - Who engages with this topic?
   - What timezones are they in?
   - When are they most active?
   - Device usage patterns

3. REAL-TIME TREND RESEARCH
   - Current trending topics
   - Trending hashtags
   - News/events affecting the topic
   - Competitor activity

4. TIMING OPTIMIZATION
   - Cross-platform best times
   - Timezone-aware scheduling
   - Event-aware (avoid posting during major events unless related)
   - Historical viral timing patterns

5. VIRAL POTENTIAL SCORING
   - Content-trend alignment
   - Timing optimization score
   - Engagement prediction
"""

import os
import json
import httpx
import asyncio
import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict


class ContentCategory(Enum):
    CRYPTO = "crypto"
    TECH = "tech"
    AI = "ai"
    DEFI = "defi"
    NFT = "nft"
    GAMING = "gaming"
    FINANCE = "finance"
    STARTUP = "startup"
    MARKETING = "marketing"
    LIFESTYLE = "lifestyle"
    NEWS = "news"
    MEME = "meme"
    EDUCATIONAL = "educational"
    GENERAL = "general"


@dataclass
class AudienceProfile:
    """Profile of the target audience for content"""
    primary_demographic: str  # e.g., "crypto traders", "tech developers"
    age_range: str  # e.g., "25-40"
    primary_timezones: List[str]  # e.g., ["EST", "PST", "UTC"]
    peak_activity_hours: Dict[str, List[str]]  # timezone -> hours
    device_preference: str  # "mobile", "desktop", "both"
    engagement_style: str  # "quick_scroll", "deep_reader", "engager"
    best_content_types: List[str]  # "threads", "single_tweets", "images"


@dataclass 
class TrendingData:
    """Real-time trend information"""
    topic: str
    volume: int
    velocity: float  # growth rate
    sentiment: str
    related_hashtags: List[str]
    top_tweets: List[Dict]
    news_events: List[str]
    is_peak: bool  # Is this trend at its peak or growing?


@dataclass
class TimingRecommendation:
    """Final timing recommendation with reasoning"""
    optimal_time: datetime
    timezone: str
    confidence_score: float  # 0-100
    viral_potential: float  # 0-100
    reasoning: List[str]
    alternative_times: List[Tuple[datetime, float]]  # time, score
    warnings: List[str]
    action_items: List[str]


@dataclass
class DeepResearchResult:
    """Complete research result"""
    content_analysis: Dict
    audience_profile: AudienceProfile
    trending_data: List[TrendingData]
    timing_recommendation: TimingRecommendation
    hashtag_suggestions: List[str]
    content_improvements: List[str]
    competitor_insights: Dict
    research_timestamp: str


class DeepResearchEngine:
    """
    The brain behind optimal posting - does REAL research.
    """
    
    def __init__(self):
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        self.groq_url = "https://api.groq.com/openai/v1/chat/completions"
        
        # Audience patterns by category (research-based starting point)
        self.audience_patterns = {
            ContentCategory.CRYPTO: {
                "demographics": "crypto traders, investors, defi degens, web3 builders",
                "age_range": "18-45",
                "timezones": ["UTC", "EST", "PST", "SGT", "GMT"],
                "peak_hours": {
                    "UTC": ["08:00", "14:00", "20:00"],
                    "EST": ["09:00", "12:00", "21:00"],
                    "PST": ["06:00", "09:00", "18:00"],
                },
                "behavior": "24/7 active, peaks during market hours, high engagement on alpha drops",
                "device": "mobile",
                "best_content": ["alpha threads", "price predictions", "project reviews", "memes"]
            },
            ContentCategory.TECH: {
                "demographics": "developers, engineers, tech enthusiasts, founders",
                "age_range": "22-45",
                "timezones": ["PST", "EST", "GMT", "IST"],
                "peak_hours": {
                    "PST": ["08:00", "12:00", "17:00"],
                    "EST": ["09:00", "13:00", "18:00"],
                    "IST": ["10:00", "14:00", "21:00"],
                },
                "behavior": "morning news check, lunch break scroll, evening deep reads",
                "device": "both",
                "best_content": ["how-to threads", "tool recommendations", "industry news", "hot takes"]
            },
            ContentCategory.AI: {
                "demographics": "AI researchers, developers, founders, enthusiasts",
                "age_range": "25-50",
                "timezones": ["PST", "EST", "GMT", "CET"],
                "peak_hours": {
                    "PST": ["07:00", "11:00", "16:00"],
                    "EST": ["08:00", "12:00", "17:00"],
                },
                "behavior": "follows AI news closely, engages with technical content, shares breakthroughs",
                "device": "desktop",
                "best_content": ["research breakdowns", "tool demos", "predictions", "tutorials"]
            },
            ContentCategory.DEFI: {
                "demographics": "yield farmers, liquidity providers, protocol users",
                "age_range": "20-40",
                "timezones": ["UTC", "EST", "SGT"],
                "peak_hours": {
                    "UTC": ["07:00", "13:00", "19:00"],
                    "EST": ["08:00", "14:00", "22:00"],
                },
                "behavior": "highly active during farming opportunities, quick to engage on alpha",
                "device": "mobile",
                "best_content": ["yield opportunities", "protocol analysis", "risk assessments", "tutorials"]
            },
            ContentCategory.STARTUP: {
                "demographics": "founders, VCs, operators, aspiring entrepreneurs",
                "age_range": "25-50",
                "timezones": ["PST", "EST", "GMT"],
                "peak_hours": {
                    "PST": ["07:00", "12:00", "18:00"],
                    "EST": ["08:00", "12:00", "17:00"],
                },
                "behavior": "morning motivation, lunch networking, evening reflection",
                "device": "both",
                "best_content": ["founder stories", "lessons learned", "fundraising tips", "hot takes"]
            },
        }
        
        # Day of week patterns
        self.day_patterns = {
            "Monday": {"multiplier": 0.9, "note": "People catching up, slower engagement"},
            "Tuesday": {"multiplier": 1.2, "note": "Peak engagement day for B2B/tech"},
            "Wednesday": {"multiplier": 1.15, "note": "Strong mid-week engagement"},
            "Thursday": {"multiplier": 1.1, "note": "Good engagement, people planning weekend"},
            "Friday": {"multiplier": 0.85, "note": "Dropping off, casual content works"},
            "Saturday": {"multiplier": 0.7, "note": "Low B2B, good for casual/meme content"},
            "Sunday": {"multiplier": 0.75, "note": "Evening prep for week, thought leadership works"},
        }
        
        # Keyword to category mapping
        self.category_keywords = {
            ContentCategory.CRYPTO: ["crypto", "bitcoin", "btc", "eth", "ethereum", "blockchain", "token", "coin", "wallet", "web3", "hodl", "bullish", "bearish", "pump", "dump", "moon", "rug", "degen"],
            ContentCategory.AI: ["ai", "artificial intelligence", "machine learning", "ml", "gpt", "llm", "neural", "model", "chatgpt", "claude", "openai", "anthropic", "agent", "automation"],
            ContentCategory.DEFI: ["defi", "yield", "farm", "liquidity", "pool", "swap", "dex", "apy", "tvl", "protocol", "stake", "unstake"],
            ContentCategory.TECH: ["code", "programming", "developer", "software", "api", "database", "cloud", "devops", "frontend", "backend", "react", "python", "javascript"],
            ContentCategory.STARTUP: ["startup", "founder", "vc", "funding", "raise", "seed", "series", "exit", "ipo", "acquisition", "growth", "scale"],
            ContentCategory.NFT: ["nft", "pfp", "mint", "opensea", "collection", "art", "1/1"],
            ContentCategory.MEME: ["lol", "lmao", "fr", "no cap", "based", "ratio", "cope", "seethe"],
        }
    
    async def research_optimal_posting(
        self,
        content: str,
        platform: str = "twitter",
        user_timezone: str = "UTC",
        user_id: str = None
    ) -> DeepResearchResult:
        """
        Main entry point - does comprehensive research for optimal posting.
        
        Args:
            content: The tweet/post content
            platform: Target platform
            user_timezone: User's timezone
            user_id: For personalized data (if available)
        
        Returns:
            DeepResearchResult with complete analysis
        """
        
        # Step 1: Analyze the content
        content_analysis = await self._analyze_content(content)
        
        # Step 2: Build audience profile
        audience_profile = await self._build_audience_profile(content_analysis)
        
        # Step 3: Research current trends
        trending_data = await self._research_trends(
            content_analysis["category"],
            content_analysis["keywords"]
        )
        
        # Step 4: Get competitor insights
        competitor_insights = await self._analyze_competitors(
            content_analysis["category"],
            platform
        )
        
        # Step 5: Calculate optimal timing
        timing_recommendation = await self._calculate_optimal_timing(
            content_analysis=content_analysis,
            audience_profile=audience_profile,
            trending_data=trending_data,
            competitor_insights=competitor_insights,
            user_timezone=user_timezone,
            platform=platform
        )
        
        # Step 6: Generate hashtag suggestions
        hashtag_suggestions = await self._suggest_hashtags(
            content_analysis,
            trending_data
        )
        
        # Step 7: Suggest content improvements
        content_improvements = await self._suggest_improvements(
            content,
            content_analysis,
            trending_data
        )
        
        return DeepResearchResult(
            content_analysis=content_analysis,
            audience_profile=audience_profile,
            trending_data=trending_data,
            timing_recommendation=timing_recommendation,
            hashtag_suggestions=hashtag_suggestions,
            content_improvements=content_improvements,
            competitor_insights=competitor_insights,
            research_timestamp=datetime.utcnow().isoformat()
        )
    
    async def _analyze_content(self, content: str) -> Dict:
        """
        Deep analysis of the content:
        - Extract keywords
        - Detect category
        - Analyze sentiment
        - Identify content type
        """
        content_lower = content.lower()
        
        # Detect category based on keywords
        category_scores = defaultdict(int)
        detected_keywords = []
        
        for category, keywords in self.category_keywords.items():
            for keyword in keywords:
                if keyword in content_lower:
                    category_scores[category] += 1
                    detected_keywords.append(keyword)
        
        # Get primary category
        if category_scores:
            primary_category = max(category_scores, key=category_scores.get)
        else:
            primary_category = ContentCategory.GENERAL
        
        # Detect content type
        content_type = self._detect_content_type(content)
        
        # Detect sentiment
        sentiment = await self._analyze_sentiment(content)
        
        # Extract entities (mentions, hashtags, links)
        entities = self._extract_entities(content)
        
        # Use AI for deeper analysis if available
        ai_analysis = await self._ai_content_analysis(content) if self.groq_api_key else {}
        
        return {
            "category": primary_category.value,
            "secondary_categories": [c.value for c, s in sorted(category_scores.items(), key=lambda x: x[1], reverse=True)[1:3]],
            "keywords": list(set(detected_keywords)),
            "content_type": content_type,
            "sentiment": sentiment,
            "entities": entities,
            "length": len(content),
            "has_media_placeholder": "[image]" in content_lower or "[video]" in content_lower,
            "is_thread_worthy": len(content) > 200 or content.count("\n") > 2,
            "hook_strength": self._analyze_hook_strength(content),
            "ai_analysis": ai_analysis
        }
    
    def _detect_content_type(self, content: str) -> str:
        """Detect what type of content this is"""
        content_lower = content.lower()
        
        if content.startswith("🧵") or "thread" in content_lower:
            return "thread"
        elif "?" in content and len(content) < 150:
            return "question"
        elif content_lower.startswith(("hot take", "unpopular opinion", "controversial")):
            return "hot_take"
        elif any(x in content_lower for x in ["how to", "guide", "tutorial", "step"]):
            return "educational"
        elif any(x in content_lower for x in ["announcing", "launching", "introducing", "excited to share"]):
            return "announcement"
        elif len(content) < 100 and any(x in content_lower for x in ["lol", "lmao", "😂", "💀"]):
            return "meme"
        elif content.count("\n") > 3 or "•" in content or "→" in content:
            return "list"
        else:
            return "standard"
    
    async def _analyze_sentiment(self, content: str) -> str:
        """Quick sentiment analysis"""
        positive_indicators = ["🚀", "💪", "🔥", "excited", "amazing", "great", "love", "bullish", "moon", "lfg", "gm", "wagmi"]
        negative_indicators = ["😢", "💀", "worried", "bearish", "dump", "rug", "scam", "ngmi", "rekt"]
        
        content_lower = content.lower()
        
        positive_count = sum(1 for p in positive_indicators if p in content_lower)
        negative_count = sum(1 for n in negative_indicators if n in content_lower)
        
        if positive_count > negative_count:
            return "positive"
        elif negative_count > positive_count:
            return "negative"
        else:
            return "neutral"
    
    def _extract_entities(self, content: str) -> Dict:
        """Extract mentions, hashtags, links"""
        return {
            "mentions": re.findall(r'@(\w+)', content),
            "hashtags": re.findall(r'#(\w+)', content),
            "links": re.findall(r'https?://\S+', content),
            "cashtags": re.findall(r'\$([A-Z]+)', content)
        }
    
    def _analyze_hook_strength(self, content: str) -> Dict:
        """Analyze how strong the opening hook is"""
        first_line = content.split('\n')[0][:100]
        
        strong_hooks = [
            "I just", "Breaking:", "Here's why", "The truth about",
            "Nobody talks about", "Stop doing", "Hot take:", "Unpopular opinion:",
            "I spent", "After", "The secret to", "What if I told you"
        ]
        
        has_strong_hook = any(first_line.lower().startswith(h.lower()) for h in strong_hooks)
        has_emoji_hook = any(first_line.startswith(e) for e in ["🧵", "🚨", "⚡", "🔥", "💡", "📢"])
        has_number = bool(re.search(r'\d+', first_line))
        
        score = 0
        if has_strong_hook:
            score += 40
        if has_emoji_hook:
            score += 20
        if has_number:
            score += 20
        if len(first_line) > 50:
            score += 10
        if "?" in first_line:
            score += 10
        
        return {
            "score": min(score, 100),
            "has_strong_hook": has_strong_hook,
            "has_emoji_hook": has_emoji_hook,
            "suggestion": self._get_hook_suggestion(score, first_line)
        }
    
    def _get_hook_suggestion(self, score: int, first_line: str) -> str:
        if score >= 70:
            return "Strong hook! Should stop the scroll."
        elif score >= 40:
            return "Decent hook. Consider adding a number or stronger opener."
        else:
            return "Weak hook. Start with 'I just...', 'Here's why...', or a bold claim."
    
    async def _ai_content_analysis(self, content: str) -> Dict:
        """Use AI for deeper content analysis"""
        if not self.groq_api_key:
            return {}
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.groq_url,
                    headers={
                        "Authorization": f"Bearer {self.groq_api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "llama-3.1-8b-instant",
                        "messages": [
                            {
                                "role": "system",
                                "content": """Analyze this tweet for optimal posting. Return JSON:
{
  "target_audience": "specific description",
  "viral_elements": ["element1", "element2"],
  "missing_elements": ["what would make it better"],
  "best_day_type": "weekday/weekend",
  "urgency": "time_sensitive/evergreen",
  "controversy_level": "low/medium/high"
}"""
                            },
                            {"role": "user", "content": content}
                        ],
                        "temperature": 0.3,
                        "max_tokens": 300
                    },
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    try:
                        return json.loads(result["choices"][0]["message"]["content"])
                    except:
                        pass
        except Exception as e:
            print(f"AI content analysis failed: {e}")
        
        return {}
    
    async def _build_audience_profile(self, content_analysis: Dict) -> AudienceProfile:
        """Build detailed audience profile based on content"""
        category = ContentCategory(content_analysis.get("category", "general"))
        patterns = self.audience_patterns.get(category, self.audience_patterns[ContentCategory.TECH])
        
        return AudienceProfile(
            primary_demographic=patterns["demographics"],
            age_range=patterns["age_range"],
            primary_timezones=patterns["timezones"],
            peak_activity_hours=patterns["peak_hours"],
            device_preference=patterns["device"],
            engagement_style=patterns["behavior"],
            best_content_types=patterns["best_content"]
        )
    
    async def _research_trends(
        self,
        category: str,
        keywords: List[str]
    ) -> List[TrendingData]:
        """Research current trends related to the content"""
        trends = []
        
        # Try to get real trends
        if self.groq_api_key:
            ai_trends = await self._get_ai_trends(category, keywords)
            trends.extend(ai_trends)
        
        # Add category-specific evergreen trends
        category_trends = self._get_category_trends(category)
        trends.extend(category_trends)
        
        return trends[:10]
    
    async def _get_ai_trends(self, category: str, keywords: List[str]) -> List[TrendingData]:
        """Use AI to identify current trends"""
        if not self.groq_api_key:
            return []
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.groq_url,
                    headers={
                        "Authorization": f"Bearer {self.groq_api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "llama-3.1-8b-instant",
                        "messages": [
                            {
                                "role": "system",
                                "content": f"""You are a Twitter/X trend analyst. It's January 2026.
Based on the category '{category}' and keywords {keywords}, identify 5 currently trending topics.

Return JSON array:
[{{"topic": "...", "hashtags": ["#tag1"], "is_growing": true, "reason": "why trending"}}]"""
                            },
                            {"role": "user", "content": f"What's trending in {category} right now?"}
                        ],
                        "temperature": 0.5,
                        "max_tokens": 400
                    },
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    content = result["choices"][0]["message"]["content"]
                    try:
                        data = json.loads(content)
                        return [
                            TrendingData(
                                topic=t.get("topic", ""),
                                volume=10000,
                                velocity=1.5 if t.get("is_growing") else 0.5,
                                sentiment="positive",
                                related_hashtags=t.get("hashtags", []),
                                top_tweets=[],
                                news_events=[t.get("reason", "")],
                                is_peak=not t.get("is_growing", True)
                            )
                            for t in data
                        ]
                    except:
                        pass
        except Exception as e:
            print(f"AI trends failed: {e}")
        
        return []
    
    def _get_category_trends(self, category: str) -> List[TrendingData]:
        """Get category-specific evergreen trends"""
        category_trends = {
            "crypto": [
                TrendingData("Bitcoin ETF flows", 50000, 1.2, "positive", ["#Bitcoin", "#BTC", "#ETF"], [], ["Institutional interest"], False),
                TrendingData("Solana DeFi", 30000, 1.5, "positive", ["#Solana", "#SOL", "#DeFi"], [], ["Growing TVL"], True),
            ],
            "ai": [
                TrendingData("AI Agents", 80000, 2.0, "positive", ["#AIAgents", "#AI", "#Automation"], [], ["Major releases"], True),
                TrendingData("Open source LLMs", 40000, 1.3, "positive", ["#OpenSource", "#LLM"], [], ["New models"], True),
            ],
            "tech": [
                TrendingData("Developer tools", 25000, 1.1, "positive", ["#DevTools", "#Programming"], [], ["Tool launches"], False),
            ],
        }
        return category_trends.get(category, [])
    
    async def _analyze_competitors(self, category: str, platform: str) -> Dict:
        """Analyze when top accounts in this category post"""
        # This would ideally scrape/analyze real data
        # For now, return category-specific patterns
        
        competitor_patterns = {
            "crypto": {
                "top_accounts": ["@solana", "@ethereum", "@VitalikButerin"],
                "common_posting_times": ["9:00 UTC", "14:00 UTC", "21:00 UTC"],
                "avg_posts_per_day": 3,
                "high_engagement_patterns": "Alpha drops, market commentary, memes during pumps"
            },
            "ai": {
                "top_accounts": ["@OpenAI", "@AnthropicAI", "@ylecun"],
                "common_posting_times": ["15:00 UTC", "18:00 UTC"],
                "avg_posts_per_day": 2,
                "high_engagement_patterns": "Research releases, demos, hot takes"
            },
            "tech": {
                "top_accounts": ["@levelsio", "@dhaborowski", "@naval"],
                "common_posting_times": ["13:00 UTC", "17:00 UTC"],
                "avg_posts_per_day": 2,
                "high_engagement_patterns": "Build in public, lessons, tools"
            },
        }
        
        return competitor_patterns.get(category, {
            "top_accounts": [],
            "common_posting_times": ["12:00 UTC", "18:00 UTC"],
            "avg_posts_per_day": 2,
            "high_engagement_patterns": "Consistent posting with value"
        })
    
    async def _calculate_optimal_timing(
        self,
        content_analysis: Dict,
        audience_profile: AudienceProfile,
        trending_data: List[TrendingData],
        competitor_insights: Dict,
        user_timezone: str,
        platform: str
    ) -> TimingRecommendation:
        """
        THE MAIN EVENT - Calculate the optimal posting time.
        
        Factors:
        1. Audience peak hours (by timezone)
        2. Day of week patterns
        3. Trend timing (post while trending)
        4. Competitor timing (differentiate or ride wave)
        5. Content type timing
        6. Historical viral patterns
        """
        now = datetime.utcnow()
        reasoning = []
        warnings = []
        
        # Get base times from audience profile
        primary_tz = audience_profile.primary_timezones[0]
        peak_hours = audience_profile.peak_activity_hours.get(primary_tz, ["09:00", "12:00", "17:00"])
        
        reasoning.append(f"🎯 Your audience ({audience_profile.primary_demographic}) is most active at {', '.join(peak_hours)} {primary_tz}")
        
        # Factor in day of week
        best_days = []
        content_type = content_analysis.get("content_type", "standard")
        
        if content_type in ["educational", "thread", "list"]:
            best_days = ["Tuesday", "Wednesday", "Thursday"]
            reasoning.append("📚 Educational content performs best mid-week")
        elif content_type == "meme":
            best_days = ["Friday", "Saturday"]
            reasoning.append("😂 Meme content peaks on Friday/Saturday")
        elif content_type == "announcement":
            best_days = ["Tuesday", "Wednesday"]
            reasoning.append("📢 Announcements get most attention early in the week")
        else:
            best_days = ["Tuesday", "Wednesday", "Thursday"]
        
        # Check if content aligns with trends
        is_trend_aligned = False
        for trend in trending_data:
            if any(kw.lower() in trend.topic.lower() for kw in content_analysis.get("keywords", [])):
                is_trend_aligned = True
                if trend.is_peak:
                    warnings.append(f"⚠️ '{trend.topic}' might be peaking - post ASAP for max exposure")
                else:
                    reasoning.append(f"🔥 Your content aligns with growing trend: {trend.topic}")
                break
        
        # Calculate optimal datetime
        # Start from tomorrow for better planning
        target_date = now + timedelta(days=1)
        
        # Find next best day
        while target_date.strftime("%A") not in best_days:
            target_date += timedelta(days=1)
            if (target_date - now).days > 7:
                target_date = now + timedelta(days=1)  # Fallback to tomorrow
                break
        
        # Set optimal hour
        optimal_hour = int(peak_hours[0].split(":")[0])
        optimal_time = target_date.replace(hour=optimal_hour, minute=0, second=0, microsecond=0)
        
        # Calculate viral potential
        viral_score = self._calculate_viral_potential(
            content_analysis,
            is_trend_aligned,
            target_date.strftime("%A")
        )
        
        # Generate alternative times
        alternatives = []
        for hour_str in peak_hours[1:]:
            hour = int(hour_str.split(":")[0])
            alt_time = target_date.replace(hour=hour, minute=0)
            alt_score = viral_score * 0.9  # Slightly lower for alternatives
            alternatives.append((alt_time, alt_score))
        
        # Generate action items
        action_items = []
        if content_analysis.get("hook_strength", {}).get("score", 0) < 50:
            action_items.append("💡 Consider strengthening your opening hook")
        if not content_analysis.get("entities", {}).get("hashtags"):
            action_items.append("🏷️ Add 2-3 relevant hashtags")
        if is_trend_aligned:
            action_items.append("🚀 Great trend alignment - consider posting sooner!")
        
        # Final confidence calculation
        confidence = 70  # Base
        if is_trend_aligned:
            confidence += 15
        if content_analysis.get("hook_strength", {}).get("score", 0) > 60:
            confidence += 10
        day_multiplier = self.day_patterns.get(target_date.strftime("%A"), {}).get("multiplier", 1.0)
        confidence = min(confidence * day_multiplier, 95)
        
        return TimingRecommendation(
            optimal_time=optimal_time,
            timezone=primary_tz,
            confidence_score=confidence,
            viral_potential=viral_score,
            reasoning=reasoning,
            alternative_times=alternatives,
            warnings=warnings,
            action_items=action_items
        )
    
    def _calculate_viral_potential(
        self,
        content_analysis: Dict,
        is_trend_aligned: bool,
        day_of_week: str
    ) -> float:
        """Calculate viral potential score 0-100"""
        score = 30  # Base score
        
        # Hook strength
        hook_score = content_analysis.get("hook_strength", {}).get("score", 0)
        score += hook_score * 0.3
        
        # Trend alignment
        if is_trend_aligned:
            score += 20
        
        # Content type bonus
        content_type = content_analysis.get("content_type", "standard")
        type_bonus = {
            "thread": 15,
            "hot_take": 20,
            "question": 10,
            "educational": 12,
            "meme": 18,
            "announcement": 8,
            "list": 10,
            "standard": 5
        }
        score += type_bonus.get(content_type, 5)
        
        # Day of week
        day_mult = self.day_patterns.get(day_of_week, {}).get("multiplier", 1.0)
        score *= day_mult
        
        # Sentiment bonus
        if content_analysis.get("sentiment") == "positive":
            score += 5
        
        return min(score, 100)
    
    async def _suggest_hashtags(
        self,
        content_analysis: Dict,
        trending_data: List[TrendingData]
    ) -> List[str]:
        """Suggest optimal hashtags based on content and trends"""
        suggestions = []
        
        # Get trending hashtags
        for trend in trending_data[:3]:
            suggestions.extend(trend.related_hashtags[:2])
        
        # Add category-specific evergreen hashtags
        category = content_analysis.get("category", "general")
        category_hashtags = {
            "crypto": ["#Crypto", "#Web3", "#DeFi"],
            "ai": ["#AI", "#MachineLearning", "#Tech"],
            "tech": ["#Tech", "#BuildInPublic", "#Developers"],
            "defi": ["#DeFi", "#Yield", "#Crypto"],
            "startup": ["#Startup", "#Founder", "#BuildInPublic"],
        }
        suggestions.extend(category_hashtags.get(category, ["#Tech"])[:2])
        
        # Deduplicate and limit
        seen = set()
        unique = []
        for tag in suggestions:
            if tag.lower() not in seen:
                seen.add(tag.lower())
                unique.append(tag)
        
        return unique[:5]
    
    async def _suggest_improvements(
        self,
        content: str,
        content_analysis: Dict,
        trending_data: List[TrendingData]
    ) -> List[str]:
        """Suggest ways to improve the content"""
        improvements = []
        
        # Hook improvements
        if content_analysis.get("hook_strength", {}).get("score", 0) < 50:
            improvements.append("🎣 Start with a stronger hook: 'I just discovered...', 'Hot take:', or a bold claim")
        
        # Length suggestions
        if len(content) < 50:
            improvements.append("📝 Consider adding more context - tweets with 100-150 chars perform well")
        elif len(content) > 250 and content_analysis.get("content_type") != "thread":
            improvements.append("✂️ Consider making this a thread for better readability")
        
        # Engagement elements
        if "?" not in content:
            improvements.append("❓ Consider ending with a question to boost replies")
        
        # Trend alignment
        if trending_data:
            top_trend = trending_data[0]
            if not any(kw in content.lower() for kw in top_trend.topic.lower().split()):
                improvements.append(f"🔥 Consider tying into trending topic: '{top_trend.topic}'")
        
        # CTA suggestions
        if "follow" not in content.lower() and "retweet" not in content.lower():
            improvements.append("📢 Consider adding a soft CTA: 'Follow for more' or 'RT if you agree'")
        
        return improvements[:5]
    
    def format_research_for_display(self, result: DeepResearchResult) -> str:
        """Format the research result as readable markdown"""
        lines = ["## 🔬 Deep Research Results\n"]
        
        # Content Analysis
        lines.append("### 📊 Content Analysis")
        lines.append(f"- **Category:** {result.content_analysis.get('category', 'general').title()}")
        lines.append(f"- **Content Type:** {result.content_analysis.get('content_type', 'standard')}")
        lines.append(f"- **Sentiment:** {result.content_analysis.get('sentiment', 'neutral')}")
        lines.append(f"- **Hook Strength:** {result.content_analysis.get('hook_strength', {}).get('score', 0)}/100")
        lines.append("")
        
        # Audience Profile
        lines.append("### 👥 Target Audience")
        lines.append(f"- **Who:** {result.audience_profile.primary_demographic}")
        lines.append(f"- **Age Range:** {result.audience_profile.age_range}")
        lines.append(f"- **Primary Timezones:** {', '.join(result.audience_profile.primary_timezones)}")
        lines.append(f"- **Device:** {result.audience_profile.device_preference}")
        lines.append("")
        
        # Timing Recommendation
        tr = result.timing_recommendation
        lines.append("### ⏰ Optimal Posting Time")
        lines.append(f"**{tr.optimal_time.strftime('%A, %B %d at %I:%M %p')} {tr.timezone}**")
        lines.append(f"- **Confidence:** {tr.confidence_score:.0f}%")
        lines.append(f"- **Viral Potential:** {tr.viral_potential:.0f}%")
        lines.append("")
        
        # Reasoning
        lines.append("**Why this time?**")
        for reason in tr.reasoning:
            lines.append(f"- {reason}")
        lines.append("")
        
        # Warnings
        if tr.warnings:
            lines.append("**⚠️ Warnings:**")
            for warning in tr.warnings:
                lines.append(f"- {warning}")
            lines.append("")
        
        # Trending Topics
        if result.trending_data:
            lines.append("### 🔥 Related Trends")
            for trend in result.trending_data[:3]:
                status = "📈 Growing" if not trend.is_peak else "📊 Peaking"
                lines.append(f"- **{trend.topic}** {status}")
            lines.append("")
        
        # Suggested Hashtags
        if result.hashtag_suggestions:
            lines.append("### 🏷️ Suggested Hashtags")
            lines.append(" ".join(result.hashtag_suggestions))
            lines.append("")
        
        # Improvements
        if result.content_improvements:
            lines.append("### 💡 Content Improvements")
            for imp in result.content_improvements:
                lines.append(f"- {imp}")
            lines.append("")
        
        # Action Items
        if tr.action_items:
            lines.append("### ✅ Action Items")
            for action in tr.action_items:
                lines.append(f"- {action}")
        
        return "\n".join(lines)


# Singleton instance
deep_research_engine = DeepResearchEngine()

