"""
FREE Real-Time Research Service

HONEST about what's actually free:

✅ FREE Sources:
1. Reddit API - Public endpoints, no auth needed for basic access
2. Google Trends via PyTrends (free library, no API key)
3. Groq AI for trend analysis (generous free tier)
4. RSS News Feeds (completely free)
5. CoinGecko API (free for crypto data)

⚠️ PAID Sources (NOT included):
- Twitter/X API - $100/mo minimum for useful access
- NewsAPI - Free only on localhost, $449/mo for production
- Official Google Trends API - Requires SerpAPI ($75+/mo)
"""

import os
import json
import httpx
import asyncio
import feedparser  # For RSS feeds
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from collections import defaultdict


@dataclass
class FreeTrendData:
    """Trend data from free sources"""
    topic: str
    source: str  # reddit, rss, coingecko, google_trends
    volume: Optional[int]
    velocity: float
    url: Optional[str]
    related_topics: List[str]
    sentiment: str
    fetched_at: str
    is_real_data: bool


class FreeResearchService:
    """
    Research service using ONLY free APIs and data sources.
    No paid APIs required!
    """
    
    def __init__(self):
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        
        # Category-specific subreddits (free to access)
        self.category_subreddits = {
            "crypto": ["cryptocurrency", "solana", "defi", "ethfinance", "CryptoMarkets", "solanatrader"],
            "ai": ["MachineLearning", "artificial", "LocalLLaMA", "OpenAI", "ClaudeAI"],
            "tech": ["programming", "webdev", "technology", "startups", "SideProject"],
            "defi": ["defi", "solana", "ethereum", "yield_farming"],
            "startup": ["startups", "Entrepreneur", "SaaS", "venturecapital"],
            "nft": ["NFT", "NFTsMarketplace", "opensea"],
        }
        
        # Free RSS news feeds by category
        self.rss_feeds = {
            "crypto": [
                "https://cointelegraph.com/rss",
                "https://www.coindesk.com/arc/outboundfeeds/rss/",
                "https://cryptoslate.com/feed/",
            ],
            "ai": [
                "https://techcrunch.com/category/artificial-intelligence/feed/",
                "https://www.wired.com/feed/category/artificial-intelligence/latest/rss",
            ],
            "tech": [
                "https://techcrunch.com/feed/",
                "https://www.theverge.com/rss/index.xml",
                "https://feeds.arstechnica.com/arstechnica/technology-lab",
            ],
            "startup": [
                "https://techcrunch.com/category/startups/feed/",
                "https://www.entrepreneur.com/latest.rss",
            ],
        }
    
    # ==================== REDDIT (FREE) ====================
    
    async def get_reddit_trends(
        self,
        category: str = "crypto",
        limit: int = 25
    ) -> List[FreeTrendData]:
        """
        Get hot posts from Reddit - 100% FREE!
        Uses public JSON endpoints (no auth required for reading).
        """
        subreddits = self.category_subreddits.get(category, ["all"])
        trends = []
        
        for subreddit in subreddits[:3]:  # Limit to avoid rate limits
            try:
                async with httpx.AsyncClient() as client:
                    # Reddit public JSON endpoint - FREE!
                    response = await client.get(
                        f"https://www.reddit.com/r/{subreddit}/hot.json",
                        headers={"User-Agent": "SocialAnywhere/1.0 (research bot)"},
                        params={"limit": limit},
                        timeout=10.0
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        posts = data.get("data", {}).get("children", [])
                        
                        for post in posts[:8]:
                            post_data = post.get("data", {})
                            
                            # Calculate velocity (upvotes per hour)
                            created_utc = post_data.get("created_utc", 0)
                            score = post_data.get("score", 0)
                            hours_old = max((datetime.utcnow().timestamp() - created_utc) / 3600, 0.1)
                            velocity = score / hours_old
                            
                            trends.append(FreeTrendData(
                                topic=post_data.get("title", "")[:150],
                                source="reddit",
                                volume=score,
                                velocity=min(velocity / 50, 3.0),  # Normalize to 0-3 scale
                                url=f"https://reddit.com{post_data.get('permalink', '')}",
                                related_topics=[subreddit],
                                sentiment=self._quick_sentiment(post_data.get("title", "")),
                                fetched_at=datetime.utcnow().isoformat(),
                                is_real_data=True
                            ))
                    
                    # Rate limit: wait between requests
                    await asyncio.sleep(1)
                    
            except Exception as e:
                print(f"⚠️ Reddit r/{subreddit} failed: {e}")
        
        # Sort by velocity (most viral first)
        trends.sort(key=lambda x: x.velocity, reverse=True)
        return trends[:15]
    
    # ==================== RSS NEWS FEEDS (FREE) ====================
    
    async def get_news_from_rss(
        self,
        category: str = "crypto",
        limit: int = 10
    ) -> List[Dict]:
        """
        Get news from RSS feeds - 100% FREE!
        No API key needed, works in production.
        """
        feeds = self.rss_feeds.get(category, self.rss_feeds["tech"])
        all_articles = []
        
        for feed_url in feeds[:2]:  # Limit feeds
            try:
                # feedparser handles RSS/Atom feeds
                feed = feedparser.parse(feed_url)
                
                for entry in feed.entries[:limit]:
                    published = entry.get("published_parsed") or entry.get("updated_parsed")
                    if published:
                        pub_date = datetime(*published[:6]).isoformat()
                    else:
                        pub_date = datetime.utcnow().isoformat()
                    
                    all_articles.append({
                        "title": entry.get("title", ""),
                        "url": entry.get("link", ""),
                        "source": feed.feed.get("title", "Unknown"),
                        "published_at": pub_date,
                        "summary": entry.get("summary", "")[:300],
                        "is_real_data": True
                    })
                    
            except Exception as e:
                print(f"⚠️ RSS feed failed: {e}")
        
        # Sort by date (newest first)
        all_articles.sort(key=lambda x: x.get("published_at", ""), reverse=True)
        return all_articles[:limit]
    
    # ==================== COINGECKO (FREE for Crypto) ====================
    
    async def get_crypto_trends(self) -> Dict:
        """
        Get crypto market trends from CoinGecko - FREE API!
        No API key required.
        """
        try:
            async with httpx.AsyncClient() as client:
                # Trending coins
                trending_response = await client.get(
                    "https://api.coingecko.com/api/v3/search/trending",
                    timeout=10.0
                )
                
                # Global market data
                global_response = await client.get(
                    "https://api.coingecko.com/api/v3/global",
                    timeout=10.0
                )
                
                result = {
                    "trending_coins": [],
                    "market_data": {},
                    "is_real_data": True,
                    "fetched_at": datetime.utcnow().isoformat()
                }
                
                if trending_response.status_code == 200:
                    data = trending_response.json()
                    for coin in data.get("coins", [])[:7]:
                        item = coin.get("item", {})
                        result["trending_coins"].append({
                            "name": item.get("name"),
                            "symbol": item.get("symbol"),
                            "market_cap_rank": item.get("market_cap_rank"),
                            "price_btc": item.get("price_btc"),
                            "score": item.get("score"),
                        })
                
                if global_response.status_code == 200:
                    global_data = global_response.json().get("data", {})
                    result["market_data"] = {
                        "total_market_cap_usd": global_data.get("total_market_cap", {}).get("usd"),
                        "total_volume_24h_usd": global_data.get("total_volume", {}).get("usd"),
                        "btc_dominance": global_data.get("market_cap_percentage", {}).get("btc"),
                        "market_cap_change_24h": global_data.get("market_cap_change_percentage_24h_usd"),
                    }
                
                return result
                
        except Exception as e:
            print(f"❌ CoinGecko API failed: {e}")
            return {"error": str(e), "is_real_data": False}
    
    # ==================== PYTRENDS (FREE Google Trends) ====================
    
    async def get_google_trends_free(self, keyword: str) -> Dict:
        """
        Get Google Trends data using PyTrends library - FREE!
        No API key required.
        
        NOTE: This uses web scraping, may be rate limited.
        """
        try:
            from pytrends.request import TrendReq
            
            # Initialize PyTrends (uses Google's public interface)
            pytrends = TrendReq(hl='en-US', tz=360)
            
            # Build payload
            pytrends.build_payload([keyword], timeframe='now 7-d')
            
            # Get interest over time
            interest_df = pytrends.interest_over_time()
            
            # Get related queries
            related_queries = pytrends.related_queries()
            
            # Process results
            result = {
                "keyword": keyword,
                "is_real_data": True,
                "fetched_at": datetime.utcnow().isoformat(),
                "interest_trend": "unknown",
                "related_queries": []
            }
            
            if not interest_df.empty:
                recent_value = interest_df[keyword].iloc[-1]
                older_value = interest_df[keyword].iloc[0] if len(interest_df) > 1 else recent_value
                
                if recent_value > older_value:
                    result["interest_trend"] = "rising"
                elif recent_value < older_value:
                    result["interest_trend"] = "falling"
                else:
                    result["interest_trend"] = "stable"
                
                result["current_interest"] = int(recent_value)
            
            if keyword in related_queries and related_queries[keyword].get("rising") is not None:
                rising = related_queries[keyword]["rising"]
                if rising is not None and not rising.empty:
                    result["related_queries"] = rising["query"].tolist()[:5]
            
            return result
            
        except ImportError:
            return {
                "keyword": keyword,
                "error": "pytrends not installed. Run: pip install pytrends",
                "is_real_data": False
            }
        except Exception as e:
            return {
                "keyword": keyword,
                "error": str(e),
                "is_real_data": False
            }
    
    # ==================== AI TREND ANALYSIS (FREE with Groq) ====================
    
    async def analyze_trends_with_ai(
        self,
        topic: str,
        reddit_data: List[FreeTrendData],
        news_data: List[Dict]
    ) -> Dict:
        """
        Use Groq AI to analyze trends - FREE tier is generous!
        
        Takes real data from Reddit/News and provides insights.
        """
        if not self.groq_api_key:
            return {"error": "GROQ_API_KEY not set", "is_real_data": False}
        
        # Prepare context from real data
        reddit_context = "\n".join([
            f"- {t.topic} (score: {t.volume}, velocity: {t.velocity:.1f})"
            for t in reddit_data[:5]
        ])
        
        news_context = "\n".join([
            f"- {n['title']} ({n['source']})"
            for n in news_data[:5]
        ])
        
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
                                "content": """You analyze social media trends and news for optimal posting.
Based on the REAL data provided, give:
1. What's hot right now
2. Best topics to post about
3. Suggested posting angle
4. Urgency level (post now vs can wait)

Return JSON:
{
  "hot_topics": ["topic1", "topic2"],
  "best_angle": "suggested content angle",
  "urgency": "high/medium/low",
  "reasoning": "why this recommendation"
}"""
                            },
                            {
                                "role": "user",
                                "content": f"""Analyze trends for topic: {topic}

REAL Reddit Data (hot posts):
{reddit_context}

REAL News Headlines:
{news_context}

What should I post about and when?"""
                            }
                        ],
                        "temperature": 0.4,
                        "max_tokens": 400
                    },
                    timeout=15.0
                )
                
                if response.status_code == 200:
                    content = response.json()["choices"][0]["message"]["content"]
                    try:
                        return {
                            "analysis": json.loads(content),
                            "based_on_real_data": True,
                            "sources": {
                                "reddit_posts": len(reddit_data),
                                "news_articles": len(news_data)
                            }
                        }
                    except json.JSONDecodeError:
                        return {
                            "analysis": content,
                            "based_on_real_data": True
                        }
                        
        except Exception as e:
            return {"error": str(e), "is_real_data": False}
        
        return {"error": "Unknown error", "is_real_data": False}
    
    # ==================== COMPREHENSIVE FREE RESEARCH ====================
    
    async def comprehensive_free_research(
        self,
        topic: str,
        category: str = "crypto"
    ) -> Dict:
        """
        Run comprehensive research using ONLY FREE sources.
        
        Sources:
        - Reddit (free public API)
        - RSS News Feeds (free)
        - CoinGecko (free, for crypto)
        - Groq AI analysis (free tier)
        """
        results = {
            "topic": topic,
            "category": category,
            "researched_at": datetime.utcnow().isoformat(),
            "data_sources": [],
            "all_free": True
        }
        
        # 1. Reddit trends
        reddit_data = await self.get_reddit_trends(category)
        results["reddit"] = {
            "posts": [
                {
                    "title": t.topic,
                    "score": t.volume,
                    "velocity": t.velocity,
                    "subreddit": t.related_topics[0] if t.related_topics else "",
                    "url": t.url
                }
                for t in reddit_data[:10]
            ],
            "is_real_data": len(reddit_data) > 0 and reddit_data[0].is_real_data,
            "source": "Reddit Public API (FREE)"
        }
        results["data_sources"].append("reddit")
        
        # 2. RSS News
        news_data = await self.get_news_from_rss(category)
        results["news"] = {
            "articles": news_data[:10],
            "is_real_data": len(news_data) > 0,
            "source": "RSS Feeds (FREE)"
        }
        results["data_sources"].append("rss_news")
        
        # 3. Crypto trends (if crypto category)
        if category in ["crypto", "defi", "nft"]:
            crypto_data = await self.get_crypto_trends()
            results["crypto"] = crypto_data
            results["crypto"]["source"] = "CoinGecko API (FREE)"
            results["data_sources"].append("coingecko")
        
        # 4. AI Analysis
        ai_analysis = await self.analyze_trends_with_ai(topic, reddit_data, news_data)
        results["ai_analysis"] = ai_analysis
        results["ai_analysis"]["source"] = "Groq AI (FREE tier)"
        results["data_sources"].append("groq_ai")
        
        # Calculate data quality
        real_sources = sum([
            results["reddit"]["is_real_data"],
            results["news"]["is_real_data"],
            results.get("crypto", {}).get("is_real_data", False),
            results["ai_analysis"].get("based_on_real_data", False)
        ])
        
        results["data_quality"] = {
            "real_data_sources": real_sources,
            "total_sources": len(results["data_sources"]),
            "quality_score": f"{int(real_sources / len(results['data_sources']) * 100)}%"
        }
        
        return results
    
    # ==================== HELPER METHODS ====================
    
    def _quick_sentiment(self, text: str) -> str:
        """Quick sentiment analysis without AI"""
        text_lower = text.lower()
        
        positive = ["🚀", "bullish", "moon", "pump", "gain", "up", "great", "amazing", "ath", "breakout", "good"]
        negative = ["bearish", "dump", "crash", "down", "loss", "scam", "rug", "dead", "rekt", "bad"]
        
        pos_count = sum(1 for p in positive if p in text_lower)
        neg_count = sum(1 for n in negative if n in text_lower)
        
        if pos_count > neg_count:
            return "positive"
        elif neg_count > pos_count:
            return "negative"
        return "neutral"


# Singleton instance
free_research = FreeResearchService()

