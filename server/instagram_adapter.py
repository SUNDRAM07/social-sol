"""
Instagram Adapter for Social Media Agent
Handles Instagram posting using Facebook Graph API
"""

import os
import logging
import requests
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class InstagramAdapter:
    """Instagram API adapter using Facebook Graph API - STATIC CREDENTIALS FROM DB"""
    
    def __init__(self, access_token: Optional[str] = None, instagram_account_id: Optional[str] = None):
        """
        Initialize Instagram adapter with credentials
        
        Args:
            access_token: Instagram access token (from DB or manual entry)
            instagram_account_id: Instagram Business Account ID (from DB or manual entry)
            
        NOTE: Static flow - credentials are now stored in database per user.
        Fallback to environment variables for backward compatibility only.
        """
        self.access_token = access_token or os.getenv("INSTAGRAM_ACCESS_TOKEN")
        self.instagram_account_id = instagram_account_id or os.getenv("INSTAGRAM_ACCOUNT_ID")
        self.graph_api_base = "https://graph.facebook.com/v21.0"
        
        if not self.access_token:
            logger.debug("INSTAGRAM_ACCESS_TOKEN not provided (will be loaded per-user from database)")
        if not self.instagram_account_id:
            logger.debug("INSTAGRAM_ACCOUNT_ID not provided (will be loaded per-user from database)")
    
    def is_configured(self) -> bool:
        """Check if Instagram credentials are properly configured"""
        return bool(self.access_token and self.instagram_account_id)
    
    def test_connection(self) -> Dict[str, Any]:
        """Test Instagram API connection"""
        if not self.is_configured():
            return {"error": "Instagram credentials not configured"}
        
        try:
            # Test connection by getting account info
            url = f"{self.graph_api_base}/{self.instagram_account_id}"
            params = {
                "fields": "id,username,account_type,media_count",
                "access_token": self.access_token
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                account_data = response.json()
                logger.info(f"Instagram connection successful. Account: {account_data.get('username')}")
                
                return {
                    "success": True,
                    "account_id": account_data.get('id'),
                    "username": account_data.get('username'),
                    "account_type": account_data.get('account_type'),
                    "media_count": account_data.get('media_count')
                }
            else:
                error_data = response.json() if response.content else {}
                error_msg = error_data.get('error', {}).get('message', f'HTTP {response.status_code}')
                
                return {
                    "success": False,
                    "error": f"Instagram API error: {error_msg}"
                }
                
        except Exception as e:
            logger.error(f"Instagram connection test failed: {e}")
            return {"error": f"Connection test failed: {str(e)}"}
    
    def create_media_container(self, image_url: str, caption: str = "") -> Dict[str, Any]:
        """
        Create a media container for Instagram post
        
        Args:
            image_url: URL of the image to post
            caption: Caption text for the post
            
        Returns:
            Dictionary with creation result
        """
        if not self.is_configured():
            return {
                "success": False,
                "error": "Instagram credentials not configured"
            }
        
        try:
            url = f"{self.graph_api_base}/{self.instagram_account_id}/media"
            
            data = {
                "image_url": image_url,
                "caption": caption,
                "access_token": self.access_token
            }
            
            logger.info(f"Creating Instagram media container for image: {image_url}")
            logger.info(f"Caption: {caption[:100]}...")
            
            response = requests.post(url, data=data, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                creation_id = result.get('id')
                
                logger.info(f"✅ Instagram media container created successfully: {creation_id}")
                
                return {
                    "success": True,
                    "creation_id": creation_id,
                    "container_data": result
                }
            else:
                error_data = response.json() if response.content else {}
                error_msg = error_data.get('error', {}).get('message', f'HTTP {response.status_code}')
                error_code = error_data.get('error', {}).get('code', 0)
                
                logger.error(f"❌ Instagram media container creation failed: {error_msg}")
                
                # Provide specific guidance for common errors
                if "API access blocked" in error_msg:
                    detailed_error = (
                        "Instagram API access blocked. This usually means your Facebook App is in Development Mode. "
                        "To fix this: 1) Switch your app to Live Mode, 2) Add test users in Development Mode, "
                        "or 3) Submit your app for App Review. See INSTAGRAM_API_ACCESS_BLOCKED_FIX.md for details."
                    )
                elif error_code == 190:
                    detailed_error = "Access token is invalid or expired. Please generate a new access token."
                elif error_code == 100:
                    detailed_error = "Permission denied. Check that your app has the required Instagram permissions."
                elif error_code == 200:
                    detailed_error = "Rate limit exceeded or temporary API issue. Please try again later."
                else:
                    detailed_error = error_msg
                
                return {
                    "success": False,
                    "error": f"Instagram API error: {detailed_error}",
                    "status_code": response.status_code,
                    "error_code": error_code,
                    "raw_error": error_msg
                }
                
        except Exception as e:
            logger.error(f"Exception creating Instagram media container: {e}")
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}"
            }
    
    def publish_media_container(self, creation_id: str) -> Dict[str, Any]:
        """
        Publish a media container to Instagram
        
        Args:
            creation_id: ID returned from create_media_container
            
        Returns:
            Dictionary with publishing result
        """
        if not self.is_configured():
            return {
                "success": False,
                "error": "Instagram credentials not configured"
            }
        
        try:
            url = f"{self.graph_api_base}/{self.instagram_account_id}/media_publish"
            
            data = {
                "creation_id": creation_id,
                "access_token": self.access_token
            }
            
            logger.info(f"Publishing Instagram media container: {creation_id}")
            
            response = requests.post(url, data=data, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                media_id = result.get('id')
                
                logger.info(f"✅ Instagram post published successfully: {media_id}")
                
                return {
                    "success": True,
                    "media_id": media_id,
                    "post_url": f"https://www.instagram.com/p/{media_id}/",
                    "published_at": datetime.now(timezone.utc).isoformat()
                }
            else:
                error_data = response.json() if response.content else {}
                error_msg = error_data.get('error', {}).get('message', f'HTTP {response.status_code}')
                error_code = error_data.get('error', {}).get('code', 0)
                
                logger.error(f"❌ Instagram post publishing failed: {error_msg}")
                
                # Provide specific guidance for common errors
                if "API access blocked" in error_msg:
                    detailed_error = (
                        "Instagram API access blocked. This usually means your Facebook App is in Development Mode. "
                        "To fix this: 1) Switch your app to Live Mode, 2) Add test users in Development Mode, "
                        "or 3) Submit your app for App Review. See INSTAGRAM_API_ACCESS_BLOCKED_FIX.md for details."
                    )
                elif error_code == 190:
                    detailed_error = "Access token is invalid or expired. Please generate a new access token."
                elif error_code == 100:
                    detailed_error = "Permission denied. Check that your app has the required Instagram permissions."
                elif error_code == 200:
                    detailed_error = "Rate limit exceeded or temporary API issue. Please try again later."
                else:
                    detailed_error = error_msg
                
                return {
                    "success": False,
                    "error": f"Instagram API error: {detailed_error}",
                    "status_code": response.status_code,
                    "error_code": error_code,
                    "raw_error": error_msg
                }
                
        except Exception as e:
            logger.error(f"Exception publishing Instagram post: {e}")
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}"
            }
    
    def post_with_image(self, image_url: str, caption: str = "") -> Dict[str, Any]:
        """
        Post to Instagram with an image (two-step process)
        
        Args:
            image_url: URL of the image to post
            caption: Caption text for the post
            
        Returns:
            Dictionary with posting result
        """
        if not self.is_configured():
            return {
                "success": False,
                "error": "Instagram credentials not configured"
            }
        
        try:
            # Step 1: Create media container
            container_result = self.create_media_container(image_url, caption)
            
            if not container_result.get("success"):
                return container_result
            
            creation_id = container_result.get("creation_id")
            
            # Step 2: Publish the container
            publish_result = self.publish_media_container(creation_id)
            
            if publish_result.get("success"):
                return {
                    "success": True,
                    "post_id": publish_result.get("media_id"),
                    "platform": "instagram",
                    "url": publish_result.get("post_url"),
                    "posted_at": publish_result.get("published_at")
                }
            else:
                return publish_result
                
        except Exception as e:
            logger.error(f"Exception posting to Instagram: {e}")
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}"
            }
    
    def get_media_info(self, media_id: str) -> Dict[str, Any]:
        """
        Get information about a specific Instagram media post
        
        Args:
            media_id: Instagram media ID
            
        Returns:
            Dictionary with media information
        """
        if not self.is_configured():
            return {"error": "Instagram credentials not configured"}
        
        try:
            url = f"{self.graph_api_base}/{media_id}"
            params = {
                "fields": "id,caption,media_type,media_url,permalink,like_count,comments_count,timestamp",
                "access_token": self.access_token
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            else:
                error_data = response.json() if response.content else {}
                error_msg = error_data.get('error', {}).get('message', f'HTTP {response.status_code}')
                return {"error": f"Instagram API error: {error_msg}"}
                
        except Exception as e:
            return {"error": f"Request failed: {str(e)}"}
    
    def get_recent_posts(self, limit: int = 25) -> Dict[str, Any]:
        """
        Get recent Instagram posts
        
        Args:
            limit: Maximum number of posts to retrieve
            
        Returns:
            Dictionary with posts data
        """
        if not self.is_configured():
            return {"error": "Instagram credentials not configured"}
        
        try:
            url = f"{self.graph_api_base}/{self.instagram_account_id}/media"
            params = {
                "fields": "id,caption,media_type,media_url,permalink,like_count,comments_count,timestamp",
                "limit": min(limit, 100),
                "access_token": self.access_token
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            else:
                error_data = response.json() if response.content else {}
                error_msg = error_data.get('error', {}).get('message', f'HTTP {response.status_code}')
                return {"error": f"Instagram API error: {error_msg}"}
                
        except Exception as e:
            return {"error": f"Request failed: {str(e)}"}


# Global Instagram adapter instance
instagram_adapter = InstagramAdapter()


# Convenience functions for direct usage
def post_to_instagram(image_url: str, caption: str = "") -> Dict[str, Any]:
    """
    Post content to Instagram
    
    Args:
        image_url: URL of the image to post
        caption: Caption text for the post
        
    Returns:
        Dictionary with posting result
    """
    return instagram_adapter.post_with_image(image_url, caption)


def verify_instagram_setup() -> Dict[str, Any]:
    """Verify Instagram configuration"""
    return instagram_adapter.test_connection()


if __name__ == "__main__":
    # Test the adapter
    print("Instagram Adapter")
    print("-" * 40)
    
    # Check configuration
    if instagram_adapter.is_configured():
        print("✅ Instagram credentials found in environment")
        
        # Verify credentials
        verification = verify_instagram_setup()
        if verification.get('success'):
            print(f"✅ Connection verified for account: {verification.get('username')}")
        else:
            print(f"❌ Connection verification failed: {verification.get('error')}")
    else:
        print("❌ Instagram credentials not configured")
        print("Please set INSTAGRAM_ACCESS_TOKEN and INSTAGRAM_ACCOUNT_ID in .env file")


