from fastapi import APIRouter, Depends, HTTPException, Header
from typing import Dict, Any, Optional
from database_service import db_service
from auth_service import auth_service

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

@router.get("/statistics")
async def get_dashboard_statistics(authorization: str = Header(None)):
    """Get dashboard statistics for the current user"""
    try:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Invalid authorization header")
            
        token = authorization.replace("Bearer ", "")
        current_user = await auth_service.get_current_user(token)
        user_id = str(current_user.id)
        
        stats = await db_service.get_dashboard_statistics(user_id)
        return {
            "success": True, 
            "statistics": stats
        }
    except Exception as e:
        print(f"Error getting dashboard statistics: {e}")
        return {"success": False, "error": str(e)}