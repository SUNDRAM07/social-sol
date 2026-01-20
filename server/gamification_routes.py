"""
Gamification API Routes
Handles streaks, achievements, and stats
"""

from fastapi import APIRouter, Depends, HTTPException
from auth_routes import get_current_user
from models import UserResponse
from gamification_service import gamification_service

router = APIRouter(prefix="/gamification", tags=["gamification"])


@router.get("/stats")
async def get_user_stats(current_user: UserResponse = Depends(get_current_user)):
    """Get user's gamification stats including streak, achievements, level"""
    try:
        stats = await gamification_service.get_user_stats(current_user.id)
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/achievements")
async def get_achievements(current_user: UserResponse = Depends(get_current_user)):
    """Get user's earned achievements"""
    try:
        stats = await gamification_service.get_user_stats(current_user.id)
        return {
            "achievements": stats.get("achievements", []),
            "total": stats.get("achievements_count", 0)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/leaderboard")
async def get_leaderboard(limit: int = 10, current_user: UserResponse = Depends(get_current_user)):
    """Get top users leaderboard"""
    try:
        leaders = await gamification_service.get_leaderboard(limit=min(limit, 50))
        return {"leaderboard": leaders}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/record-post")
async def record_post(current_user: UserResponse = Depends(get_current_user)):
    """Record a post for streak tracking (called automatically on post creation)"""
    try:
        result = await gamification_service.record_post(current_user.id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
