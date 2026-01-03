"""
Facebook service stub - Facebook integration has been removed
This file provides stub implementations to maintain API compatibility
"""

import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class FacebookService:
    """Stub class for Facebook API operations - integration disabled"""
    
    def __init__(self):
        self.access_token = None
        self.page_id = None
        self.instagram_id = None
        self.graph_api_url = None
        logger.info("Facebook service initialized as stub - integration disabled")
    
    def is_configured(self) -> bool:
        """Always returns False as Facebook is disabled"""
        return False
    
    def get_drive_direct_url(self, url: str) -> str:
        """Stub - returns URL unchanged"""
        return url
    
    def download_image(self, image_url: str) -> Optional[bytes]:
        """Stub - returns None"""
        logger.debug("Facebook download_image stub called")
        return None
    
    def optimize_image_for_facebook(self, image_bytes: bytes) -> bytes:
        """Stub - returns bytes unchanged"""
        return image_bytes
    
    def post_to_facebook(self, message: str, image_url: Optional[str] = None) -> Dict[str, Any]:
        """Stub - Facebook posting disabled"""
        logger.debug("Facebook post_to_facebook stub called")
        return {"error": "Facebook integration has been disabled", "success": False}
    
    def post_to_instagram(self, message: str, image_url: str) -> Dict[str, Any]:
        """Stub - Instagram posting disabled"""
        logger.debug("Facebook post_to_instagram stub called")
        return {"error": "Instagram integration has been disabled", "success": False}
    
    def post_to_platform(self, platform: str, message: str, image_url: Optional[str] = None) -> Dict[str, Any]:
        """Stub - all platform posting disabled"""
        logger.debug(f"Facebook post_to_platform stub called for platform: {platform}")
        return {"error": "Facebook/Instagram integration has been disabled", "success": False}
    
    def get_page_info(self) -> Dict[str, Any]:
        """Stub - returns error"""
        logger.debug("Facebook get_page_info stub called")
        return {"error": "Facebook integration has been disabled", "success": False}
    
    def get_post_insights(self, post_id: str) -> Dict[str, Any]:
        """Stub - returns error"""
        logger.debug(f"Facebook get_post_insights stub called for post_id: {post_id}")
        return {"error": "Facebook integration has been disabled", "success": False}


# Global service instance
facebook_service = FacebookService()
