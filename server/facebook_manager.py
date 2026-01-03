"""
Comprehensive Facebook Graph API Implementation
Based on Facebook Graph API Complete Guide
Handles posting content, reading posts, and analytics for Facebook Pages
"""

import os
import logging
import requests
import json
import time
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


class FacebookManager:
    """Comprehensive Facebook Graph API implementation for social media management"""
    
    def __init__(self):
        """Initialize Facebook manager - credentials should come from database, not .env"""
        # Don't load access tokens from .env - only client ID/secret should be in .env
        self.access_token = None
        self.page_id = None
        self.base_url = "https://graph.facebook.com/v21.0"
        self.last_request_time = None
        self.min_interval = 1  # Rate limiting
        self.metadata = {}
        self.current_user_id = None
        self.credential_source = "unset"  # Will be set when configured from database

    def configure_from_credentials(
        self,
        *,
        access_token: Optional[str],
        page_id: Optional[str],
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Configure manager with explicit credentials (typically fetched from database)."""
        if not access_token or not page_id:
            raise ValueError("Both access_token and page_id are required to configure FacebookManager")

        self.access_token = access_token
        self.page_id = page_id
        self.metadata = metadata or {}
        self.current_user_id = user_id
        self.credential_source = "database" if user_id else "env"

        # Don't write to .env - credentials should only be in database
        # Only client ID/secret should be in .env

        facebook_user_id = None
        if isinstance(self.metadata, dict):
            facebook_user_id = self.metadata.get("facebook_user_id")

        if facebook_user_id:
            os.environ["FACEBOOK_USER_ID"] = facebook_user_id

    async def configure_for_user(self, user_id: Optional[str], account_id: Optional[str] = None) -> bool:
        """Load credentials for the specified user from the social_media_accounts table."""
        if not user_id:
            logger.warning("configure_for_user called without user_id")
            return False

        try:
            from database_service import db_service

            account = await db_service.get_social_media_account(
                user_id,
                platform="facebook",
                account_id=account_id
            )
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
            self.configure_from_credentials(
                access_token=account.get("access_token"),
                page_id=account.get("account_id"),
                user_id=user_id,
                metadata=metadata
            )
            return True
        except Exception as exc:
            logger.error(f"Failed to configure FacebookManager for user {user_id}: {exc}")
            return False
    
    def _rate_limit(self):
        """Implement rate limiting for API calls"""
        if self.last_request_time:
            elapsed = datetime.now() - self.last_request_time
            if elapsed < timedelta(seconds=self.min_interval):
                time.sleep(self.min_interval - elapsed.total_seconds())
        self.last_request_time = datetime.now()
    
    def _make_request(self, method: str, endpoint: str, data: Dict = None, params: Dict = None) -> Dict[str, Any]:
        """Make API request with error handling and rate limiting"""
        self._rate_limit()
        
        url = f"{self.base_url}/{endpoint}"
        
        if params is None:
            params = {}
        params['access_token'] = self.access_token
        
        try:
            if method.upper() == 'GET':
                response = requests.get(url, params=params, timeout=30)
            elif method.upper() == 'POST':
                response = requests.post(url, data=data, params=params, timeout=30)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            result = response.json()
            
            if 'error' in result:
                error_msg = result['error'].get('message', 'Unknown error')
                error_code = result['error'].get('code', 0)
                
                if error_code == 190:
                    logger.error("Facebook access token expired or invalid")
                elif error_code == 200:
                    logger.error("Insufficient permissions for this operation")
                elif error_code == 4:
                    logger.error("Facebook API rate limit exceeded")
                
                return {"error": error_msg, "success": False}
            
            return result
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error: {e}")
            return {"error": f"Network error: {str(e)}", "success": False}
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return {"error": f"Unexpected error: {str(e)}", "success": False}
    
    def is_configured(self) -> bool:
        """Check if Facebook credentials are properly configured"""
        return bool(self.access_token and self.page_id)
    
    def verify_credentials(self) -> Dict[str, Any]:
        """Verify that the Facebook credentials are valid"""
        if not self.is_configured():
            return {
                "success": False,
                "configured": False,
                "error": "Facebook credentials not configured"
            }
        
        result = self._make_request('GET', f"{self.page_id}", {"fields": "id,name"})
        
        if "error" in result:
            return {
                "success": False,
                "configured": True,
                "error": result["error"]
            }
        
        return {
            "success": True,
            "configured": True,
            "page_id": result.get('id'),
            "page_name": result.get('name')
        }
    
    # POSTING METHODS
    
    def post_text(self, message: str, scheduled_time: Optional[datetime] = None) -> Dict[str, Any]:
        """Post text content to Facebook Page"""
        if not self.is_configured():
            return {"success": False, "error": "Facebook credentials not configured"}
        
        data = {'message': message}
        
        if scheduled_time:
            data['scheduled_publish_time'] = int(scheduled_time.timestamp())
            data['published'] = 'false'
        
        result = self._make_request('POST', f"{self.page_id}/feed", data=data)
        
        if "error" in result:
            return {"success": False, "error": result["error"]}
        
        return {
            "success": True,
            "post_id": result.get('id'),
            "platform": "facebook",
            "posted_at": datetime.now(timezone.utc).isoformat(),
            "url": f"https://www.facebook.com/{result.get('id')}" if result.get('id') else None
        }
    
    def post_photo(self, image_url: str, caption: str = "") -> Dict[str, Any]:
        """Post single photo to Facebook Page"""
        if not self.is_configured():
            return {"success": False, "error": "Facebook credentials not configured"}
        
        data = {
            'url': image_url,
            'message': caption
        }
        
        result = self._make_request('POST', f"{self.page_id}/photos", data=data)
        
        if "error" in result:
            return {"success": False, "error": result["error"]}
        
        return {
            "success": True,
            "post_id": result.get('id'),
            "platform": "facebook",
            "posted_at": datetime.now(timezone.utc).isoformat(),
            "url": f"https://www.facebook.com/{result.get('id')}" if result.get('id') else None
        }
    
    def post_photo_from_file(self, image_path: str, caption: str = "") -> Dict[str, Any]:
        """Post photo from local file to Facebook Page"""
        if not self.is_configured():
            return {"success": False, "error": "Facebook credentials not configured"}
        
        # Construct the full image path
        if image_path.startswith("/public/"):
            actual_path = image_path[1:]  # Remove leading /
        elif image_path.startswith("public/"):
            actual_path = image_path
        else:
            actual_path = f"public/{image_path}"
        
        # Check if image file exists
        if not os.path.exists(actual_path):
            return {"success": False, "error": f"Image file not found: {actual_path}"}
        
        try:
            url = f"{self.base_url}/{self.page_id}/photos"
            params = {
                "access_token": self.access_token,
                "message": caption
            }
            
            with open(actual_path, 'rb') as image_file:
                files = {
                    'source': ('image.jpg', image_file, 'image/jpeg')
                }
                
                self._rate_limit()
                response = requests.post(url, params=params, files=files, timeout=30)
                result = response.json()
                
                if 'error' in result:
                    return {"success": False, "error": result['error']['message']}
                
                return {
                    "success": True,
                    "post_id": result.get('id'),
                    "platform": "facebook",
                    "posted_at": datetime.now(timezone.utc).isoformat(),
                    "url": f"https://www.facebook.com/{result.get('id')}" if result.get('id') else None
                }
                
        except Exception as e:
            return {"success": False, "error": f"File upload error: {str(e)}"}
    
    def post_video(self, video_url: str, description: str = "") -> Dict[str, Any]:
        """Post video to Facebook Page"""
        if not self.is_configured():
            return {"success": False, "error": "Facebook credentials not configured"}
        
        data = {
            'file_url': video_url,
            'description': description
        }
        
        result = self._make_request('POST', f"{self.page_id}/videos", data=data)
        
        if "error" in result:
            return {"success": False, "error": result["error"]}
        
        return {
            "success": True,
            "post_id": result.get('id'),
            "platform": "facebook",
            "posted_at": datetime.now(timezone.utc).isoformat(),
            "url": f"https://www.facebook.com/{result.get('id')}" if result.get('id') else None
        }
    
    def post_link(self, link: str, message: str = "", custom_image: str = "") -> Dict[str, Any]:
        """Post link with custom thumbnail to Facebook Page"""
        if not self.is_configured():
            return {"success": False, "error": "Facebook credentials not configured"}
        
        data = {
            'link': link,
            'message': message
        }
        
        if custom_image:
            data['picture'] = custom_image
        
        result = self._make_request('POST', f"{self.page_id}/feed", data=data)
        
        if "error" in result:
            return {"success": False, "error": result["error"]}
        
        return {
            "success": True,
            "post_id": result.get('id'),
            "platform": "facebook",
            "posted_at": datetime.now(timezone.utc).isoformat(),
            "url": f"https://www.facebook.com/{result.get('id')}" if result.get('id') else None
        }
    
    # READING METHODS
    
    def get_posts(self, limit: int = 25, include_insights: bool = True) -> Dict[str, Any]:
        """Get page posts with optional insights"""
        if not self.is_configured():
            return {"success": False, "error": "Facebook credentials not configured"}
        
        fields = 'id,message,created_time,story,attachments,likes.summary(true),comments.summary(true),shares'
        
        if include_insights:
            fields += ',insights.metric(post_impressions,post_engaged_users)'
        
        params = {
            'fields': fields,
            'limit': limit
        }
        
        result = self._make_request('GET', f"{self.page_id}/feed", params=params)
        
        if "error" in result:
            error_msg = result["error"]
            if isinstance(error_msg, dict):
                error_msg = error_msg.get("message", str(error_msg))
            logger.warning(f"Failed to fetch posts from /feed: {error_msg}")
            return {"success": False, "error": str(error_msg)}
        
        if not isinstance(result, dict):
            logger.error(f"Unexpected response type from Facebook API: {type(result)}")
            return {"success": False, "error": "Unexpected response format from Facebook API"}
        
        return {
            "success": True,
            "posts": result.get('data', []),
            "paging": result.get('paging', {})
        }
    
    def get_published_posts(self, limit: int = 25) -> Dict[str, Any]:
        """Get only posts published by the page itself"""
        if not self.is_configured():
            return {"success": False, "error": "Facebook credentials not configured"}
        
        # Try simpler fields first (without insights) for better compatibility
        params = {
            'fields': 'id,message,created_time,story,attachments,likes.summary(true),comments.summary(true),shares',
            'limit': limit
        }
        
        result = self._make_request('GET', f"{self.page_id}/published_posts", params=params)
        
        if "error" in result:
            error_msg = result["error"]
            if isinstance(error_msg, dict):
                error_msg = error_msg.get("message", str(error_msg))
            logger.warning(f"Failed to fetch posts from /published_posts: {error_msg}")
            return {"success": False, "error": str(error_msg)}
        
        if not isinstance(result, dict):
            logger.error(f"Unexpected response type from Facebook API: {type(result)}")
            return {"success": False, "error": "Unexpected response format from Facebook API"}
        
        return {
            "success": True,
            "posts": result.get('data', []),
            "paging": result.get('paging', {})
        }
    
    def get_all_posts(self, max_posts: int = 1000) -> List[Dict[str, Any]]:
        """Get all posts with pagination handling"""
        if not self.is_configured():
            return []
        
        all_posts = []
        url = f"{self.base_url}/{self.page_id}/feed"
        params = {
            'fields': 'id,message,created_time,insights.metric(post_impressions)',
            'limit': 100,
            'access_token': self.access_token
        }
        
        while url and len(all_posts) < max_posts:
            self._rate_limit()
            response = requests.get(url, params=params)
            data = response.json()
            
            if 'error' in data:
                logger.error(f"Error fetching posts: {data['error']}")
                break
            
            all_posts.extend(data.get('data', []))
            
            # Check for next page
            url = data.get('paging', {}).get('next')
            params = {}  # Clear params for subsequent requests
        
        return all_posts[:max_posts]
    
    # ANALYTICS METHODS
    
    def get_page_insights(self, start_date: str, end_date: str, metrics: List[str] = None) -> Dict[str, Any]:
        """Get page analytics for specific date range"""
        if not self.is_configured():
            return {"success": False, "error": "Facebook credentials not configured"}
        
        if metrics is None:
            metrics = ['page_engaged_users', 'page_impressions', 'page_fans']
        
        params = {
            'metric': ','.join(metrics),
            'since': start_date,
            'until': end_date,
            'period': 'day'
        }
        
        result = self._make_request('GET', f"{self.page_id}/insights", params=params)
        
        if "error" in result:
            return {"success": False, "error": result["error"]}
        
        return {
            "success": True,
            "insights": result.get('data', [])
        }
    
    def get_post_insights(self, post_id: str) -> Dict[str, Any]:
        """Get detailed post analytics"""
        if not self.is_configured():
            return {"success": False, "error": "Facebook credentials not configured"}
        
        params = {
            'metric': 'post_impressions,post_engaged_users,post_clicks,post_reactions_like_total'
        }
        
        result = self._make_request('GET', f"{post_id}/insights", params=params)
        
        if "error" in result:
            return {"success": False, "error": result["error"]}
        
        return {
            "success": True,
            "insights": result.get('data', [])
        }
    
    def get_page_followers(self) -> Dict[str, Any]:
        """Get total page followers"""
        if not self.is_configured():
            return {"success": False, "error": "Facebook credentials not configured"}
        
        params = {'metric': 'page_fans'}
        result = self._make_request('GET', f"{self.page_id}/insights", params=params)
        
        if "error" in result:
            return {"success": False, "error": result["error"]}
        
        data = result.get('data', [])
        if not data:
            return {"success": True, "followers": 0}
        
        values = data[0].get('values', [])
        if not values:
            return {"success": True, "followers": 0}
        
        return {
            "success": True,
            "followers": values[-1].get('value', 0)
        }
    
    def get_audience_demographics(self) -> Dict[str, Any]:
        """Get audience demographics by country, age, and gender"""
        if not self.is_configured():
            return {"success": False, "error": "Facebook credentials not configured"}
        
        # Get country demographics
        country_result = self._make_request('GET', f"{self.page_id}/insights", {
            'metric': 'page_fans_country',
            'period': 'lifetime'
        })
        
        # Get age/gender demographics
        age_gender_result = self._make_request('GET', f"{self.page_id}/insights", {
            'metric': 'page_fans_gender_age',
            'period': 'lifetime'
        })
        
        if "error" in country_result or "error" in age_gender_result:
            return {
                "success": False,
                "error": {
                    "country": country_result.get("error"),
                    "age_gender": age_gender_result.get("error")
                }
            }
        
        # Extract country data
        by_country = {}
        if "data" in country_result and country_result["data"]:
            values = country_result["data"][0].get("values", [])
            if values:
                by_country = values[-1].get("value", {})
        
        # Extract age/gender data
        by_age_gender = {}
        if "data" in age_gender_result and age_gender_result["data"]:
            values = age_gender_result["data"][0].get("values", [])
            if values:
                by_age_gender = values[-1].get("value", {})
        
        return {
            "success": True,
            "by_country": by_country,
            "by_age_gender": by_age_gender
        }
    
    def get_comprehensive_analytics(self) -> Dict[str, Any]:
        """Get comprehensive analytics data for dashboard"""
        if not self.is_configured():
            return {"success": False, "error": "Facebook credentials not configured"}
        
        try:
            # Get basic metrics
            followers_data = self.get_page_followers()
            demographics = self.get_audience_demographics()
            
            # Try to get posts with multiple fallback strategies
            posts_data = None
            posts = []
            
            # Strategy 1: Try with insights
            posts_data = self.get_posts(20, include_insights=True)
            if posts_data.get("success"):
                posts = posts_data.get("posts", [])
            else:
                # Strategy 2: Try without insights
                logger.warning(f"Posts with insights failed: {posts_data.get('error')}, trying without insights")
                posts_data = self.get_posts(20, include_insights=False)
                if posts_data.get("success"):
                    posts = posts_data.get("posts", [])
                else:
                    # Strategy 3: Try published_posts endpoint
                    logger.warning(f"Posts feed failed: {posts_data.get('error')}, trying published_posts")
                    posts_data = self.get_published_posts(20)
                    if posts_data.get("success"):
                        posts = posts_data.get("posts", [])
                    else:
                        logger.warning(f"All post fetching strategies failed: {posts_data.get('error')}")
                        # Continue with empty posts - we'll still return other metrics
            
            # Calculate totals from posts
            total_impressions = 0
            total_engaged = 0
            
            for post in posts:
                # Try to get insights from post
                insights = post.get('insights', {})
                if isinstance(insights, dict):
                    insights_data = insights.get('data', [])
                elif isinstance(insights, list):
                    insights_data = insights
                else:
                    insights_data = []
                
                for insight in insights_data:
                    if insight.get('name') == 'post_impressions':
                        values = insight.get('values', [])
                        if values:
                            total_impressions += values[-1].get('value', 0)
                    elif insight.get('name') == 'post_engaged_users':
                        values = insight.get('values', [])
                        if values:
                            total_engaged += values[-1].get('value', 0)
                
                # Also calculate from engagement metrics if insights not available
                if total_impressions == 0 and total_engaged == 0:
                    likes = post.get('likes', {})
                    if isinstance(likes, dict):
                        likes_count = likes.get('summary', {}).get('total_count', 0)
                    else:
                        likes_count = 0
                    
                    comments = post.get('comments', {})
                    if isinstance(comments, dict):
                        comments_count = comments.get('summary', {}).get('total_count', 0)
                    else:
                        comments_count = 0
                    
                    shares = post.get('shares', {})
                    if isinstance(shares, dict):
                        shares_count = shares.get('count', 0)
                    else:
                        shares_count = shares if isinstance(shares, (int, float)) else 0
                    
                    # Use engagement as a proxy for impressions if not available
                    total_engaged += likes_count + comments_count + shares_count
            
            # Get best performing post
            best_post = None
            best_engagement = 0
            
            for post in posts:
                likes = post.get('likes', {})
                if isinstance(likes, dict):
                    likes_count = likes.get('summary', {}).get('total_count', 0)
                else:
                    likes_count = 0
                
                comments = post.get('comments', {})
                if isinstance(comments, dict):
                    comments_count = comments.get('summary', {}).get('total_count', 0)
                else:
                    comments_count = 0
                
                shares = post.get('shares', {})
                if isinstance(shares, dict):
                    shares_count = shares.get('count', 0)
                else:
                    shares_count = shares if isinstance(shares, (int, float)) else 0
                
                total_engagement = likes_count + comments_count + shares_count
                
                if total_engagement > best_engagement:
                    best_engagement = total_engagement
                    best_post = post
            
            # Build page info from verification if available
            page_info = {}
            try:
                verification = self.verify_credentials()
                if verification.get("success"):
                    page_info = {
                        "page_id": verification.get("page_id"),
                        "page_name": verification.get("page_name")
                    }
            except:
                pass
            
            return {
                "success": True,
                "totals": {
                    "followers": followers_data.get("followers", 0),
                    "impressions": total_impressions if total_impressions > 0 else (total_engaged if total_engaged > 0 else 0),
                    "engaged_users": total_engaged,
                    "best_post": best_post.get("id") if best_post else None
                },
                "demographics": demographics if isinstance(demographics, dict) and "by_country" in demographics else {"by_country": {}, "by_age_gender": {}},
                "posts": posts,
                "best_post": best_post if best_post else {},
                "page": page_info,
                "metrics_available": len(posts) > 0,
                "note": "Some metrics may be limited due to API permissions" if not posts_data or not posts_data.get("success") else None
            }
            
        except Exception as e:
            logger.error(f"Error getting comprehensive analytics: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                "success": False,
                "error": str(e),
                "totals": {
                    "followers": 0,
                    "impressions": 0,
                    "engaged_users": 0,
                    "best_post": None
                },
                "demographics": {"by_country": {}, "by_age_gender": {}},
                "posts": [],
                "best_post": {},
                "metrics_available": False
            }


# Global instance
facebook_manager = FacebookManager()


# Convenience functions for backward compatibility
def post_to_facebook(caption: str, image_path: Optional[str] = None) -> Dict[str, Any]:
    """Post content to Facebook - convenience function"""
    if image_path:
        return facebook_manager.post_photo_from_file(image_path, caption)
    else:
        return facebook_manager.post_text(caption)


def verify_facebook_setup() -> Dict[str, Any]:
    """Verify Facebook configuration - convenience function"""
    return facebook_manager.verify_credentials()


if __name__ == "__main__":
    # Test the manager
    print("Facebook Manager Test")
    print("-" * 40)
    
    # Check configuration
    if facebook_manager.is_configured():
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
