"""
Authentication service for Google OAuth integration
Handles user authentication, session management, and user data operations
"""

import os
import uuid
import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import HTTPException, status
from google.auth.transport import requests
from google.oauth2 import id_token
from passlib.context import CryptContext
from database import db_manager
from models import User, UserResponse


class AuthService:
    """Service class for authentication operations"""
    
    def __init__(self):
        self.google_client_id = os.getenv("GOOGLE_CLIENT_ID", "")
        self.jwt_secret = os.getenv("JWT_SECRET", "your-super-secret-jwt-key-change-this-in-production")
        self.jwt_algorithm = "HS256"
        self.jwt_expiration_hours = 24 * 7  # 7 days
        # Password hashing context
        # Try Argon2 first, fallback to bcrypt if Argon2 is not available
        import hashlib
        import base64
        self._hashlib = hashlib
        self._base64 = base64
        self._use_bcrypt_fallback = False  # Initialize to False
        
        try:
            self.pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
            # Test if Argon2 is actually available by trying to hash
            test_hash = self.pwd_context.hash("test")
            # Verify the hash method is callable
            if not callable(self.pwd_context.hash):
                raise Exception("Argon2 hash method is not callable")
            print("✅ Using Argon2 for password hashing")
            self._use_bcrypt_fallback = False
        except Exception as e:
            print(f"⚠️ Argon2 not available ({e}), falling back to bcrypt")
            # Fallback to bcrypt with SHA256 preprocessing to handle long passwords
            self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
            # Test bcrypt works
            test_hash = self.pwd_context.hash("test")
            if not callable(self.pwd_context.hash):
                raise Exception("Bcrypt hash method is not callable")
            self._use_bcrypt_fallback = True
            print("✅ Using bcrypt for password hashing (with SHA256 preprocessing)")
    
    async def verify_google_token(self, token: str) -> Dict[str, Any]:
        """Verify Google OAuth token and extract user information"""
        try:
            print(f"🔍 Verifying Google token with client_id: {self.google_client_id}")
            print(f"🔍 Token length: {len(token)}")
            print(f"🔍 Token (first 50 chars): {token[:50]}...")
            
            # Verify the token
            idinfo = id_token.verify_oauth2_token(
                token, 
                requests.Request(), 
                self.google_client_id,
                clock_skew_in_seconds=60  # tolerate small client/server clock differences
            )
            
            print(f"✅ Token verified successfully for user: {idinfo.get('email')}")
            
            # Extract user information
            user_info = {
                "google_id": idinfo["sub"],
                "email": idinfo["email"],
                "name": idinfo["name"],
                "picture_url": idinfo.get("picture"),
                "email_verified": idinfo.get("email_verified", False)
            }
            
            print(f"📋 User info extracted: {user_info}")
            return user_info
            
        except ValueError as e:
            print(f"❌ Google token verification failed (ValueError): {str(e)}")
            print(f"❌ ValueError type: {type(e).__name__}")
            import traceback
            print(f"❌ Traceback: {traceback.format_exc()}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid Google token: {str(e)}"
            )
        except Exception as e:
            print(f"❌ Unexpected error during token verification: {str(e)}")
            print(f"❌ Exception type: {type(e).__name__}")
            import traceback
            print(f"❌ Traceback: {traceback.format_exc()}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Authentication error: {str(e)}"
            )
    
    async def get_or_create_user(self, user_info: Dict[str, Any]) -> User:
        """Get existing user or create new user from Google info"""
        try:
            # Check if user exists by Google ID (if provided)
            google_id = user_info.get("google_id")
            if google_id:
                query = "SELECT * FROM users WHERE google_id = :google_id"
                existing_user = await db_manager.fetch_one(query, {"google_id": google_id})
            else:
                existing_user = None
            
            if existing_user:
                existing_user = dict(existing_user)
                # Update user info if needed
                user = User(
                    id=existing_user["id"],
                    google_id=existing_user.get("google_id"),  # Can be None for email/password users
                    email=existing_user["email"],
                    name=existing_user["name"],
                    picture_url=existing_user.get("picture_url"),
                    is_active=existing_user["is_active"],
                    created_at=existing_user["created_at"],
                    updated_at=existing_user["updated_at"]
                )
                
                # Update user info if it has changed (only for Google users)
                if google_id and (user.name != user_info["name"] or 
                    user.picture_url != user_info.get("picture_url")):
                    
                    update_query = """
                        UPDATE users 
                        SET name = :name, picture_url = :picture_url, updated_at = NOW()
                        WHERE google_id = :google_id
                    """
                    await db_manager.execute_query(update_query, {
                        "name": user_info["name"],
                        "picture_url": user_info.get("picture_url"),
                        "google_id": google_id
                    })
                
                return user

            # No user found by google_id; check for an existing account with same email (email/password sign-up)
            email = user_info["email"]
            existing_user_by_email = await db_manager.fetch_one(
                "SELECT * FROM users WHERE email = :email",
                {"email": email}
            )

            if existing_user_by_email:
                existing_user_by_email = dict(existing_user_by_email)

                # If google_id missing, attach it so future lookups use google_id
                if not existing_user_by_email.get("google_id"):
                    attach_google_query = """
                        UPDATE users
                        SET google_id = :google_id,
                            name = :name,
                            picture_url = :picture_url,
                            updated_at = NOW()
                        WHERE email = :email
                    """
                    await db_manager.execute_query(attach_google_query, {
                        "google_id": google_id,
                        "name": user_info["name"],
                        "picture_url": user_info.get("picture_url"),
                        "email": email
                    })

                    # Refresh data after update
                    existing_user_by_email = await db_manager.fetch_one(
                        "SELECT * FROM users WHERE email = :email",
                        {"email": email}
                    )
                    existing_user_by_email = dict(existing_user_by_email)

                return User(
                    id=existing_user_by_email["id"],
                    google_id=existing_user_by_email.get("google_id"),
                    email=existing_user_by_email["email"],
                    name=existing_user_by_email["name"],
                    picture_url=existing_user_by_email.get("picture_url"),
                    is_active=existing_user_by_email["is_active"],
                    created_at=existing_user_by_email["created_at"],
                    updated_at=existing_user_by_email["updated_at"]
                )

                # Create new user
                user_id = str(uuid.uuid4())
                insert_query = """
                    INSERT INTO users (id, google_id, email, name, picture_url, is_active)
                    VALUES (:id, :google_id, :email, :name, :picture_url, :is_active)
                """
                
                await db_manager.execute_query(insert_query, {
                    "id": user_id,
                    "google_id": user_info.get("google_id"),  # Can be None for email/password users
                    "email": user_info["email"],
                    "name": user_info["name"],
                    "picture_url": user_info.get("picture_url"),
                    "is_active": True
                })
                
                # Fetch the created user
                query = "SELECT * FROM users WHERE id = :id"
                new_user = await db_manager.fetch_one(query, {"id": user_id})
                new_user = dict(new_user)
                
                return User(
                    id=new_user["id"],
                    google_id=new_user.get("google_id"),  # Can be None for email/password users
                    email=new_user["email"],
                    name=new_user["name"],
                    picture_url=new_user.get("picture_url"),
                    is_active=new_user["is_active"],
                    created_at=new_user["created_at"],
                    updated_at=new_user["updated_at"]
                )
                
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error managing user: {str(e)}"
            )
    
    def create_access_token(self, user_id: str) -> str:
        """Create JWT token for user session"""
        payload = {
            "user_id": str(user_id),
            "exp": datetime.utcnow() + timedelta(hours=self.jwt_expiration_hours),
            "iat": datetime.utcnow()
        }
        
        token = jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)
        return token
    
    def verify_jwt_token(self, token: str) -> Dict[str, Any]:
        """Verify JWT token and return payload"""
        try:
            # Removed verbose logging for successful token verifications to reduce log spam
            payload = jwt.decode(token, self.jwt_secret, algorithms=[self.jwt_algorithm])
            return payload
        except jwt.ExpiredSignatureError as e:
            print(f"❌ JWT token expired: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.InvalidTokenError as e:
            print(f"❌ Invalid JWT token: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        except Exception as e:
            print(f"❌ Unexpected JWT error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Token verification failed: {str(e)}"
            )
    
    async def get_current_user(self, token: str) -> User:
        """Get current user from JWT token"""
        try:
            # Verify the JWT token (logging reduced to prevent spam)
            payload = self.verify_jwt_token(token)
            user_id = payload.get("user_id")
            
            if not user_id:
                print("❌ No user_id in token payload")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token payload"
                )
            
            # Get user from database
            user = await self.get_user_by_id(user_id)
            if not user:
                print(f"❌ User not found in database for user_id: {user_id}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found"
                )
            
            # Only log successful user lookups every 100th time to reduce spam
            # while still providing some visibility into system activity
            import random
            if random.randint(1, 100) == 1:
                print(f"✅ User authenticated: {user.email}")
            
            return user
            
        except HTTPException as e:
            print(f"❌ HTTP Exception in get_current_user: {e.detail}")
            raise e
        except Exception as e:
            print(f"❌ Unexpected error in get_current_user: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Authentication failed: {str(e)}"
            )
    
    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        try:
            query = "SELECT * FROM users WHERE id = :user_id AND is_active = true"
            user_data = self._row_to_dict(await db_manager.fetch_one(query, {"user_id": user_id}))
            
            if user_data:
                return User(
                    id=user_data["id"],
                    google_id=user_data["google_id"] if "google_id" in user_data else None,
                    email=user_data["email"],
                    name=user_data["name"],
                    picture_url=user_data["picture_url"] if "picture_url" in user_data else None,
                    is_active=user_data["is_active"],
                    created_at=user_data["created_at"],
                    updated_at=user_data["updated_at"]
                )
            return None
            
        except Exception as e:
            import traceback
            print(f"Error getting user by ID: {e}")
            print(traceback.format_exc())
            return None
    
    async def get_user_by_token(self, token: str) -> Optional[User]:
        """Get user from JWT token"""
        try:
            payload = self.verify_jwt_token(token)
            user_id = payload.get("user_id")
            
            if user_id:
                return await self.get_user_by_id(user_id)
            return None
            
        except HTTPException:
            return None
        except Exception as e:
            print(f"Error getting user by token: {e}")
            return None
    
    def hash_password(self, password: str) -> str:
        """Hash a password using Argon2 (or bcrypt fallback)."""
        try:
            if self._use_bcrypt_fallback:
                print("🔐 hash_password: using bcrypt fallback")
                # Bcrypt has a 72-byte limit, so we hash with SHA256 first
                password_bytes = password.encode('utf-8')
                sha256_digest = self._hashlib.sha256(password_bytes).digest()  # 32 bytes
                sha256_base64 = self._base64.b64encode(sha256_digest).decode('utf-8')  # 44 chars
                hash_fn = getattr(self.pwd_context, "hash", None)
                print(f"   hash_fn type: {type(hash_fn)}")
                if not callable(hash_fn):
                    raise Exception("pwd_context.hash is not callable (bcrypt fallback)")
                result = hash_fn(sha256_base64)
                print("   bcrypt hash generated successfully")
                return result
            else:
                print("🔐 hash_password: using Argon2")
                hash_fn = getattr(self.pwd_context, "hash", None)
                print(f"   hash_fn type: {type(hash_fn)}")
                if not callable(hash_fn):
                    raise Exception("pwd_context.hash is not callable (Argon2)")
                result = hash_fn(password)
                print("   Argon2 hash generated successfully")
                return result
        except Exception as e:
            print(f"❌ Error in hash_password: {e}")
            print(f"   _use_bcrypt_fallback: {self._use_bcrypt_fallback}")
            print(f"   pwd_context type: {type(self.pwd_context)}")
            print(f"   pwd_context.hash type: {type(getattr(self.pwd_context, 'hash', None))}")
            raise
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against a hash"""
        if self._use_bcrypt_fallback:
            # Hash the plain password with SHA256 first, then verify against bcrypt hash
            password_bytes = plain_password.encode('utf-8')
            sha256_digest = self._hashlib.sha256(password_bytes).digest()  # 32 bytes
            sha256_base64 = self._base64.b64encode(sha256_digest).decode('utf-8')  # 44 chars
            return self.pwd_context.verify(sha256_base64, hashed_password)
        else:
            return self.pwd_context.verify(plain_password, hashed_password)

    def _row_to_dict(self, row):
        """Safely convert DB row/record to a plain dict for consistent access."""
        if row is None:
            return None
        if isinstance(row, dict):
            return row
        try:
            return dict(row)
        except Exception:
            try:
                return dict(getattr(row, "_mapping", {}))
            except Exception:
                return row
    
    async def register_user(self, email: str, password: str, name: str) -> User:
        """Register a new user with email and password"""
        try:
            print(f"🆕 register_user: email={email}, name={name}")
            # Check if user already exists
            query = "SELECT * FROM users WHERE email = :email"
            print("   Fetching existing user")
            existing_user = await db_manager.fetch_one(query, {"email": email})
            
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered"
                )
            
            # Hash password
            print("   Hashing password")
            password_hash = self.hash_password(password)
            print("   Password hash generated")
            
            # Create new user
            user_id = str(uuid.uuid4())
            insert_query = """
                INSERT INTO users (id, email, name, password_hash, is_active)
                VALUES (:id, :email, :name, :password_hash, :is_active)
                RETURNING id, google_id, email, name, picture_url, is_active, created_at, updated_at
            """
            print("   Inserting user into database with RETURNING clause")
            new_user = await db_manager.fetch_one(insert_query, {
                "id": user_id,
                "email": email,
                "name": name,
                "password_hash": password_hash,
                "is_active": True
            })
            if not new_user:
                raise Exception("Failed to fetch inserted user record")
            # Ensure we can safely access optional columns such as google_id using dict semantics
            if not isinstance(new_user, dict):
                new_user = dict(new_user)
            print(f"✅ register_user: user created with id={user_id}")
            
            return User(
                id=new_user["id"],
                google_id=new_user.get("google_id"),
                email=new_user["email"],
                name=new_user["name"],
                picture_url=new_user.get("picture_url"),
                is_active=new_user["is_active"],
                created_at=new_user["created_at"],
                updated_at=new_user["updated_at"]
            )
            
        except HTTPException:
            raise
        except Exception as e:
            import traceback
            print(f"❌ Error registering user: {e}")
            print(traceback.format_exc())
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error registering user: {str(e)}"
            )
    
    async def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """Authenticate user with email and password"""
        try:
            # Get user by email
            print(f"🔎 authenticate_user: email={email}")
            query = "SELECT * FROM users WHERE email = :email AND is_active = true"
            user_data = self._row_to_dict(await db_manager.fetch_one(query, {"email": email}))
            print(f"   user_data found: {bool(user_data)}")
            
            if not user_data:
                print("   No user with this email")
                return None
            
            # Check if user has password_hash (email/password user)
            password_hash = user_data["password_hash"] if user_data and "password_hash" in user_data else None
            if not password_hash:
                # User registered with Google OAuth only
                print("   password_hash missing (likely Google-only user)")
                return None
            
            # Verify password
            try:
                print(f"   Verifying password (fallback={getattr(self, '_use_bcrypt_fallback', False)}), hash_prefix={password_hash[:15] if password_hash else None}")
                ok = self.verify_password(password, password_hash)
                print(f"   verify result: {ok}")
            except Exception as e:
                print(f"   ❌ verify_password threw: {e}")
                ok = False
            if not ok:
                print("   Password verification failed")
                return None
            
            print("   Password verified, building User model")
            return User(
                id=user_data["id"],
                google_id=user_data.get("google_id"),
                email=user_data["email"],
                name=user_data["name"],
                picture_url=user_data.get("picture_url"),
                is_active=user_data["is_active"],
                created_at=user_data["created_at"],
                updated_at=user_data["updated_at"]
            )
            
        except Exception as e:
            import traceback
            print(f"Error authenticating user: {e}")
            print(traceback.format_exc())
            return None
    
    async def delete_user_account(self, user_id: str) -> bool:
        """Delete user account and all associated data"""
        try:
            # Delete all user-related data in the correct order (respecting foreign key constraints)
            
            # 1. Delete calendar events
            await db_manager.execute_query(
                "DELETE FROM calendar_events WHERE user_id = :user_id",
                {"user_id": user_id}
            )
            
            # 2. Delete batch operations
            await db_manager.execute_query(
                "DELETE FROM batch_operations WHERE user_id = :user_id",
                {"user_id": user_id}
            )
            
            # 3. Delete posting schedules (via posts)
            await db_manager.execute_query(
                "DELETE FROM posting_schedules WHERE post_id IN (SELECT id FROM posts WHERE user_id = :user_id)",
                {"user_id": user_id}
            )
            
            # 4. Delete captions (via posts)
            await db_manager.execute_query(
                "DELETE FROM captions WHERE post_id IN (SELECT id FROM posts WHERE user_id = :user_id)",
                {"user_id": user_id}
            )
            
            # 5. Delete images (via posts)
            await db_manager.execute_query(
                "DELETE FROM images WHERE post_id IN (SELECT id FROM posts WHERE user_id = :user_id)",
                {"user_id": user_id}
            )
            
            # 6. Delete posts
            await db_manager.execute_query(
                "DELETE FROM posts WHERE user_id = :user_id",
                {"user_id": user_id}
            )
            
            # 7. Delete campaigns
            await db_manager.execute_query(
                "DELETE FROM campaigns WHERE user_id = :user_id",
                {"user_id": user_id}
            )
            
            # 8. Finally, delete the user
            await db_manager.execute_query(
                "DELETE FROM users WHERE id = :user_id",
                {"user_id": user_id}
            )
            
            print(f"Successfully deleted user account: {user_id}")
            return True
            
        except Exception as e:
            print(f"Error deleting user account: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete user account: {str(e)}"
            )
    
    # ============================================
    # SOLANA WALLET AUTHENTICATION METHODS
    # ============================================
    
    async def get_or_create_wallet_user(self, wallet_address: str) -> User:
        """Get existing user by wallet address or create a new user"""
        try:
            # Check if user exists by wallet address
            query = "SELECT * FROM users WHERE wallet_address = :wallet_address AND is_active = true"
            existing_user = self._row_to_dict(await db_manager.fetch_one(query, {"wallet_address": wallet_address}))
            
            if existing_user:
                print(f"✅ Found existing wallet user: {wallet_address[:8]}...{wallet_address[-4:]}")
                return User(
                    id=existing_user["id"],
                    google_id=existing_user.get("google_id"),
                    email=existing_user.get("email"),
                    name=existing_user.get("name"),
                    picture_url=existing_user.get("picture_url"),
                    wallet_address=existing_user.get("wallet_address"),
                    is_active=existing_user["is_active"],
                    created_at=existing_user["created_at"],
                    updated_at=existing_user["updated_at"]
                )
            
            # Create new user with wallet
            user_id = str(uuid.uuid4())
            # Generate a display name from wallet address
            display_name = f"Wallet {wallet_address[:4]}...{wallet_address[-4:]}"
            
            insert_query = """
                INSERT INTO users (id, name, wallet_address, is_active)
                VALUES (:id, :name, :wallet_address, :is_active)
                RETURNING id, google_id, email, name, picture_url, wallet_address, is_active, created_at, updated_at
            """
            
            new_user = await db_manager.fetch_one(insert_query, {
                "id": user_id,
                "name": display_name,
                "wallet_address": wallet_address,
                "is_active": True
            })
            
            if not new_user:
                raise Exception("Failed to create wallet user")
            
            new_user = self._row_to_dict(new_user)
            print(f"✅ Created new wallet user: {wallet_address[:8]}...{wallet_address[-4:]}")
            
            return User(
                id=new_user["id"],
                google_id=new_user.get("google_id"),
                email=new_user.get("email"),
                name=new_user["name"],
                picture_url=new_user.get("picture_url"),
                wallet_address=new_user.get("wallet_address"),
                is_active=new_user["is_active"],
                created_at=new_user["created_at"],
                updated_at=new_user["updated_at"]
            )
            
        except HTTPException:
            raise
        except Exception as e:
            print(f"❌ Error in get_or_create_wallet_user: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to authenticate wallet: {str(e)}"
            )
    
    async def link_wallet_to_user(self, user_id: str, wallet_address: str) -> User:
        """Link a wallet address to an existing user account"""
        try:
            # Check if wallet is already linked to another account
            check_query = "SELECT id FROM users WHERE wallet_address = :wallet_address AND id != :user_id"
            existing = await db_manager.fetch_one(check_query, {
                "wallet_address": wallet_address,
                "user_id": user_id
            })
            
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="This wallet is already linked to another account"
                )
            
            # Update user with wallet address
            update_query = """
                UPDATE users 
                SET wallet_address = :wallet_address, updated_at = NOW()
                WHERE id = :user_id
                RETURNING id, google_id, email, name, picture_url, wallet_address, is_active, created_at, updated_at
            """
            
            updated_user = await db_manager.fetch_one(update_query, {
                "wallet_address": wallet_address,
                "user_id": user_id
            })
            
            if not updated_user:
                raise Exception("Failed to link wallet to user")
            
            updated_user = self._row_to_dict(updated_user)
            print(f"✅ Linked wallet {wallet_address[:8]}...{wallet_address[-4:]} to user {user_id}")
            
            return User(
                id=updated_user["id"],
                google_id=updated_user.get("google_id"),
                email=updated_user.get("email"),
                name=updated_user["name"],
                picture_url=updated_user.get("picture_url"),
                wallet_address=updated_user.get("wallet_address"),
                is_active=updated_user["is_active"],
                created_at=updated_user["created_at"],
                updated_at=updated_user["updated_at"]
            )
            
        except HTTPException:
            raise
        except Exception as e:
            print(f"❌ Error linking wallet: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to link wallet: {str(e)}"
            )
    
    async def get_user_by_wallet(self, wallet_address: str) -> Optional[User]:
        """Get user by wallet address"""
        try:
            query = "SELECT * FROM users WHERE wallet_address = :wallet_address AND is_active = true"
            user_data = self._row_to_dict(await db_manager.fetch_one(query, {"wallet_address": wallet_address}))
            
            if user_data:
                return User(
                    id=user_data["id"],
                    google_id=user_data.get("google_id"),
                    email=user_data.get("email"),
                    name=user_data["name"],
                    picture_url=user_data.get("picture_url"),
                    wallet_address=user_data.get("wallet_address"),
                    is_active=user_data["is_active"],
                    created_at=user_data["created_at"],
                    updated_at=user_data["updated_at"]
                )
            return None
            
        except Exception as e:
            print(f"Error getting user by wallet: {e}")
            return None


# Global auth service instance
auth_service = AuthService()

# Verify the instance is properly initialized
if not hasattr(auth_service, 'pwd_context') or not callable(auth_service.pwd_context.hash):
    print("⚠️ WARNING: auth_service pwd_context not properly initialized!")
    # Try to reinitialize
    try:
        auth_service.__init__()
        print("✅ auth_service reinitialized successfully")
    except Exception as e:
        print(f"❌ Failed to reinitialize auth_service: {e}")
else:
    print("✅ auth_service global instance initialized successfully")
