"""
Instagram Service for Social Media Agent
Integrates Instagram posting functionality into the main social media agent
"""

import os
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from PIL import Image
from instagram_adapter import InstagramAdapter
from image_path_utils import convert_url_to_local_path
from image_upload_service import image_upload_service

logger = logging.getLogger(__name__)

class InstagramService:
    """Service class for Instagram operations in the social media agent - STATIC CREDENTIALS FROM DB"""
    
    def __init__(self, user_id: Optional[str] = None, access_token: Optional[str] = None, account_id: Optional[str] = None):
        """
        Initialize Instagram service
        
        Args:
            user_id: User ID to fetch credentials from database (preferred method)
            access_token: Direct access token (fallback)
            account_id: Direct account ID (fallback)
            
        NOTE: Static flow - credentials are loaded from database per user.
        """
        self.user_id = user_id
        self._access_token = access_token
        self._account_id = account_id
        self.adapter = None
        
        # If direct credentials provided, initialize adapter immediately
        if access_token and account_id:
            self.adapter = InstagramAdapter(access_token=access_token, instagram_account_id=account_id)
    
    async def _ensure_adapter(self):
        """Ensure adapter is initialized with credentials from database if user_id provided"""
        if self.adapter is not None:
            return
        
        if not self.user_id:
            # Try environment variables as last resort
            self.adapter = InstagramAdapter()
            return
        
        # Fetch credentials from database
        try:
            from database_service import db_service
            accounts = await db_service.get_social_media_accounts(
                self.user_id, platform="instagram", active_only=True
            )
            
            if accounts and len(accounts) > 0:
                account = accounts[0]
                access_token = account.get("access_token")
                account_id = account.get("account_id") or account.get("instagram_account_id")
                
                if access_token and account_id:
                    self.adapter = InstagramAdapter(
                        access_token=access_token,
                        instagram_account_id=str(account_id)
                    )
                    logger.info(f"✅ Instagram adapter initialized for user {self.user_id} with account {account_id}")
                    return
            
            # No credentials found
            logger.warning(f"⚠️ No Instagram credentials found for user {self.user_id}")
            self.adapter = InstagramAdapter()  # Empty adapter
            
        except Exception as e:
            logger.error(f"❌ Error loading Instagram credentials from database: {e}")
            self.adapter = InstagramAdapter()  # Empty adapter
    
    async def is_configured(self) -> bool:
        """Check if Instagram service is properly configured"""
        await self._ensure_adapter()
        return self.adapter.is_configured() if self.adapter else False
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test Instagram API connection"""
        await self._ensure_adapter()
        if not self.adapter:
            return {"error": "Instagram adapter not initialized"}
        return self.adapter.test_connection()
    
    async def post_to_instagram(self, caption: str, image_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Post content to Instagram
        
        Args:
            caption: Post caption text
            image_path: Path to image file to upload with post
            
        Returns:
            Dictionary with posting result
        """
        await self._ensure_adapter()
        if not await self.is_configured():
            return {
                "success": False,
                "error": "Instagram service not configured. Please check your Instagram API credentials."
            }
        
        try:
            # Validate inputs
            if not caption or not caption.strip():
                return {"success": False, "error": "Caption cannot be empty"}
            
            if len(caption) > 2200:  # Instagram caption limit
                return {"success": False, "error": f"Caption too long ({len(caption)}/2200 characters)"}
            
            # Handle image upload if image provided
            image_url = None
            if image_path:
                logger.info(f"Processing image path: {image_path}")
                
                # Prepare image for Instagram (convert format if needed)
                processed_image_path = self._prepare_image_for_instagram(image_path)
                if not processed_image_path:
                    return {
                        "success": False,
                        "error": f"Could not process image: {image_path}"
                    }
                
                # Get public URL for the image (upload to hosting service if needed)
                image_url = image_upload_service.get_public_image_url(processed_image_path)
                
                if not image_url:
                    return {
                        "success": False,
                        "error": f"Could not get public URL for image: {processed_image_path}. Instagram requires publicly accessible URLs."
                    }
                
                logger.info(f"✅ Image URL prepared: {image_url}")
            else:
                return {
                    "success": False,
                    "error": "Instagram requires an image for posting"
                }
            
            # Create the post
            logger.info(f"Posting to Instagram: {caption[:50]}...")
            result = self.adapter.post_with_image(
                image_url=image_url,
                caption=caption
            )
            
            if result.get("success"):
                logger.info(f"✅ Instagram post created successfully: {result.get('post_id')}")
                
                return {
                    "success": True,
                    "post_id": result.get("post_id"),
                    "url": result.get("url"),
                    "platform": "instagram",
                    "content": caption,
                    "image_uploaded": bool(image_url)
                }
            else:
                error_msg = result.get("error", "Unknown error")
                logger.error(f"❌ Failed to post to Instagram: {error_msg}")
                
                return {
                    "success": False,
                    "error": error_msg,
                    "platform": "instagram"
                }
                
        except Exception as e:
            error_msg = f"Instagram posting error: {str(e)}"
            logger.error(error_msg)
            
            return {
                "success": False,
                "error": error_msg,
                "platform": "instagram"
            }
    
    def _prepare_image_for_instagram(self, image_path: str) -> Optional[str]:
        """
        Prepare image for Instagram posting by converting format and validating
        
        Args:
            image_path: Local path to image file
            
        Returns:
            Path to processed image file, or None if processing fails
        """
        try:
            # Convert to local path if it's a URL
            local_path = convert_url_to_local_path(image_path)
            if not local_path:
                local_path = image_path
            
            # Check if file exists
            if not os.path.exists(local_path):
                logger.error(f"Image file not found: {local_path}")
                return None
            
            # Open and validate image
            with Image.open(local_path) as img:
                # Check image format and convert if needed
                if img.format not in ['JPEG', 'PNG']:
                    logger.warning(f"Unsupported image format: {img.format}")
                    return None
                
                # Convert PNG to JPEG for better Instagram compatibility
                if img.format == 'PNG':
                    # Create JPEG version
                    jpeg_path = local_path.replace('.png', '_instagram.jpg')
                    
                    # Convert RGBA/LA/P to RGB for JPEG
                    if img.mode in ('RGBA', 'LA', 'P'):
                        # Create white background for transparency
                        background = Image.new('RGB', img.size, (255, 255, 255))
                        if img.mode == 'P':
                            img = img.convert('RGBA')
                        background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                        img = background
                    elif img.mode != 'RGB':
                        img = img.convert('RGB')
                    
                    # Save as JPEG with high quality
                    img.save(jpeg_path, 'JPEG', quality=95, optimize=True)
                    logger.info(f"Converted PNG to JPEG: {jpeg_path}")
                    return jpeg_path
                
                # For JPEG, check if we need to optimize
                elif img.format == 'JPEG':
                    # Check file size (Instagram limit is 8MB)
                    file_size = os.path.getsize(local_path)
                    if file_size > 8 * 1024 * 1024:  # 8MB
                        logger.warning(f"Image too large: {file_size} bytes, optimizing...")
                        
                        # Create optimized version
                        optimized_path = local_path.replace('.jpg', '_instagram.jpg')
                        img.save(optimized_path, 'JPEG', quality=85, optimize=True)
                        logger.info(f"Optimized JPEG: {optimized_path}")
                        return optimized_path
                    
                    return local_path
                
                return local_path
                
        except Exception as e:
            logger.error(f"Error preparing image for Instagram: {e}")
            return None
    
    def _get_image_url(self, image_path: str) -> Optional[str]:
        """
        Convert image path to accessible URL for Instagram
        
        Args:
            image_path: Local path to image file
            
        Returns:
            Accessible URL for the image, or None if conversion fails
        """
        if not image_path:
            return None
        
        # If it's already a full URL, return as-is
        if image_path.startswith(("http://", "https://")):
            return image_path
        
        # For Instagram, we need a publicly accessible URL
        # Check if we have a public domain configured
        public_domain = os.getenv("PUBLIC_DOMAIN", "localhost:8000")
        
        # If using localhost, Instagram cannot access the image
        if public_domain == "localhost:8000":
            logger.error("Instagram Graph API cannot access localhost URLs!")
            logger.error("Instagram's servers need to fetch images from publicly accessible URLs")
            logger.error("Solutions:")
            logger.error("1. Use ngrok: ngrok http 8000 (then set PUBLIC_DOMAIN to your ngrok URL)")
            logger.error("2. Deploy to a public server")
            logger.error("3. Upload images to cloud storage (S3, Cloudinary, etc.)")
            logger.error("4. Use a public image hosting service")
            
            # For testing only - use a public test image
            logger.warning("Using public test image for Instagram posting (testing only)")
            return "https://picsum.photos/1080/1080.jpg"
        
        # Convert local path to public URL
        if image_path.startswith("/public/"):
            return f"http://{public_domain}{image_path}"
        elif image_path.startswith("public/"):
            return f"http://{public_domain}/{image_path}"
        else:
            # Assume it's a relative path in public folder
            return f"http://{public_domain}/public/{image_path}"
    
    async def get_media_info(self, media_id: str) -> Dict[str, Any]:
        """
        Get information about a specific Instagram post
        
        Args:
            media_id: Instagram media ID
            
        Returns:
            Dictionary with media information
        """
        await self._ensure_adapter()
        if not await self.is_configured():
            return {
                "success": False,
                "error": "Instagram service not configured"
            }
        
        try:
            result = self.adapter.get_media_info(media_id)
            
            if "error" in result:
                return {
                    "success": False,
                    "error": f"Instagram API error: {result['error']}"
                }
            
            return {
                "success": True,
                "media_info": result
            }
            
        except Exception as e:
            logger.error(f"Error getting Instagram media info: {e}")
            return {
                "success": False,
                "error": f"Failed to get media info: {str(e)}"
            }
    
    async def get_recent_posts(self, limit: int = 10) -> Dict[str, Any]:
        """
        Get recent Instagram posts
        
        Args:
            limit: Maximum number of posts to retrieve
            
        Returns:
            Dictionary with posts data
        """
        await self._ensure_adapter()
        if not await self.is_configured():
            return {
                "success": False,
                "error": "Instagram service not configured"
            }
        
        try:
            result = self.adapter.get_recent_posts(limit)
            
            if "error" in result:
                return {
                    "success": False,
                    "error": f"Instagram API error: {result['error']}"
                }
            
            return {
                "success": True,
                "posts": result.get("data", []),
                "count": len(result.get("data", []))
            }
            
        except Exception as e:
            logger.error(f"Error getting recent Instagram posts: {e}")
            return {
                "success": False,
                "error": f"Failed to get recent posts: {str(e)}"
            }
    
    async def get_service_status(self) -> Dict[str, Any]:
        """Get Instagram service status"""
        await self._ensure_adapter()
        return {
            "configured": await self.is_configured(),
            "adapter_available": self.adapter is not None,
            "user_id": self.user_id,
            "has_credentials": self.adapter.is_configured() if self.adapter else False
        }


# Helper function to create Instagram service instance for a user
def get_instagram_service(user_id: str) -> InstagramService:
    """
    Get Instagram service instance for a specific user
    
    Args:
        user_id: User ID to fetch Instagram credentials from database
        
    Returns:
        InstagramService instance configured for the user
    """
    return InstagramService(user_id=user_id)


# Global Instagram service instance (legacy, no user context)
instagram_service = InstagramService()
