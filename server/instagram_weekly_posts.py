"""
Instagram Weekly Posts Service
Provides functionality to fetch Instagram posts from the current week
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List

from instagram_analytics_service import instagram_analytics_service

logger = logging.getLogger(__name__)

class InstagramWeeklyPostsService:
    """Service for fetching Instagram posts from the current week"""
    
    def __init__(self):
        """Initialize Instagram weekly posts service"""
        self.analytics_service = instagram_analytics_service
    
    def get_weekly_posts(self) -> Dict[str, Any]:
        """
        Get Instagram posts from the current week
        
        Returns:
            Dictionary with weekly posts data
        """
        if not self.analytics_service.is_configured():
            return {"success": False, "error": "Instagram service not configured"}
        
        try:
            # Get all media posts (limit to 50 for performance)
            media_result = self.analytics_service.get_media_list(limit=50)
            
            if not media_result.get("success", False):
                return {"success": False, "error": media_result.get("error", "Failed to fetch media")}
            
            # Calculate the start of the current week (Monday)
            today = datetime.now()
            start_of_week = today - timedelta(days=today.weekday())
            start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)
            
            # Filter posts from the current week
            weekly_posts = []
            all_media = media_result.get("media", [])
            
            for post in all_media:
                post_timestamp = post.get("timestamp")
                if post_timestamp:
                    try:
                        post_date = datetime.fromisoformat(post_timestamp.replace('Z', '+00:00'))
                        if post_date >= start_of_week:
                            weekly_posts.append(post)
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Error parsing timestamp {post_timestamp}: {e}")
            
            return {
                "success": True,
                "posts": weekly_posts,
                "total_posts": len(weekly_posts),
                "week_start": start_of_week.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting weekly posts: {e}")
            return {"success": False, "error": str(e)}

# Global instance
instagram_weekly_posts_service = InstagramWeeklyPostsService()