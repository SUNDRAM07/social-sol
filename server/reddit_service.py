"""
Reddit Service for Social Media Agent
Integrates Reddit posting functionality into the main social media agent
"""

import os
import logging
import json
import requests
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from reddit_token_refresh import RedditTokenRefresh

logger = logging.getLogger(__name__)

class RedditService:
    """Service class for Reddit operations in the social media agent"""
    
    def __init__(self, access_token=None, refresh_token=None):
        """Initialize Reddit service"""
        self.adapter = None
        self.schedule_file = "reddit_scheduled_posts.json"
        
        # Initialize token refresh service with optional credentials
        self.token_service = RedditTokenRefresh()
        if access_token:
            self.token_service.access_token = access_token
        if refresh_token:
            self.token_service.refresh_token = refresh_token
        
        # Reddit API base URL
        self.api_base = "https://oauth.reddit.com"
        
        self._initialize_adapter()
    
    def set_credentials(self, access_token: str, refresh_token: str = None):
        """Set credentials for the service"""
        self.token_service.access_token = access_token
        if refresh_token:
            self.token_service.refresh_token = refresh_token
        self._initialize_adapter()
    
    def _initialize_adapter(self):
        """Initialize Reddit adapter with token management"""
        try:
            # Test connection and refresh token if needed
            if self.token_service.test_connection():
                logger.info("✅ Reddit service initialized successfully")
                self.adapter = True
            else:
                logger.error("❌ Failed to initialize Reddit service")
                self.adapter = False
        except Exception as e:
            logger.error(f"❌ Failed to initialize Reddit service: {e}")
            self.adapter = False
    
    def is_configured(self) -> bool:
        """Check if service is properly configured"""
        return bool(self.adapter and self.token_service.access_token)

    def _get_headers(self) -> dict:
        """Get headers with valid access token"""
        return self.token_service.get_headers()

    def test_connection(self) -> Dict[str, Any]:
        """Test Reddit connection"""
        try:
            if self.token_service.test_connection():
                return {"status": "connected", "message": "Reddit connection successful"}
            else:
                return {"status": "disconnected", "message": "Reddit connection failed"}
        except Exception as e:
            return {"status": "error", "message": f"Reddit connection error: {e}"}

    def post_to_reddit(self, title: str, content: str, subreddit: str = "test") -> Dict[str, Any]:
        """Post content to Reddit"""
        try:
            if not self.adapter:
                return {"success": False, "message": "Reddit service not initialized"}

            headers = self._get_headers()
            
            # Prepare post data
            post_data = {
                'sr': subreddit,
                'kind': 'self',
                'text': content,
                'title': title
            }

            # Submit post
            response = requests.post(
                f"{self.api_base}/api/submit",
                headers=headers,
                data=post_data,
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    post_url = f"https://reddit.com{result['data']['url']}"
                    return {
                        "success": True,
                        "message": "Post submitted successfully",
                        "url": post_url,
                        "post_id": result['data']['id']
                    }
                else:
                    return {
                        "success": False,
                        "message": f"Reddit API error: {result.get('errors', 'Unknown error')}"
                    }
            else:
                return {
                    "success": False,
                    "message": f"HTTP error: {response.status_code} - {response.text}"
                }

        except Exception as e:
            logger.error(f"❌ Error posting to Reddit: {e}")
            return {"success": False, "message": f"Posting error: {e}"}

    def get_reddit_analytics(self, post_id: str = None) -> Dict[str, Any]:
        """Get Reddit analytics for a post"""
        try:
            if not self.adapter:
                return {"success": False, "message": "Reddit service not initialized"}

            headers = self._get_headers()
            
            # Get user's recent posts if no post_id provided
            if not post_id:
                response = requests.get(
                    f"{self.api_base}/user/SuspiciousPapaya3497/submitted",
                    headers=headers,
                    timeout=10
                )
            else:
                response = requests.get(
                    f"{self.api_base}/api/info",
                    headers=headers,
                    params={'id': f't3_{post_id}'},
                    timeout=10
                )

            if response.status_code == 200:
                data = response.json()
                posts = data.get('data', {}).get('children', [])
                
                analytics = []
                for post in posts:
                    post_data = post.get('data', {})
                    analytics.append({
                        'title': post_data.get('title'),
                        'score': post_data.get('score', 0),
                        'upvote_ratio': post_data.get('upvote_ratio', 0),
                        'num_comments': post_data.get('num_comments', 0),
                        'created_utc': post_data.get('created_utc'),
                        'url': f"https://reddit.com{post_data.get('permalink', '')}"
                    })
                
                return {
                    "success": True,
                    "analytics": analytics,
                    "message": f"Retrieved {len(analytics)} posts"
                }
            else:
                return {
                    "success": False,
                    "message": f"HTTP error: {response.status_code} - {response.text}"
                }
                
        except Exception as e:
            logger.error(f"❌ Error getting Reddit analytics: {e}")
            return {"success": False, "message": f"Analytics error: {e}"}

    def get_service_status(self) -> Dict[str, Any]:
        """Get the current status of the Reddit service"""
        try:
            if not all([self.token_service.client_id, self.token_service.client_secret, self.token_service.refresh_token]):
                return {
                    "status": "disconnected",
                    "message": "Missing Reddit credentials. Please set REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, and REDDIT_REFRESH_TOKEN environment variables."
                }

            if self.token_service.test_connection():
                return {
                    "status": "connected",
                    "message": "Reddit service is ready",
                    "auto_refresh": "Access token will auto-refresh when needed"
                }
            else:
                return {
                    "status": "disconnected", 
                    "message": "Reddit connection failed"
                }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Reddit service error: {e}"
            }

# Create global instance
reddit_service = RedditService()