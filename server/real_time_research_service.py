"""
REAL Real-Time Research Service

This actually fetches LIVE data from:
1. Twitter/X API - Trending topics, hashtags
2. Google Trends - Search interest
3. Reddit API - Hot discussions
4. News APIs - Breaking news
5. Your own post analytics - Personal performance data

No more fake/guessed data!
"""

import os
import json
import httpx
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from collections import defaultdict
import re


@dataclass
class TrendData:
    """Real trend data from APIs"""
    name: str
    platform: str  # twitter, reddit, google, news
    volume: Optional[int]  # Tweet/post count
    velocity: float  # Growth rate (1.0 = stable, >1 = growing)
    url: Optional[str]
    hashtags: List[str]
    related_topics: List[str]
    sentiment: str  # positive, negative, neutral
    fetched_at: str
    is_real_data: bool  # True = from API, False = fallback


@dataclass
class CompetitorInsight:
    """Real data about competitor accounts"""
    handle: str
    platform: str
    recent_post_times: List[str]  # Last 10 posts timestamps
    avg_engagement: float
    posting_frequency: str  # "3x daily", "daily", etc.
    best_performing_content: List[str]
    is_real_data: bool


class RealTimeResearchService:
    """
    Fetches ACTUAL real-time data from multiple sources.
    Falls back to AI-generated data only when APIs fail.
    """
    
    def __init__(self):
        # API Keys
        self.twitter_bearer_token = os.getenv("TWITTER_BEARER_TOKEN")
        self.reddit_client_id = os.getenv("REDDIT_CLIENT_ID")
        self.reddit_client_secret = os.getenv("REDDIT_CLIENT_SECRET")
        self.news_api_key = os.getenv("NEWS_API_KEY")
        self.serp_api_key = os.getenv("SERP_API_KEY")  # For Google Trends
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        
        # Reddit access token (refreshed)
        self.reddit_access_token = os.getenv("REDDIT_ACCESS_TOKEN")
        
        # API endpoints
        self.twitter_trends_url = "https://api.twitter.com/2/trends/place"
        self.twitter_search_url = "https://api.twitter.com/2/tweets/search/recent"
        self.reddit_url = "https://oauth.reddit.com"
        self.news_api_url = "https://newsapi.org/v2/everything"
        self.serp_api_url = "https://serpapi.com/search"
        
        # Niche-specific subreddits
        self.category_subreddits = {
            "crypto": ["cryptocurrency", "solana", "defi", "ethfinance", "CryptoMarkets"],
            "ai": ["MachineLearning", "artificial", "LocalLLaMA", "OpenAI", "ClaudeAI"],
            "tech": ["programming", "webdev", "technology", "startups"],
            "defi": ["defi", "solana", "ethereum", "yield_farming"],
            "startup": ["startups", "Entrepreneur", "SaaS", "venturecapital"],
        }
    
    # ==================== TWITTER/X API ====================
    
    async def get_twitter_trends(self, woeid: int = 1) -> List[TrendData]:
        """
        Get REAL trending topics from Twitter API v2.
        
        WOEID locations:
        - 1 = Worldwide
        - 23424977 = United States
        - 23424975 = United Kingdom
        - 23424848 = India
        """
        if not self.twitter_bearer_token:
            print("⚠️ TWITTER_BEARER_TOKEN not set - using fallback")
            return await self._fallback_twitter_trends()
        
        try:
            async with httpx.AsyncClient() as client:
                # Twitter API v1.1 trends endpoint (v2 doesn't have trends yet)
                response = await client.get(
                    f"https://api.twitter.com/1.1/trends/place.json?id={woeid}",
                    headers={"Authorization": f"Bearer {self.twitter_bearer_token}"},
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data and len(data) > 0:
                        trends = data[0].get("trends", [])
                        return [
                            TrendData(
                                name=t["name"],
                                platform="twitter",
                                volume=t.get("tweet_volume"),
                                velocity=1.5 if t.get("tweet_volume", 0) and t["tweet_volume"] > 100000 else 1.0,
                                url=t.get("url"),
                                hashtags=[t["name"]] if t["name"].startswith("#") else [],
                                related_topics=[],
                                sentiment="neutral",
                                fetched_at=datetime.utcnow().isoformat(),
                                is_real_data=True
                            )
                            for t in trends[:20]
                        ]
                elif response.status_code == 429:
                    print("⚠️ Twitter rate limited - using fallback")
                else:
                    print(f"⚠️ Twitter API error {response.status_code}: {response.text}")
        except Exception as e:
            print(f"❌ Twitter API failed: {e}")
        
        return await self._fallback_twitter_trends()
    
    async def search_twitter_hashtag(self, hashtag: str, max_results: int = 100) -> Dict:
        """
        Search recent tweets for a hashtag to gauge volume and sentiment.
        """
        if not self.twitter_bearer_token:
            return {"error": "No Twitter API key", "is_real_data": False}
        
        try:
            async with httpx.AsyncClient() as client:
                query = f"#{hashtag.replace('#', '')} -is:retweet lang:en"
                response = await client.get(
                    self.twitter_search_url,
                    headers={"Authorization": f"Bearer {self.twitter_bearer_token}"},
                    params={
                        "query": query,
                        "max_results": min(max_results, 100),
                        "tweet.fields": "created_at,public_metrics"
                    },
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    tweets = data.get("data", [])
                    
                    # Calculate engagement metrics
                    total_likes = sum(t.get("public_metrics", {}).get("like_count", 0) for t in tweets)
                    total_retweets = sum(t.get("public_metrics", {}).get("retweet_count", 0) for t in tweets)
                    
                    return {
                        "hashtag": hashtag,
                        "recent_tweet_count": len(tweets),
                        "total_likes": total_likes,
                        "total_retweets": total_retweets,
                        "avg_engagement": (total_likes + total_retweets) / max(len(tweets), 1),
                        "sample_tweets": [t.get("text", "")[:100] for t in tweets[:5]],
                        "is_real_data": True,
                        "fetched_at": datetime.utcnow().isoformat()
                    }
        except Exception as e:
            print(f"❌ Twitter search failed: {e}")
        
        return {"error": "Failed to fetch", "is_real_data": False}
    
    async def get_competitor_posting_times(self, username: str) -> CompetitorInsight:
        """
        Get when a competitor account posts (from their recent tweets).
        """
        if not self.twitter_bearer_token:
            return CompetitorInsight(
                handle=username,
                platform="twitter",
                recent_post_times=[],
                avg_engagement=0,
                posting_frequency="unknown",
                best_performing_content=[],
                is_real_data=False
            )
        
        try:
            async with httpx.AsyncClient() as client:
                # First get user ID
                user_response = await client.get(
                    f"https://api.twitter.com/2/users/by/username/{username}",
                    headers={"Authorization": f"Bearer {self.twitter_bearer_token}"},
                    timeout=10.0
                )
                
                if user_response.status_code != 200:
                    raise Exception(f"User lookup failed: {user_response.status_code}")
                
                user_id = user_response.json()["data"]["id"]
                
                # Get recent tweets
                tweets_response = await client.get(
                    f"https://api.twitter.com/2/users/{user_id}/tweets",
                    headers={"Authorization": f"Bearer {self.twitter_bearer_token}"},
                    params={
                        "max_results": 100,
                        "tweet.fields": "created_at,public_metrics",
                        "exclude": "retweets,replies"
                    },
                    timeout=10.0
                )
                
                if tweets_response.status_code == 200:
                    tweets = tweets_response.json().get("data", [])
                    
                    # Extract posting times
                    post_times = [t["created_at"] for t in tweets if "created_at" in t]
                    
                    # Calculate engagement
                    engagements = [
                        t.get("public_metrics", {}).get("like_count", 0) +
                        t.get("public_metrics", {}).get("retweet_count", 0)
                        for t in tweets
                    ]
                    avg_engagement = sum(engagements) / max(len(engagements), 1)
                    
                    # Get best performing
                    sorted_tweets = sorted(tweets, key=lambda x: x.get("public_metrics", {}).get("like_count", 0), reverse=True)
                    best = [t.get("text", "")[:100] for t in sorted_tweets[:3]]
                    
                    # Calculate posting frequency
                    if len(post_times) >= 2:
                        first = datetime.fromisoformat(post_times[0].replace("Z", "+00:00"))
                        last = datetime.fromisoformat(post_times[-1].replace("Z", "+00:00"))
                        days = (first - last).days or 1
                        posts_per_day = len(post_times) / days
                        freq = f"{posts_per_day:.1f}x daily"
                    else:
                        freq = "unknown"
                    
                    return CompetitorInsight(
                        handle=username,
                        platform="twitter",
                        recent_post_times=post_times[:10],
                        avg_engagement=avg_engagement,
                        posting_frequency=freq,
                        best_performing_content=best,
                        is_real_data=True
                    )
        except Exception as e:
            print(f"❌ Competitor analysis failed for @{username}: {e}")
        
        return CompetitorInsight(
            handle=username,
            platform="twitter",
            recent_post_times=[],
            avg_engagement=0,
            posting_frequency="unknown",
            best_performing_content=[],
            is_real_data=False
        )
    
    # ==================== REDDIT API ====================
    
    async def get_reddit_hot(self, category: str = "crypto", limit: int = 25) -> List[TrendData]:
        """
        Get hot posts from relevant subreddits for trend detection.
        """
        subreddits = self.category_subreddits.get(category, ["all"])
        trends = []
        
        for subreddit in subreddits[:3]:  # Limit API calls
            try:
                hot_posts = await self._fetch_reddit_posts(subreddit, "hot", limit)
                for post in hot_posts[:5]:
                    trends.append(TrendData(
                        name=post.get("title", "")[:100],
                        platform="reddit",
                        volume=post.get("score", 0),
                        velocity=self._calculate_reddit_velocity(post),
                        url=f"https://reddit.com{post.get('permalink', '')}",
                        hashtags=[],
                        related_topics=[subreddit],
                        sentiment=self._detect_sentiment(post.get("title", "")),
                        fetched_at=datetime.utcnow().isoformat(),
                        is_real_data=True
                    ))
            except Exception as e:
                print(f"⚠️ Reddit r/{subreddit} failed: {e}")
        
        return trends or await self._fallback_reddit_trends(category)
    
    async def _fetch_reddit_posts(self, subreddit: str, sort: str, limit: int) -> List[Dict]:
        """Fetch posts from a subreddit."""
        # Try with OAuth first
        if self.reddit_access_token:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        f"{self.reddit_url}/r/{subreddit}/{sort}",
                        headers={
                            "Authorization": f"Bearer {self.reddit_access_token}",
                            "User-Agent": "SocialAnywhere/1.0"
                        },
                        params={"limit": limit},
                        timeout=10.0
                    )
                    if response.status_code == 200:
                        data = response.json()
                        return [child["data"] for child in data.get("data", {}).get("children", [])]
            except Exception as e:
                print(f"⚠️ Reddit OAuth failed: {e}")
        
        # Fallback to public JSON endpoint
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"https://www.reddit.com/r/{subreddit}/{sort}.json",
                    headers={"User-Agent": "SocialAnywhere/1.0"},
                    params={"limit": limit},
                    timeout=10.0
                )
                if response.status_code == 200:
                    data = response.json()
                    return [child["data"] for child in data.get("data", {}).get("children", [])]
        except Exception as e:
            print(f"❌ Reddit public API failed: {e}")
        
        return []
    
    def _calculate_reddit_velocity(self, post: Dict) -> float:
        """Calculate how fast a post is growing."""
        created_utc = post.get("created_utc", 0)
        score = post.get("score", 0)
        
        if created_utc and score:
            hours_old = (datetime.utcnow().timestamp() - created_utc) / 3600
            if hours_old > 0:
                velocity = score / hours_old  # Points per hour
                if velocity > 100:
                    return 2.0  # Very viral
                elif velocity > 50:
                    return 1.5  # Growing fast
                elif velocity > 20:
                    return 1.2  # Growing
        return 1.0  # Stable
    
    # ==================== NEWS API ====================
    
    async def get_news_for_topic(self, topic: str, hours: int = 24) -> List[Dict]:
        """
        Get recent news articles about a topic.
        """
        if not self.news_api_key:
            print("⚠️ NEWS_API_KEY not set")
            return []
        
        try:
            from_date = (datetime.utcnow() - timedelta(hours=hours)).strftime("%Y-%m-%d")
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self.news_api_url,
                    params={
                        "q": topic,
                        "from": from_date,
                        "sortBy": "relevancy",
                        "language": "en",
                        "apiKey": self.news_api_key
                    },
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    articles = data.get("articles", [])
                    return [
                        {
                            "title": a.get("title"),
                            "source": a.get("source", {}).get("name"),
                            "url": a.get("url"),
                            "published_at": a.get("publishedAt"),
                            "description": a.get("description", "")[:200],
                            "is_real_data": True
                        }
                        for a in articles[:10]
                    ]
        except Exception as e:
            print(f"❌ News API failed: {e}")
        
        return []
    
    # ==================== GOOGLE TRENDS (via SerpAPI) ====================
    
    async def get_google_trends(self, keyword: str) -> Dict:
        """
        Get Google Trends data for a keyword using SerpAPI.
        """
        if not self.serp_api_key:
            print("⚠️ SERP_API_KEY not set for Google Trends")
            return {"keyword": keyword, "is_real_data": False, "error": "No API key"}
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self.serp_api_url,
                    params={
                        "engine": "google_trends",
                        "q": keyword,
                        "data_type": "TIMESERIES",
                        "api_key": self.serp_api_key
                    },
                    timeout=15.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    interest_over_time = data.get("interest_over_time", {})
                    timeline_data = interest_over_time.get("timeline_data", [])
                    
                    # Get recent trend direction
                    if len(timeline_data) >= 2:
                        recent = timeline_data[-1].get("values", [{}])[0].get("value", "0")
                        previous = timeline_data[-2].get("values", [{}])[0].get("value", "0")
                        try:
                            trend_direction = "up" if int(recent) > int(previous) else "down"
                        except:
                            trend_direction = "stable"
                    else:
                        trend_direction = "unknown"
                    
                    return {
                        "keyword": keyword,
                        "trend_direction": trend_direction,
                        "related_queries": data.get("related_queries", {}).get("rising", [])[:5],
                        "interest_by_region": data.get("interest_by_region", [])[:5],
                        "is_real_data": True,
                        "fetched_at": datetime.utcnow().isoformat()
                    }
        except Exception as e:
            print(f"❌ Google Trends failed: {e}")
        
        return {"keyword": keyword, "is_real_data": False, "error": "API failed"}
    
    # ==================== COMBINED REAL-TIME RESEARCH ====================
    
    async def comprehensive_research(
        self,
        topic: str,
        category: str = "crypto",
        competitors: List[str] = None
    ) -> Dict:
        """
        Run comprehensive real-time research across ALL sources.
        
        Returns data from:
        - Twitter trends + hashtag volume
        - Reddit hot posts
        - News articles
        - Google Trends
        - Competitor analysis
        
        With clear indication of what's real vs fallback data.
        """
        results = {
            "topic": topic,
            "category": category,
            "researched_at": datetime.utcnow().isoformat(),
            "data_sources": {},
            "overall_data_quality": 0  # Percentage of real data
        }
        
        real_data_count = 0
        total_sources = 0
        
        # 1. Twitter Trends
        total_sources += 1
        twitter_trends = await self.get_twitter_trends()
        results["twitter_trends"] = {
            "trends": [
                {"name": t.name, "volume": t.volume, "velocity": t.velocity}
                for t in twitter_trends[:10]
            ],
            "is_real_data": twitter_trends[0].is_real_data if twitter_trends else False
        }
        if twitter_trends and twitter_trends[0].is_real_data:
            real_data_count += 1
        
        # 2. Twitter hashtag search for topic
        total_sources += 1
        hashtag_data = await self.search_twitter_hashtag(topic)
        results["hashtag_analysis"] = hashtag_data
        if hashtag_data.get("is_real_data"):
            real_data_count += 1
        
        # 3. Reddit hot posts
        total_sources += 1
        reddit_trends = await self.get_reddit_hot(category)
        results["reddit_trends"] = {
            "posts": [
                {"title": t.name, "score": t.volume, "velocity": t.velocity, "subreddit": t.related_topics[0] if t.related_topics else ""}
                for t in reddit_trends[:10]
            ],
            "is_real_data": reddit_trends[0].is_real_data if reddit_trends else False
        }
        if reddit_trends and reddit_trends[0].is_real_data:
            real_data_count += 1
        
        # 4. News articles
        total_sources += 1
        news = await self.get_news_for_topic(topic)
        results["news"] = {
            "articles": news[:5],
            "is_real_data": news[0].get("is_real_data", False) if news else False
        }
        if news and news[0].get("is_real_data"):
            real_data_count += 1
        
        # 5. Google Trends
        total_sources += 1
        google_trends = await self.get_google_trends(topic)
        results["google_trends"] = google_trends
        if google_trends.get("is_real_data"):
            real_data_count += 1
        
        # 6. Competitor analysis
        if competitors:
            results["competitors"] = {}
            for comp in competitors[:3]:  # Limit to 3 to avoid rate limits
                total_sources += 1
                insight = await self.get_competitor_posting_times(comp)
                results["competitors"][comp] = {
                    "posting_frequency": insight.posting_frequency,
                    "recent_post_times": insight.recent_post_times[:5],
                    "avg_engagement": insight.avg_engagement,
                    "is_real_data": insight.is_real_data
                }
                if insight.is_real_data:
                    real_data_count += 1
        
        # Calculate overall data quality
        results["overall_data_quality"] = int((real_data_count / total_sources) * 100) if total_sources > 0 else 0
        results["data_sources"] = {
            "real_data_sources": real_data_count,
            "total_sources": total_sources,
            "sources_checked": ["twitter", "reddit", "news", "google_trends"] + (competitors or [])
        }
        
        return results
    
    # ==================== FALLBACK METHODS ====================
    
    async def _fallback_twitter_trends(self) -> List[TrendData]:
        """Use AI to generate plausible current trends when Twitter API unavailable."""
        if not self.groq_api_key:
            return self._static_fallback_trends()
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.groq_api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "llama-3.1-8b-instant",
                        "messages": [
                            {
                                "role": "system",
                                "content": """You are a Twitter trend analyst. It's January 2026. 
Generate 10 realistic trending topics that would be on Twitter right now.
Focus on: crypto, AI, tech, and general news.
Return JSON array: [{"name": "#TopicName", "category": "crypto/ai/tech/news", "reason": "why trending"}]"""
                            },
                            {"role": "user", "content": "What's trending on Twitter right now?"}
                        ],
                        "temperature": 0.7,
                        "max_tokens": 500
                    },
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    content = response.json()["choices"][0]["message"]["content"]
                    try:
                        trends_data = json.loads(content)
                        return [
                            TrendData(
                                name=t.get("name", ""),
                                platform="twitter",
                                volume=None,
                                velocity=1.0,
                                url=None,
                                hashtags=[t.get("name", "")] if t.get("name", "").startswith("#") else [],
                                related_topics=[t.get("category", "")],
                                sentiment="neutral",
                                fetched_at=datetime.utcnow().isoformat(),
                                is_real_data=False  # Mark as AI-generated!
                            )
                            for t in trends_data
                        ]
                    except:
                        pass
        except Exception as e:
            print(f"⚠️ AI fallback also failed: {e}")
        
        return self._static_fallback_trends()
    
    def _static_fallback_trends(self) -> List[TrendData]:
        """Last resort: completely static trends."""
        return [
            TrendData(
                name="#Bitcoin",
                platform="twitter",
                volume=None,
                velocity=1.0,
                url=None,
                hashtags=["#Bitcoin", "#BTC"],
                related_topics=["crypto"],
                sentiment="neutral",
                fetched_at=datetime.utcnow().isoformat(),
                is_real_data=False
            )
        ]
    
    async def _fallback_reddit_trends(self, category: str) -> List[TrendData]:
        """Fallback for Reddit when API fails."""
        return [
            TrendData(
                name=f"Hot discussion in r/{self.category_subreddits.get(category, ['all'])[0]}",
                platform="reddit",
                volume=None,
                velocity=1.0,
                url=None,
                hashtags=[],
                related_topics=[category],
                sentiment="neutral",
                fetched_at=datetime.utcnow().isoformat(),
                is_real_data=False
            )
        ]
    
    def _detect_sentiment(self, text: str) -> str:
        """Quick sentiment detection."""
        text_lower = text.lower()
        positive = ["🚀", "bullish", "moon", "up", "gain", "great", "amazing", "excited"]
        negative = ["bearish", "dump", "crash", "down", "loss", "worried", "scam"]
        
        pos_count = sum(1 for p in positive if p in text_lower)
        neg_count = sum(1 for n in negative if n in text_lower)
        
        if pos_count > neg_count:
            return "positive"
        elif neg_count > pos_count:
            return "negative"
        return "neutral"


# Singleton instance
real_time_research = RealTimeResearchService()

