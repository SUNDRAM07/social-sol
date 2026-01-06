"""
Authentication routes for Google OAuth integration
"""

from fastapi import APIRouter, HTTPException, status, Depends, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional
from auth_service import auth_service
from models import UserResponse

router = APIRouter(prefix="/auth", tags=["authentication"])


# Explicit OPTIONS handlers for CORS preflight
@router.options("/register")
async def options_register():
    """Handle CORS preflight for register endpoint"""
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "*",
        }
    )


@router.options("/login")
async def options_login():
    """Handle CORS preflight for login endpoint"""
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "*",
        }
    )


@router.options("/google")
async def options_google():
    """Handle CORS preflight for google auth endpoint"""
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "*",
        }
    )
security = HTTPBearer()
# Use the global instance from auth_service module instead of creating a new one


class GoogleTokenRequest(BaseModel):
    token: str


class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str


class LoginRequest(BaseModel):
    email: str
    password: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


@router.post("/register")
async def register(request: RegisterRequest, response: Response):
    """
    Register a new user with email and password
    """
    # Add CORS headers to response
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "*"
    
    try:
        # Validate email format
        if "@" not in request.email or "." not in request.email.split("@")[1]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid email format"
            )
        
        # Validate password length
        if len(request.password) < 6:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must be at least 6 characters"
            )
        
        # Register user
        user = await auth_service.register_user(
            email=request.email,
            password=request.password,
            name=request.name
        )
        
        # Generate JWT token
        access_token = auth_service.create_access_token(user.id)
        
        print(f"✅ Registration successful for user: {user.email}")
        
        return AuthResponse(
            access_token=access_token,
            user=UserResponse.from_orm(user)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Registration failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )


@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest):
    """
    Login user with email and password
    """
    try:
        # Authenticate user
        user = await auth_service.authenticate_user(
            email=request.email,
            password=request.password
        )
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Generate JWT token
        access_token = auth_service.create_access_token(user.id)
        
        print(f"✅ Login successful for user: {user.email}")
        
        return AuthResponse(
            access_token=access_token,
            user=UserResponse.from_orm(user)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Login failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )


@router.post("/google", response_model=AuthResponse)
async def google_auth(request: GoogleTokenRequest):
    """
    Authenticate user with Google OAuth token
    """
    try:
        print(f"🚀 Google auth request received for token: {request.token[:50]}...")
        
        # Verify Google token and get user info
        user_info = await auth_service.verify_google_token(request.token)
        
        # Create or get user from database
        user = await auth_service.get_or_create_user(user_info)
        
        # Generate JWT token
        access_token = auth_service.create_access_token(user.id)
        
        print(f"✅ Authentication successful for user: {user.email}")
        
        return AuthResponse(
            access_token=access_token,
            user=UserResponse.from_orm(user)
        )
        
    except Exception as e:
        print(f"❌ Authentication failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}"
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Get current authenticated user
    """
    try:
        user = await auth_service.get_current_user(credentials.credentials)
        return UserResponse.from_orm(user)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )


@router.post("/logout")
async def logout():
    """
    Logout user (client-side token removal)
    """
    return {"message": "Successfully logged out"}


@router.delete("/delete-account")
async def delete_account(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Delete user account and all associated data
    """
    try:
        print(f"🔍 Delete account request received for token: {credentials.credentials[:50]}...")
        
        # Get current user
        user = await auth_service.get_current_user(credentials.credentials)
        print(f"✅ User found for deletion: {user.email}")
        
        # Delete user and all associated data
        await auth_service.delete_user_account(str(user.id))
        
        print(f"✅ Account deleted successfully for user: {user.email}")
        return {"message": "Account deleted successfully"}
        
    except HTTPException as e:
        print(f"❌ HTTP Exception in delete account: {e.detail}")
        raise e
    except Exception as e:
        print(f"❌ Unexpected error in delete account: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete account: {str(e)}"
        )


# Dependency to get current user in other routes
async def get_current_user_dependency(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Dependency to get current user for protected routes"""
    return await auth_service.get_current_user(credentials.credentials)
