"""
Fresh Facebook Posting Adapter for Scheduled Posts
Handles automatic posting of scheduled content to Facebook
"""

import os
import logging
import requests
import json
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from dotenv import load_dotenv
from image_path_utils import convert_url_to_local_path

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


class FacebookPoster:
    """Clean implementation for posting scheduled content to Facebook"""
    
    def __init__(self):
        """Initialize with Facebook credentials from environment"""
        self.access_token = os.getenv("FACEBOOK_ACCESS_TOKEN")
        self.page_id = os.getenv("FACEBOOK_PAGE_ID")
        self.graph_api_base = "https://graph.facebook.com/v21.0"
        self.metadata: Dict[str, Any] = {}
        self.current_user_id: Optional[str] = None
        self.credential_source: str = "env" if self.access_token and self.page_id else "unset"
        
        if not self.access_token:
            logger.warning("FACEBOOK_ACCESS_TOKEN not found in environment")
        if not self.page_id:
            logger.warning("FACEBOOK_PAGE_ID not found in environment")
    
    def configure_from_credentials(
        self,
        *,
        access_token: str,
        page_id: str,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Configure poster with explicit credentials (typically fetched from database)."""
        if not access_token or not page_id:
            raise ValueError("Both access_token and page_id are required to configure FacebookPoster")

        self.access_token = access_token
        self.page_id = page_id
        self.metadata = metadata or {}
        self.current_user_id = user_id
        self.credential_source = "database" if user_id else "env"

        # Maintain backwards compatibility for components reading env vars
        os.environ["FACEBOOK_ACCESS_TOKEN"] = access_token
        os.environ["FACEBOOK_PAGE_ID"] = page_id

        facebook_user_id = None
        if isinstance(self.metadata, dict):
            facebook_user_id = self.metadata.get("facebook_user_id")
        if facebook_user_id:
            os.environ["FACEBOOK_USER_ID"] = facebook_user_id

    async def configure_for_user(self, user_id: Optional[str]) -> bool:
        """Load credentials for the specified user from the social_media_accounts table."""
        if not user_id:
            logger.warning("configure_for_user called without user_id")
            return False

        try:
            from database_service import db_service

            account = await db_service.get_social_media_account(user_id, platform="facebook")
            if not account:
                logger.info(f"No Facebook account found in database for user {user_id}")
                return False

            metadata = account.get("metadata")
            if isinstance(metadata, str):
                try:
                    metadata = json.loads(metadata)
                except json.JSONDecodeError:
                    metadata = {}
            elif not isinstance(metadata, dict):
                metadata = {}

            page_id = account.get("account_id") or metadata.get("page_id")
            access_token = account.get("access_token")

            if not access_token or not page_id:
                logger.warning(f"Facebook account record for user {user_id} missing access token or page_id")
                return False

            self.configure_from_credentials(
                access_token=access_token,
                page_id=page_id,
                user_id=user_id,
                metadata=metadata,
            )
            return True
        except Exception as exc:
            logger.error(f"Failed to configure FacebookPoster for user {user_id}: {exc}")
            return False

    def is_configured(self) -> bool:
        """Check if Facebook credentials are properly configured"""
        return bool(self.access_token and self.page_id)
    
    def post_with_image(self, caption: str, image_path: str) -> Dict[str, Any]:
        """
        Post to Facebook with an image
        
        Args:
            caption: Text caption for the post
            image_path: Local path to the image file (e.g., /public/image.png)
            
        Returns:
            Dictionary with success status and post details
        """
        if not self.is_configured():
            return {
                "success": False,
                "error": "Facebook credentials not configured"
            }
        
        try:
            # Convert image path to local file path using centralized utility
            actual_path = convert_url_to_local_path(image_path)
            
            # If conversion failed or returned None, use fallback
            if not actual_path:
                actual_path = f"public/{image_path}"
            
            # Check if image file exists
            if not os.path.exists(actual_path):
                logger.error(f"Image file not found: {actual_path}")
                return {
                    "success": False,
                    "error": f"Image file not found: {actual_path}"
                }
            
            # Prepare the API endpoint for photo upload
            url = f"{self.graph_api_base}/{self.page_id}/photos"
            
            # Prepare the request
            params = {
                "access_token": self.access_token,
                "message": caption
            }
            
            # Open and send the image file
            with open(actual_path, 'rb') as image_file:
                files = {
                    'source': ('image.jpg', image_file, 'image/jpeg')
                }
                
                logger.info(f"Posting to Facebook: {url}")
                logger.info(f"Caption: {caption[:100]}...")
                logger.info(f"Image: {actual_path}")
                
                # Make the API request
                response = requests.post(url, params=params, files=files, timeout=30)
                
                # Check response
                if response.status_code == 200:
                    result = response.json()
                    post_id = result.get('id', result.get('post_id'))
                    
                    logger.info(f"Successfully posted to Facebook! Post ID: {post_id}")
                    
                    return {
                        "success": True,
                        "post_id": post_id,
                        "platform": "facebook",
                        "posted_at": datetime.now(timezone.utc).isoformat(),
                        "url": f"https://www.facebook.com/{post_id}" if post_id else None
                    }
                else:
                    error_data = response.json() if response.content else {}
                    error_msg = error_data.get('error', {}).get('message', f'HTTP {response.status_code}')
                    
                    logger.error(f"Facebook API error: {error_msg}")
                    logger.error(f"Full response: {response.text[:500]}")
                    
                    return {
                        "success": False,
                        "error": f"Facebook API error: {error_msg}",
                        "status_code": response.status_code
                    }
                    
        except FileNotFoundError as e:
            logger.error(f"Image file not found: {e}")
            return {
                "success": False,
                "error": f"Image file not found: {str(e)}"
            }
        except requests.RequestException as e:
            logger.error(f"Network error posting to Facebook: {e}")
            return {
                "success": False,
                "error": f"Network error: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Unexpected error posting to Facebook: {e}")
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}"
            }
    
    def post_text_only(self, caption: str) -> Dict[str, Any]:
        """
        Post text-only content to Facebook
        
        Args:
            caption: Text content to post
            
        Returns:
            Dictionary with success status and post details
        """
        if not self.is_configured():
            return {
                "success": False,
                "error": "Facebook credentials not configured"
            }
        
        try:
            # Prepare the API endpoint for feed post
            url = f"{self.graph_api_base}/{self.page_id}/feed"
            
            # Prepare the request
            params = {
                "access_token": self.access_token,
                "message": caption
            }
            
            logger.info(f"Posting text to Facebook: {caption[:100]}...")
            
            # Make the API request
            response = requests.post(url, params=params, timeout=30)
            
            # Check response
            if response.status_code == 200:
                result = response.json()
                post_id = result.get('id')
                
                logger.info(f"Successfully posted text to Facebook! Post ID: {post_id}")
                
                return {
                    "success": True,
                    "post_id": post_id,
                    "platform": "facebook",
                    "posted_at": datetime.now(timezone.utc).isoformat(),
                    "url": f"https://www.facebook.com/{post_id}" if post_id else None
                }
            else:
                error_data = response.json() if response.content else {}
                error_msg = error_data.get('error', {}).get('message', f'HTTP {response.status_code}')
                
                logger.error(f"Facebook API error: {error_msg}")
                
                return {
                    "success": False,
                    "error": f"Facebook API error: {error_msg}",
                    "status_code": response.status_code
                }
                
        except requests.RequestException as e:
            logger.error(f"Network error posting to Facebook: {e}")
            return {
                "success": False,
                "error": f"Network error: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Unexpected error posting to Facebook: {e}")
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}"
            }
    
    def verify_credentials(self) -> Dict[str, Any]:
        """
        Verify that the Facebook credentials are valid
        
        Returns:
            Dictionary with verification status
        """
        if not self.is_configured():
            return {
                "success": False,
                "configured": False,
                "error": "Facebook credentials not configured"
            }
        
        try:
            # Try to get page information to verify credentials
            url = f"{self.graph_api_base}/{self.page_id}"
            params = {
                "access_token": self.access_token,
                "fields": "id,name"
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                page_data = response.json()
                logger.info(f"Facebook credentials verified. Page: {page_data.get('name')}")
                
                return {
                    "success": True,
                    "configured": True,
                    "page_id": page_data.get('id'),
                    "page_name": page_data.get('name')
                }
            else:
                error_data = response.json() if response.content else {}
                error_msg = error_data.get('error', {}).get('message', 'Invalid credentials')
                
                return {
                    "success": False,
                    "configured": True,
                    "error": f"Invalid credentials: {error_msg}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "configured": True,
                "error": f"Verification failed: {str(e)}"
            }


# Global instance
facebook_poster = FacebookPoster()


# Convenience functions for direct usage
def post_to_facebook(caption: str, image_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Post content to Facebook
    
    Args:
        caption: Text content/caption
        image_path: Optional path to image file
        
    Returns:
        Dictionary with posting result
    """
    if image_path:
        return facebook_poster.post_with_image(caption, image_path)
    else:
        return facebook_poster.post_text_only(caption)


async def post_to_facebook_for_user(
    user_id: Optional[str],
    caption: str,
    image_path: Optional[str] = None
) -> Dict[str, Any]:
    """Configure poster for the user and publish."""
    configured = await facebook_poster.configure_for_user(user_id)
    if not configured:
        return {
            "success": False,
            "error": "No Facebook account connected. Please connect your Facebook page in Settings."
        }

    if image_path:
        return facebook_poster.post_with_image(caption, image_path)
    return facebook_poster.post_text_only(caption)


def verify_facebook_setup() -> Dict[str, Any]:
    """Verify Facebook configuration"""
    return facebook_poster.verify_credentials()


if __name__ == "__main__":
    # Test the adapter
    print("Facebook Poster Adapter")
    print("-" * 40)
    
    # Check configuration
    if facebook_poster.is_configured():
        print("✅ Facebook credentials found in environment")
        
        # Verify credentials
        verification = verify_facebook_setup()
        if verification['success']:
            print(f"✅ Credentials verified for page: {verification.get('page_name')}")
        else:
            print(f"❌ Credential verification failed: {verification.get('error')}")
    else:
        print("❌ Facebook credentials not configured")
        print("Please set FACEBOOK_ACCESS_TOKEN and FACEBOOK_PAGE_ID in .env file")
