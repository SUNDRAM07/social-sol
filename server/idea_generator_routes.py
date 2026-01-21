"""
Idea Generator API Routes
Handles idea generation requests using AI services
"""

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import os
import json
import hashlib
from datetime import datetime
from auth_routes import get_current_user_dependency
from idea_generator_service import IdeaGeneratorService
from middleware.tier_check import check_ai_limit, increment_ai_usage

router = APIRouter(prefix="/api/idea-generator", tags=["idea-generator"])

# Initialize the service
idea_service = IdeaGeneratorService()

class IdeaGenerationRequest(BaseModel):
    # Audience
    age_range: List[int]  # [min_age, max_age]
    location: Optional[str] = None
    
    # Goals and Voice
    goals: List[str]
    brand_voice: Optional[str] = None
    
    # Platforms
    platforms: List[str]
    
    # Information
    trend_miner_data: Optional[str] = None
    brand_assets_urls: Optional[str] = None
    competitor_urls: Optional[str] = None
    seasonal_event: Optional[str] = None
    extra_information: Optional[str] = None

class GeneratedIdea(BaseModel):
    id: str
    title: str
    summary: str
    description: str
    platforms: List[str]
    estimated_engagement: float
    trending_score: int
    content_type: str
    best_time_to_post: str
    hashtags: List[str]
    target_audience: str
    created_at: str

class IdeaGenerationResponse(BaseModel):
    success: bool
    ideas: List[GeneratedIdea]
    generation_info: Dict[str, Any]
    error: Optional[str] = None

@router.post("/generate", response_model=IdeaGenerationResponse)
async def generate_ideas(
    request: IdeaGenerationRequest,
    current_user = Depends(get_current_user_dependency),
    ai_limit = Depends(check_ai_limit)  # Checks daily AI generation limit
):
    """
    Generate 5 trending content ideas based on user input with comprehensive analysis
    """
    try:
        print(f"🎯 Generating ideas for user: {current_user.email}")
        print(f"📊 Request data: {request.dict()}")
        
        # Validate request
        if not request.platforms:
            raise HTTPException(status_code=400, detail="At least one platform must be selected")
        
        if not request.goals:
            raise HTTPException(status_code=400, detail="At least one goal must be selected")
        
        # Check for uploaded files in the public directory
        uploaded_files = []
        try:
            user_upload_dir = f"public/idea_generator/{current_user.id}"
            if os.path.exists(user_upload_dir):
                for file_type in ["trend_data", "brand_assets", "competitor_assets"]:
                    type_dir = os.path.join(user_upload_dir, file_type)
                    if os.path.exists(type_dir):
                        for filename in os.listdir(type_dir):
                            file_path = os.path.join(type_dir, filename)
                            if os.path.isfile(file_path):
                                uploaded_files.append({
                                    'path': file_path,
                                    'filename': filename,
                                    'type': file_type
                                })
            print(f"📁 Found {len(uploaded_files)} uploaded files for analysis")
        except Exception as e:
            print(f"⚠️ Warning: Failed to check for uploaded files: {e}")
        
        # Generate ideas using the AI service with file analysis
        ideas = await idea_service.generate_ideas(
            user_data=request.dict(),
            user_id=str(current_user.id),
            uploaded_files=uploaded_files
        )
        
        if not ideas:
            raise HTTPException(status_code=500, detail="Failed to generate ideas")
        
        # Format response
        generated_ideas = []
        for i, idea in enumerate(ideas):
            generated_idea = GeneratedIdea(
                id=f"idea_{hashlib.md5(f'{current_user.id}_{i}_{datetime.now().timestamp()}'.encode()).hexdigest()[:12]}",
                title=idea.get("title", f"Content Idea {i+1}"),
                summary=idea.get("summary", ""),
                description=idea.get("description", ""),
                platforms=idea.get("platforms", request.platforms),
                estimated_engagement=idea.get("estimated_engagement", 4.5),
                trending_score=idea.get("trending_score", 85),
                content_type=idea.get("content_type", "Mixed"),
                best_time_to_post=idea.get("best_time_to_post", "6-8 PM"),
                hashtags=idea.get("hashtags", []),
                target_audience=idea.get("target_audience", f"{request.age_range[0]}-{request.age_range[1]} years"),
                created_at=datetime.now().isoformat()
            )
            generated_ideas.append(generated_idea)
        
        generation_info = {
            "user_id": str(current_user.id),
            "generation_time": datetime.now().isoformat(),
            "platforms": request.platforms,
            "goals": request.goals,
            "brand_voice": request.brand_voice,
            "location": request.location
        }
        
        print(f"✅ Successfully generated {len(generated_ideas)} ideas")
        
        # Increment AI usage counter after successful generation
        await increment_ai_usage(current_user.id)
        
        return IdeaGenerationResponse(
            success=True,
            ideas=generated_ideas,
            generation_info=generation_info
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error generating ideas: {str(e)}")
        return IdeaGenerationResponse(
            success=False,
            ideas=[],
            generation_info={},
            error=f"Failed to generate ideas: {str(e)}"
        )

@router.get("/idea/{idea_id}")
async def get_idea_details(
    idea_id: str,
    current_user = Depends(get_current_user_dependency)
):
    """
    Get detailed information about a specific idea
    """
    try:
        # In a real implementation, you might store ideas in database
        # For now, we'll return a placeholder response
        return {
            "success": True,
            "idea": {
                "id": idea_id,
                "title": "Sample Idea",
                "description": "Detailed description of the idea...",
                "platforms": ["instagram", "facebook"],
                "status": "generated"
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/upload-files")
async def upload_idea_files(
    files: List[UploadFile] = File(...),
    file_type: str = "brand_assets",  # brand_assets, competitor_assets, trend_data
    current_user = Depends(get_current_user_dependency)
):
    """
    Upload files for idea generation (brand assets, competitor assets, trend data)
    """
    try:
        uploaded_files = []
        
        # Create user-specific upload directory
        upload_dir = f"public/idea_generator/{current_user.id}/{file_type}"
        os.makedirs(upload_dir, exist_ok=True)
        
        for file in files:
            # Generate unique filename
            timestamp = int(datetime.now().timestamp())
            file_hash = hashlib.md5(f"{file.filename}_{timestamp}".encode()).hexdigest()[:8]
            filename = f"{file_hash}_{file.filename}"
            file_path = os.path.join(upload_dir, filename)
            
            # Save file
            with open(file_path, "wb") as buffer:
                content = await file.read()
                buffer.write(content)
            
            uploaded_files.append({
                "original_name": file.filename,
                "saved_name": filename,
                "file_path": f"/public/idea_generator/{current_user.id}/{file_type}/{filename}",
                "file_size": len(content),
                "content_type": file.content_type
            })
        
        return {
            "success": True,
            "files": uploaded_files,
            "message": f"Successfully uploaded {len(uploaded_files)} files"
        }
        
    except Exception as e:
        print(f"❌ File upload error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"File upload failed: {str(e)}")