"""
Background scheduler service for automated social media posting
Monitors scheduled posts and publishes them to Facebook at the scheduled time
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from database_service import db_service
from facebook_poster import post_to_facebook_for_user
from image_path_utils import convert_image_path_for_facebook, convert_image_path_for_twitter, convert_image_path_for_reddit

logger = logging.getLogger(__name__)

class SchedulerService:
    """Background service for scheduling and publishing posts"""
    
    def __init__(self):
        self.is_running = False
        self.poll_interval = 60  # Check every 60 seconds
        self.task = None
    
    async def start(self):
        """Start the background scheduler"""
        if self.is_running:
            logger.info("Scheduler is already running")
            return
        
        self.is_running = True
        logger.info("Starting scheduler service...")
        
        self.task = asyncio.create_task(self._run_scheduler_loop())
    
    async def stop(self):
        """Stop the background scheduler"""
        if not self.is_running:
            return
        
        logger.info("Stopping scheduler service...")
        self.is_running = False
        
        if self.task and not self.task.done():
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
    
    async def _run_scheduler_loop(self):
        """Main scheduler loop"""
        logger.info("Scheduler loop started")
        
        while self.is_running:
            try:
                await self._process_scheduled_posts()
                await asyncio.sleep(self.poll_interval)
            except asyncio.CancelledError:
                logger.info("Scheduler loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                await asyncio.sleep(self.poll_interval)  # Continue after error
    
    async def _process_scheduled_posts(self):
        """Check for and process posts that are due for publishing"""
        try:
            # Get posts scheduled for now or earlier
            scheduled_posts = await db_service.get_posts_due_for_publishing()
            
            if not scheduled_posts:
                return
            
            logger.info(f"Found {len(scheduled_posts)} posts due for publishing")
            
            for post in scheduled_posts:
                await self._publish_post(post)
                
        except Exception as e:
            logger.error(f"Error processing scheduled posts: {e}")
    
    async def _check_user_can_auto_post(self, user_id: str) -> dict:
        """Check if user has Premium/Agency tier for auto-posting"""
        try:
            from subscription_service import subscription_service
            from uuid import UUID
            
            status = await subscription_service.get_subscription_status(UUID(user_id))
            
            return {
                "allowed": status.can_auto_post,
                "tier": status.tier,
                "reason": None if status.can_auto_post else "Auto-posting requires Premium or Agency subscription"
            }
        except Exception as e:
            logger.error(f"Error checking auto-post permission: {e}")
            # Default to not allowed if check fails
            return {
                "allowed": False,
                "tier": "unknown",
                "reason": f"Error checking subscription: {str(e)}"
            }
    
    async def _publish_post(self, post: Dict[str, Any]):
        """Publish a scheduled post to multiple platforms"""
        post_id = post.get("id")
        user_id = post.get("user_id")
        platforms = post.get("platforms", [])
        caption = post.get("caption", "")
        image_path = post.get("image_path")
        subreddit = post.get("subreddit", "test")
        
        logger.info(f"Publishing scheduled post {post_id} to platforms: {platforms}")
        logger.info(f"Caption: {caption[:100]}...")
        logger.info(f"Image path: {image_path}")
        
        if not platforms:
            logger.warning(f"No platforms specified for post {post_id}")
            await self._mark_post_failed(post_id, "No platforms specified")
            return
        
        # CHECK AUTO-POST PERMISSION (Premium/Agency only)
        if user_id:
            permission = await self._check_user_can_auto_post(str(user_id))
            if not permission["allowed"]:
                logger.warning(f"User {user_id} cannot auto-post: {permission['reason']} (tier: {permission['tier']})")
                await self._mark_post_failed(
                    post_id, 
                    f"Auto-posting requires Premium subscription. Current tier: {permission['tier']}"
                )
                return
            logger.info(f"User {user_id} has auto-post permission (tier: {permission['tier']})")
        
        # Track results for each platform
        platform_results = {}
        all_successful = True
        
        try:
            for platform in platforms:
                platform = platform.lower()
                logger.info(f"Publishing to {platform}...")
                
                try:
                    if platform == "facebook":
                        # Post to Facebook using the new adapter
                        logger.info(f"Attempting to post to Facebook for post {post_id}")
                        
                        if not user_id:
                            error_msg = "Missing user_id for scheduled Facebook post"
                            platform_results[platform] = {
                                "success": False,
                                "error": error_msg
                            }
                            all_successful = False
                            logger.error(f"❌ Failed to publish post {post_id} to {platform}: {error_msg}")
                            continue
                        
                        # Convert image path to local file path for Facebook
                        local_image_path = convert_image_path_for_facebook(image_path)
                        
                        # Use the Facebook poster to publish
                        result = await post_to_facebook_for_user(
                            user_id=user_id,
                            caption=caption,
                            image_path=local_image_path
                        )
                        
                        if result["success"]:
                            platform_results[platform] = {
                                "success": True,
                                "post_id": result.get('post_id'),
                                "url": result.get('url')
                            }
                            logger.info(f"✅ Successfully published post {post_id} to {platform}!")
                            logger.info(f"{platform.title()} Post ID: {result.get('post_id')}")
                            logger.info(f"Post URL: {result.get('url')}")
                        else:
                            error_msg = result.get("error", "Unknown error")
                            platform_results[platform] = {
                                "success": False,
                                "error": error_msg
                            }
                            all_successful = False
                            logger.error(f"❌ Failed to publish post {post_id} to {platform}: {error_msg}")
                    
                    elif platform == "reddit":
                        # Post to Reddit using the Reddit service
                        logger.info(f"Attempting to post to Reddit for post {post_id}")
                        
                        if not user_id:
                            error_msg = "Missing user_id for scheduled Reddit post"
                            platform_results[platform] = {
                                "success": False,
                                "error": error_msg
                            }
                            all_successful = False
                            logger.error(f"❌ Failed to publish post {post_id} to {platform}: {error_msg}")
                            continue
                        
                        # Get user's Reddit account from database
                        account = await db_service.get_social_media_account(user_id, platform="reddit")
                        
                        if not account:
                            error_msg = "No Reddit account found for user. Please connect your Reddit account."
                            platform_results[platform] = {
                                "success": False,
                                "error": error_msg
                            }
                            all_successful = False
                            logger.error(f"❌ Failed to publish post {post_id} to {platform}: {error_msg}")
                            continue
                        
                        from reddit_service import RedditService
                        reddit_service = RedditService(
                            access_token=account.get('access_token'),
                            refresh_token=account.get('refresh_token')
                        )
                        
                        if not reddit_service.is_configured():
                            error_msg = "Reddit service not configured"
                            platform_results[platform] = {
                                "success": False,
                                "error": error_msg
                            }
                            all_successful = False
                            logger.error(f"❌ Failed to publish post {post_id} to {platform}: {error_msg}")
                            continue
                        
                        # Post to Reddit (title will be first part of caption)
                        title = caption[:100] if caption else "Social Media Post"
                        
                        # Convert image path to local file path for Reddit
                        local_image_path = convert_image_path_for_reddit(image_path)
                        
                        result = reddit_service.post_to_reddit(
                            title=title,
                            content=caption,
                            subreddit=subreddit
                        )
                        
                        if result.get("success", False):
                            platform_results[platform] = {
                                "success": True,
                                "post_id": result.get('post_id'),
                                "url": result.get('url')
                            }
                            logger.info(f"✅ Successfully published post {post_id} to Reddit!")
                            logger.info(f"Reddit Post ID: {result.get('post_id')}")
                            logger.info(f"Post URL: {result.get('url')}")
                        else:
                            error_msg = result.get("message") or result.get("error", "Unknown error")
                            platform_results[platform] = {
                                "success": False,
                                "error": error_msg
                            }
                            all_successful = False
                            logger.error(f"❌ Failed to publish post {post_id} to Reddit: {error_msg}")
                    
                    elif platform == "twitter":
                        # Post to Twitter using the Twitter service
                        logger.info(f"Attempting to post to Twitter for post {post_id}")
                        
                        from twitter_service import TwitterService
                        twitter_service = TwitterService()
                        
                        if not twitter_service.is_configured():
                            error_msg = "Twitter service not configured"
                            platform_results[platform] = {
                                "success": False,
                                "error": error_msg
                            }
                            all_successful = False
                            logger.error(f"❌ Failed to publish post {post_id} to {platform}: {error_msg}")
                            continue
                        
                        # Post to Twitter - convert image path to local file path
                        local_image_path = convert_image_path_for_twitter(image_path)
                        
                        result = twitter_service.post_to_twitter(
                            content=caption,
                            image_path=local_image_path
                        )
                        
                        if result.get("success", False):
                            platform_results[platform] = {
                                "success": True,
                                "post_id": result.get('post_id'),
                                "url": result.get('url')
                            }
                            logger.info(f"✅ Successfully published post {post_id} to Twitter!")
                            logger.info(f"Twitter Post ID: {result.get('post_id')}")
                            logger.info(f"Post URL: {result.get('url')}")
                        else:
                            error_msg = result.get("error", "Unknown error")
                            platform_results[platform] = {
                                "success": False,
                                "error": error_msg
                            }
                            all_successful = False
                            logger.error(f"❌ Failed to publish post {post_id} to Twitter: {error_msg}")
                    
                    elif platform == "linkedin":
                        # Post to LinkedIn using the LinkedIn service
                        logger.info(f"Attempting to post to LinkedIn for post {post_id}")
                        
                        from linkedin_service import LinkedInService
                        linkedin_service = LinkedInService()
                        
                        if not linkedin_service.is_configured():
                            error_msg = "LinkedIn service not configured"
                            platform_results[platform] = {
                                "success": False,
                                "error": error_msg
                            }
                            all_successful = False
                            logger.error(f"❌ LinkedIn service not configured for post {post_id}")
                            continue
                        
                        # Post to LinkedIn with text and image support
                        result = linkedin_service.post_to_linkedin(text=caption, image_url=image_path)
                        
                        if result.get("success", False):
                            platform_results[platform] = {
                                "success": True,
                                "post_id": result.get('post_id'),
                                "url": result.get('url')
                            }
                            logger.info(f"✅ Successfully published post {post_id} to LinkedIn!")
                            logger.info(f"LinkedIn Post ID: {result.get('post_id')}")
                            logger.info(f"Post URL: {result.get('url')}")
                        else:
                            error_msg = result.get("message", "Unknown error")
                            platform_results[platform] = {
                                "success": False,
                                "error": error_msg
                            }
                            all_successful = False
                            logger.error(f"❌ Failed to publish post {post_id} to LinkedIn: {error_msg}")
                    
                    elif platform == "instagram":
                        # Post to Instagram using the Instagram service (STATIC CREDENTIALS FROM DB)
                        logger.info(f"Attempting to post to Instagram for post {post_id}")
                        
                        if not user_id:
                            error_msg = "Missing user_id for scheduled Instagram post"
                            platform_results[platform] = {
                                "success": False,
                                "error": error_msg
                            }
                            all_successful = False
                            logger.error(f"❌ Failed to publish post {post_id} to {platform}: {error_msg}")
                            continue
                        
                        from instagram_service import get_instagram_service
                        instagram_service = get_instagram_service(user_id)
                        
                        if not await instagram_service.is_configured():
                            error_msg = "Instagram service not configured for this user"
                            platform_results[platform] = {
                                "success": False,
                                "error": error_msg
                            }
                            all_successful = False
                            logger.error(f"❌ Failed to publish post {post_id} to {platform}: {error_msg}")
                            continue
                        
                        # Post to Instagram - convert image path to local file path
                        local_image_path = convert_image_path_for_facebook(image_path)  # Use same conversion as Facebook
                        
                        result = await instagram_service.post_to_instagram(
                            caption=caption,
                            image_path=local_image_path
                        )
                        
                        if result.get("success", False):
                            platform_results[platform] = {
                                "success": True,
                                "post_id": result.get('post_id'),
                                "url": result.get('url')
                            }
                            logger.info(f"✅ Successfully published post {post_id} to Instagram!")
                            logger.info(f"Instagram Post ID: {result.get('post_id')}")
                            logger.info(f"Post URL: {result.get('url')}")
                        else:
                            error_msg = result.get("error", "Unknown error")
                            platform_results[platform] = {
                                "success": False,
                                "error": error_msg
                            }
                            all_successful = False
                            logger.error(f"❌ Failed to publish post {post_id} to Instagram: {error_msg}")
                    
                    else:
                        logger.warning(f"Unsupported platform: {platform}")
                        platform_results[platform] = {
                            "success": False,
                            "error": f"Unsupported platform: {platform}"
                        }
                        all_successful = False
                
                except Exception as platform_error:
                    logger.error(f"Exception publishing to {platform}: {platform_error}")
                    platform_results[platform] = {
                        "success": False,
                        "error": str(platform_error)
                    }
                    all_successful = False
            
            # Mark post status based on results
            if all_successful:
                await self._mark_post_published_multi_platform(post_id, platform_results)
            else:
                # Check if at least one platform succeeded
                successful_platforms = [p for p, r in platform_results.items() if r.get("success")]
                if successful_platforms:
                    await self._mark_post_partially_published(post_id, platform_results)
                else:
                    await self._mark_post_failed(post_id, "All platforms failed")
                
        except Exception as e:
            logger.error(f"Exception publishing post {post_id}: {e}")
            await self._mark_post_failed(post_id, str(e))
    
    def _get_image_url(self, image_path: Optional[str]) -> Optional[str]:
        """Convert image path to accessible URL"""
        if not image_path:
            return None
        
        # If it's already a full URL, return as-is
        if image_path.startswith(("http://", "https://")):
            return image_path
        
        # Get public domain from environment or use request host
        public_domain = os.getenv("PUBLIC_DOMAIN")
        if not public_domain or public_domain == "localhost:8000":
            # In production, we should have PUBLIC_DOMAIN set
            # For now, return relative path which will work with current domain
            if image_path.startswith("/public/"):
                return image_path
            elif image_path.startswith("public/"):
                return f"/{image_path}"
            return image_path
        
        # Use configured public domain
        if image_path.startswith("/public/"):
            return f"http://{public_domain}{image_path}"
        elif image_path.startswith("public/"):
            return f"http://{public_domain}/{image_path}"
        
        return image_path
    
    async def _update_calendar_events_for_post(self, post_id: str, status: str):
        """Update calendar events for a post to reflect the new status"""
        try:
            from database import db_manager
            
            # Update calendar events for this post
            calendar_update_query = """
                UPDATE calendar_events 
                SET status = :status, 
                    updated_at = NOW()
                WHERE post_id = :post_id
            """
            
            await db_manager.execute_query(calendar_update_query, {
                "post_id": str(post_id),
                "status": status
            })
            
            logger.info(f"Updated calendar events for post {post_id} to status: {status}")
            
        except Exception as e:
            logger.error(f"Error updating calendar events for post {post_id}: {e}")

    async def _mark_post_published_multi_platform(self, post_id: str, platform_results: Dict[str, Any]):
        """Mark a post as successfully published to all platforms"""
        try:
            from database import db_manager
            import json
            
            published_at = datetime.now(timezone.utc)
            
            # Update post status to published
            update_query = """
                UPDATE posts 
                SET status = 'published', 
                    posted_at = :posted_at,
                    updated_at = NOW()
                WHERE id = :post_id
            """
            
            values = {
                "post_id": post_id,
                "posted_at": published_at
            }
            
            await db_manager.execute_query(update_query, values)
            
            # Store multi-platform post details in engagement_metrics
            engagement_data = {
                "platforms": list(platform_results.keys()),
                "platform_results": platform_results,
                "published_at": published_at.isoformat(),
                "status": "published",
                "all_platforms_successful": True
            }
            
            # Escape single quotes in JSON for SQL
            json_str = json.dumps(engagement_data).replace("'", "''")
            
            metrics_query = f"""
                UPDATE posts 
                SET engagement_metrics = '{json_str}'::jsonb
                WHERE id = :post_id
            """
            
            await db_manager.execute_query(metrics_query, {"post_id": post_id})
            
            successful_platforms = list(platform_results.keys())
            
            # Update calendar events for this post
            await self._update_calendar_events_for_post(post_id, "published")
            
            logger.info(f"Marked post {post_id} as published to all platforms: {successful_platforms}")
            
        except Exception as e:
            logger.error(f"Error marking post {post_id} as published: {e}")
    
    async def _mark_post_partially_published(self, post_id: str, platform_results: Dict[str, Any]):
        """Mark a post as partially published (some platforms succeeded, some failed)"""
        try:
            from database import db_manager
            import json
            
            published_at = datetime.now(timezone.utc)
            
            # Update post status to partially_published
            update_query = """
                UPDATE posts 
                SET status = 'partially_published', 
                    posted_at = :posted_at,
                    updated_at = NOW()
                WHERE id = :post_id
            """
            
            values = {
                "post_id": post_id,
                "posted_at": published_at
            }
            
            await db_manager.execute_query(update_query, values)
            
            # Store partial platform results in engagement_metrics
            successful_platforms = [p for p, r in platform_results.items() if r.get("success")]
            failed_platforms = [p for p, r in platform_results.items() if not r.get("success")]
            
            engagement_data = {
                "platforms": list(platform_results.keys()),
                "platform_results": platform_results,
                "successful_platforms": successful_platforms,
                "failed_platforms": failed_platforms,
                "published_at": published_at.isoformat(),
                "status": "partially_published",
                "all_platforms_successful": False
            }
            
            # Escape single quotes in JSON for SQL
            json_str = json.dumps(engagement_data).replace("'", "''")
            
            metrics_query = f"""
                UPDATE posts 
                SET engagement_metrics = '{json_str}'::jsonb
                WHERE id = :post_id
            """
            
            await db_manager.execute_query(metrics_query, {"post_id": post_id})
            
            # Update calendar events for this post
            await self._update_calendar_events_for_post(post_id, "partially_published")
            
            logger.info(f"Marked post {post_id} as partially published - Success: {successful_platforms}, Failed: {failed_platforms}")
            
        except Exception as e:
            logger.error(f"Error marking post {post_id} as partially published: {e}")
    
    async def _mark_post_failed(self, post_id: str, error_message: str):
        """Mark a post as failed to publish"""
        try:
            from database import db_manager
            import json
            
            # Simpler query without explicit casting
            update_query = """
                UPDATE posts 
                SET status = 'failed', 
                    updated_at = NOW()
                WHERE id = :post_id
            """
            
            values = {
                "post_id": post_id
            }
            
            await db_manager.execute_query(update_query, values)
            
            # Update engagement_metrics in a separate query to avoid parameter binding issues
            error_data = {
                "error": error_message,
                "failed_at": datetime.now(timezone.utc).isoformat(),
                "retry_count": 1  # Could be enhanced with retry logic
            }
            
            # Escape single quotes in JSON for SQL
            json_str = json.dumps(error_data).replace("'", "''")
            
            metrics_query = f"""
                UPDATE posts 
                SET engagement_metrics = '{json_str}'::jsonb
                WHERE id = :post_id
            """
            
            await db_manager.execute_query(metrics_query, {"post_id": post_id})
            
            # Update calendar events for this post
            await self._update_calendar_events_for_post(post_id, "failed")
            
            logger.info(f"Marked post {post_id} as failed: {error_message}")
            
        except Exception as e:
            logger.error(f"Error marking post {post_id} as failed: {e}")
    
    async def schedule_post(self, post_id: str, scheduled_time: datetime, platform: str):
        """Schedule a specific post for publishing"""
        try:
            from database import db_manager
            
            update_query = """
                UPDATE posts 
                SET scheduled_at = :scheduled_at,
                    status = 'scheduled',
                    platform = :platform,
                    updated_at = NOW()
                WHERE id = :post_id
            """
            
            values = {
                "post_id": post_id,
                "scheduled_at": scheduled_time,
                "platform": platform
            }
            
            await db_manager.execute_query(update_query, values)
            logger.info(f"Scheduled post {post_id} for {scheduled_time} on {platform}")
            
        except Exception as e:
            logger.error(f"Error scheduling post {post_id}: {e}")
            raise
    
    async def cancel_scheduled_post(self, post_id: str):
        """Cancel a scheduled post"""
        try:
            from database import db_manager
            
            update_query = """
                UPDATE posts 
                SET scheduled_at = NULL,
                    status = 'draft',
                    updated_at = NOW()
                WHERE id = :post_id
            """
            
            values = {"post_id": post_id}
            await db_manager.execute_query(update_query, values)
            logger.info(f"Cancelled scheduled post {post_id}")
            
        except Exception as e:
            logger.error(f"Error cancelling scheduled post {post_id}: {e}")
            raise
    
    async def get_scheduler_status(self) -> Dict[str, Any]:
        """Get current scheduler status"""
        try:
            scheduled_count = await db_service.count_scheduled_posts()
            recent_posts = await db_service.get_recent_published_posts(limit=5)
            
            return {
                "is_running": self.is_running,
                "poll_interval": self.poll_interval,
                "scheduled_posts_count": scheduled_count,
                "recent_published": recent_posts,
                "last_check": datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            logger.error(f"Error getting scheduler status: {e}")
            return {
                "is_running": self.is_running,
                "error": str(e)
            }


# Global scheduler instance
scheduler_service = SchedulerService()


async def start_scheduler():
    """Start the global scheduler service"""
    await scheduler_service.start()


async def stop_scheduler():
    """Stop the global scheduler service"""
    await scheduler_service.stop()
