"""
Flow Routes - API endpoints for automation flows
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import logging

from auth_routes import get_current_user
from flow_service import flow_service, TRIGGER_TYPES, ACTION_TYPES, CONDITION_OPERATORS
from subscription_service import subscription_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/flows", tags=["flows"])


# ============================================
# REQUEST/RESPONSE MODELS
# ============================================

class CreateFlowRequest(BaseModel):
    name: str
    description: Optional[str] = None
    trigger_type: str
    trigger_config: Dict[str, Any]
    conditions: Optional[List[Dict[str, Any]]] = None
    actions: List[Dict[str, Any]]


class UpdateFlowRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    trigger_type: Optional[str] = None
    trigger_config: Optional[Dict[str, Any]] = None
    conditions: Optional[List[Dict[str, Any]]] = None
    actions: Optional[List[Dict[str, Any]]] = None
    is_active: Optional[bool] = None


# ============================================
# ENDPOINTS
# ============================================

@router.get("/triggers")
async def get_trigger_types(user: dict = Depends(get_current_user)):
    """Get available trigger types for the user's tier"""
    try:
        # Get user's tier
        tier = await subscription_service.get_user_tier(user["id"])
        
        # Get triggers available for this tier
        triggers = flow_service.get_trigger_types(tier)
        
        return {
            "success": True,
            "tier": tier,
            "triggers": triggers
        }
    except Exception as e:
        logger.error(f"Error getting triggers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/actions")
async def get_action_types(user: dict = Depends(get_current_user)):
    """Get all available action types"""
    return {
        "success": True,
        "actions": ACTION_TYPES
    }


@router.get("/operators")
async def get_condition_operators(user: dict = Depends(get_current_user)):
    """Get all condition operators"""
    return {
        "success": True,
        "operators": CONDITION_OPERATORS
    }


@router.get("/")
async def list_flows(user: dict = Depends(get_current_user)):
    """List all flows for the current user"""
    try:
        flows = await flow_service.get_user_flows(user["id"])
        stats = await flow_service.get_flow_stats(user["id"])
        
        return {
            "success": True,
            "flows": flows,
            "stats": stats
        }
    except Exception as e:
        logger.error(f"Error listing flows: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_flow_stats(user: dict = Depends(get_current_user)):
    """Get flow statistics"""
    try:
        stats = await flow_service.get_flow_stats(user["id"])
        return {
            "success": True,
            "stats": stats
        }
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{flow_id}")
async def get_flow(flow_id: str, user: dict = Depends(get_current_user)):
    """Get a specific flow by ID"""
    try:
        flow = await flow_service.get_flow(flow_id, user["id"])
        
        if not flow:
            raise HTTPException(status_code=404, detail="Flow not found")
        
        return {
            "success": True,
            "flow": flow
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting flow: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/")
async def create_flow(request: CreateFlowRequest, user: dict = Depends(get_current_user)):
    """Create a new automation flow"""
    try:
        # Check user's tier for trigger access
        tier = await subscription_service.get_user_tier(user["id"])
        
        # Validate trigger is available for tier
        trigger_info = TRIGGER_TYPES.get(request.trigger_type)
        if not trigger_info:
            raise HTTPException(status_code=400, detail=f"Invalid trigger type: {request.trigger_type}")
        
        tier_order = {"FREE": 0, "BASIC": 1, "PREMIUM": 2, "AGENCY": 3}
        if tier_order.get(tier.upper(), 0) < tier_order.get(trigger_info["tier"], 3):
            raise HTTPException(
                status_code=403, 
                detail=f"Trigger '{request.trigger_type}' requires {trigger_info['tier']} tier or higher"
            )
        
        # Check flow limit for tier
        stats = await flow_service.get_flow_stats(user["id"])
        flow_limits = {"FREE": 0, "BASIC": 0, "PREMIUM": 5, "AGENCY": 999}
        
        if stats["total_flows"] >= flow_limits.get(tier.upper(), 0):
            raise HTTPException(
                status_code=403,
                detail=f"Flow limit reached for {tier} tier ({flow_limits.get(tier.upper(), 0)} flows)"
            )
        
        # Create the flow
        result = await flow_service.create_flow(
            user_id=user["id"],
            name=request.name,
            description=request.description,
            trigger_type=request.trigger_type,
            trigger_config=request.trigger_config,
            conditions=request.conditions,
            actions=request.actions
        )
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result.get("error", "Failed to create flow"))
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating flow: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{flow_id}")
async def update_flow(
    flow_id: str, 
    request: UpdateFlowRequest, 
    user: dict = Depends(get_current_user)
):
    """Update an existing flow"""
    try:
        updates = request.dict(exclude_unset=True)
        
        if not updates:
            raise HTTPException(status_code=400, detail="No updates provided")
        
        result = await flow_service.update_flow(flow_id, user["id"], updates)
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result.get("error", "Failed to update flow"))
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating flow: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{flow_id}")
async def delete_flow(flow_id: str, user: dict = Depends(get_current_user)):
    """Delete a flow"""
    try:
        result = await flow_service.delete_flow(flow_id, user["id"])
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result.get("error", "Failed to delete flow"))
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting flow: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{flow_id}/toggle")
async def toggle_flow(flow_id: str, user: dict = Depends(get_current_user)):
    """Toggle flow active status"""
    try:
        # Get current status
        flow = await flow_service.get_flow(flow_id, user["id"])
        
        if not flow:
            raise HTTPException(status_code=404, detail="Flow not found")
        
        # Toggle
        new_status = not flow["is_active"]
        result = await flow_service.toggle_flow(flow_id, user["id"], new_status)
        
        return {
            "success": True,
            "is_active": new_status,
            "message": f"Flow {'activated' if new_status else 'deactivated'}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error toggling flow: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{flow_id}/test")
async def test_flow(flow_id: str, user: dict = Depends(get_current_user)):
    """Test execute a flow with mock data"""
    try:
        flow = await flow_service.get_flow(flow_id, user["id"])
        
        if not flow:
            raise HTTPException(status_code=404, detail="Flow not found")
        
        # Create mock context based on trigger type
        mock_context = {
            "trigger_event": f"Test trigger for {flow['trigger_type']}",
            "timestamp": "2024-01-25T12:00:00Z",
            "price": 1.50,
            "holder_count": 1000,
            "amount": 50000
        }
        
        # Execute flow (dry run would be better)
        result = await flow_service.execute_flow(flow_id, mock_context)
        
        return {
            "success": True,
            "test_result": result,
            "mock_context": mock_context
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error testing flow: {e}")
        raise HTTPException(status_code=500, detail=str(e))
