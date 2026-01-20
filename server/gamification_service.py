"""
Gamification Service for SocialAnywhere.ai
Handles streaks, achievements, and engagement tracking
"""

import logging
from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Optional
from uuid import UUID

from database import db_manager

logger = logging.getLogger(__name__)


def _row_to_dict(row):
    """Convert database row to dictionary"""
    if row is None:
        return None
    if isinstance(row, dict):
        return row
    mapping = getattr(row, "_mapping", None)
    if mapping is not None:
        return dict(mapping)
    try:
        return dict(row)
    except:
        return None


class GamificationService:
    """Service for managing user gamification features"""

    # Achievement definitions
    ACHIEVEMENTS = {
        "first_post": {
            "name": "First Steps",
            "description": "Created your first post",
            "icon": "🎯",
            "xp": 50
        },
        "streak_7": {
            "name": "Weekly Warrior",
            "description": "Posted for 7 days in a row",
            "icon": "🔥",
            "xp": 100
        },
        "streak_30": {
            "name": "Monthly Master",
            "description": "Posted for 30 days in a row",
            "icon": "⭐",
            "xp": 500
        },
        "posts_10": {
            "name": "Content Creator",
            "description": "Created 10 posts",
            "icon": "📝",
            "xp": 75
        },
        "posts_50": {
            "name": "Prolific Poster",
            "description": "Created 50 posts",
            "icon": "🚀",
            "xp": 200
        },
        "posts_100": {
            "name": "Social Media Pro",
            "description": "Created 100 posts",
            "icon": "🏆",
            "xp": 500
        },
        "platforms_3": {
            "name": "Multi-Platform",
            "description": "Connected 3 social platforms",
            "icon": "🌐",
            "xp": 100
        },
        "ai_master": {
            "name": "AI Master",
            "description": "Generated 50 AI captions",
            "icon": "🤖",
            "xp": 150
        },
        "early_bird": {
            "name": "Early Bird",
            "description": "Posted before 8 AM",
            "icon": "🌅",
            "xp": 25
        },
        "night_owl": {
            "name": "Night Owl",
            "description": "Posted after 10 PM",
            "icon": "🦉",
            "xp": 25
        },
    }

    async def get_user_stats(self, user_id: UUID) -> Dict[str, Any]:
        """Get complete gamification stats for a user"""
        try:
            # Get or create streak record
            streak = await self._get_or_create_streak(user_id)
            
            # Get achievements
            achievements = await self._get_user_achievements(user_id)
            
            # Calculate XP
            total_xp = sum(
                self.ACHIEVEMENTS.get(a["achievement_type"], {}).get("xp", 0)
                for a in achievements
            )
            
            # Calculate level (100 XP per level)
            level = 1 + (total_xp // 100)
            xp_to_next = 100 - (total_xp % 100)
            
            # Get total post count from database
            total_posts = await self._get_total_posts(user_id)
            
            return {
                "current_streak": streak.get("current_streak", 0),
                "longest_streak": streak.get("longest_streak", 0),
                "total_posts": total_posts,
                "last_post_date": streak.get("last_post_date"),
                "total_xp": total_xp,
                "level": level,
                "xp_to_next_level": xp_to_next,
                "achievements": achievements,
                "achievements_count": len(achievements),
            }
        except Exception as e:
            logger.error(f"Error getting user stats: {e}")
            return {
                "current_streak": 0,
                "longest_streak": 0,
                "total_posts": 0,
                "last_post_date": None,
                "total_xp": 0,
                "level": 1,
                "xp_to_next_level": 100,
                "achievements": [],
                "achievements_count": 0,
            }

    async def record_post(self, user_id: UUID) -> Dict[str, Any]:
        """Record a post and update streak/achievements"""
        try:
            today = date.today()
            
            # Get current streak info
            streak = await self._get_or_create_streak(user_id)
            last_post_date = streak.get("last_post_date")
            current_streak = streak.get("current_streak", 0)
            longest_streak = streak.get("longest_streak", 0)
            total_posts = streak.get("total_posts", 0)
            
            # Calculate new streak
            new_streak = current_streak
            if last_post_date is None:
                # First ever post
                new_streak = 1
            elif last_post_date == today:
                # Already posted today, no change
                pass
            elif last_post_date == today - timedelta(days=1):
                # Consecutive day, increment streak
                new_streak = current_streak + 1
            else:
                # Streak broken, start fresh
                new_streak = 1
            
            new_longest = max(longest_streak, new_streak)
            new_total = total_posts + 1
            
            # Update database
            await db_manager.execute_query(
                """INSERT INTO user_streaks (user_id, current_streak, longest_streak, last_post_date, total_posts)
                   VALUES (:user_id, :current_streak, :longest_streak, :last_post_date, :total_posts)
                   ON CONFLICT (user_id) DO UPDATE SET
                     current_streak = :current_streak,
                     longest_streak = :longest_streak,
                     last_post_date = :last_post_date,
                     total_posts = :total_posts""",
                {
                    "user_id": str(user_id),
                    "current_streak": new_streak,
                    "longest_streak": new_longest,
                    "last_post_date": today,
                    "total_posts": new_total
                }
            )
            
            # Check for new achievements
            new_achievements = await self._check_achievements(user_id, new_streak, new_total)
            
            return {
                "success": True,
                "current_streak": new_streak,
                "longest_streak": new_longest,
                "total_posts": new_total,
                "streak_increased": new_streak > current_streak,
                "new_achievements": new_achievements,
            }
        except Exception as e:
            logger.error(f"Error recording post: {e}")
            return {"success": False, "error": str(e)}

    async def _get_or_create_streak(self, user_id: UUID) -> Dict[str, Any]:
        """Get or create streak record for user"""
        try:
            streak = _row_to_dict(await db_manager.fetch_one(
                "SELECT * FROM user_streaks WHERE user_id = :user_id",
                {"user_id": str(user_id)}
            ))
            
            if not streak:
                # Create new record
                await db_manager.execute_query(
                    """INSERT INTO user_streaks (user_id, current_streak, longest_streak, total_posts)
                       VALUES (:user_id, 0, 0, 0)
                       ON CONFLICT DO NOTHING""",
                    {"user_id": str(user_id)}
                )
                return {"current_streak": 0, "longest_streak": 0, "total_posts": 0, "last_post_date": None}
            
            return streak
        except Exception as e:
            logger.error(f"Error getting streak: {e}")
            return {"current_streak": 0, "longest_streak": 0, "total_posts": 0, "last_post_date": None}

    async def _get_user_achievements(self, user_id: UUID) -> List[Dict[str, Any]]:
        """Get all achievements for a user"""
        try:
            achievements = await db_manager.fetch_all(
                "SELECT * FROM achievements WHERE user_id = :user_id ORDER BY achieved_at DESC",
                {"user_id": str(user_id)}
            )
            
            result = []
            for a in (achievements or []):
                a_dict = _row_to_dict(a)
                if a_dict and a_dict.get("achievement_type") in self.ACHIEVEMENTS:
                    achievement_info = self.ACHIEVEMENTS[a_dict["achievement_type"]]
                    result.append({
                        **a_dict,
                        "name": achievement_info["name"],
                        "description": achievement_info["description"],
                        "icon": achievement_info["icon"],
                        "xp": achievement_info["xp"],
                    })
            
            return result
        except Exception as e:
            logger.error(f"Error getting achievements: {e}")
            return []

    async def _get_total_posts(self, user_id: UUID) -> int:
        """Get total post count for user"""
        try:
            result = _row_to_dict(await db_manager.fetch_one(
                "SELECT COUNT(*) as count FROM posts WHERE user_id = :user_id",
                {"user_id": str(user_id)}
            ))
            return result.get("count", 0) if result else 0
        except Exception as e:
            logger.error(f"Error getting post count: {e}")
            return 0

    async def _check_achievements(self, user_id: UUID, streak: int, total_posts: int) -> List[Dict[str, Any]]:
        """Check and award new achievements"""
        new_achievements = []
        
        try:
            # Get existing achievements
            existing = await db_manager.fetch_all(
                "SELECT achievement_type FROM achievements WHERE user_id = :user_id",
                {"user_id": str(user_id)}
            )
            existing_types = {_row_to_dict(a).get("achievement_type") for a in (existing or []) if a}
            
            # Check each achievement
            checks = [
                ("first_post", total_posts >= 1),
                ("posts_10", total_posts >= 10),
                ("posts_50", total_posts >= 50),
                ("posts_100", total_posts >= 100),
                ("streak_7", streak >= 7),
                ("streak_30", streak >= 30),
            ]
            
            for achievement_type, condition in checks:
                if condition and achievement_type not in existing_types:
                    # Award achievement
                    await db_manager.execute_query(
                        """INSERT INTO achievements (user_id, achievement_type)
                           VALUES (:user_id, :achievement_type)
                           ON CONFLICT DO NOTHING""",
                        {"user_id": str(user_id), "achievement_type": achievement_type}
                    )
                    
                    achievement_info = self.ACHIEVEMENTS[achievement_type]
                    new_achievements.append({
                        "type": achievement_type,
                        "name": achievement_info["name"],
                        "description": achievement_info["description"],
                        "icon": achievement_info["icon"],
                        "xp": achievement_info["xp"],
                    })
                    logger.info(f"User {user_id} earned achievement: {achievement_type}")
            
            return new_achievements
        except Exception as e:
            logger.error(f"Error checking achievements: {e}")
            return []

    async def get_leaderboard(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top users by streak/posts"""
        try:
            leaders = await db_manager.fetch_all(
                """SELECT u.id, u.name, us.current_streak, us.longest_streak, us.total_posts
                   FROM user_streaks us
                   JOIN users u ON u.id = us.user_id
                   ORDER BY us.total_posts DESC, us.longest_streak DESC
                   LIMIT :limit""",
                {"limit": limit}
            )
            return [_row_to_dict(l) for l in (leaders or []) if l]
        except Exception as e:
            logger.error(f"Error getting leaderboard: {e}")
            return []


# Singleton instance
gamification_service = GamificationService()
