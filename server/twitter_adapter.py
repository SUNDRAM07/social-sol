import os
import logging
import requests 
from datetime import datetime, timezone, timedelta
from requests_oauthlib import OAuth1Session
from typing import List, Dict, Optional, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Twitter API Configuration
TWITTER_CONSUMER_KEY = os.getenv("TWITTER_CONSUMER_KEY")
TWITTER_CONSUMER_SECRET = os.getenv("TWITTER_CONSUMER_SECRET")
TWITTER_ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN")
TWITTER_ACCESS_TOKEN_SECRET = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")
TWITTER_BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN")

TWITTER_API_BASE = "https://api.twitter.com/2"
TWITTER_API_V1 = "https://api.twitter.com/1.1"

logger = logging.getLogger(__name__)

class TwitterAdapter:
    """Low-level Twitter API adapter for social media agent"""
    
    def __init__(self):
        self.oauth1 = None
        self.bearer_token = TWITTER_BEARER_TOKEN
        self._setup_oauth1()
    
    def _setup_oauth1(self):
        """Setup OAuth 1.0a session for authenticated requests"""
        if all([TWITTER_CONSUMER_KEY, TWITTER_CONSUMER_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET]):
            self.oauth1 = OAuth1Session(
                TWITTER_CONSUMER_KEY,
                TWITTER_CONSUMER_SECRET,
                TWITTER_ACCESS_TOKEN,
                TWITTER_ACCESS_TOKEN_SECRET
            )
            logger.info("Twitter OAuth 1.0a session initialized")
        else:
            logger.warning("Twitter OAuth 1.0a credentials not fully configured")
    
    def _get_headers(self, use_bearer: bool = False) -> Dict[str, str]:
        """Get appropriate headers for API requests"""
        if use_bearer and self.bearer_token:
            return {"Authorization": f"Bearer {self.bearer_token}"}
        return {"Content-Type": "application/json"}
    
    def is_configured(self) -> bool:
        """Check if Twitter API is properly configured"""
        return bool(self.oauth1 and self.bearer_token)
    
    def test_connection(self) -> Dict[str, Any]:
        """Test Twitter API connection"""
        if not self.is_configured():
            return {"error": "Twitter API not configured"}
        
        try:
            # Test with a simple API call
            url = f"{TWITTER_API_BASE}/users/me"
            response = self.oauth1.get(url)
            
            if response.status_code == 200:
                user_data = response.json()
                return {
                    "success": True,
                    "user": user_data.get("data", {}),
                    "message": "Twitter connection successful"
                }
            else:
                return {
                    "error": f"Twitter API error: {response.status_code}",
                    "details": response.text
                }
        except Exception as e:
            logger.error(f"Twitter connection test failed: {e}")
            return {"error": f"Connection test failed: {str(e)}"}
    
    def create_tweet(self, text: str, media_ids: Optional[List[str]] = None, 
                    reply_to: Optional[str] = None, quote_tweet_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a new tweet using Twitter API v2
        
        Args:
            text: Tweet content
            media_ids: List of media IDs to attach
            reply_to: Tweet ID to reply to
            quote_tweet_id: Tweet ID to quote
        
        Returns:
            API response data
        """
        if not self.oauth1:
            return {"error": "Twitter OAuth 1.0a not configured"}
        
        url = f"{TWITTER_API_BASE}/tweets"
        payload = {"text": text}
        
        # Add media if provided
        if media_ids:
            payload["media"] = {"media_ids": media_ids}
        
        # Add reply settings
        if reply_to:
            payload["reply"] = {"in_reply_to_tweet_id": reply_to}
        
        # Add quote tweet
        if quote_tweet_id:
            payload["quote_tweet_id"] = quote_tweet_id
        
        try:
            response = self.oauth1.post(url, json=payload)
            response.raise_for_status()
            result = response.json()
            logger.info(f"Tweet created successfully: {result.get('data', {}).get('id')}")
            return result
        except requests.exceptions.RequestException as e:
            logger.error(f"Error creating tweet: {e}")
            return {"error": str(e)}
    
    def upload_media(self, media_path: str) -> Optional[str]:
        """
        Upload media using Twitter API v1.1 (correct endpoint for media uploads)
        
        Args:
            media_path: Path to media file
        
        Returns:
            Media ID if successful, None otherwise
        """
        if not self.oauth1:
            logger.error("Twitter OAuth 1.0a not configured for media upload")
            return None
        
        # Use the correct v1.1 endpoint for media uploads
        url = "https://upload.twitter.com/1.1/media/upload.json"
        
        try:
            # Get file info
            file_size = os.path.getsize(media_path)
            file_extension = os.path.splitext(media_path)[1].lower()
            
            # Determine media type
            media_type_map = {
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg', 
                '.png': 'image/png',
                '.gif': 'image/gif',
                '.webp': 'image/webp'
            }
            media_type = media_type_map.get(file_extension, 'image/jpeg')
            
            # Check file size (Twitter limit is 5MB for images)
            if file_size > 5 * 1024 * 1024:  # 5MB
                logger.error(f"Media file too large: {file_size} bytes (max 5MB)")
                return None
            
            # For small files (< 5MB), use simple upload
            if file_size < 5 * 1024 * 1024:
                logger.info(f"Using simple upload for {media_path} ({file_size} bytes)")
                
                with open(media_path, 'rb') as media_file:
                    files = {'media': media_file}
                    data = {
                        'media_category': 'tweet_image'
                    }
                    
                    response = self.oauth1.post(url, files=files, data=data)
                    response.raise_for_status()
                    result = response.json()
                    media_id = result.get('media_id_string')
                    
                    if media_id:
                        logger.info(f"Media uploaded successfully: {media_id}")
                        return media_id
                    else:
                        logger.error(f"No media_id in response: {result}")
                        return None
            else:
                # For larger files, would need chunked upload
                logger.error("Chunked upload not implemented for large files")
                return None
                
        except Exception as e:
            logger.error(f"Error uploading media: {e}")
            return None
    
    def delete_tweet(self, tweet_id: str) -> Dict[str, Any]:
        """Delete a tweet"""
        if not self.oauth1:
            return {"error": "Twitter OAuth 1.0a not configured"}
        
        url = f"{TWITTER_API_BASE}/tweets/{tweet_id}"
        
        try:
            response = self.oauth1.delete(url)
            response.raise_for_status()
            result = response.json()
            logger.info(f"Tweet {tweet_id} deleted successfully")
            return result
        except requests.exceptions.RequestException as e:
            logger.error(f"Error deleting tweet: {e}")
            return {"error": str(e)}
    
    def get_user_tweets(self, user_id: str = None, username: str = None, 
                       max_results: int = 10) -> Dict[str, Any]:
        """Get tweets from a user's timeline"""
        if not self.bearer_token:
            return {"error": "Twitter Bearer token not configured"}
        
        # If username provided, get user ID first
        if username and not user_id:
            user_info = self.get_user_by_username(username)
            if "data" in user_info:
                user_id = user_info["data"]["id"]
            else:
                return {"error": "Could not find user"}
        
        if not user_id:
            return {"error": "User ID or username required"}
        
        url = f"{TWITTER_API_BASE}/users/{user_id}/tweets"
        params = {
            "max_results": min(max_results, 100),
            "tweet.fields": "created_at,public_metrics,entities"
        }
        
        try:
            response = requests.get(
                url, 
                headers=self._get_headers(use_bearer=True),
                params=params
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting user tweets: {e}")
            return {"error": str(e)}
    
    def get_user_by_username(self, username: str) -> Dict[str, Any]:
        """Get user information by username"""
        if not self.bearer_token:
            return {"error": "Twitter Bearer token not configured"}
        
        url = f"{TWITTER_API_BASE}/users/by/username/{username}"
        params = {"user.fields": "id,name,username,description,public_metrics"}
        
        try:
            response = requests.get(
                url,
                headers=self._get_headers(use_bearer=True),
                params=params
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting user info: {e}")
            return {"error": str(e)}
