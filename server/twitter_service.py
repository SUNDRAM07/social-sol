import os
import logging
from typing import Dict, Any, Optional
from twitter_adapter import TwitterAdapter

logger = logging.getLogger(__name__)

class TwitterService:
    """Main Twitter service for social media agent"""
    
    def __init__(self):
        self.adapter = TwitterAdapter()
    
    def is_configured(self) -> bool:
        """Check if Twitter service is properly configured"""
        return self.adapter.is_configured()
    
    def test_connection(self) -> Dict[str, Any]:
        """Test Twitter API connection"""
        return self.adapter.test_connection()
    
    def post_to_twitter(self, content: str, image_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Post content to Twitter
        
        Args:
            content: Tweet text content
            image_path: Optional path to image file
        
        Returns:
            Result dictionary with success status and tweet details
        """
        if not self.is_configured():
            return {
                "success": False,
                "error": "Twitter service not configured. Please check your Twitter API credentials."
            }
        
        try:
            # Validate content length
            if len(content) > 280:
                return {
                    "success": False,
                    "error": f"Tweet too long: {len(content)}/280 characters"
                }
            
            # Handle media upload if image provided
            media_ids = None
            if image_path:
                logger.info(f"Processing image path: {image_path}")
                if os.path.exists(image_path):
                    logger.info(f"Image file exists, uploading media: {image_path}")
                    media_id = self.adapter.upload_media(image_path)
                    if media_id:
                        media_ids = [media_id]
                        logger.info(f"✅ Media uploaded successfully: {media_id}")
                    else:
                        logger.error(f"❌ Failed to upload media: {image_path}")
                else:
                    logger.error(f"❌ Image file not found: {image_path}")
                    logger.error(f"Current working directory: {os.getcwd()}")
                    logger.error(f"File exists check: {os.path.exists(image_path)}")
            else:
                logger.info("No image path provided for this tweet")
            
            # Create the tweet
            logger.info(f"Posting tweet: {content[:50]}...")
            result = self.adapter.create_tweet(
                text=content,
                media_ids=media_ids
            )
            
            if "data" in result and "id" in result["data"]:
                tweet_id = result["data"]["id"]
                tweet_url = f"https://twitter.com/i/status/{tweet_id}"
                
                logger.info(f"✅ Tweet posted successfully: {tweet_id}")
                
                return {
                    "success": True,
                    "post_id": tweet_id,
                    "url": tweet_url,
                    "platform": "twitter",
                    "content": content,
                    "media_uploaded": bool(media_ids)
                }
            else:
                error_msg = result.get("error", "Unknown error")
                logger.error(f"❌ Failed to post tweet: {error_msg}")
                
                return {
                    "success": False,
                    "error": error_msg,
                    "platform": "twitter"
                }
                
        except Exception as e:
            error_msg = f"Twitter posting error: {str(e)}"
            logger.error(error_msg)
            
            return {
                "success": False,
                "error": error_msg,
                "platform": "twitter"
            }
    
    def delete_tweet(self, tweet_id: str) -> Dict[str, Any]:
        """
        Delete a tweet from Twitter
        
        Args:
            tweet_id: ID of the tweet to delete
        
        Returns:
            Result dictionary with success status
        """
        if not self.is_configured():
            return {
                "success": False,
                "error": "Twitter service not configured"
            }
        
        try:
            result = self.adapter.delete_tweet(tweet_id)
            
            if "error" in result:
                return {
                    "success": False,
                    "error": result["error"]
                }
            
            logger.info(f"✅ Tweet deleted successfully: {tweet_id}")
            return {
                "success": True,
                "tweet_id": tweet_id,
                "message": "Tweet deleted successfully"
            }
            
        except Exception as e:
            error_msg = f"Twitter deletion error: {str(e)}"
            logger.error(error_msg)
            
            return {
                "success": False,
                "error": error_msg
            }
    
    def get_user_info(self, username: str) -> Dict[str, Any]:
        """
        Get Twitter user information
        
        Args:
            username: Twitter username (without @)
        
        Returns:
            User information dictionary
        """
        if not self.is_configured():
            return {
                "success": False,
                "error": "Twitter service not configured"
            }
        
        try:
            result = self.adapter.get_user_by_username(username)
            
            if "error" in result:
                return {
                    "success": False,
                    "error": result["error"]
                }
            
            return {
                "success": True,
                "user": result.get("data", {})
            }
            
        except Exception as e:
            error_msg = f"Twitter user lookup error: {str(e)}"
            logger.error(error_msg)
            
            return {
                "success": False,
                "error": error_msg
            }
    
    def get_user_tweets(self, username: str, max_results: int = 10) -> Dict[str, Any]:
        """
        Get tweets from a user's timeline
        
        Args:
            username: Twitter username (without @)
            max_results: Maximum number of tweets to return
        
        Returns:
            Tweets data dictionary
        """
        if not self.is_configured():
            return {
                "success": False,
                "error": "Twitter service not configured"
            }
        
        try:
            result = self.adapter.get_user_tweets(
                username=username,
                max_results=max_results
            )
            
            if "error" in result:
                return {
                    "success": False,
                    "error": result["error"]
                }
            
            return {
                "success": True,
                "tweets": result.get("data", []),
                "meta": result.get("meta", {})
            }
            
        except Exception as e:
            error_msg = f"Twitter tweets lookup error: {str(e)}"
            logger.error(error_msg)
            
            return {
                "success": False,
                "error": error_msg
            }
