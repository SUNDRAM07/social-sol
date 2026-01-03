from fastapi import APIRouter, HTTPException, status, Request, Header
from pydantic import BaseModel, validator
from typing import Dict, Optional, Any
import asyncio
from datetime import datetime
import os
 
# Import platform adapters
from facebook_manager import facebook_manager
from twitter_adapter import TwitterAdapter  
from reddit_service import reddit_service
from reddit_oauth_helper import get_reddit_auth_url, exchange_code_for_tokens, get_reddit_user_info
from linkedin_service import linkedin_service
from linkedin_oauth_helper import get_linkedin_auth_url, exchange_code_for_tokens as exchange_linkedin_code, get_linkedin_user_info
from env_manager import env_manager
from fastapi.responses import RedirectResponse, HTMLResponse
import secrets
from trending_topics_service import TrendingTopicsService
 
router = APIRouter(prefix="/social-media", tags=["social-media"])
 
class PlatformCredentials(BaseModel):
    """Model for platform credentials"""
    credentials: Dict[str, str]
   
    class Config:
        # Allow extra fields for flexibility
        extra = "allow"
 
class ConnectionResponse(BaseModel):
    success: bool
    connected: bool
    message: str
    error: Optional[str] = None

class OAuth2Response(BaseModel):
    auth_url: str
    success: bool = True
    message: str = "OAuth2 flow initiated"
 
class StatusResponse(BaseModel):
    connected: bool
    has_credentials: bool
    platform: str
    last_checked: str
    details: Optional[Dict[str, Any]] = None

class TopicDetailsRequest(BaseModel):
    topic: str
    category: str

class TopicDetailsResponse(BaseModel):
    success: bool
    overview: Optional[str] = None
    key_points: Optional[list] = None
    related_topics: Optional[list] = None
    error: Optional[str] = None

# Initialize trending topics service
trending_topics_service = TrendingTopicsService()

@router.post("/trending/topic-details", response_model=TopicDetailsResponse)
async def get_topic_details(request: TopicDetailsRequest):
    """Get detailed information about a trending topic using Groq API"""
    try:
        details = trending_topics_service.get_topic_details(request.topic, request.category)
        return {
            "success": True,
            "overview": details.get("overview"),
            "key_points": details.get("key_points"),
            "related_topics": details.get("related_topics")
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
 
FACEBOOK_APP_ID = os.getenv("FACEBOOK_APP_ID")
FACEBOOK_APP_SECRET = os.getenv("FACEBOOK_APP_SECRET")

# Instagram Business Login with Instagram Login app credentials.
# Prefer dedicated Instagram app ID/secret if set; fall back to Facebook app as a convenience.
INSTAGRAM_APP_ID = os.getenv("INSTAGRAM_APP_ID", FACEBOOK_APP_ID)
INSTAGRAM_APP_SECRET = os.getenv("INSTAGRAM_APP_SECRET", FACEBOOK_APP_SECRET)

# Use environment variable or construct from PUBLIC_DOMAIN
public_domain = os.getenv("PUBLIC_DOMAIN", "localhost:8000")
use_https = os.getenv("USE_HTTPS", "false").lower() == "true"
scheme = "https" if (use_https or public_domain != "localhost:8000") else "http"

FACEBOOK_REDIRECT_URI = os.getenv("FACEBOOK_REDIRECT_URI")
if not FACEBOOK_REDIRECT_URI:
    if use_https and ":" not in public_domain:
        domain_with_port = public_domain
    elif ":" in public_domain:
        domain_with_port = public_domain
    else:
        port = os.getenv("PORT", "8000")
        domain_with_port = f"{public_domain}:{port}"
    FACEBOOK_REDIRECT_URI = f"{scheme}://{domain_with_port}/socialanywhere/social-media/facebook/callback"

# Redirect URI for Instagram Business Login with Instagram Login
INSTAGRAM_REDIRECT_URI = os.getenv("INSTAGRAM_REDIRECT_URI")
if not INSTAGRAM_REDIRECT_URI:
    if use_https and ":" not in public_domain:
        domain_with_port = public_domain
    elif ":" in public_domain:
        domain_with_port = public_domain
    else:
        port = os.getenv("PORT", "8000")
        domain_with_port = f"{public_domain}:{port}"
    INSTAGRAM_REDIRECT_URI = f"{scheme}://{domain_with_port}/socialanywhere/social-media/instagram/callback"
 
# Platform connection testers
async def test_facebook_connection(user_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Test Facebook connection using database accounts.
    If user_id is provided, test all Facebook pages for that user from database.
    Only returns connected=True if accounts exist in database.
    """
    try:
        from database_service import db_service
        
        pages = []
        if user_id:
            # Get Facebook pages from unified database table (active only)
            pages = await db_service.get_social_media_accounts(user_id, platform="facebook", active_only=True)
            if not pages:
                return {"connected": False, "error": f"No active Facebook pages found for user {user_id}"}
        else:
            # Without user_id, we can't check database, so return not connected
            return {"connected": False, "error": "User ID required to check Facebook connection"}

        if not pages or len(pages) == 0:
            return {"connected": False, "error": "No Facebook pages found"}

        # Quick test first page token
        import requests
        page_id_to_test = pages[0].get("account_id") or pages[0].get("page_id")
        access_token_to_test = pages[0].get("access_token")
        
        if not page_id_to_test or not access_token_to_test:
            return {"connected": False, "error": "Missing page ID or access token"}
        
        test_resp = requests.get(
            f"https://graph.facebook.com/v19.0/{page_id_to_test}",
            params={"access_token": access_token_to_test},
            timeout=10
        )
        connected = test_resp.status_code == 200

        return {
            "connected": connected,
            "details": {"pages": pages, "test_first_page": connected, "page_id": page_id_to_test, "account_count": len(pages)}
        }

    except Exception as e:
        print(f"❌ Error testing Facebook connection: {e}")
        return {"connected": False, "error": str(e)}
 
 
async def test_twitter_connection(user_id: Optional[str] = None) -> Dict[str, Any]:
    """Test Twitter connection using database accounts or env vars"""
    try:
        from database_service import db_service
        
        accounts = []
        if user_id:
            # Get Twitter accounts from unified database table
            accounts = await db_service.get_social_media_accounts(user_id, platform="twitter")
            if accounts:
                # Test connection with database account
                # Get credentials from metadata
                account = accounts[0]
                metadata = account.get("metadata", {})
                consumer_key = metadata.get("consumer_key") or os.getenv('TWITTER_CONSUMER_KEY')
                consumer_secret = metadata.get("consumer_secret") or os.getenv('TWITTER_CONSUMER_SECRET')
                access_token = account.get("access_token") or os.getenv('TWITTER_ACCESS_TOKEN')
                access_token_secret = metadata.get("refresh_token") or os.getenv('TWITTER_ACCESS_TOKEN_SECRET')
                
                if all([consumer_key, consumer_secret, access_token, access_token_secret]):
                    # Temporarily set env vars for testing
                    original_env = {}
                    for key, value in [
                        ('TWITTER_CONSUMER_KEY', consumer_key),
                        ('TWITTER_CONSUMER_SECRET', consumer_secret),
                        ('TWITTER_ACCESS_TOKEN', access_token),
                        ('TWITTER_ACCESS_TOKEN_SECRET', access_token_secret)
                    ]:
                        original_env[key] = os.getenv(key)
                        os.environ[key] = value
                    
                    try:
                        twitter_adapter = TwitterAdapter()
                        test_result = twitter_adapter.test_connection()
                        if test_result.get("status") == "connected":
                            return {"connected": True, "details": test_result}
                        else:
                            return {"connected": False, "error": "Twitter credentials invalid"}
                    finally:
                        # Restore original env vars
                        for key, value in original_env.items():
                            if value is None:
                                os.environ.pop(key, None)
                            else:
                                os.environ[key] = value
                else:
                    return {"connected": False, "error": "Twitter credentials incomplete in database"}
            
            # Fallback to env vars for backwards compatibility
            consumer_key = os.getenv('TWITTER_CONSUMER_KEY')
            consumer_secret = os.getenv('TWITTER_CONSUMER_SECRET')
            access_token = os.getenv('TWITTER_ACCESS_TOKEN')
            access_token_secret = os.getenv('TWITTER_ACCESS_TOKEN_SECRET')
            if all([consumer_key, consumer_secret, access_token, access_token_secret]):
                # Test connection
                twitter_adapter = TwitterAdapter()
                test_result = twitter_adapter.test_connection()
                if test_result.get("status") == "connected":
                    return {"connected": True, "details": test_result}
                else:
                    return {"connected": False, "error": "Twitter credentials invalid"}
            else:
                return {"connected": False, "error": f"No Twitter accounts found for user {user_id}"}
        else:
            # Fallback to env vars
            creds = env_manager.check_platform_credentials('twitter')
            if not creds['has_credentials']:
                return {"connected": False, "error": "Missing required credentials"}
           
            # Use existing TwitterAdapter to test connection
            twitter_adapter = TwitterAdapter()
            test_result = twitter_adapter.test_connection()
            
            if test_result.get("status") == "connected":
                return {
                    "connected": True,
                    "details": test_result
                }
            else:
                return {"connected": False, "error": "Twitter connection test failed"}
       
    except Exception as e:
        return {"connected": False, "error": str(e)}
 
async def test_reddit_connection(user_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Test Reddit connection using database accounts.
    If user_id is provided, test all Reddit accounts for that user from database.
    Only returns connected=True if accounts exist in database.
    """
    try:
        from database_service import db_service
        
        accounts = []
        if user_id:
            # Get Reddit accounts from unified database table (active only)
            accounts = await db_service.get_social_media_accounts(user_id, platform="reddit", active_only=True)
            if not accounts:
                return {"connected": False, "error": f"No active Reddit accounts found for user {user_id}"}
        else:
            # Without user_id, we can't check database, so return not connected
            return {"connected": False, "error": "User ID required to check Reddit connection"}
        
        if not accounts or len(accounts) == 0:
            return {"connected": False, "error": "No Reddit accounts found"}
        
        # Test first account connection
        import requests
        access_token_to_test = accounts[0].get("access_token")
        
        if not access_token_to_test:
            return {"connected": False, "error": "Missing access token"}
        
        test_resp = requests.get(
            "https://oauth.reddit.com/api/v1/me",
            headers={
                "Authorization": f"Bearer {access_token_to_test}",
                "User-Agent": os.getenv('REDDIT_USER_AGENT', 'SocialMediaAgent/1.0')
            },
            timeout=10
        )
        connected = test_resp.status_code == 200
        
        return {
            "connected": connected,
            "details": {"accounts": accounts, "test_first_account": connected, "account_count": len(accounts)}
        }
       
    except Exception as e:
        print(f"❌ Error testing Reddit connection: {e}")
        return {"connected": False, "error": str(e)}


async def test_linkedin_connection(user_id: Optional[str] = None) -> Dict[str, Any]:
    """Test LinkedIn connection"""
    try:
        result = linkedin_service.test_connection()
        return {
            "connected": result.get("status") == "connected",
            "details": result
        }
    except Exception as e:
        return {"connected": False, "error": str(e)}
   
 
async def test_instagram_connection(user_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Test Instagram connection using database accounts.
    If user_id is provided, test all Instagram accounts for that user from database.
    Only returns connected=True if accounts exist in database.
    """
    try:
        from database_service import db_service
        
        accounts = []
        if user_id:
            # Get accounts from unified database table (active only)
            accounts = await db_service.get_social_media_accounts(user_id, platform="instagram", active_only=True)
            if not accounts:
                return {"connected": False, "error": f"No active Instagram accounts found for user {user_id}"}
        else:
            # Without user_id, we can't check database, so return not connected
            return {"connected": False, "error": "User ID required to check Instagram connection"}

        if not accounts or len(accounts) == 0:
            return {"connected": False, "error": "No Instagram accounts found"}

        # Quick test first account using Instagram Graph API with Instagram Login
        import requests
        account_id_to_test = str(accounts[0].get("account_id") or accounts[0].get("instagram_account_id"))
        access_token_to_test = accounts[0].get("access_token")
        
        if not account_id_to_test or not access_token_to_test:
            return {"connected": False, "error": "Missing account ID or access token"}
        
        test_resp = requests.get(
            f"https://graph.instagram.com/{account_id_to_test}",
            params={"fields": "id,username", "access_token": access_token_to_test},
            timeout=10
        )
        connected = test_resp.status_code == 200

        return {
            "connected": connected,
            "details": {
                "accounts": accounts,
                "test_first_account": connected,
                "account_id": account_id_to_test,
                "account_count": len(accounts)
            }
        }

    except Exception as e:
        print(f"❌ Error testing Instagram connection: {e}")
        return {"connected": False, "error": str(e)}
 
 
# API Routes
 
@router.get("/{platform}/status", response_model=StatusResponse)
async def get_platform_status(platform: str, authorization: Optional[str] = Header(None)):
    """Get connection status for a social media platform"""
    if platform not in ["facebook", "instagram", "twitter", "reddit", "linkedin"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported platform: {platform}"
        )
   
    # Try to get user_id from authorization header (if authenticated)
    user_id = None
    try:
        from auth_service import auth_service
        from database_service import db_service
        if authorization and authorization.startswith("Bearer "):
            token = authorization.replace("Bearer ", "")
            current_user = await auth_service.get_current_user(token)
            user_id = str(current_user.id) if current_user else None
    except:
        pass  # If auth fails, continue without user_id
   
    # Test connection based on platform, passing user_id if available
    connection_testers = {
        "facebook": test_facebook_connection,
        "instagram": test_instagram_connection,
        "twitter": test_twitter_connection,
        "reddit": test_reddit_connection,
        "linkedin": test_linkedin_connection
    }
   
    try:
        result = await connection_testers[platform](user_id)
        creds_check = env_manager.check_platform_credentials(platform)
        
        # Get account details if user is authenticated
        accounts_list = []
        if user_id:
            try:
                from database_service import db_service
                accounts = await db_service.get_social_media_accounts(user_id, platform=platform, active_only=True)
                for account in accounts:
                    accounts_list.append({
                        "id": str(account.get("id")),
                        "account_id": account.get("account_id"),
                        "username": account.get("username"),
                        "display_name": account.get("display_name"),
                        "is_primary": account.get("is_primary", False)
                    })
            except:
                pass  # If we can't get accounts, continue without them
       
        details = result.get("details", {})
        details["accounts"] = accounts_list
        details["account_count"] = len(accounts_list)
       
        return StatusResponse(
            connected=result.get("connected", False),
            has_credentials=creds_check["has_credentials"],
            platform=platform,
            last_checked=datetime.now().isoformat(),
            details=details
        )
       
    except Exception as e:
        return StatusResponse(
            connected=False,
            has_credentials=False,
            platform=platform,
            last_checked=datetime.now().isoformat(),
            details={"error": str(e)}
        )
 
@router.post("/{platform}/connect")
async def connect_platform(
    platform: str, 
    credentials: Dict[str, str] = {}, 
    authorization: Optional[str] = Header(None)
):
    """Connect to a social media platform by saving credentials"""
    if platform not in ["facebook", "instagram", "twitter", "reddit", "linkedin"]:
        raise HTTPException(status_code=400, detail=f"Unsupported platform: {platform}")

    try:
        # Try to get user_id from authorization header (if authenticated)
        user_id = None
        try:
            from auth_service import auth_service
            if authorization and authorization.startswith("Bearer "):
                token = authorization.replace("Bearer ", "")
                current_user = await auth_service.get_current_user(token)
                user_id = str(current_user.id) if current_user else None
        except:
            pass  # If auth fails, continue without user_id
        
        if not user_id:
            raise HTTPException(status_code=401, detail="User not authenticated. Please sign in again before connecting a platform.")
        
        # Encode user_id in state parameter for OAuth callbacks
        import base64
        import json
        state_data = {"user_id": user_id}
        state_encoded = base64.urlsafe_b64encode(json.dumps(state_data).encode()).decode()
        
        # ----- FACEBOOK FLOW -----
        if platform == "facebook":
            if not FACEBOOK_APP_ID or not FACEBOOK_APP_SECRET:
                raise HTTPException(status_code=400, detail="Facebook App ID and Secret must be configured in environment variables")
            
            from urllib.parse import quote_plus
            redirect_uri_encoded = quote_plus(FACEBOOK_REDIRECT_URI)
            
            # Log redirect URI for debugging
            print(f"🔗 Facebook OAuth Redirect URI: {FACEBOOK_REDIRECT_URI}")
            print(f"📝 Make sure this URL is added to Facebook App Settings > Basic > App Domains")
            print(f"📝 And also add to Settings > Basic > Valid OAuth Redirect URIs")
            
            auth_url = (
                f"https://www.facebook.com/v19.0/dialog/oauth?"
                f"client_id={FACEBOOK_APP_ID}&redirect_uri={redirect_uri_encoded}"
                f"&scope=pages_show_list,pages_read_engagement,pages_manage_posts"
                f"&response_type=code&state={state_encoded}"
            )
            return OAuth2Response(auth_url=auth_url)

        # ----- INSTAGRAM FLOW (STATIC CREDENTIALS - MANUAL ENTRY) -----
        # NOTE: Instagram now uses static credential entry instead of OAuth
        # Users manually enter Access Token and Account ID from their Instagram Business account
        if platform == "instagram":
            # Return a special response indicating static credential entry is required
            # Frontend will show a modal form for manual credential input
            raise HTTPException(
                status_code=400,
                detail="INSTAGRAM_STATIC_FLOW: Please use manual credential entry for Instagram"
            )
        
        # ----- INSTAGRAM FLOW (Instagram Business Login with Instagram Login) ----- [DISABLED - COMMENTED OUT]
        # if platform == "instagram":
        #     # Use Instagram App credentials as per
        #     # https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/business-login/
        #     if not INSTAGRAM_APP_ID or not INSTAGRAM_APP_SECRET:
        #         raise HTTPException(
        #             status_code=400,
        #             detail="Instagram App ID and Secret must be configured in environment variables (INSTAGRAM_APP_ID, INSTAGRAM_APP_SECRET)."
        #         )
        #
        #     from urllib.parse import quote_plus
        #     redirect_uri_encoded = quote_plus(INSTAGRAM_REDIRECT_URI)
        #
        #     # Log redirect URI for debugging
        #     print(f"🔗 Instagram Business Login Redirect URI: {INSTAGRAM_REDIRECT_URI}")
        #     print("📝 Make sure this URL is added to Instagram > API setup with Instagram login > Business login settings > OAuth redirect URIs")
        #
        #     # Request Instagram Business Login scopes (new names, see docs)
        #     scopes = [
        #         "instagram_business_basic",
        #         "instagram_business_content_publish",
        #         "instagram_business_manage_messages",
        #         "instagram_business_manage_comments",
        #     ]
        #     scope_param = ",".join(scopes)
        #
        #     auth_url = (
        #         "https://www.instagram.com/oauth/authorize"
        #         f"?client_id={INSTAGRAM_APP_ID}"
        #         f"&redirect_uri={redirect_uri_encoded}"
        #         f"&response_type=code"
        #         f"&scope={scope_param}"
        #         f"&state={state_encoded}"
        #     )
        #     return OAuth2Response(auth_url=auth_url)
        
        # ----- REDDIT FLOW -----
        if platform == "reddit":
            from reddit_oauth_helper import REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET
            if not REDDIT_CLIENT_ID or not REDDIT_CLIENT_SECRET:
                raise HTTPException(
                    status_code=400, 
                    detail="Reddit Client ID and Client Secret must be configured in environment variables. Please set REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET in your .env file."
                )
            
            # Encode user_id in state parameter
            import base64
            import json
            state_data = {"user_id": user_id, "csrf": secrets.token_urlsafe(16)}
            state_encoded = base64.urlsafe_b64encode(json.dumps(state_data).encode()).decode()
            auth_url = get_reddit_auth_url(state_encoded)
            return OAuth2Response(auth_url=auth_url)
        
        # ----- LINKEDIN FLOW -----
        if platform == "linkedin":
            # Generate random state for CSRF protection
            state = secrets.token_urlsafe(32)
            auth_url = get_linkedin_auth_url(state)
            return OAuth2Response(auth_url=auth_url)
 
        # ----- TWITTER FLOW (OAuth 2.0 with PKCE) -----
        if platform == "twitter":
            from twitter_oauth_helper import TWITTER_CLIENT_ID, get_twitter_auth_url, generate_code_verifier
            if not TWITTER_CLIENT_ID:
                raise HTTPException(status_code=400, detail="Twitter Client ID must be configured in environment variables")
            
            # Generate code verifier for PKCE
            code_verifier = generate_code_verifier()
            
            # Encode user_id and code_verifier in state parameter
            import base64
            import json
            state_data = {
                "user_id": user_id,
                "csrf": secrets.token_urlsafe(16),
                "code_verifier": code_verifier  # Store verifier for token exchange
            }
            state_encoded = base64.urlsafe_b64encode(json.dumps(state_data).encode()).decode()
            
            auth_url, _ = get_twitter_auth_url(state_encoded, code_verifier)
            return OAuth2Response(auth_url=auth_url)
        
        # ----- TWITTER FLOW (Manual Credentials - Fallback) -----
        if platform == "twitter_manual":
            required_fields = ["TWITTER_CONSUMER_KEY", "TWITTER_CONSUMER_SECRET",
                              "TWITTER_ACCESS_TOKEN", "TWITTER_ACCESS_TOKEN_SECRET",
                              "TWITTER_BEARER_TOKEN", "TWITTER_CLIENT_ID", "TWITTER_CLIENT_SECRET", "TWITTER_USERNAME"]
            missing_fields = [f for f in required_fields if f not in credentials or not credentials[f].strip()]
            if missing_fields:
                raise HTTPException(status_code=400, detail=f"Missing required fields: {', '.join(missing_fields)}")
            
            # Get Twitter user info to get account_id
            from database_service import db_service
            import requests
            from twitter_adapter import TwitterAdapter
            
            # Temporarily set env vars for testing
            original_env = {}
            for key in required_fields:
                original_env[key] = os.getenv(key)
                os.environ[key] = credentials[key]
            
            try:
                # Test connection with provided credentials using TwitterAdapter directly
                twitter_adapter = TwitterAdapter()
                test_result = twitter_adapter.test_connection()
                if test_result.get("status") != "connected":
                    raise HTTPException(status_code=400, detail=f"Twitter connection test failed: {test_result.get('error', 'Invalid credentials')}")
            finally:
                # Restore original env vars
                for key, value in original_env.items():
                    if value is None:
                        os.environ.pop(key, None)
                    else:
                        os.environ[key] = value
            
            try:
                # Use Twitter API to get user info
                twitter_username = credentials.get("TWITTER_USERNAME", "")
                # For Twitter, we'll use the username as account_id if we can't get user_id from API
                account_id = twitter_username
                
                # Try to get user_id from Twitter API
                bearer_token = credentials.get("TWITTER_BEARER_TOKEN")
                if bearer_token:
                    try:
                        user_resp = requests.get(
                            "https://api.twitter.com/2/users/by/username/" + twitter_username,
                            headers={"Authorization": f"Bearer {bearer_token}"},
                            timeout=10
                        )
                        if user_resp.status_code == 200:
                            user_data = user_resp.json()
                            account_id = user_data.get("data", {}).get("id", twitter_username)
                    except:
                        pass  # Fallback to username
                
                # Save to unified database table
                await db_service.save_social_media_account(
                    user_id=user_id or "demo_user_123",
                    platform="twitter",
                    account_id=account_id,
                    access_token=credentials.get("TWITTER_ACCESS_TOKEN"),
                    username=twitter_username,
                    display_name=twitter_username,
                    refresh_token=credentials.get("TWITTER_ACCESS_TOKEN_SECRET"),  # Store as refresh_token
                    expires_at=None,  # Twitter tokens don't expire by default
                    metadata={
                        "consumer_key": credentials.get("TWITTER_CONSUMER_KEY"),
                        "consumer_secret": credentials.get("TWITTER_CONSUMER_SECRET"),
                        "bearer_token": credentials.get("TWITTER_BEARER_TOKEN"),
                        "client_id": credentials.get("TWITTER_CLIENT_ID"),
                        "client_secret": credentials.get("TWITTER_CLIENT_SECRET"),
                        "twitter_user_id": account_id,
                        "screen_name": twitter_username
                    },
                    scopes=["read", "write", "tweet.read", "tweet.write", "users.read"],
                    is_primary=True
                )
                
                # Also save to .env for backwards compatibility
                valid_keys = env_manager.get_platform_env_keys(platform)
                filtered_credentials = {k: v for k, v in credentials.items() if k in valid_keys}
                env_manager.update_env_vars(filtered_credentials)
                
                return ConnectionResponse(
                    success=True,
                    connected=True,
                    message="Successfully connected to Twitter"
                )
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to save Twitter credentials: {str(e)}")
 
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to connect to {platform}: {str(e)}")
 
 
 
@router.post("/{platform}/disconnect", response_model=ConnectionResponse)
async def disconnect_platform(platform: str):
    """Disconnect from a social media platform by removing credentials"""
    if platform not in ["facebook", "instagram", "twitter", "reddit", "linkedin"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported platform: {platform}"
        )
   
    try:
        # Get platform-specific environment keys
        keys_to_remove = env_manager.get_platform_env_keys(platform)
       
        # Remove credentials from .env file
        success = env_manager.remove_env_vars(keys_to_remove)
       
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to remove credentials"
            )
       
        return ConnectionResponse(
            success=True,
            connected=False,
            message=f"Successfully disconnected from {platform.title()}"
        )
       
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to disconnect from {platform}: {str(e)}"
        )
 
@router.get("/platforms")
async def get_supported_platforms():
    """Get list of supported platforms"""
    return {
        "platforms": [
            {
                "id": "facebook",
                "name": "Facebook",
                "description": "Connect your Facebook page to post content automatically",
                "required_credentials": ["FACEBOOK_PAGE_ID", "FACEBOOK_ACCESS_TOKEN"]
            },
            {
                "id": "twitter",
                "name": "Twitter",
                "description": "Connect your Twitter account to post tweets automatically",
                "required_credentials": ["TWITTER_CONSUMER_KEY", "TWITTER_CONSUMER_SECRET",
                                       "TWITTER_ACCESS_TOKEN", "TWITTER_ACCESS_TOKEN_SECRET",
                                       "TWITTER_BEARER_TOKEN", "TWITTER_CLIENT_ID", "TWITTER_CLIENT_SECRET", "TWITTER_USERNAME"]
            },
            {
                "id": "reddit",
                "name": "Reddit",
                "description": "Connect your Reddit account to post to subreddits automatically",
                "required_credentials": ["REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET",
                                       "REDDIT_USERNAME", "REDDIT_PASSWORD",
                                       "REDDIT_USER_AGENT", "REDDIT_ACCESS_TOKEN", "REDDIT_REFRESH_TOKEN"]
            },
            {
                "id": "linkedin",
                "name": "LinkedIn",
                "description": "Connect your LinkedIn account to post content automatically",
                "required_credentials": ["LINKEDIN_CLIENT_ID", "LINKEDIN_CLIENT_SECRET", "LINKEDIN_ACCESS_TOKEN"]
            }
        ]
    }
 
@router.get("/status")
async def get_all_platforms_status():
    """Get connection status for all platforms"""
    platforms = ["facebook", "instagram", "twitter", "reddit", "linkedin"]
    status_results = {}
   
    for platform in platforms:
        try:
            # Get individual platform status
            status_response = await get_platform_status(platform)
            status_results[platform] = {
                "connected": status_response.connected,
                "has_credentials": status_response.has_credentials,
                "last_checked": status_response.last_checked,
                "details": status_response.details
            }
        except Exception as e:
            status_results[platform] = {
                "connected": False,
                "has_credentials": False,
                "last_checked": datetime.now().isoformat(),
                "error": str(e)
            }
   
    return {"platforms": status_results}


@router.get("/check-connections")
async def check_user_platform_connections(authorization: Optional[str] = Header(None)):
    """Check if user has any connected social media platforms"""
    try:
        from auth_service import auth_service
        from database_service import db_service
        
        if not authorization or not authorization.startswith("Bearer "):
            return {"has_connections": False, "connected_platforms": []}
        
        token = authorization.replace("Bearer ", "")
        current_user = await auth_service.get_current_user(token)
        user_id = str(current_user.id)
        
        # Get all social media accounts for the user
        accounts = await db_service.get_social_media_accounts(user_id, active_only=True)
        
        # Extract unique platforms
        connected_platforms = list(set([acc.get("platform") for acc in accounts if acc.get("platform")]))
        
        return {
            "has_connections": len(connected_platforms) > 0,
            "connected_platforms": connected_platforms,
            "total_connections": len(accounts)
        }
    except Exception as e:
        # If auth fails or any error, assume no connections
        return {"has_connections": False, "connected_platforms": [], "error": str(e)}


@router.get("/accounts")
async def get_all_accounts(
    platform: Optional[str] = None,
    authorization: Optional[str] = Header(None)
):
    """Get all connected social media accounts for the current user with details"""
    try:
        from auth_service import auth_service
        from database_service import db_service
        
        if not authorization or not authorization.startswith("Bearer "):
            return {"success": False, "error": "User not authenticated", "accounts": []}
        
        token = authorization.replace("Bearer ", "")
        current_user = await auth_service.get_current_user(token)
        user_id = str(current_user.id)
        
        # Get all social media accounts for the user
        accounts = await db_service.get_social_media_accounts(user_id, platform=platform, active_only=True)
        
        # Remove sensitive tokens and format response
        # Also filter by is_active as a defensive measure (even though database query should handle it)
        formatted_accounts = []
        for account in accounts:
            # Skip inactive accounts (defensive filtering)
            if not account.get("is_active", True):
                continue
            # Handle datetime fields - they might already be strings
            def format_datetime(dt_value):
                if not dt_value:
                    return None
                if isinstance(dt_value, str):
                    return dt_value
                if hasattr(dt_value, 'isoformat'):
                    return dt_value.isoformat()
                return str(dt_value)
            
            formatted_account = {
                "id": str(account.get("id")),
                "platform": account.get("platform"),
                "account_id": account.get("account_id"),
                "username": account.get("username"),
                "display_name": account.get("display_name"),
                "is_primary": account.get("is_primary", False),
                "is_active": account.get("is_active", True),
                "created_at": format_datetime(account.get("created_at")),
                "expires_at": format_datetime(account.get("expires_at")),
                "metadata": account.get("metadata", {})
            }
            formatted_accounts.append(formatted_account)
        
        return {
            "success": True,
            "accounts": formatted_accounts,
            "total": len(formatted_accounts)
        }
    except Exception as e:
        return {"success": False, "error": str(e), "accounts": []}


@router.delete("/accounts/{account_id}")
async def disconnect_account(
    account_id: str,
    authorization: Optional[str] = Header(None)
):
    """Disconnect a specific social media account by ID"""
    try:
        from auth_service import auth_service
        from database_service import db_service
        
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="User not authenticated")
        
        token = authorization.replace("Bearer ", "")
        current_user = await auth_service.get_current_user(token)
        user_id = str(current_user.id)
        
        # Verify the account belongs to the user and deactivate it
        from database import db_manager
        
        # First check if account exists and belongs to user
        existing = await db_manager.fetch_one(
            """SELECT id, platform, display_name, username, is_active 
               FROM social_media_accounts 
               WHERE id = :account_id AND user_id = :user_id""",
            {"account_id": account_id, "user_id": user_id}
        )
        
        if not existing:
            raise HTTPException(status_code=404, detail="Account not found")
        
        if not existing.get("is_active"):
            raise HTTPException(status_code=400, detail="Account is already disconnected")
        
        # Deactivate the account
        await db_manager.execute_query(
            """UPDATE social_media_accounts 
               SET is_active = FALSE, updated_at = NOW() 
               WHERE id = :account_id AND user_id = :user_id""",
            {"account_id": account_id, "user_id": user_id}
        )
        
        return {
            "success": True,
            "message": "Account disconnected successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to disconnect account: {str(e)}")


# Facebook OAuth Callback
 
@router.get("/facebook/callback")
async def facebook_callback(
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    error_code: Optional[str] = None,
    error_description: Optional[str] = None,
    error_reason: Optional[str] = None
):
    """
    Handle Facebook OAuth redirect, get long-lived token, and store multiple pages to database.
    """
    try:
        import httpx
        import requests
        import base64
        import json

        def _popup_response(event_type: str, message: str):
            safe_message = (message or "").replace("'", "\\'").replace("\n", " ")
            html = f"""<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <title>Facebook Connection</title>
    <style>
      body {{
        font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        margin: 0;
        padding: 24px;
        background: #f9fafb;
        color: #111827;
        text-align: center;
      }}
      .card {{
        background: white;
        border-radius: 12px;
        padding: 24px;
        box-shadow: 0 10px 25px rgba(15, 23, 42, 0.08);
        display: inline-block;
      }}
      h1 {{
        font-size: 18px;
        margin-bottom: 8px;
      }}
      p {{
        margin: 0;
        color: #4b5563;
        font-size: 14px;
      }}
    </style>
  </head>
  <body>
    <div class="card">
      <h1>{'Connected!' if event_type == 'SOCIAL_CONNECT_SUCCESS' else 'Connection Failed'}</h1>
      <p>{safe_message or ('You may close this window when ready.' if event_type != 'SOCIAL_CONNECT_SUCCESS' else 'Connection successful. This window will close automatically.')}</p>
    </div>
    <script>
      (function () {{
        const isSuccess = '{event_type}' === 'SOCIAL_CONNECT_SUCCESS';
        try {{
          if (window.opener) {{
            window.opener.postMessage({{
              type: '{event_type}',
              platform: 'facebook',
              message: '{safe_message}'
            }}, '*');
          }}
        }} catch (err) {{
          console.error('postMessage failed', err);
        }}
        if (isSuccess) {{
          setTimeout(function () {{
            window.close();
          }}, 600);
        }} else {{
          // For errors leave the window open so details can be captured.
        }}
      }})();
    </script>
  </body>
</html>"""
            return HTMLResponse(content=html, status_code=200 if event_type == "SOCIAL_CONNECT_SUCCESS" else 400)

        def _popup_error(message: str):
            message = message or "Facebook authorization failed."
            return _popup_response("SOCIAL_CONNECT_ERROR", message)

        # Handle error responses (e.g., user cancelled)
        if error or not code:
            error_msg = error_description or error or "Facebook authorization was cancelled."
            if error_reason == "user_denied" or (error_code and str(error_code) == "200"):
                error_msg = "Facebook authorization was cancelled by the user. Please grant the requested permissions to continue."
            return _popup_error(error_msg)

        # Decode user_id from state parameter if available
        user_id = None
        if state:
            try:
                state_decoded = base64.urlsafe_b64decode(state.encode()).decode()
                state_data = json.loads(state_decoded)
                user_id = state_data.get("user_id")
            except:
                pass
        
        if not user_id:
            raise HTTPException(status_code=400, detail="Missing user identity in Facebook OAuth callback. Please retry the connection.")

        # Short-lived token
        from urllib.parse import quote_plus
        redirect_uri_encoded = quote_plus(FACEBOOK_REDIRECT_URI)
        print("🔁 Exchanging code for short-lived Facebook token...")
        async with httpx.AsyncClient() as client:
            token_resp = await client.get(
                f"https://graph.facebook.com/v19.0/oauth/access_token?"
                f"client_id={FACEBOOK_APP_ID}&redirect_uri={redirect_uri_encoded}"
                f"&client_secret={FACEBOOK_APP_SECRET}&code={code}"
            )
            token_data = token_resp.json()
        print(f"   ↳ Token exchange response: {token_resp.status_code} {token_data}")
        short_token = token_data.get("access_token")
        if not short_token:
            error_obj = token_data.get("error", {})
            if isinstance(error_obj, dict):
                error_code = error_obj.get("code")
                error_msg = error_obj.get("message", "Unknown error")
                error_type = error_obj.get("type", "")
                
                # Handle "App not active" error
                if error_code == 190 or "app is not active" in error_msg.lower() or "app_not_active" in error_type.lower():
                    error_detail = (
                        "Your Facebook app is not currently active. This usually happens when:\n"
                        "1. The app is in Development mode and you need to add test users\n"
                        "2. The app needs to be submitted for review\n"
                        "3. The app was disabled by Facebook\n\n"
                        "Please check your Facebook App Dashboard and ensure the app is active."
                    )
                    raise HTTPException(status_code=400, detail=error_detail)
                else:
                    raise HTTPException(status_code=400, detail=f"Failed to get short-lived token: {error_msg}")
            else:
                error_msg = str(error_obj) if error_obj else "Failed to get short-lived token"
                raise HTTPException(status_code=400, detail=f"Failed to get short-lived token: {error_msg}")

        # Long-lived token
        print("🔁 Upgrading to long-lived Facebook token...")
        async with httpx.AsyncClient() as client:
            long_resp = await client.get(
                f"https://graph.facebook.com/v19.0/oauth/access_token?"
                f"grant_type=fb_exchange_token&client_id={FACEBOOK_APP_ID}"
                f"&client_secret={FACEBOOK_APP_SECRET}&fb_exchange_token={short_token}"
            )
            long_data = long_resp.json()
        print(f"   ↳ Long-lived token response: {long_resp.status_code} {long_data}")
        long_token = long_data.get("access_token")
        expires_in = long_data.get("expires_in")
        if not long_token:
            raise HTTPException(status_code=400, detail="Failed to get long-lived token")

        # Get Facebook user ID
        print("🔍 Fetching Facebook /me profile...")
        user_info_resp = requests.get("https://graph.facebook.com/me", params={"access_token": long_token})
        user_info = user_info_resp.json()
        print(f"   ↳ /me response: {user_info_resp.status_code} {user_info}")
        facebook_user_id = user_info.get("id")

        # Get all pages for this user
        print("📄 Fetching managed pages (/me/accounts)...")
        page_resp_obj = requests.get(f"https://graph.facebook.com/me/accounts", params={"access_token": long_token})
        page_resp = page_resp_obj.json()
        print(f"   ↳ /me/accounts response: {page_resp_obj.status_code} {page_resp}")
        pages = page_resp.get("data", [])
        if not pages:
            return _popup_error(
                "Facebook did not return any managed Pages. Please ensure you have at least one Facebook Page and you granted the required permissions (pages_show_list, pages_read_engagement, pages_manage_posts)."
            )
        
        from datetime import datetime, timedelta
        from database_service import db_service
        expires_at = datetime.now() + timedelta(seconds=expires_in) if expires_in else None

        # Connect all available pages (flexible multiple pages support)
        if not pages:
            return _popup_error(
                "Facebook did not return any managed Pages. Please ensure you have at least one Facebook Page and you granted the required permissions (pages_show_list, pages_read_engagement, pages_manage_posts)."
            )
        
        # Get existing accounts to check which ones are already connected
        existing_accounts = await db_service.get_social_media_accounts(user_id, platform="facebook", active_only=False)
        existing_account_ids = {acc.get("account_id") for acc in existing_accounts if acc.get("account_id")}
        
        # Save all pages (allow multiple pages)
        saved_pages = []
        updated_pages = []
        from database import db_manager
        
        for page in pages:
            page_id = page.get("id")
            page_name = page.get("name", f"Facebook Page {page_id}")
            page_access_token = page.get("access_token", long_token)
            
            if page_id in existing_account_ids:
                # Account already exists - just update token and reactivate if needed
                print(f"ℹ️ Facebook page '{page_name}' already exists. Updating token...")
                try:
                    await db_manager.execute_query(
                        """UPDATE social_media_accounts 
                           SET access_token = :access_token, expires_at = :expires_at, 
                               is_active = TRUE, updated_at = NOW()
                           WHERE user_id = :user_id AND platform = 'facebook' AND account_id = :account_id""",
                        {
                            "user_id": user_id,
                            "account_id": page_id,
                            "access_token": page_access_token,
                            "expires_at": expires_at
                        }
                    )
                    updated_pages.append(page_name)
                except Exception as e:
                    print(f"⚠️ Failed to update existing page {page_name}: {e}")
            else:
                # New page - save it
                print(f"💾 Saving new Facebook page: {page_name} (ID: {page_id}) for user {user_id}")
                # Set as primary only if this is the first page and no other primary exists
                is_primary = len(saved_pages) == 0 and not any(acc.get("is_primary") for acc in existing_accounts)
                saved = await db_service.save_social_media_account(
                    user_id=user_id,
                    platform="facebook",
                    account_id=page_id,
                    access_token=page_access_token,
                    display_name=page_name,
                    expires_at=expires_at,
                    metadata={
                        "facebook_user_id": facebook_user_id,
                        "page_id": page_id,
                        "page_access_token": page_access_token
                    },
                    scopes=["pages_show_list", "pages_read_engagement", "pages_manage_posts"],
                    is_primary=is_primary
                )
                if saved:
                    saved_pages.append(page_name)
                else:
                    print(f"❌ Failed to save Facebook page {page_name} for user {user_id}")
        
        # Verify the accounts were saved
        verify_accounts = await db_service.get_social_media_accounts(user_id, platform="facebook", active_only=True)
        print(f"✅ Verified: {len(verify_accounts)} Facebook account(s) active for user {user_id}")
        
        # Build success message
        if saved_pages and updated_pages:
            message = f"Connected {len(saved_pages)} new page(s) and updated {len(updated_pages)} existing page(s). Total: {len(verify_accounts)} page(s) connected."
        elif saved_pages:
            message = f"Successfully connected {len(saved_pages)} Facebook page(s). Total: {len(verify_accounts)} page(s) connected."
        elif updated_pages:
            message = f"Updated {len(updated_pages)} existing Facebook page(s). Total: {len(verify_accounts)} page(s) connected."
        else:
            message = f"Facebook pages processed. Total: {len(verify_accounts)} page(s) connected."
        print(f"✅ {message}")

        return _popup_response("SOCIAL_CONNECT_SUCCESS", message)

    except HTTPException as e:
        detail = e.detail if isinstance(e.detail, str) else str(e.detail)
        return _popup_error(detail)
    except Exception as e:
        return _popup_error(str(e))
   
@router.get("/reddit/callback")
async def reddit_callback(code: Optional[str] = None, state: Optional[str] = None, error: Optional[str] = None):
    """
    Handle Reddit OAuth redirect and save account for user
    """
    # Helper functions for popup communication (same as Facebook callback)
    def _popup_response(event_type: str, message: str):
        safe_message = (message or "").replace("'", "\\'").replace("\n", " ")
        html = f"""<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <title>Reddit Connection</title>
    <style>
      body {{
        font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        margin: 0;
        padding: 24px;
        background: #f9fafb;
        color: #111827;
        text-align: center;
      }}
      .card {{
        background: white;
        border-radius: 12px;
        padding: 24px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        max-width: 400px;
        margin: 40px auto;
      }}
      .success {{ color: #10b981; }}
      .error {{ color: #ef4444; }}
    </style>
  </head>
  <body>
    <div class="card">
      <p class="{'error' if 'ERROR' in event_type else 'success'}">{safe_message}</p>
    </div>
    <script>
      if (window.opener) {{
        window.opener.postMessage({{ type: '{event_type}', message: '{safe_message}' }}, '*');
        setTimeout(() => window.close(), 1500);
      }} else {{
        setTimeout(() => {{
          window.location.href = '/socialanywhere/settings';
        }}, 1500);
      }}
    </script>
  </body>
</html>"""
        return HTMLResponse(content=html)
    
    def _popup_error(message: str):
        return _popup_response("SOCIAL_CONNECT_ERROR", message)
    
    try:
        # Check for OAuth errors from Reddit
        if error:
            error_msg = f"Reddit OAuth error: {error}"
            print(f"❌ {error_msg}")
            return _popup_error(error_msg)
        
        if not code:
            return _popup_error("Authorization code not provided by Reddit")
        
        if not state:
            return _popup_error("State parameter not provided")
        
        # 1️⃣ Exchange code for tokens
        try:
            token_data = exchange_code_for_tokens(code)
        except Exception as e:
            error_msg = f"Failed to exchange Reddit code for tokens: {str(e)}"
            print(f"❌ {error_msg}")
            return _popup_error(error_msg)
        
        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")
        expires_in = token_data.get("expires_in", 3600)  # Default 1 hour
        scope = token_data.get("scope", "")
        
        if not access_token or not refresh_token:
            error_detail = token_data.get("error", "Unknown error")
            error_msg = f"Failed to get Reddit tokens: {error_detail}"
            print(f"❌ {error_msg}")
            return _popup_error(error_msg)
        
        # 2️⃣ Get user info
        try:
            user_info = get_reddit_user_info(access_token)
        except Exception as e:
            error_msg = f"Failed to get Reddit user info: {str(e)}"
            print(f"❌ {error_msg}")
            return _popup_error(error_msg)
        
        reddit_user_id = user_info.get("id")
        reddit_username = user_info.get("name")
        
        if not reddit_user_id or not reddit_username:
            error_msg = "Failed to get Reddit user info - missing user ID or username"
            print(f"❌ {error_msg}")
            return _popup_error(error_msg)
        
        # Decode user_id from state parameter if available
        user_id = "demo_user_123"  # Default fallback
        if state:
            try:
                import base64
                import json
                state_decoded = base64.urlsafe_b64decode(state.encode()).decode()
                state_data = json.loads(state_decoded)
                user_id = state_data.get("user_id", "demo_user_123")
            except Exception as e:
                print(f"⚠️ Failed to decode state: {e}")
                # Continue with default user_id
        
        from datetime import datetime, timedelta
        from database_service import db_service
        expires_at = datetime.now() + timedelta(seconds=expires_in) if expires_in else None
        
        # Check if this account already exists
        existing_accounts = await db_service.get_social_media_accounts(user_id, platform="reddit", active_only=True)
        existing_account = next((acc for acc in existing_accounts if acc.get("account_id") == reddit_user_id), None)
        
        if existing_account:
            # Account already exists - just update token and reactivate if needed
            print(f"ℹ️ Reddit account '{reddit_username}' already connected. Updating token...")
            from database import db_manager
            await db_manager.execute_query(
                """UPDATE social_media_accounts 
                   SET access_token = :access_token, refresh_token = :refresh_token, 
                       expires_at = :expires_at, is_active = TRUE, updated_at = NOW()
                   WHERE user_id = :user_id AND platform = 'reddit' AND account_id = :account_id""",
                {
                    "user_id": user_id,
                    "account_id": reddit_user_id,
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                    "expires_at": expires_at
                }
            )
            message = f"Reddit account '{reddit_username}' is already connected. Token updated."
            print(f"✅ {message}")
            return _popup_response("SOCIAL_CONNECT_SUCCESS", message)
        
        # Only set as primary if no other accounts exist
        is_primary = len(existing_accounts) == 0
        
        # Save to unified database table
        try:
            print(f"💾 Saving Reddit account: {reddit_username} (ID: {reddit_user_id}) for user {user_id}")
            saved = await db_service.save_social_media_account(
                user_id=user_id,
                platform="reddit",
                account_id=reddit_user_id,
                access_token=access_token,
                username=reddit_username,
                display_name=reddit_username,
                refresh_token=refresh_token,
                expires_at=expires_at,
                metadata={
                    "reddit_user_id": reddit_user_id,
                    "reddit_username": reddit_username
                },
                scopes=scope.split() if scope else [],
                is_primary=is_primary
            )
            if not saved:
                print(f"❌ Failed to save Reddit account credentials for user {user_id}")
                raise Exception("Failed to save account to database")
            
            # Verify the account was saved
            verify_accounts = await db_service.get_social_media_accounts(user_id, platform="reddit", active_only=True)
            print(f"✅ Verified: {len(verify_accounts)} Reddit account(s) saved for user {user_id}")
            if verify_accounts:
                print(f"   ↳ Account: {verify_accounts[0].get('username')} (ID: {verify_accounts[0].get('account_id')})")
        except Exception as e:
            error_msg = f"Failed to save Reddit account: {str(e)}"
            print(f"❌ {error_msg}")
            import traceback
            traceback.print_exc()
            return _popup_error(error_msg)
        
        # Note: We no longer update .env file automatically to avoid overwriting credentials
        # Each account is stored in the database and can be managed individually
        
        message = f"Reddit account '{reddit_username}' connected successfully."
        print(f"✅ {message}")
        return _popup_response("SOCIAL_CONNECT_SUCCESS", message)
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"Reddit OAuth callback error: {str(e)}"
        print(f"❌ {error_msg}")
        import traceback
        traceback.print_exc()
        return _popup_error(error_msg)

@router.get("/twitter/callback")
async def twitter_callback(
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    error_description: Optional[str] = None
):
    """
    Handle Twitter OAuth redirect and save account for user
    """
    try:
        # Check for OAuth errors from Twitter
        if error:
            error_msg = error_description or error
            print(f"❌ Twitter OAuth error: {error} - {error_msg}")
            
            # Get the base URL for redirect
            public_domain_cb = os.getenv('PUBLIC_DOMAIN', 'localhost:8000')
            use_https_cb = os.getenv('USE_HTTPS', 'false').lower() == 'true'
            scheme_cb = "https" if use_https_cb else "http"
            
            if use_https_cb and ":" not in public_domain_cb:
                domain_with_port = public_domain_cb
            elif ":" in public_domain_cb:
                domain_with_port = public_domain_cb
            else:
                port = os.getenv("PORT", "8000")
                domain_with_port = f"{public_domain_cb}:{port}"
            
            base_url = f"{scheme_cb}://{domain_with_port}"
            
            # Redirect back with error message
            error_encoded = quote_plus(error_msg)
            return RedirectResponse(url=f"{base_url}/socialanywhere/settings?connected=twitter&success=false&error={error_encoded}")
        
        if not code:
            raise HTTPException(status_code=400, detail="Authorization code not provided")
        
        if not state:
            raise HTTPException(status_code=400, detail="State parameter not provided")
        
        from twitter_oauth_helper import exchange_code_for_tokens, get_twitter_user_info
        from database_service import db_service
        from datetime import datetime, timedelta
        from urllib.parse import quote_plus
        
        # Decode state to get user_id and code_verifier
        user_id = "demo_user_123"  # Default fallback
        code_verifier = None
        if state:
            try:
                import base64
                import json
                state_decoded = base64.urlsafe_b64decode(state.encode()).decode()
                state_data = json.loads(state_decoded)
                user_id = state_data.get("user_id", "demo_user_123")
                code_verifier = state_data.get("code_verifier")
            except Exception as e:
                print(f"⚠️ Failed to decode state: {e}")
                raise HTTPException(status_code=400, detail="Invalid state parameter")
        
        if not code_verifier:
            raise HTTPException(status_code=400, detail="Code verifier not found in state")
        
        # 1️⃣ Exchange code for tokens
        try:
            token_data = exchange_code_for_tokens(code, code_verifier)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to exchange Twitter code for tokens: {str(e)}")
        
        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")
        expires_in = token_data.get("expires_in", 7200)  # Default 2 hours
        scope = token_data.get("scope", "")
        token_type = token_data.get("token_type", "bearer")
        
        if not access_token:
            error_detail = token_data.get("error", "Unknown error")
            raise HTTPException(status_code=400, detail=f"Failed to get Twitter tokens: {error_detail}")
        
        # 2️⃣ Get user info
        try:
            user_info = get_twitter_user_info(access_token)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to get Twitter user info: {str(e)}")
        
        twitter_user_id = user_info.get("id")
        twitter_username = user_info.get("username")
        twitter_name = user_info.get("name")
        
        if not twitter_user_id or not twitter_username:
            raise HTTPException(status_code=400, detail="Failed to get Twitter user info")
        
        expires_at = datetime.now() + timedelta(seconds=expires_in) if expires_in else None
        
        # Save to unified database table
        await db_service.save_social_media_account(
            user_id=user_id,
            platform="twitter",
            account_id=twitter_user_id,
            access_token=access_token,
            username=twitter_username,
            display_name=twitter_name or twitter_username,
            refresh_token=refresh_token,
            expires_at=expires_at,
            metadata={
                "twitter_user_id": twitter_user_id,
                "twitter_username": twitter_username,
                "twitter_name": twitter_name,
                "verified": user_info.get("verified", False),
                "profile_image_url": user_info.get("profile_image_url")
            },
            scopes=scope.split() if scope else [],
            is_primary=True
        )
        
        # Get the base URL for redirect
        public_domain_cb = os.getenv('PUBLIC_DOMAIN', 'localhost:8000')
        use_https_cb = os.getenv('USE_HTTPS', 'false').lower() == 'true'
        scheme_cb = "https" if use_https_cb else "http"
        
        if use_https_cb and ":" not in public_domain_cb:
            domain_with_port = public_domain_cb
        elif ":" in public_domain_cb:
            domain_with_port = public_domain_cb
        else:
            port = os.getenv("PORT", "8000")
            domain_with_port = f"{public_domain_cb}:{port}"
        
        base_url = f"{scheme_cb}://{domain_with_port}"
        
        return RedirectResponse(url=f"{base_url}/socialanywhere/settings?connected=twitter&success=true")
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Twitter OAuth callback error: {e}")
        import traceback
        traceback.print_exc()
        
        # Try to redirect back with error
        try:
            public_domain_cb = os.getenv('PUBLIC_DOMAIN', 'localhost:8000')
            use_https_cb = os.getenv('USE_HTTPS', 'false').lower() == 'true'
            scheme_cb = "https" if use_https_cb else "http"
            
            if use_https_cb and ":" not in public_domain_cb:
                domain_with_port = public_domain_cb
            elif ":" in public_domain_cb:
                domain_with_port = public_domain_cb
            else:
                port = os.getenv("PORT", "8000")
                domain_with_port = f"{public_domain_cb}:{port}"
            
            base_url = f"{scheme_cb}://{domain_with_port}"
            error_msg = quote_plus(str(e))
            return RedirectResponse(url=f"{base_url}/socialanywhere/settings?connected=twitter&success=false&error={error_msg}")
        except:
            raise HTTPException(status_code=500, detail=f"Twitter OAuth callback error: {str(e)}")

@router.get("/linkedin/callback")
async def linkedin_callback(code: Optional[str] = None, state: Optional[str] = None, error: Optional[str] = None, error_description: Optional[str] = None):
    """
    Handle LinkedIn OAuth redirect and save tokens
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # Check for OAuth errors first
        if error:
            error_msg = error_description or error
            logger.error(f"❌ LinkedIn OAuth error: {error} - {error_msg}")
            raise HTTPException(
                status_code=400,
                detail=f"LinkedIn authorization failed: {error_msg}"
            )
        
        # Check if code is present
        if not code:
            raise HTTPException(
                status_code=400,
                detail="Missing authorization code from LinkedIn. Please try connecting again."
            )
        
        # 1️⃣ Exchange code for tokens
        token_data = exchange_linkedin_code(code)
        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")  # May be None if not MDP approved
        expires_in = token_data.get("expires_in", 5184000)  # Default 60 days
        scope = token_data.get("scope", "")
        
        if not access_token:
            raise HTTPException(status_code=400, detail="Failed to get LinkedIn access token")
        
        # 2️⃣ Get user info
        user_info = get_linkedin_user_info(access_token)
        person_id = user_info.get("id")
        
        if not person_id:
            raise HTTPException(status_code=400, detail="Failed to get LinkedIn user info")
        
        # 3️⃣ Save credentials to .env file
        credentials = {
            "LINKEDIN_ACCESS_TOKEN": access_token
        }
        if refresh_token:
            credentials["LINKEDIN_REFRESH_TOKEN"] = refresh_token
        
        env_manager.update_env_vars(credentials)
        
        # 4️⃣ Update environment variables in current process
        # Don't write to .env - credentials should only be in database
        # Only client ID/secret should be in .env
        
        # Get the base URL for redirect
        public_domain = os.getenv('PUBLIC_DOMAIN', 'localhost:8000')
        use_https = os.getenv('USE_HTTPS', 'false').lower() == 'true'
        scheme = 'https' if use_https else 'http'
        
        # For production (HTTPS), don't include port (standard 443)
        # For localhost, include port
        if use_https and not ":" in public_domain:
            # Production domain without port
            domain_with_port = public_domain
        elif ":" in public_domain:
            # Domain already has port
            domain_with_port = public_domain
        else:
            # Local development - add port
            port = os.getenv("PORT", "8000")
            domain_with_port = f"{public_domain}:{port}"
        
        base_url = f"{scheme}://{domain_with_port}"
        
        return RedirectResponse(url=f"{base_url}/socialanywhere/settings")
        
    except HTTPException as e:
        raise e
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"❌ LinkedIn callback error: {str(e)}")
        print(f"❌ Traceback: {error_trace}")
        raise HTTPException(status_code=500, detail=f"LinkedIn callback failed: {str(e)}")

# ===== INSTAGRAM OAUTH CALLBACK - DISABLED (STATIC FLOW NOW) =====
# @router.get("/instagram/callback")
# async def instagram_callback(code: Optional[str] = None, state: Optional[str] = None, error: Optional[str] = None):
#     """
#     Handle Instagram Business Login (Instagram Login) redirect and save account to database.
#     
#     DISABLED: Instagram now uses static credential entry (manual token input)
#     Flow based on:
#     https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/business-login/
#     """
#     import httpx
#     import requests
#     from datetime import datetime, timedelta
#     from database_service import db_service
#     import base64
#     import json
#     from urllib.parse import quote_plus
# 
#     # Helper to build redirect back to frontend settings page
#     def _build_base_url() -> str:
# public_domain_cb = os.getenv("PUBLIC_DOMAIN", "localhost:8000")
# use_https_cb = os.getenv("USE_HTTPS", "false").lower() == "true"
# scheme_cb = "https" if use_https_cb else "http"
#
# if use_https_cb and ":" not in public_domain_cb:
# domain_with_port = public_domain_cb
# elif ":" in public_domain_cb:
# domain_with_port = public_domain_cb
# else:
# port = os.getenv("PORT", "8000")
# domain_with_port = f"{public_domain_cb}:{port}"
#
# return f"{scheme_cb}://{domain_with_port}"
#
# try:
# base_url = _build_base_url()
#
        # Handle OAuth error/cancel from Instagram
# if error or not code:
# error_msg = error or "Instagram authorization was cancelled or failed."
# error_encoded = quote_plus(error_msg)
# return RedirectResponse(
# url=f"{base_url}/socialanywhere/settings?error={error_encoded}&platform=instagram"
# )
#
        # Decode user_id from state parameter
# user_id = "demo_user_123"  # Default fallback
# if state:
# try:
# state_decoded = base64.urlsafe_b64decode(state.encode()).decode()
# state_data = json.loads(state_decoded)
# user_id = state_data.get("user_id", "demo_user_123")
# except Exception:
                # If state decoding fails, continue with default
# pass
#
# if not INSTAGRAM_APP_ID or not INSTAGRAM_APP_SECRET:
# raise HTTPException(
# status_code=400,
# detail="Instagram App ID and Secret must be configured in environment variables (INSTAGRAM_APP_ID, INSTAGRAM_APP_SECRET).",
# )
#
        # 1️⃣ Exchange code for short-lived Instagram User access token
# redirect_uri = INSTAGRAM_REDIRECT_URI
# async with httpx.AsyncClient() as client:
# token_resp = await client.post(
# "https://api.instagram.com/oauth/access_token",
# data={
# "client_id": INSTAGRAM_APP_ID,
# "client_secret": INSTAGRAM_APP_SECRET,
# "grant_type": "authorization_code",
# "redirect_uri": redirect_uri,
# "code": code,
# },
# timeout=30,
# )
# token_data = token_resp.json()
#
        # Some responses wrap in "data": [...], others return flat JSON
# if isinstance(token_data, dict) and "data" in token_data:
# data_entry = token_data["data"][0] if token_data["data"] else {}
# else:
# data_entry = token_data
#
# short_token = data_entry.get("access_token")
# ig_user_id = data_entry.get("user_id")
# granted_permissions = data_entry.get("permissions")
#
# if not short_token or not ig_user_id:
# error_msg = data_entry.get("error_message") or "Failed to get Instagram short-lived access token."
# raise HTTPException(status_code=400, detail=error_msg)
#
        # 2️⃣ Exchange short-lived token for long-lived token (60 days)
# long_token = short_token
# expires_in = 3600
# try:
# long_resp = requests.get(
# "https://graph.instagram.com/access_token",
# params={
# "grant_type": "ig_exchange_token",
# "client_secret": INSTAGRAM_APP_SECRET,
# "access_token": short_token,
# },
# timeout=30,
# )
# if long_resp.status_code == 200:
# long_data = long_resp.json()
# long_token = long_data.get("access_token", short_token)
# expires_in = long_data.get("expires_in", 5184000)  # 60 days default
# else:
                # If this fails, continue with short-lived token so user can at least connect
# print(f"⚠️ Failed to exchange Instagram token for long-lived token: {long_resp.text}")
# except Exception as e:
# print(f"⚠️ Exception exchanging Instagram token for long-lived token: {e}")
#
# expires_at = datetime.now() + timedelta(seconds=expires_in) if expires_in else None
#
        # 3️⃣ Fetch Instagram professional account info from /me endpoint
        # This gets the actual Instagram Business Account ID (user_id) needed for analytics
        # See: https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/get-started
# ig_username = None
# ig_professional_account_id = ig_user_id  # Default fallback
# try:
# me_resp = requests.get(
# "https://graph.instagram.com/v24.0/me",
# params={
# "fields": "user_id,username,account_type,followers_count,follows_count,media_count",
# "access_token": long_token,
# },
# timeout=30,
# )
# if me_resp.status_code == 200:
# me_data = me_resp.json()
                # The 'user_id' field is the Instagram Professional Account ID (for analytics)
                # The 'id' field (if returned) is the app-scoped user ID
# ig_professional_account_id = me_data.get("user_id", ig_user_id)
# ig_username = me_data.get("username")
# print(f"✅ Instagram /me response: user_id={ig_professional_account_id}, username={ig_username}")
# else:
# print(f"⚠️ Failed to fetch Instagram /me endpoint: {me_resp.status_code} - {me_resp.text}")
# except Exception as e:
# print(f"⚠️ Exception fetching Instagram /me profile: {e}")
#
        # 4️⃣ Save/update Instagram account in unified social_media_accounts table
# from database import db_manager
#
# existing_accounts = await db_service.get_social_media_accounts(
# user_id, platform="instagram", active_only=False
# )
        # Use the Instagram professional account ID (from /me user_id) for storage
# existing_account = next(
# (acc for acc in existing_accounts if acc.get("account_id") == str(ig_professional_account_id)), None
# )
#
# scopes_list: list[str] = []
# if isinstance(granted_permissions, str):
# scopes_list = [p.strip() for p in granted_permissions.split(",") if p.strip()]
# elif isinstance(granted_permissions, list):
# scopes_list = granted_permissions
#
# if existing_account:
            # Update existing record
# print(f"ℹ️ Instagram account '{ig_username or ig_professional_account_id}' already connected. Updating token...")
# await db_manager.execute_query(
# """
# UPDATE social_media_accounts
# SET access_token = :access_token,
# username = :username,
# expires_at = :expires_at,
# is_active = TRUE,
# updated_at = NOW()
# WHERE user_id = :user_id AND platform = 'instagram' AND account_id = :account_id
# """,
# {
# "user_id": user_id,
# "account_id": str(ig_professional_account_id),
# "username": ig_username,
# "access_token": long_token,
# "expires_at": expires_at,
# },
# )
# message = f"Instagram account '{ig_username or ig_professional_account_id}' is already connected. Token updated."
# else:
            # Deactivate any active Instagram accounts for this user (single active account at a time)
# await db_manager.execute_query(
# """
# UPDATE social_media_accounts
# SET is_active = FALSE, updated_at = NOW()
# WHERE user_id = :user_id AND platform = 'instagram' AND is_active = TRUE
# """,
# {"user_id": user_id},
# )
#
# print(f"💾 Saving Instagram account: {ig_username or ig_professional_account_id} (Professional ID: {ig_professional_account_id}) for user {user_id}")
# saved = await db_service.save_social_media_account(
# user_id=user_id,
# platform="instagram",
# account_id=str(ig_professional_account_id),  # Use professional account ID for analytics
# access_token=long_token,
# username=ig_username,
# display_name=ig_username or f"Instagram {ig_professional_account_id}",
# expires_at=expires_at,
# metadata={
# "instagram_user_id": str(ig_user_id),  # Store app-scoped ID for reference
# "instagram_professional_id": str(ig_professional_account_id),
# "source": "instagram_login_business",
# },
# scopes=scopes_list
# or [
# "instagram_business_basic",
# "instagram_business_content_publish",
# "instagram_business_manage_messages",
# "instagram_business_manage_comments",
# ],
# is_primary=True,
# )
# if not saved:
# raise Exception("Failed to save Instagram account to database")
# message = f"Instagram account '{ig_username or ig_professional_account_id}' connected successfully."
#
        # Verify save
# verify_accounts = await db_service.get_social_media_accounts(
# user_id, platform="instagram", active_only=True
# )
# print(f"✅ Verified: {len(verify_accounts)} Instagram account(s) active for user {user_id}")
#
# print(f"✅ {message}")
# message_encoded = quote_plus(message)
# return RedirectResponse(
# url=f"{base_url}/socialanywhere/settings?connected=instagram&success=true&message={message_encoded}"
# )
#
# except HTTPException as e:
# base_url = _build_base_url()
# error_msg = str(e.detail).replace("\n", " ").replace('"', "'")
# error_encoded = quote_plus(error_msg)
# return RedirectResponse(
# url=f"{base_url}/socialanywhere/settings?error={error_encoded}&platform=instagram"
# )
# except Exception as e:
# base_url = _build_base_url()
# error_msg = str(e).replace("\n", " ").replace('"', "'")
# error_encoded = quote_plus(error_msg)
# return RedirectResponse(
# url=f"{base_url}/socialanywhere/settings?error={error_encoded}&platform=instagram"
# )
#
#
# Save Selected Page
@router.post("/facebook/select-page")
async def select_facebook_page(payload: Dict[str, str]):
    """
    Save selected Facebook page for a specific user
    Example payload:
    {
        "user_id": "123456",
        "page_id": "987654",
        "page_access_token": "EAA..."
    }
    """
    user_id = payload.get("user_id")
    page_id = payload.get("page_id")
    page_access_token = payload.get("page_access_token")
 
    if not user_id or not page_id or not page_access_token:
        raise HTTPException(status_code=400, detail="Missing user_id, page_id, or page_access_token")
 
    env_manager.save_facebook_page(user_id, page_id, page_access_token, expires_in=60*60*24*60)  # example 60 days
 
    # Test connection
    test_result = await test_facebook_connection(user_id)
 
    return {
        "message": f"Page {page_id} connected successfully for user {user_id}!",
        "connected": test_result.get("connected", True),
        "details": test_result.get("details")
    }
 
 
 
@router.post("/reddit/select-account")
async def select_reddit_account(payload: Dict[str, str]):
    """
    Save selected Reddit account for a user
    Example payload:
    {
        "user_id": "123456",
        "reddit_user_id": "abc123",
        "reddit_username": "example_user"
    }
    """
    user_id = payload.get("user_id")
    reddit_user_id = payload.get("reddit_user_id")
    reddit_username = payload.get("reddit_username")
    
    if not user_id or not reddit_user_id or not reddit_username:
        raise HTTPException(status_code=400, detail="Missing user_id, reddit_user_id, or reddit_username")
    
    # Test connection
    test_result = await test_reddit_connection(user_id)
    
    return {
        "message": f"Reddit account {reddit_username} selected successfully for user {user_id}!",
        "connected": test_result.get("connected", True),
        "details": test_result.get("details")
    }

@router.post("/instagram/select-account")
async def select_instagram_account(payload: Dict[str, str]):
    """
    Save Instagram account credentials (STATIC FLOW - manual entry)
    
    This endpoint saves manually-entered Instagram credentials to the database.
    User provides Access Token and Account ID from their Instagram Business account.
    
    Example payload:
    {
        "user_id": "123456",
        "account_id": "987654",
        "access_token": "EAA...",
        "username": "myinstagram" (optional)
    }
    """
    from database_service import db_service
    from database import db_manager
    import requests
    
    user_id = payload.get("user_id")
    account_id = payload.get("account_id")
    access_token = payload.get("access_token")
    username = payload.get("username", "")
 
    if not user_id or not account_id or not access_token:
        raise HTTPException(status_code=400, detail="Missing user_id, account_id, or access_token")
 
    try:
        # Verify the credentials by testing the Instagram Graph API
        verify_url = f"https://graph.facebook.com/v21.0/{account_id}"
        verify_params = {
            "fields": "id,username,account_type,media_count",
            "access_token": access_token
        }
        verify_resp = requests.get(verify_url, params=verify_params, timeout=10)
        
        if verify_resp.status_code != 200:
            error_data = verify_resp.json() if verify_resp.content else {}
            error_msg = error_data.get('error', {}).get('message', 'Invalid Instagram credentials')
            raise HTTPException(status_code=400, detail=f"Instagram API error: {error_msg}")
        
        account_data = verify_resp.json()
        ig_username = account_data.get('username', username)
        
        # Check if account already exists
        existing_accounts = await db_service.get_social_media_accounts(
            user_id, platform="instagram", active_only=False
        )
        existing_account = next(
            (acc for acc in existing_accounts if acc.get("account_id") == str(account_id)), None
        )
        
        if existing_account:
            # Update existing record
            print(f"ℹ️ Instagram account '{ig_username or account_id}' already connected. Updating credentials...")
            await db_manager.execute_query(
                """
                UPDATE social_media_accounts
                SET access_token = :access_token,
                    username = :username,
                    is_active = TRUE,
                    updated_at = NOW()
                WHERE user_id = :user_id AND platform = 'instagram' AND account_id = :account_id
                """,
                {
                    "user_id": user_id,
                    "account_id": str(account_id),
                    "username": ig_username,
                    "access_token": access_token,
                },
            )
            message = f"Instagram account '{ig_username or account_id}' credentials updated successfully."
        else:
            # Deactivate any active Instagram accounts for this user (single active account at a time)
            await db_manager.execute_query(
                """
                UPDATE social_media_accounts
                SET is_active = FALSE, updated_at = NOW()
                WHERE user_id = :user_id AND platform = 'instagram' AND is_active = TRUE
                """,
                {"user_id": user_id},
            )
            
            # Insert new account
            print(f"💾 Saving Instagram account: {ig_username or account_id} (Account ID: {account_id}) for user {user_id}")
            saved = await db_service.save_social_media_account(
                user_id=user_id,
                platform="instagram",
                account_id=str(account_id),
                access_token=access_token,
                username=ig_username,
                display_name=ig_username or f"Instagram {account_id}",
                expires_at=None,  # Static credentials don't expire unless manually revoked
                metadata={
                    "account_type": account_data.get("account_type"),
                    "media_count": account_data.get("media_count"),
                    "source": "static_manual_entry"
                },
                scopes=["instagram_business_basic", "instagram_business_content_publish"],
                is_primary=True,
            )
            if not saved:
                raise Exception("Failed to save Instagram account to database")
            message = f"Instagram account '{ig_username or account_id}' connected successfully."
        
        # Test connection
        test_result = await test_instagram_connection(user_id)
        
        return {
            "success": True,
            "message": message,
            "connected": test_result.get("connected", True),
            "details": test_result.get("details", {
                "account_id": account_id,
                "username": ig_username
            })
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error saving Instagram account: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save Instagram account: {str(e)}")   