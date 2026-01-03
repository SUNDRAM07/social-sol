#!/usr/bin/env python3
"""
Twitter Analytics Service
Provides comprehensive analytics for your own Twitter posts using API v2 free tier
"""

import os
import logging
import requests
import json
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TwitterAnalyticsService:
    """Service for Twitter analytics and account data using API v2"""
    
    def __init__(self):
        """Initialize Twitter analytics service"""
        self.bearer_token = None
        self.consumer_key = None
        self.consumer_secret = None
        self.access_token = None
        self.access_token_secret = None
        self.username = None
        
        self.base_url = "https://api.twitter.com/2"
        self.user_id = None
        
        # Rate limiting and caching
        self.last_request_time = 0
        self.request_count = 0
        self.rate_limit_window = 15 * 60  # 15 minutes in seconds
        self.max_requests_per_window = 800  # Conservative limit (900 - 100 buffer)
        self.cache = {}
        self.cache_duration = 5 * 60  # 5 minutes cache
        self.last_successful_data = {}  # Store last successful data for fallback
        
        # Load from environment by default (for backwards compatibility)
        self._load_from_env()
    
    def _load_from_env(self):
        """Load ONLY client credentials from environment variables (not access tokens)"""
        # Only client ID/secret should be in .env, not access tokens
        self.consumer_key = os.getenv('TWITTER_CONSUMER_KEY')  # Client ID - OK in .env
        self.consumer_secret = os.getenv('TWITTER_CONSUMER_SECRET')  # Client Secret - OK in .env
        # Access tokens should come from database, not .env
        self.bearer_token = None
        self.access_token = None
        self.access_token_secret = None
        self.username = None
    
    def configure(self, access_token: Optional[str] = None, bearer_token: Optional[str] = None,
                  consumer_key: Optional[str] = None, consumer_secret: Optional[str] = None,
                  access_token_secret: Optional[str] = None, username: Optional[str] = None,
                  user_id: Optional[str] = None) -> None:
        """
        Configure Twitter analytics service with credentials at runtime
        
        Args:
            access_token: OAuth 2.0 access token (preferred)
            bearer_token: Bearer token for API v2
            consumer_key: OAuth 1.0a consumer key
            consumer_secret: OAuth 1.0a consumer secret
            access_token_secret: OAuth 1.0a access token secret
            username: Twitter username
            user_id: Twitter user ID
        """
        if access_token:
            self.access_token = access_token
        if bearer_token:
            self.bearer_token = bearer_token
        if consumer_key:
            self.consumer_key = consumer_key
        if consumer_secret:
            self.consumer_secret = consumer_secret
        if access_token_secret:
            self.access_token_secret = access_token_secret
        if username:
            self.username = username
        if user_id:
            self.user_id = user_id
        
        # Clear cache when credentials change
        self.cache.clear()
        logger.info("Twitter analytics service configured with new credentials")
        
    def _get_headers(self) -> Dict[str, str]:
        """Get headers for API v2 requests"""
        # Prefer OAuth 2.0 access token, fallback to bearer token
        auth_token = self.access_token or self.bearer_token
        if not auth_token:
            logger.error("No Twitter authentication token available. Please configure access_token or bearer_token.")
            logger.error(f"access_token: {self.access_token[:20] + '...' if self.access_token else 'None'}")
            logger.error(f"bearer_token: {self.bearer_token[:20] + '...' if self.bearer_token else 'None'}")
            raise ValueError("No Twitter authentication token available. Please configure access_token or bearer_token.")
        
        logger.debug(f"Using Twitter auth token: {auth_token[:20]}... (length: {len(auth_token)})")
        
        return {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json"
        }
    
    def _check_rate_limit(self) -> bool:
        """Check if we can make a request without hitting rate limits"""
        current_time = time.time()
        
        # Reset counter if we're in a new window
        if current_time - self.last_request_time > self.rate_limit_window:
            self.request_count = 0
            self.last_request_time = current_time
        
        # Check if we've exceeded the limit
        if self.request_count >= self.max_requests_per_window:
            logger.warning(f"Rate limit reached: {self.request_count}/{self.max_requests_per_window}")
            return False
        
        return True
    
    def _make_request(self, url: str, params: Dict = None, headers: Dict = None) -> requests.Response:
        """Make a rate-limited request to Twitter API"""
        if not self._check_rate_limit():
            # Return a mock 429 response
            response = requests.Response()
            response.status_code = 429
            response._content = b'{"title":"Too Many Requests","detail":"Rate limit exceeded"}'
            return response
        
        # Use headers from _get_headers if not provided
        if headers is None:
            headers = self._get_headers()
        
        # Log request details for debugging
        logger.debug(f"Making Twitter API request to: {url}")
        auth_header = headers.get('Authorization', '')
        if auth_header:
            logger.debug(f"Using auth token: {auth_header[:30]}...")
        
        # Make the actual request
        response = requests.get(url, params=params, headers=headers, timeout=30)
        self.request_count += 1
        self.last_request_time = time.time()
        
        # Log response for debugging
        if response.status_code == 401:
            logger.warning(f"Twitter API 401 Unauthorized - Token might be invalid or expired")
            logger.warning(f"Response: {response.text[:200]}")
            logger.warning(f"URL: {url}")
            logger.warning(f"Token being used: {auth_header[:50]}...")
        
        return response
    
    def _get_cached_data(self, key: str) -> Optional[Dict]:
        """Get cached data if it's still valid"""
        if key in self.cache:
            data, timestamp = self.cache[key]
            if time.time() - timestamp < self.cache_duration:
                return data
            else:
                del self.cache[key]
        return None
    
    def _cache_data(self, key: str, data: Dict):
        """Cache data with timestamp"""
        self.cache[key] = (data, time.time())
    
    def _get_oauth_auth(self):
        """Get OAuth 1.0a authentication for API v1.1 requests"""
        try:
            from requests_oauthlib import OAuth1
            return OAuth1(
                self.consumer_key,
                self.consumer_secret,
                self.access_token,
                self.access_token_secret
            )
        except ImportError:
            logger.error("requests_oauthlib not installed. Install with: pip install requests-oauthlib")
            return None
    
    def _get_user_id(self) -> Optional[str]:
        """Get Twitter user ID from username"""
        if self.user_id:
            return self.user_id
            
        # Try OAuth 1.0a first (more reliable)
        auth = self._get_oauth_auth()
        if auth:
            try:
                # Use API v1.1 to get user info
                response = requests.get(
                    'https://api.twitter.com/1.1/account/verify_credentials.json',
                    auth=auth
                )
                
                if response.status_code == 200:
                    data = response.json()
                    self.user_id = str(data.get('id'))
                    return self.user_id
                else:
                    logger.error(f"OAuth 1.0a failed: {response.status_code} - {response.text}")
            except Exception as e:
                logger.error(f"OAuth 1.0a error: {e}")
        
        # Fallback to Bearer Token
        if not self.bearer_token:
            logger.error("No authentication available")
            return None
            
        try:
            url = f"{self.base_url}/users/by/username/{self.username}"
            response = requests.get(url, headers=self._get_headers())
            
            if response.status_code == 200:
                data = response.json()
                if 'data' in data:
                    self.user_id = data['data']['id']
                    return self.user_id
                else:
                    logger.error(f"User not found: {data}")
                    return None
            else:
                logger.error(f"Failed to get user ID: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting user ID: {e}")
            return None
    
    def is_configured(self) -> bool:
        """Check if service is properly configured"""
        return bool(self.consumer_key and self.consumer_secret and self.access_token and self.access_token_secret)
    
    def get_account_info(self) -> Dict[str, Any]:
        """Get your Twitter account information using OAuth 2.0 API v2"""
        try:
            # Try OAuth 2.0 API v2 first (preferred)
            if self.access_token or self.bearer_token:
                url = f"{self.base_url}/users/me"
                params = {
                    "user.fields": "id,name,username,description,location,verified,public_metrics,created_at,profile_image_url"
                }
                
                response = self._make_request(url, params=params)
                
                if response.status_code == 200:
                    data = response.json()
                    user_data = data.get('data', {})
                    metrics = user_data.get('public_metrics', {})
                    
                    return {
                        "success": True,
                        "account": {
                            "username": user_data.get('username'),
                            "name": user_data.get('name'),
                            "user_id": str(user_data.get('id', '')),
                            "followers_count": metrics.get('followers_count', 0),
                            "following_count": metrics.get('following_count', 0),
                            "tweet_count": metrics.get('tweet_count', 0),
                            "listed_count": metrics.get('listed_count', 0),
                            "verified": user_data.get('verified', False),
                            "description": user_data.get('description', ''),
                            "location": user_data.get('location', ''),
                            "created_at": user_data.get('created_at'),
                            "profile_image_url": user_data.get('profile_image_url')
                        }
                    }
                elif response.status_code == 401:
                    logger.warning("OAuth 2.0 failed with 401, trying OAuth 1.0a fallback")
                else:
                    logger.warning(f"OAuth 2.0 API error: {response.status_code} - {response.text[:200]}")
            
            # Fallback to OAuth 1.0a if available
            auth = self._get_oauth_auth()
            if auth:
                # Get user info using API v1.1
                response = requests.get(
                    'https://api.twitter.com/1.1/account/verify_credentials.json',
                    auth=auth,
                    timeout=30
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "success": True,
                        "account": {
                            "username": data.get('screen_name'),
                            "name": data.get('name'),
                            "user_id": str(data.get('id')),
                            "followers_count": data.get('followers_count', 0),
                            "following_count": data.get('friends_count', 0),
                            "tweet_count": data.get('statuses_count', 0),
                            "listed_count": data.get('listed_count', 0),
                            "verified": data.get('verified', False),
                            "description": data.get('description', ''),
                            "location": data.get('location', ''),
                            "created_at": data.get('created_at')
                        }
                    }
            
            return {"success": False, "error": "OAuth not configured or authentication failed"}
                
        except Exception as e:
            logger.error(f"Error getting account info: {e}")
            import traceback
            traceback.print_exc()
            return {"success": False, "error": str(e)}
    
    def get_my_tweets(self, limit: int = 25) -> Dict[str, Any]:
        """Get your own tweets with public metrics using API v2 with rate limiting"""
        try:
            # Check cache first
            cache_key = f"tweets_{limit}"
            cached_data = self._get_cached_data(cache_key)
            if cached_data:
                logger.info("Returning cached tweet data")
                return cached_data
            
            # Check if we have last successful data to show as fallback
            if cache_key in self.last_successful_data:
                logger.info("Rate limited - returning last successful data as fallback")
                fallback_data = self.last_successful_data[cache_key].copy()
                fallback_data["message"] = "Showing last fetched data (rate limited)"
                fallback_data["cached"] = True
                return fallback_data
            
            # Get user ID - try OAuth 2.0 first, then OAuth 1.0a fallback
            user_id = self.user_id  # Use configured user_id if available
            
            if not user_id:
                # Try to get user ID from OAuth 2.0 API
                if self.access_token or self.bearer_token:
                    url = f"{self.base_url}/users/me"
                    response = self._make_request(url, params={"user.fields": "id"})
                    if response.status_code == 200:
                        data = response.json()
                        user_id = str(data.get('data', {}).get('id', ''))
                        self.user_id = user_id
                
                # Fallback to OAuth 1.0a
                if not user_id:
                    auth = self._get_oauth_auth()
                    if auth:
                        user_id = self._get_user_id()
                        if user_id:
                            self.user_id = user_id
            
            if not user_id:
                return {"success": False, "error": "Could not get user ID - OAuth not configured"}
            
            # Try API v2 with OAuth 2.0 access token or Bearer Token for tweet metrics
            if self.access_token or self.bearer_token:
                url = f"{self.base_url}/users/{user_id}/tweets"
                params = {
                    "tweet.fields": "public_metrics,created_at,conversation_id",
                    "max_results": max(5, min(limit, 100))  # API requires 5-100
                }
                
                response = self._make_request(url, params=params, headers=self._get_headers())
                
                if response.status_code == 200:
                    data = response.json()
                    tweets_data = data.get('data', [])
                    tweets = []
                    
                    for tweet in tweets_data:
                        metrics = tweet.get('public_metrics', {})
                        tweets.append({
                            "id": str(tweet.get('id')),
                            "text": tweet.get('text', ''),
                            "created_at": tweet.get('created_at'),
                            "conversation_id": str(tweet.get('conversation_id', tweet.get('id'))),
                            "like_count": metrics.get('like_count', 0),
                            "retweet_count": metrics.get('retweet_count', 0),
                            "reply_count": metrics.get('reply_count', 0),
                            "quote_count": metrics.get('quote_count', 0),
                            "bookmark_count": metrics.get('bookmark_count', 0),
                            "impression_count": metrics.get('impression_count', 0),
                            "url": f"https://twitter.com/{self.username}/status/{tweet.get('id')}"
                        })
                    
                    result = {
                        "success": True,
                        "tweets": tweets,
                        "total_tweets": len(tweets)
                    }
                    
                    # Cache the result and store as last successful data
                    self._cache_data(cache_key, result)
                    self.last_successful_data[cache_key] = result
                    return result
                    
                elif response.status_code == 403:
                    # Account is private or restricted
                    result = {
                        "success": True,
                        "tweets": [],
                        "total_tweets": 0,
                        "message": "Account is private - tweets not accessible via public API"
                    }
                    self._cache_data(cache_key, result)
                    self.last_successful_data[cache_key] = result
                    return result
                    
                elif response.status_code == 429:
                    # Rate limited - return last successful data if available
                    logger.warning("Rate limited - checking for last successful data")
                    if cache_key in self.last_successful_data:
                        fallback_data = self.last_successful_data[cache_key].copy()
                        fallback_data["message"] = "Showing last fetched data (rate limited)"
                        fallback_data["cached"] = True
                        return fallback_data
                    else:
                        return {
                            "success": True,
                            "tweets": [],
                            "total_tweets": 0,
                            "message": "Rate limited - no previous data available"
                        }
                else:
                    logger.warning(f"API v2 error {response.status_code}: {response.text}")
            
            # Fallback to OAuth 1.0a search API (only if Bearer Token fails)
            url = 'https://api.twitter.com/1.1/search/tweets.json'
            params = {
                'q': f'from:{self.username}',
                'count': min(limit, 100),  # API limit
                'result_type': 'recent'
            }
            
            response = requests.get(url, auth=auth, params=params)
            
            if response.status_code == 200:
                data = response.json()
                tweets_data = data.get('statuses', [])
                tweets = []
                
                for tweet in tweets_data:
                    tweets.append({
                        "id": str(tweet.get('id')),
                        "text": tweet.get('text', ''),
                        "created_at": tweet.get('created_at'),
                        "conversation_id": str(tweet.get('id')),
                        "like_count": tweet.get('favorite_count', 0),
                        "retweet_count": tweet.get('retweet_count', 0),
                        "reply_count": 0,  # Not available in v1.1
                        "quote_count": 0,  # Not available in v1.1
                        "bookmark_count": 0,  # Not available in v1.1
                        "impression_count": 0,  # Not available in free tier
                        "url": f"https://twitter.com/{self.username}/status/{tweet.get('id')}"
                    })
                
                result = {
                    "success": True,
                    "tweets": tweets,
                    "total_tweets": len(tweets)
                }
                self._cache_data(cache_key, result)
                self.last_successful_data[cache_key] = result
                return result
            else:
                # If both fail, return last successful data if available
                if cache_key in self.last_successful_data:
                    fallback_data = self.last_successful_data[cache_key].copy()
                    fallback_data["message"] = "Showing last fetched data (API unavailable)"
                    fallback_data["cached"] = True
                    return fallback_data
                else:
                    logger.warning(f"All API methods failed, returning empty tweets")
                    return {
                        "success": True,
                        "tweets": [],
                        "total_tweets": 0,
                        "message": "Tweets not accessible with current API access level"
                    }
                
        except Exception as e:
            logger.error(f"Error getting my tweets: {e}")
            return {"success": False, "error": str(e)}
    
    def get_tweet_replies(self, tweet_id: str, limit: int = 25) -> Dict[str, Any]:
        """Get replies to a specific tweet"""
        if not self.is_configured():
            return {"success": False, "error": "Service not configured"}
        
        try:
            url = f"{self.base_url}/tweets/search/recent"
            params = {
                "query": f"conversation_id:{tweet_id}",
                "tweet.fields": "author_id,created_at,public_metrics",
                "max_results": min(limit, 100)
            }
            
            response = requests.get(url, headers=self._get_headers(), params=params)
            
            if response.status_code == 200:
                data = response.json()
                replies = []
                
                for tweet in data.get('data', []):
                    # Skip the original tweet (same ID)
                    if tweet.get('id') == tweet_id:
                        continue
                        
                    metrics = tweet.get('public_metrics', {})
                    replies.append({
                        "id": tweet.get('id'),
                        "text": tweet.get('text', ''),
                        "author_id": tweet.get('author_id'),
                        "created_at": tweet.get('created_at'),
                        "like_count": metrics.get('like_count', 0),
                        "retweet_count": metrics.get('retweet_count', 0),
                        "reply_count": metrics.get('reply_count', 0),
                        "quote_count": metrics.get('quote_count', 0)
                    })
                
                return {
                    "success": True,
                    "replies": replies,
                    "total_replies": len(replies)
                }
            else:
                return {"success": False, "error": f"API error: {response.status_code}"}
                
        except Exception as e:
            logger.error(f"Error getting tweet replies: {e}")
            return {"success": False, "error": str(e)}
    
    def get_tweet_analytics(self, tweet_id: str) -> Dict[str, Any]:
        """Get detailed analytics for a specific tweet"""
        if not self.is_configured():
            return {"success": False, "error": "Service not configured"}
        
        try:
            # Get tweet details
            url = f"{self.base_url}/tweets/{tweet_id}"
            params = {
                "tweet.fields": "public_metrics,created_at,conversation_id"
            }
            
            response = requests.get(url, headers=self._get_headers(), params=params)
            
            if response.status_code == 200:
                data = response.json()
                tweet_data = data.get('data', {})
                metrics = tweet_data.get('public_metrics', {})
                
                # Get replies for engagement analysis
                replies_data = self.get_tweet_replies(tweet_id, limit=100)
                replies = replies_data.get('replies', []) if replies_data.get('success') else []
                
                # Calculate engagement metrics
                like_count = metrics.get('like_count', 0)
                retweet_count = metrics.get('retweet_count', 0)
                reply_count = metrics.get('reply_count', 0)
                quote_count = metrics.get('quote_count', 0)
                impression_count = metrics.get('impression_count', 0)
                
                total_engagement = like_count + retweet_count + reply_count + quote_count
                engagement_rate = (total_engagement / impression_count * 100) if impression_count > 0 else 0
                
                # Calculate time metrics
                created_at = tweet_data.get('created_at')
                if created_at:
                    tweet_time = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    time_since_tweet = datetime.now(timezone.utc) - tweet_time
                else:
                    time_since_tweet = None
                
                analytics = {
                    "tweet_id": tweet_id,
                    "text": tweet_data.get('text', ''),
                    "created_at": created_at,
                    "time_since_tweet": str(time_since_tweet).split('.')[0] if time_since_tweet else None,
                    "metrics": {
                        "likes": like_count,
                        "retweets": retweet_count,
                        "replies": reply_count,
                        "quotes": quote_count,
                        "bookmarks": metrics.get('bookmark_count', 0),
                        "impressions": impression_count,
                        "total_engagement": total_engagement,
                        "engagement_rate": round(engagement_rate, 2)
                    },
                    "replies": {
                        "count": len(replies),
                        "recent_replies": replies[:5]  # Last 5 replies
                    },
                    "url": f"https://twitter.com/{self.username}/status/{tweet_id}"
                }
                
                return {"success": True, "analytics": analytics}
            else:
                return {"success": False, "error": f"API error: {response.status_code}"}
                
        except Exception as e:
            logger.error(f"Error getting tweet analytics: {e}")
            return {"success": False, "error": str(e)}
    
    def get_account_analytics(self) -> Dict[str, Any]:
        """Get comprehensive account analytics"""
        if not self.is_configured():
            return {"success": False, "error": "Service not configured"}
        
        try:
            # Get account info
            account_info = self.get_account_info()
            if not account_info.get("success"):
                return account_info
            
            # Get recent tweets
            tweets_data = self.get_my_tweets(limit=100)
            if not tweets_data.get("success"):
                return tweets_data
            
            tweets = tweets_data.get("tweets", [])
            
            # Calculate analytics
            total_tweets = len(tweets)
            
            # Tweet analytics
            total_likes = sum(tweet.get("like_count", 0) for tweet in tweets)
            total_retweets = sum(tweet.get("retweet_count", 0) for tweet in tweets)
            total_replies = sum(tweet.get("reply_count", 0) for tweet in tweets)
            total_quotes = sum(tweet.get("quote_count", 0) for tweet in tweets)
            total_impressions = sum(tweet.get("impression_count", 0) for tweet in tweets)
            
            avg_likes = total_likes / total_tweets if total_tweets > 0 else 0
            avg_retweets = total_retweets / total_tweets if total_tweets > 0 else 0
            avg_replies = total_replies / total_tweets if total_tweets > 0 else 0
            avg_impressions = total_impressions / total_tweets if total_tweets > 0 else 0
            
            # Engagement rate calculation
            total_engagement = total_likes + total_retweets + total_replies + total_quotes
            overall_engagement_rate = (total_engagement / total_impressions * 100) if total_impressions > 0 else 0
            
            # Top performing tweets
            top_tweets = sorted(tweets, key=lambda x: x.get("like_count", 0) + x.get("retweet_count", 0), reverse=True)[:5]
            
            # Recent activity (last 7 days)
            week_ago = datetime.now(timezone.utc) - timedelta(days=7)
            recent_tweets = []
            for tweet in tweets:
                if tweet.get("created_at"):
                    tweet_time = datetime.fromisoformat(tweet["created_at"].replace('Z', '+00:00'))
                    if tweet_time > week_ago:
                        recent_tweets.append(tweet)
            
            analytics = {
                "account": account_info.get("account", {}),
                "summary": {
                    "total_tweets": total_tweets,
                    "total_likes": total_likes,
                    "total_retweets": total_retweets,
                    "total_replies": total_replies,
                    "total_quotes": total_quotes,
                    "total_impressions": total_impressions,
                    "avg_likes": round(avg_likes, 2),
                    "avg_retweets": round(avg_retweets, 2),
                    "avg_replies": round(avg_replies, 2),
                    "avg_impressions": round(avg_impressions, 2),
                    "overall_engagement_rate": round(overall_engagement_rate, 2),
                    "recent_tweets_7_days": len(recent_tweets)
                },
                "top_tweets": top_tweets,
                "recent_activity": {
                    "tweets": recent_tweets[:10]
                }
            }
            
            return {"success": True, "analytics": analytics}
            
        except Exception as e:
            logger.error(f"Error getting account analytics: {e}")
            return {"success": False, "error": str(e)}

# Global service instance
twitter_analytics_service = TwitterAnalyticsService()
