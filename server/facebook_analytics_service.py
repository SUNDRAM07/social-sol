import os
import requests
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class FacebookAnalyticsService:
    """Service for fetching Facebook Page and Post analytics using Graph API"""
    
    def __init__(self):
        self.page_id = os.getenv("FACEBOOK_PAGE_ID")
        self.access_token = os.getenv("FACEBOOK_ACCESS_TOKEN")
        self.base_url = "https://graph.facebook.com/v21.0"
        self.metadata: Dict[str, Any] = {}
        
        if not self.page_id or not self.access_token:
            logger.warning("Facebook credentials not properly configured")
    
    def configure_from_credentials(
        self,
        *,
        page_id: str,
        access_token: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Configure analytics service with explicit credentials."""
        if not page_id or not access_token:
            raise ValueError("Both page_id and access_token are required to configure Facebook analytics.")

        self.page_id = page_id
        self.access_token = access_token
        if isinstance(metadata, dict):
            self.metadata = metadata

        # Maintain backwards compatibility for consumers that read from environment
        os.environ["FACEBOOK_PAGE_ID"] = page_id
        os.environ["FACEBOOK_ACCESS_TOKEN"] = access_token
    
    def _fb_get(self, endpoint: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Helper method to make Facebook Graph API requests"""
        if params is None:
            params = {}
        
        params["access_token"] = self.access_token
        url = f"{self.base_url}/{endpoint}"
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError:
            try:
                return {"error": response.json()}
            except ValueError:
                return {"error": response.text}
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}
    
    def get_page_followers(self) -> Dict[str, Any]:
        """Get total page followers"""
        try:
            if not self.page_id or not self.access_token:
                return {"error": "Facebook credentials not configured"}
            
            data = self._fb_get(f"{self.page_id}/insights", {"metric": "page_fans"})
            
            if "error" in data:
                return {"followers": 0, "error": data["error"]}
            
            if "data" not in data or not data["data"]:
                return {"followers": 0}
            
            values = data["data"][0].get("values", [])
            if not values:
                return {"followers": 0}
            
            return {"followers": values[-1].get("value", 0)}
            
        except Exception as e:
            logger.error(f"Error fetching page followers: {e}")
            return {"followers": 0, "error": str(e)}
    
    def get_audience_demographics(self) -> Dict[str, Any]:
        """Get audience demographics by country, age, and gender"""
        try:
            if not self.page_id or not self.access_token:
                return {"error": "Facebook credentials not configured"}
            
            # Get country demographics
            country_data = self._fb_get(
                f"{self.page_id}/insights",
                {"metric": "page_fans_country", "period": "lifetime"}
            )
            
            # Get age/gender demographics
            age_gender_data = self._fb_get(
                f"{self.page_id}/insights",
                {"metric": "page_fans_gender_age", "period": "lifetime"}
            )
            
            if "error" in country_data or "error" in age_gender_data:
                return {
                    "by_country": {},
                    "by_age_gender": {},
                    "error": {
                        "country": country_data.get("error"),
                        "age_gender": age_gender_data.get("error")
                    }
                }
            
            # Extract country data
            by_country = {}
            if "data" in country_data and country_data["data"]:
                values = country_data["data"][0].get("values", [])
                if values:
                    by_country = values[-1].get("value", {})
            
            # Extract age/gender data
            by_age_gender = {}
            if "data" in age_gender_data and age_gender_data["data"]:
                values = age_gender_data["data"][0].get("values", [])
                if values:
                    by_age_gender = values[-1].get("value", {})
            
            return {
                "by_country": by_country,
                "by_age_gender": by_age_gender
            }
            
        except Exception as e:
            logger.error(f"Error fetching audience demographics: {e}")
            return {
                "by_country": {},
                "by_age_gender": {},
                "error": str(e)
            }
    
    def get_recent_posts(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent posts from the page with engagement data"""
        try:
            if not self.page_id or not self.access_token:
                return []
            
            # Get posts with engagement fields - try both likes and reactions
            params = {
                "limit": limit,
                "fields": "id,message,created_time,likes.summary(true),reactions.summary(true),comments.summary(true),shares"
            }
            
            data = self._fb_get(f"{self.page_id}/posts", params)
            
            if "error" in data:
                logger.error(f"Error fetching recent posts: {data['error']}")
                return []
            
            return data.get("data", [])
            
        except Exception as e:
            logger.error(f"Error fetching recent posts: {e}")
            return []
    
    def get_post_insights(self, post_id: str) -> Dict[str, Any]:
        """Get insights for a specific post"""
        try:
            if not self.access_token:
                return {}
            
            metrics = "post_impressions,post_reach,post_engaged_users,post_reactions_by_type_total"
            data = self._fb_get(f"{post_id}/insights", {"metric": metrics})
            
            if "error" in data or "data" not in data:
                return {}
            
            insights = {}
            for item in data.get("data", []):
                values = item.get("values", [])
                if values:
                    insights[item["name"]] = values[-1].get("value", 0)
            
            return insights
            
        except Exception as e:
            logger.error(f"Error fetching post insights for {post_id}: {e}")
            return {}
    
    def analyze_posts(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Analyze posts with only real data from Facebook API endpoints"""
        try:
            posts = self.get_recent_posts(limit)
            analyzed = []
            
            for post in posts:
                post_id = post.get("id")
                if not post_id:
                    continue
                
                # Extract ONLY real engagement data from post fields
                likes_data = post.get("likes", {})
                reactions_data = post.get("reactions", {})
                comments_data = post.get("comments", {})
                shares_data = post.get("shares", {})
                
                # Get counts from summary - real data from Facebook API
                # Use likes.summary.total_count (this is the actual likes count)
                reactions_count = 0
                if likes_data and isinstance(likes_data, dict) and "summary" in likes_data:
                    reactions_count = likes_data["summary"].get("total_count", 0)
                elif reactions_data and isinstance(reactions_data, dict) and "summary" in reactions_data:
                    reactions_count = reactions_data["summary"].get("total_count", 0)
                
                comments_count = 0
                if comments_data and isinstance(comments_data, dict) and "summary" in comments_data:
                    comments_count = comments_data["summary"].get("total_count", 0)
                
                shares_count = 0
                if shares_data:
                    if isinstance(shares_data, dict) and "count" in shares_data:
                        shares_count = shares_data["count"]
                    elif isinstance(shares_data, (int, float)):
                        shares_count = int(shares_data)
                
                # Get real insights data from Facebook Insights API
                insights = self.get_post_insights(post_id)
                real_impressions = insights.get("post_impressions", 0)
                real_reach = insights.get("post_reach", 0)
                real_engaged_users = insights.get("post_engaged_users", 0)
                
                # Build reactions breakdown from actual data
                reactions_breakdown = {}
                if reactions_data and "data" in reactions_data and reactions_data["data"]:
                    for reaction in reactions_data["data"]:
                        reaction_type = reaction.get("type", "unknown").lower()
                        reactions_breakdown[reaction_type] = reactions_breakdown.get(reaction_type, 0) + 1
                
                analyzed.append({
                    "id": post_id,
                    "message": post.get("message", ""),
                    "created_time": post.get("created_time", ""),
                    "reach": real_reach,  # Only real data from Facebook Insights
                    "impressions": real_impressions,  # Only real data from Facebook Insights
                    "engaged_users": real_engaged_users,  # Only real data from Facebook Insights
                    "reactions_count": reactions_count,  # Real data from post reactions
                    "comments_count": comments_count,  # Real data from post comments
                    "shares_count": shares_count,  # Real data from post shares
                    "reactions_breakdown": reactions_breakdown  # Actual reaction types
                })
            
            return analyzed
            
        except Exception as e:
            logger.error(f"Error analyzing posts: {e}")
            return []
    
    def get_best_performing_post(self, limit: int = 10) -> Dict[str, Any]:
        """Get the best performing post by total engagement"""
        try:
            analyzed = self.analyze_posts(limit)
            if not analyzed:
                return {}
            
            # Use total real engagement (reactions + comments + shares)
            return max(analyzed, key=lambda x: x["reactions_count"] + x["comments_count"] + x["shares_count"])
            
        except Exception as e:
            logger.error(f"Error getting best performing post: {e}")
            return {}
    
    def get_worst_performing_post(self, limit: int = 10) -> Dict[str, Any]:
        """Get the worst performing post by total engagement"""
        try:
            analyzed = self.analyze_posts(limit)
            if not analyzed:
                return {}
            
            # Use total real engagement (reactions + comments + shares)
            return min(analyzed, key=lambda x: x["reactions_count"] + x["comments_count"] + x["shares_count"])
            
        except Exception as e:
            logger.error(f"Error getting worst performing post: {e}")
            return {}
    
    def get_available_metrics(self) -> Dict[str, List[str]]:
        """Get list of available metrics"""
        return {
            "available_metrics": [
                "page_fans",                   # Total followers
                "page_fans_country",           # Followers by country
                "page_fans_gender_age",        # Followers by age/gender
                "post_impressions",            # Post impressions
                "post_reach",                  # Post reach
                "post_engaged_users",          # Engaged users
                "post_reactions_by_type_total" # Reactions breakdown
            ]
        }
    
    def get_comprehensive_analytics(self) -> Dict[str, Any]:
        """Get comprehensive analytics data for dashboard - OPTIMIZED VERSION"""
        try:
            # Get basic metrics with reduced data
            followers_data = self.get_page_followers()
            demographics = self.get_audience_demographics()
            
            # Get posts with basic data only (no individual insights calls)
            posts = self.get_recent_posts(10)  # Reduced from 20 to 10
            analyzed_posts = []
            
            # Process posts without individual insights calls for speed
            for post in posts:
                post_id = post.get("id")
                if not post_id:
                    continue
                
                # Extract basic engagement data from post fields only
                likes_data = post.get("likes", {})
                comments_data = post.get("comments", {})
                shares_data = post.get("shares", {})
                
                reactions_count = 0
                if likes_data and isinstance(likes_data, dict) and "summary" in likes_data:
                    reactions_count = likes_data["summary"].get("total_count", 0)
                
                comments_count = 0
                if comments_data and isinstance(comments_data, dict) and "summary" in comments_data:
                    comments_count = comments_data["summary"].get("total_count", 0)
                
                shares_count = 0
                if shares_data:
                    if isinstance(shares_data, dict) and "count" in shares_data:
                        shares_count = shares_data["count"]
                    elif isinstance(shares_data, (int, float)):
                        shares_count = int(shares_data)
                
                analyzed_posts.append({
                    "id": post_id,
                    "message": post.get("message", ""),
                    "created_time": post.get("created_time", ""),
                    "reactions_count": reactions_count,
                    "comments_count": comments_count,
                    "shares_count": shares_count,
                    "total_engagement": reactions_count + comments_count + shares_count
                })
            
            # Calculate totals
            total_engagement = sum(post.get("total_engagement", 0) for post in analyzed_posts)
            
            # Get best post from basic data
            best_post = max(analyzed_posts, key=lambda x: x.get("total_engagement", 0)) if analyzed_posts else {}
            best_post_id = best_post.get("id", "N/A") if best_post else "N/A"
            
            return {
                "success": True,
                "totals": {
                    "followers": followers_data.get("followers", 0),
                    "total_engagement": total_engagement,
                    "best_post": best_post_id
                },
                "demographics": demographics,
                "posts": analyzed_posts,
                "best_post": best_post,
                "metrics_available": len(analyzed_posts) > 0,
                "note": "Optimized version - basic engagement data only"
            }
            
        except Exception as e:
            logger.error(f"Error getting comprehensive analytics: {e}")
            return {
                "success": False,
                "error": str(e),
                "totals": {
                    "followers": 0,
                    "total_engagement": 0,
                    "best_post": "N/A"
                },
                "demographics": {"by_country": {}, "by_age_gender": {}},
                "posts": [],
                "best_post": {},
                "metrics_available": False
            }
    
    def is_configured(self) -> bool:
        """Check if Facebook analytics is properly configured"""
        return bool(self.page_id and self.access_token)

# Create a global instance
facebook_analytics = FacebookAnalyticsService()
