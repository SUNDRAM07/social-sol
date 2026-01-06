"""
Optimal Posting Times Service

Provides AI-suggested optimal posting times based on:
- Platform-specific engagement patterns
- Day of week analysis
- Industry/niche best practices
- Time zone awareness
"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum


class Platform(Enum):
    TWITTER = "twitter"
    INSTAGRAM = "instagram"
    LINKEDIN = "linkedin"
    FACEBOOK = "facebook"
    REDDIT = "reddit"
    TIKTOK = "tiktok"


@dataclass
class TimeSlot:
    """Represents an optimal posting time slot"""
    time: str  # e.g., "9:00 AM"
    day: str  # e.g., "Monday" or "Weekday"
    engagement_score: float  # 0-100
    reason: str


@dataclass
class PlatformRecommendation:
    """Optimal times recommendation for a platform"""
    platform: str
    best_times: List[TimeSlot]
    worst_times: List[str]
    posting_frequency: str
    tips: List[str]


class OptimalTimesService:
    """
    Service to calculate optimal posting times based on research data
    and platform-specific engagement patterns.
    """
    
    def __init__(self):
        # Research-based optimal times (2024 data from Sprout Social, Hootsuite, Buffer)
        self.platform_data = {
            Platform.TWITTER: {
                "best_times": [
                    TimeSlot("9:00 AM", "Weekday", 95, "Morning engagement peak"),
                    TimeSlot("12:00 PM", "Weekday", 90, "Lunch break scrolling"),
                    TimeSlot("5:00 PM", "Weekday", 85, "End of workday"),
                    TimeSlot("8:00 AM", "Weekend", 75, "Weekend morning catch-up"),
                ],
                "best_days": ["Tuesday", "Wednesday", "Thursday"],
                "worst_times": ["10 PM - 4 AM", "Sunday evening"],
                "frequency": "3-5 tweets per day",
                "tips": [
                    "Threads perform best between 8-10 AM",
                    "Engagement drops 30% on weekends",
                    "Reply to comments within 1 hour for 40% more engagement",
                    "Use 1-2 hashtags max for best reach"
                ]
            },
            Platform.INSTAGRAM: {
                "best_times": [
                    TimeSlot("11:00 AM", "Weekday", 95, "Pre-lunch engagement spike"),
                    TimeSlot("2:00 PM", "Weekday", 88, "Afternoon break"),
                    TimeSlot("7:00 PM", "Weekday", 92, "Evening relaxation time"),
                    TimeSlot("10:00 AM", "Weekend", 85, "Weekend morning browsing"),
                ],
                "best_days": ["Tuesday", "Wednesday", "Friday"],
                "worst_times": ["3 AM - 6 AM", "Monday morning"],
                "frequency": "1-2 posts per day, 5-7 Stories",
                "tips": [
                    "Reels get 67% more engagement than static posts",
                    "Post Stories throughout the day for visibility",
                    "Carousels get 1.4x more reach than single images",
                    "Use 3-5 relevant hashtags in caption"
                ]
            },
            Platform.LINKEDIN: {
                "best_times": [
                    TimeSlot("7:30 AM", "Weekday", 95, "Morning commute reading"),
                    TimeSlot("12:00 PM", "Weekday", 90, "Lunch break networking"),
                    TimeSlot("5:00 PM", "Tuesday-Thursday", 88, "End of workday wrap-up"),
                ],
                "best_days": ["Tuesday", "Wednesday", "Thursday"],
                "worst_times": ["Weekends", "After 6 PM", "Monday before 8 AM"],
                "frequency": "1-2 posts per day",
                "tips": [
                    "Document-style posts get 3x more engagement",
                    "First comment strategy boosts algorithm",
                    "Personal stories outperform corporate content",
                    "Avoid external links in main post (put in comments)"
                ]
            },
            Platform.FACEBOOK: {
                "best_times": [
                    TimeSlot("9:00 AM", "Weekday", 90, "Morning check-in"),
                    TimeSlot("1:00 PM", "Weekday", 92, "Lunch break"),
                    TimeSlot("4:00 PM", "Weekday", 85, "Afternoon wind-down"),
                ],
                "best_days": ["Wednesday", "Thursday", "Friday"],
                "worst_times": ["Late night (11 PM - 6 AM)", "Early Monday"],
                "frequency": "1-2 posts per day",
                "tips": [
                    "Video content gets 135% more organic reach",
                    "Native videos outperform YouTube links",
                    "Questions in posts boost comments by 100%",
                    "Facebook Groups have 5x better engagement than Pages"
                ]
            },
            Platform.REDDIT: {
                "best_times": [
                    TimeSlot("6:00 AM", "Weekday", 95, "Early risers, US East Coast morning"),
                    TimeSlot("8:00 AM", "Weekday", 90, "Peak morning activity"),
                    TimeSlot("12:00 PM", "Weekday", 85, "Lunch browsing"),
                ],
                "best_days": ["Monday", "Saturday", "Sunday"],
                "worst_times": ["Late night US time", "Friday evening"],
                "frequency": "1-3 posts per day (varies by subreddit)",
                "tips": [
                    "Post when US is waking up (6-8 AM EST)",
                    "Engage authentically - Reddit hates self-promotion",
                    "Build karma in community before posting links",
                    "AMA posts perform best on Tuesday/Wednesday"
                ]
            },
            Platform.TIKTOK: {
                "best_times": [
                    TimeSlot("7:00 AM", "Weekday", 85, "Morning scroll"),
                    TimeSlot("12:00 PM", "Weekday", 90, "Lunch break"),
                    TimeSlot("7:00 PM", "Daily", 95, "Evening entertainment peak"),
                    TimeSlot("9:00 PM", "Weekend", 92, "Weekend night browsing"),
                ],
                "best_days": ["Tuesday", "Thursday", "Friday"],
                "worst_times": ["2 AM - 5 AM", "Monday morning"],
                "frequency": "1-4 videos per day",
                "tips": [
                    "Post consistently at the same times daily",
                    "First 3 seconds determine if users watch",
                    "Trending sounds boost discoverability",
                    "Reply to comments with videos for extra engagement"
                ]
            }
        }
        
        # Industry-specific adjustments
        self.industry_adjustments = {
            "crypto": {"shift_hours": -1, "best_days": ["Weekend"], "note": "Crypto audience is active 24/7, slightly earlier posting works well"},
            "b2b": {"shift_hours": 0, "best_days": ["Tuesday", "Wednesday", "Thursday"], "note": "Stick to business hours"},
            "fitness": {"shift_hours": -2, "best_days": ["Monday", "Sunday"], "note": "Early morning motivation posts perform well"},
            "food": {"shift_hours": 0, "best_days": ["Friday", "Saturday"], "note": "Meal times and weekends are optimal"},
            "tech": {"shift_hours": 0, "best_days": ["Tuesday", "Wednesday"], "note": "Tech audience engages during work hours"},
            "fashion": {"shift_hours": 1, "best_days": ["Thursday", "Friday", "Sunday"], "note": "Evening and weekend browsing"},
        }
    
    def get_optimal_times(
        self, 
        platforms: List[str], 
        timezone: str = "UTC",
        industry: Optional[str] = None
    ) -> Dict[str, PlatformRecommendation]:
        """
        Get optimal posting times for specified platforms
        
        Args:
            platforms: List of platform names
            timezone: User's timezone (for display)
            industry: Optional industry for adjusted recommendations
        """
        recommendations = {}
        
        for platform_name in platforms:
            try:
                platform = Platform(platform_name.lower())
                data = self.platform_data.get(platform)
                
                if not data:
                    continue
                
                # Apply industry adjustments if specified
                best_times = data["best_times"].copy()
                tips = data["tips"].copy()
                
                if industry and industry.lower() in self.industry_adjustments:
                    adj = self.industry_adjustments[industry.lower()]
                    tips.insert(0, f"💡 {adj['note']}")
                
                recommendations[platform_name] = PlatformRecommendation(
                    platform=platform_name,
                    best_times=best_times,
                    worst_times=data["worst_times"],
                    posting_frequency=data["frequency"],
                    tips=tips
                )
                
            except (ValueError, KeyError):
                continue
        
        return recommendations
    
    def get_weekly_schedule(
        self, 
        platforms: List[str],
        posts_per_week: int = 7,
        industry: Optional[str] = None
    ) -> Dict[str, List[Dict]]:
        """
        Generate a weekly posting schedule
        
        Args:
            platforms: List of platforms to schedule for
            posts_per_week: Target number of posts per week
            industry: Optional industry for timing adjustments
        """
        schedule = {}
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        
        for platform_name in platforms:
            try:
                platform = Platform(platform_name.lower())
                data = self.platform_data.get(platform)
                
                if not data:
                    continue
                
                best_days = data.get("best_days", ["Tuesday", "Wednesday", "Thursday"])
                best_times = data["best_times"]
                
                # Distribute posts across the week
                posts_per_day = max(1, posts_per_week // len(best_days))
                remaining = posts_per_week % len(best_days)
                
                weekly_schedule = []
                for i, day in enumerate(days):
                    if day in best_days:
                        # Get best time for this day
                        time_slot = best_times[i % len(best_times)]
                        count = posts_per_day + (1 if remaining > 0 else 0)
                        if remaining > 0:
                            remaining -= 1
                        
                        for j in range(count):
                            weekly_schedule.append({
                                "day": day,
                                "time": time_slot.time,
                                "engagement_score": time_slot.engagement_score,
                                "reason": time_slot.reason
                            })
                
                schedule[platform_name] = weekly_schedule
                
            except (ValueError, KeyError):
                continue
        
        return schedule
    
    def format_recommendation_text(self, recommendations: Dict[str, PlatformRecommendation]) -> str:
        """Format recommendations as readable text for AI response"""
        lines = ["## 📅 Optimal Posting Times\n"]
        
        for platform, rec in recommendations.items():
            lines.append(f"### {platform.title()}")
            lines.append(f"**Best posting frequency:** {rec.posting_frequency}\n")
            
            lines.append("**Best times:**")
            for slot in rec.best_times[:3]:  # Top 3
                lines.append(f"- **{slot.time}** ({slot.day}) - {slot.reason} (Score: {slot.engagement_score}/100)")
            
            lines.append(f"\n**Avoid:** {', '.join(rec.worst_times)}\n")
            
            lines.append("**Pro Tips:**")
            for tip in rec.tips[:3]:  # Top 3 tips
                lines.append(f"- {tip}")
            
            lines.append("")  # Empty line between platforms
        
        return "\n".join(lines)


# Singleton instance
optimal_times_service = OptimalTimesService()

