"""
Authentication routes for Google OAuth and Solana Wallet integration
"""

from fastapi import APIRouter, HTTPException, status, Depends, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional
import secrets
import time
from auth_service import auth_service
from models import UserResponse

router = APIRouter(prefix="/auth", tags=["authentication"])

# In-memory nonce storage (use Redis in production)
wallet_nonces = {}


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


class WalletNonceRequest(BaseModel):
    wallet_address: str


class WalletVerifyRequest(BaseModel):
    wallet_address: str
    signature: str
    nonce: str


class WalletNonceResponse(BaseModel):
    message: str
    nonce: str


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


# ============================================
# SOLANA WALLET AUTHENTICATION
# ============================================

@router.options("/wallet/nonce")
async def options_wallet_nonce():
    """Handle CORS preflight for wallet nonce endpoint"""
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "*",
        }
    )


@router.options("/wallet/verify")
async def options_wallet_verify():
    """Handle CORS preflight for wallet verify endpoint"""
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "*",
        }
    )


@router.post("/wallet/nonce", response_model=WalletNonceResponse)
async def get_wallet_nonce(request: WalletNonceRequest):
    """
    Generate a nonce/message for wallet signature verification.
    The user signs this message to prove wallet ownership.
    """
    try:
        wallet_address = request.wallet_address
        
        # Validate wallet address format (Solana addresses are 32-44 characters base58)
        if not wallet_address or len(wallet_address) < 32 or len(wallet_address) > 44:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid wallet address format"
            )
        
        # Generate a unique nonce
        nonce = secrets.token_hex(16)
        timestamp = int(time.time())
        
        # Create the message to sign
        message = f"Sign this message to authenticate with SocialAnywhere.AI\n\nWallet: {wallet_address}\nNonce: {nonce}\nTimestamp: {timestamp}"
        
        # Store nonce temporarily (expires after 5 minutes)
        wallet_nonces[wallet_address] = {
            "nonce": nonce,
            "timestamp": timestamp,
            "message": message,
            "expires": timestamp + 300  # 5 minutes
        }
        
        print(f"🔐 Generated nonce for wallet: {wallet_address[:8]}...{wallet_address[-4:]}")
        
        return WalletNonceResponse(message=message, nonce=nonce)
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error generating wallet nonce: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate authentication message"
        )


@router.post("/wallet/verify", response_model=AuthResponse)
async def verify_wallet_signature(request: WalletVerifyRequest):
    """
    Verify the wallet signature and authenticate/register the user.
    """
    try:
        wallet_address = request.wallet_address
        signature = request.signature
        nonce = request.nonce
        
        # Check if nonce exists and is valid
        stored = wallet_nonces.get(wallet_address)
        if not stored:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No authentication request found. Please request a new nonce."
            )
        
        # Check if nonce matches
        if stored["nonce"] != nonce:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid nonce"
            )
        
        # Check if nonce expired
        if time.time() > stored["expires"]:
            del wallet_nonces[wallet_address]
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Authentication request expired. Please request a new nonce."
            )
        
        # Verify signature using nacl
        try:
            import base58
            from nacl.signing import VerifyKey
            from nacl.exceptions import BadSignatureError
            
            # Decode the public key (wallet address) and signature
            public_key_bytes = base58.b58decode(wallet_address)
            signature_bytes = base58.b58decode(signature)
            message_bytes = stored["message"].encode('utf-8')
            
            # Verify the signature
            verify_key = VerifyKey(public_key_bytes)
            verify_key.verify(message_bytes, signature_bytes)
            
            print(f"✅ Wallet signature verified for: {wallet_address[:8]}...{wallet_address[-4:]}")
            
        except BadSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid wallet signature"
            )
        except Exception as e:
            print(f"❌ Signature verification error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Signature verification failed"
            )
        
        # Clean up used nonce
        del wallet_nonces[wallet_address]
        
        # Get or create user by wallet address
        user = await auth_service.get_or_create_wallet_user(wallet_address)
        
        # Generate JWT token
        access_token = auth_service.create_access_token(user.id)
        
        print(f"✅ Wallet authentication successful: {wallet_address[:8]}...{wallet_address[-4:]}")
        
        return AuthResponse(
            access_token=access_token,
            user=UserResponse.from_orm(user)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Wallet verification failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Wallet verification failed: {str(e)}"
        )


@router.post("/wallet/link/nonce", response_model=WalletNonceResponse)
async def get_wallet_link_nonce(
    request: WalletNonceRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Generate a nonce for linking a wallet to an existing account.
    Requires authentication.
    """
    try:
        # Verify user is authenticated
        user = await auth_service.get_current_user(credentials.credentials)
        wallet_address = request.wallet_address
        
        # Generate nonce for linking
        nonce = secrets.token_hex(16)
        timestamp = int(time.time())
        
        message = f"Link this wallet to your SocialAnywhere.AI account\n\nWallet: {wallet_address}\nUser: {user.email}\nNonce: {nonce}\nTimestamp: {timestamp}"
        
        # Store with user_id for linking
        wallet_nonces[f"link_{wallet_address}"] = {
            "nonce": nonce,
            "timestamp": timestamp,
            "message": message,
            "user_id": str(user.id),
            "expires": timestamp + 300
        }
        
        return WalletNonceResponse(message=message, nonce=nonce)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate link message"
        )


@router.post("/wallet/link", response_model=AuthResponse)
async def link_wallet_to_account(
    request: WalletVerifyRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Link a wallet to an existing authenticated account.
    """
    try:
        # Verify user is authenticated
        user = await auth_service.get_current_user(credentials.credentials)
        wallet_address = request.wallet_address
        
        # Check stored nonce
        stored = wallet_nonces.get(f"link_{wallet_address}")
        if not stored or stored["nonce"] != request.nonce:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired link request"
            )
        
        if time.time() > stored["expires"]:
            del wallet_nonces[f"link_{wallet_address}"]
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Link request expired"
            )
        
        # Verify signature
        try:
            import base58
            from nacl.signing import VerifyKey
            
            public_key_bytes = base58.b58decode(wallet_address)
            signature_bytes = base58.b58decode(request.signature)
            message_bytes = stored["message"].encode('utf-8')
            
            verify_key = VerifyKey(public_key_bytes)
            verify_key.verify(message_bytes, signature_bytes)
            
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid wallet signature"
            )
        
        # Clean up nonce
        del wallet_nonces[f"link_{wallet_address}"]
        
        # Link wallet to user
        updated_user = await auth_service.link_wallet_to_user(str(user.id), wallet_address)
        
        # Generate new token with updated info
        access_token = auth_service.create_access_token(updated_user.id)
        
        return AuthResponse(
            access_token=access_token,
            user=UserResponse.from_orm(updated_user)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to link wallet: {str(e)}"
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
