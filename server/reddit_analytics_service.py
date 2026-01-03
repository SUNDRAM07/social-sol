#!/usr/bin/env python3
"""
Reddit Analytics Service
Provides comprehensive analytics for your own Reddit posts and account
"""

import os
import logging
import requests
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
# Environment variables are loaded by the system

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RedditAnalyticsService:
    """Service for Reddit analytics and account data"""
    
    def __init__(self, access_token=None, refresh_token=None, username=None):
        """Initialize Reddit analytics service"""
        # Only client ID/secret should be in .env, not access tokens
        self.client_id = os.getenv('REDDIT_CLIENT_ID')  # Client ID - OK in .env
        self.client_secret = os.getenv('REDDIT_CLIENT_SECRET')  # Client Secret - OK in .env
        # Access tokens should come from database, not .env
        self.access_token = access_token or os.getenv('REDDIT_ACCESS_TOKEN')
        self.refresh_token = refresh_token or os.getenv('REDDIT_REFRESH_TOKEN')
        self.username = username
        self.user_agent = os.getenv('REDDIT_USER_AGENT', 'shephertz/1.0')  # User agent is OK in .env
        
        self.base_url = "https://oauth.reddit.com"
        self.auth_url = "https://www.reddit.com/api/v1/access_token"
    
    def set_credentials(self, access_token: str, refresh_token: str = None, username: str = None):
        """Set credentials for the service"""
        self.access_token = access_token
        if refresh_token:
            self.refresh_token = refresh_token
        if username:
            self.username = username
    
    def _get_headers(self) -> Dict[str, str]:
        """Get headers for API requests"""
        return {
            "User-Agent": self.user_agent,
            "Authorization": f"Bearer {self.access_token}"
        }
    
    def _refresh_access_token(self) -> bool:
        """Refresh the access token using refresh token"""
        if not self.refresh_token:
            logger.error("No refresh token available")
            return False
            
        try:
            import base64
            auth_header = base64.b64encode(f'{self.client_id}:{self.client_secret}'.encode()).decode()
            
            headers = {
                'User-Agent': self.user_agent,
                'Authorization': f'Basic {auth_header}',
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            data = {
                'grant_type': 'refresh_token',
                'refresh_token': self.refresh_token
            }
            
            logger.info("Refreshing Reddit access token...")
            response = requests.post(self.auth_url, headers=headers, data=data)
            
            if response.status_code == 200:
                tokens = response.json()
                self.access_token = tokens.get('access_token')
                os.environ['REDDIT_ACCESS_TOKEN'] = self.access_token
                logger.info("✅ Reddit access token refreshed successfully")
                return True
            else:
                logger.error(f"❌ Failed to refresh token: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Exception during token refresh: {e}")
            return False
    
    def is_configured(self) -> bool:
        """Check if service is properly configured"""
        has_credentials = bool(self.client_id and self.client_secret and self.access_token)
        if not has_credentials:
            logger.warning(f"RedditAnalyticsService not configured: client_id={bool(self.client_id)}, client_secret={bool(self.client_secret)}, access_token={bool(self.access_token)}")
        return has_credentials
    
    def get_user_subreddit_followers(self, username: str) -> int:
        """Get follower count from user's profile subreddit (r/u_username)"""
        try:
            # Try to get user-subreddit subscriber count
            url = f"https://www.reddit.com/r/u_{username}/about.json"
            headers = {'User-Agent': self.user_agent}
            
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if 'data' in data and 'subscribers' in data['data']:
                    return data['data']['subscribers']
            elif response.status_code == 404:
                # User-subreddit doesn't exist or is private
                logger.info(f"User-subreddit r/u_{username} not accessible")
                return 0
            else:
                logger.warning(f"Failed to get user-subreddit data: {response.status_code}")
                return 0
                
        except Exception as e:
            logger.error(f"Error getting user-subreddit followers: {e}")
            return 0

    def get_account_info(self) -> Dict[str, Any]:
        """Get your Reddit account information"""
        if not self.is_configured():
            return {"success": False, "error": "Service not configured"}
        
        try:
            response = requests.get(f"{self.base_url}/api/v1/me", headers=self._get_headers())
            
            if response.status_code == 401:
                # Token expired, try to refresh
                if self._refresh_access_token():
                    response = requests.get(f"{self.base_url}/api/v1/me", headers=self._get_headers())
                else:
                    return {"success": False, "error": "Failed to refresh token"}
            
            if response.status_code == 200:
                data = response.json()
                username = data.get('name')
                
                # Update instance username if not set
                if username and not self.username:
                    self.username = username
                
                # Get follower count from user-subreddit
                followers_count = 0
                if username:
                    followers_count = self.get_user_subreddit_followers(username)
                
                return {
                    "success": True,
                    "account": {
                        "username": username,
                        "user_id": data.get('id'),
                        "total_karma": data.get('total_karma', 0),
                        "link_karma": data.get('link_karma', 0),
                        "comment_karma": data.get('comment_karma', 0),
                        "followers_count": followers_count,  # Real Reddit followers
                        "account_created": data.get('created_utc'),
                        "is_gold": data.get('is_gold', False),
                        "is_mod": data.get('is_mod', False),
                        "verified": data.get('verified', False)
                    }
                }
            else:
                return {"success": False, "error": f"API error: {response.status_code}"}
                
        except Exception as e:
            logger.error(f"Error getting account info: {e}")
            return {"success": False, "error": str(e)}
    
    def get_my_posts(self, limit: int = 25, sort: str = "new") -> Dict[str, Any]:
        """Get your own submitted posts"""
        if not self.is_configured():
            return {"success": False, "error": "Service not configured"}
        
        # If username not set, get it from account info first
        if not self.username:
            account_info = self.get_account_info()
            if account_info.get("success") and account_info.get("account", {}).get("username"):
                self.username = account_info["account"]["username"]
            else:
                return {"success": False, "error": "Unable to determine Reddit username"}
        
        try:
            url = f"{self.base_url}/user/{self.username}/submitted"
            params = {
                "limit": min(limit, 100),  # Reddit API limit
                "sort": sort,
                "raw_json": 1
            }
            
            response = requests.get(url, headers=self._get_headers(), params=params)
            
            if response.status_code == 401:
                if self._refresh_access_token():
                    response = requests.get(url, headers=self._get_headers(), params=params)
                else:
                    return {"success": False, "error": "Failed to refresh token"}
            
            if response.status_code == 200:
                data = response.json()
                posts = []
                
                for child in data.get('data', {}).get('children', []):
                    post_data = child.get('data', {})
                    posts.append({
                        "id": post_data.get('id'),
                        "title": post_data.get('title', ''),
                        "subreddit": post_data.get('subreddit', ''),
                        "score": post_data.get('score', 0),
                        "upvote_ratio": post_data.get('upvote_ratio', 0),
                        "num_comments": post_data.get('num_comments', 0),
                        "created_utc": post_data.get('created_utc', 0),
                        "url": post_data.get('url', ''),
                        "permalink": f"https://reddit.com{post_data.get('permalink', '')}",
                        "is_self": post_data.get('is_self', False),
                        "selftext": post_data.get('selftext', ''),
                        "domain": post_data.get('domain', ''),
                        "over_18": post_data.get('over_18', False),
                        "spoiler": post_data.get('spoiler', False),
                        "locked": post_data.get('locked', False),
                        "stickied": post_data.get('stickied', False)
                    })
                
                return {
                    "success": True,
                    "posts": posts,
                    "total_posts": len(posts)
                }
            else:
                return {"success": False, "error": f"API error: {response.status_code}"}
                
        except Exception as e:
            logger.error(f"Error getting my posts: {e}")
            return {"success": False, "error": str(e)}
    
    def get_my_comments(self, limit: int = 25, sort: str = "new") -> Dict[str, Any]:
        """Get your own comments"""
        if not self.is_configured():
            return {"success": False, "error": "Service not configured"}
        
        # If username not set, get it from account info first
        if not self.username:
            account_info = self.get_account_info()
            if account_info.get("success") and account_info.get("account", {}).get("username"):
                self.username = account_info["account"]["username"]
            else:
                return {"success": False, "error": "Unable to determine Reddit username"}
        
        try:
            url = f"{self.base_url}/user/{self.username}/comments"
            params = {
                "limit": min(limit, 100),
                "sort": sort,
                "raw_json": 1
            }
            
            response = requests.get(url, headers=self._get_headers(), params=params)
            
            if response.status_code == 401:
                if self._refresh_access_token():
                    response = requests.get(url, headers=self._get_headers(), params=params)
                else:
                    return {"success": False, "error": "Failed to refresh token"}
            
            if response.status_code == 200:
                data = response.json()
                comments = []
                
                for child in data.get('data', {}).get('children', []):
                    comment_data = child.get('data', {})
                    comments.append({
                        "id": comment_data.get('id'),
                        "body": comment_data.get('body', ''),
                        "subreddit": comment_data.get('subreddit', ''),
                        "score": comment_data.get('score', 0),
                        "created_utc": comment_data.get('created_utc', 0),
                        "permalink": f"https://reddit.com{comment_data.get('permalink', '')}",
                        "parent_id": comment_data.get('parent_id', ''),
                        "link_title": comment_data.get('link_title', ''),
                        "link_url": comment_data.get('link_url', ''),
                        "is_submitter": comment_data.get('is_submitter', False)
                    })
                
                return {
                    "success": True,
                    "comments": comments,
                    "total_comments": len(comments)
                }
            else:
                return {"success": False, "error": f"API error: {response.status_code}"}
                
        except Exception as e:
            logger.error(f"Error getting my comments: {e}")
            return {"success": False, "error": str(e)}
    
    def get_post_analytics(self, post_id: str) -> Dict[str, Any]:
        """Get detailed analytics for a specific post"""
        if not self.is_configured():
            return {"success": False, "error": "Service not configured"}
        
        try:
            # Get post details
            url = f"{self.base_url}/comments/{post_id}"
            params = {"limit": 1, "raw_json": 1}
            
            response = requests.get(url, headers=self._get_headers(), params=params)
            
            if response.status_code == 401:
                if self._refresh_access_token():
                    response = requests.get(url, headers=self._get_headers(), params=params)
                else:
                    return {"success": False, "error": "Failed to refresh token"}
            
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    post_data = data[0]["data"]["children"][0]["data"]
                    
                    # Calculate engagement metrics
                    score = post_data.get("score", 0)
                    upvote_ratio = post_data.get("upvote_ratio", 0)
                    num_comments = post_data.get("num_comments", 0)
                    created_utc = post_data.get("created_utc", 0)
                    
                    # Calculate upvotes and downvotes
                    if upvote_ratio > 0:
                        total_votes = abs(score) / (2 * upvote_ratio - 1) if upvote_ratio != 0.5 else abs(score) * 2
                        estimated_upvotes = max(0, int((score + total_votes) / 2))
                        estimated_downvotes = max(0, int(total_votes - estimated_upvotes))
                    else:
                        estimated_upvotes = max(0, score)
                        estimated_downvotes = 0
                    
                    # Calculate engagement score
                    engagement_score = score + num_comments
                    
                    # Calculate time metrics
                    post_time = datetime.fromtimestamp(created_utc)
                    time_since_post = datetime.now(timezone.utc) - post_time
                    
                    analytics = {
                        "post_id": post_id,
                        "title": post_data.get("title", ""),
                        "subreddit": f"r/{post_data.get('subreddit', '')}",
                        "score": score,
                        "upvote_ratio": upvote_ratio,
                        "estimated_upvotes": estimated_upvotes,
                        "estimated_downvotes": estimated_downvotes,
                        "num_comments": num_comments,
                        "engagement_score": engagement_score,
                        "created_utc": created_utc,
                        "created_time": post_time.isoformat(),
                        "time_since_post_hours": round(time_since_post.total_seconds() / 3600, 2),
                        "permalink": f"https://reddit.com{post_data.get('permalink', '')}",
                        "url": post_data.get("url", ""),
                        "is_self": post_data.get("is_self", False),
                        "over_18": post_data.get("over_18", False),
                        "spoiler": post_data.get("spoiler", False),
                        "locked": post_data.get("locked", False),
                        "stickied": post_data.get("stickied", False)
                    }
                    
                    return {"success": True, "analytics": analytics}
                else:
                    return {"success": False, "error": "Post not found"}
            else:
                return {"success": False, "error": f"API error: {response.status_code}"}
                
        except Exception as e:
            logger.error(f"Error getting post analytics: {e}")
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
            
            # Get recent posts
            posts_data = self.get_my_posts(limit=100)
            if not posts_data.get("success"):
                return posts_data
            
            # Get recent comments
            comments_data = self.get_my_comments(limit=100)
            if not comments_data.get("success"):
                return comments_data
            
            posts = posts_data.get("posts", [])
            comments = comments_data.get("comments", [])
            
            # Calculate analytics
            total_posts = len(posts)
            total_comments = len(comments)
            
            # Post analytics
            total_post_score = sum(post.get("score", 0) for post in posts)
            total_post_comments = sum(post.get("num_comments", 0) for post in posts)
            avg_post_score = total_post_score / total_posts if total_posts > 0 else 0
            avg_post_comments = total_post_comments / total_posts if total_posts > 0 else 0
            
            # Comment analytics
            total_comment_score = sum(comment.get("score", 0) for comment in comments)
            avg_comment_score = total_comment_score / total_comments if total_comments > 0 else 0
            
            # Subreddit distribution
            subreddit_posts = {}
            subreddit_comments = {}
            
            for post in posts:
                subreddit = post.get("subreddit", "unknown")
                subreddit_posts[subreddit] = subreddit_posts.get(subreddit, 0) + 1
            
            for comment in comments:
                subreddit = comment.get("subreddit", "unknown")
                subreddit_comments[subreddit] = subreddit_comments.get(subreddit, 0) + 1
            
            # Top performing posts
            top_posts = sorted(posts, key=lambda x: x.get("score", 0), reverse=True)[:5]
            
            # Recent activity (last 7 days)
            week_ago = datetime.now(timezone.utc) - timedelta(days=7)
            recent_posts = [p for p in posts if datetime.fromtimestamp(p.get("created_utc", 0), tz=timezone.utc) > week_ago]
            recent_comments = [c for c in comments if datetime.fromtimestamp(c.get("created_utc", 0), tz=timezone.utc) > week_ago]
            
            analytics = {
                "account": account_info.get("account", {}),
                "summary": {
                    "total_posts": total_posts,
                    "total_comments": total_comments,
                    "total_post_score": total_post_score,
                    "total_comment_score": total_comment_score,
                    "avg_post_score": round(avg_post_score, 2),
                    "avg_post_comments": round(avg_post_comments, 2),
                    "avg_comment_score": round(avg_comment_score, 2),
                    "recent_posts_7_days": len(recent_posts),
                    "recent_comments_7_days": len(recent_comments)
                },
                "subreddit_distribution": {
                    "posts": subreddit_posts,
                    "comments": subreddit_comments
                },
                "top_posts": top_posts,
                "recent_activity": {
                    "posts": recent_posts[:10],
                    "comments": recent_comments[:10]
                }
            }
            
            return {"success": True, "analytics": analytics}
            
        except Exception as e:
            logger.error(f"Error getting account analytics: {e}")
            return {"success": False, "error": str(e)}

# Global service instance
reddit_analytics_service = RedditAnalyticsService()
