# LinkedIn Integration Guide

## ✅ Files Created (Done)

1. `server/linkedin_service.py` - Main LinkedIn service with posting and image upload
2. `server/linkedin_oauth_helper.py` - OAuth2 flow helpers
3. `server/linkedin_token_refresh.py` - Token validation and refresh

---

## 📝 Files That Need Modification

### 1. **`server/social_media_routes.py`**

Add LinkedIn OAuth routes and connection testing.

**Add these imports at the top:**
```python
from linkedin_service import linkedin_service
from linkedin_oauth_helper import get_linkedin_auth_url, exchange_code_for_tokens as exchange_linkedin_code, get_linkedin_user_info
```

**Add LinkedIn connection test function (around line 157):**
```python
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
```

**Update `get_platform_status()` to include LinkedIn (around line 263):**
```python
async def get_platform_status(platform: str):
    """Get connection status for a social media platform"""
    if platform not in ["facebook", "instagram", "twitter", "reddit", "linkedin"]:  # Add "linkedin"
        raise HTTPException(...)
```

**Update connection_testers dict (around line 275):**
```python
connection_testers = {
    "facebook": test_facebook_connection,
    "instagram": test_instagram_connection,
    "twitter": test_twitter_connection,
    "reddit": test_reddit_connection,
    "linkedin": test_linkedin_connection  # Add this line
}
```

**Update `connect_platform()` to include LinkedIn (around line 300):**
```python
async def connect_platform(platform: str, credentials: Dict[str, str] = {}):
    """Connect to a social media platform by saving credentials"""
    if platform not in ["facebook", "instagram", "twitter", "reddit", "linkedin"]:  # Add "linkedin"
        raise HTTPException(...)
```

**Add LinkedIn OAuth flow in `connect_platform()` (after Reddit flow around line 351):**
```python
        # ----- LINKEDIN FLOW -----
        if platform == "linkedin":
            # Generate random state for CSRF protection
            state = secrets.token_urlsafe(32)
            auth_url = get_linkedin_auth_url(state)
            return OAuth2Response(auth_url=auth_url)
```

**Update `disconnect_platform()` to include LinkedIn (around line 404):**
```python
async def disconnect_platform(platform: str):
    """Disconnect from a social media platform by removing credentials"""
    if platform not in ["facebook", "twitter", "reddit", "linkedin"]:  # Add "linkedin"
        raise HTTPException(...)
```

**Add LinkedIn to platforms list in `get_platforms()` (around line 463):**
```python
{
    "id": "linkedin",
    "name": "LinkedIn",
    "description": "Connect your LinkedIn account to post content automatically",
    "required_credentials": ["LINKEDIN_CLIENT_ID", "LINKEDIN_CLIENT_SECRET", "LINKEDIN_ACCESS_TOKEN"]
}
```

**Update `get_all_platforms_status()` to include LinkedIn (around line 474):**
```python
async def get_all_platforms_status():
    """Get connection status for all platforms"""
    platforms = ["facebook", "instagram", "twitter", "reddit", "linkedin"]  # Add "linkedin"
```

**Add LinkedIn callback route (around line 748):**
```python
@router.get("/linkedin/callback")
async def linkedin_callback(code: Optional[str] = None, state: Optional[str] = None, error: Optional[str] = None, error_description: Optional[str] = None):
    """
    Handle LinkedIn OAuth redirect and save tokens
    """
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
        os.environ["LINKEDIN_ACCESS_TOKEN"] = access_token
        if refresh_token:
            os.environ["LINKEDIN_REFRESH_TOKEN"] = refresh_token
        
        # Get the base URL for redirect
        public_domain = os.getenv('PUBLIC_DOMAIN', 'localhost:8000')
        use_https = os.getenv('USE_HTTPS', 'false').lower() == 'true'
        scheme = 'https' if use_https else 'http'
        base_url = f"{scheme}://{public_domain}"
        
        return RedirectResponse(url=f"{base_url}/socialanywhere/settings")
        
    except HTTPException as e:
        raise e
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"❌ LinkedIn callback error: {str(e)}")
        print(f"❌ Traceback: {error_trace}")
        raise HTTPException(status_code=500, detail=f"LinkedIn callback failed: {str(e)}")
```

---

### 2. **`server/main.py`**

Add LinkedIn API endpoints for status, posting, and scheduling.

**Add these endpoints (around line 2413):**
```python
# LinkedIn API Endpoints
@main_app.get("/api/linkedin/status")
async def get_linkedin_status():
    """Get LinkedIn service status"""
    try:
        from linkedin_service import linkedin_service
        status = linkedin_service.get_service_status()
        return {"success": True, "status": status}
    except Exception as e:
        return {"success": False, "error": str(e)}


@main_app.post("/api/linkedin/post")
async def post_to_linkedin(request: dict):
    """Post content to LinkedIn"""
    try:
        from linkedin_service import linkedin_service
        text = request.get("text", "") or request.get("content", "")
        
        if not text:
            return {"success": False, "error": "Text content is required"}
        
        result = linkedin_service.post_to_linkedin(text=text)
        return result
        
    except Exception as e:
        return {"success": False, "error": str(e)}


@main_app.post("/api/linkedin/schedule")
async def schedule_linkedin_post(request: dict):
    """Schedule a LinkedIn post"""
    try:
        from database_service import db_service
        from datetime import datetime
        
        text = request.get("text", "")
        scheduled_at = request.get("scheduled_at", "")
        
        if not text or not scheduled_at:
            return {
                "success": False,
                "error": "Text and scheduled_at are required"
            }
        
        # Parse scheduled datetime
        scheduled_dt = datetime.fromisoformat(scheduled_at.replace('Z', '+00:00'))
        
        # Create post in database
        post_id = await db_service.create_post(
            campaign_name="LinkedIn Scheduled Post",
            original_description=text,
            caption=text,
            scheduled_at=scheduled_dt,
            platforms=["linkedin"],
            status="scheduled"
        )
        
        return {
            "success": True,
            "message": "LinkedIn post scheduled successfully",
            "post_id": post_id,
            "scheduled_at": scheduled_at
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}
```

---

### 3. **`server/scheduler_service.py`**

Add LinkedIn posting support in the scheduler.

**Add LinkedIn posting logic in `publish_scheduled_posts()` (around line 201):**
```python
                    elif platform == "linkedin":
                        # Post to LinkedIn using the LinkedIn service
                        logger.info(f"Attempting to post to LinkedIn for post {post_id}")
                        
                        from linkedin_service import LinkedInService
                        linkedin_service = LinkedInService()
                        
                        if not linkedin_service.is_configured():
                            error_msg = "LinkedIn service not configured"
                            platform_results[platform] = {
                                "success": False,
                                "error": error_msg
                            }
                            all_successful = False
                            logger.error(f"❌ LinkedIn service not configured for post {post_id}")
                            continue
                        
                        # Post to LinkedIn with text and image support
                        result = linkedin_service.post_to_linkedin(text=caption, image_url=image_path)
                        
                        if result.get("success", False):
                            platform_results[platform] = {
                                "success": True,
                                "post_id": result.get('post_id'),
                                "url": result.get('url')
                            }
                            logger.info(f"✅ Successfully published post {post_id} to LinkedIn!")
                            logger.info(f"LinkedIn Post ID: {result.get('post_id')}")
                            logger.info(f"Post URL: {result.get('url')}")
                        else:
                            error_msg = result.get("message", "Unknown error")
                            platform_results[platform] = {
                                "success": False,
                                "error": error_msg
                            }
                            all_successful = False
                            logger.error(f"❌ Failed to publish post {post_id} to LinkedIn: {error_msg}")
```

---

### 4. **`server/env_manager.py`**

Add LinkedIn credentials to environment management.

**Update `get_platform_keys()` (around line 186):**
```python
            'linkedin': [
                'LINKEDIN_CLIENT_ID',
                'LINKEDIN_CLIENT_SECRET',
                'LINKEDIN_ACCESS_TOKEN',
                'LINKEDIN_REFRESH_TOKEN'
            ]
```

**Update `check_platform_credentials()` (around line 209):**
```python
            'linkedin': ['LINKEDIN_CLIENT_ID', 'LINKEDIN_CLIENT_SECRET', 'LINKEDIN_ACCESS_TOKEN']
```

---

### 5. **`docker-compose.yml`**

Add LinkedIn environment variables.

**Add these lines in the `environment` section (around line 62):**
```yaml
      LINKEDIN_CLIENT_ID: ${LINKEDIN_CLIENT_ID}
      LINKEDIN_CLIENT_SECRET: ${LINKEDIN_CLIENT_SECRET}
      LINKEDIN_ACCESS_TOKEN: ${LINKEDIN_ACCESS_TOKEN:-}
      LINKEDIN_REFRESH_TOKEN: ${LINKEDIN_REFRESH_TOKEN:-}
      # LinkedIn OAuth redirect (auto-detected from PUBLIC_DOMAIN and USE_HTTPS, or set explicitly)
      LINKEDIN_REDIRECT_URI: ${LINKEDIN_REDIRECT_URI:-}
```

---

### 6. **`.env` file**

Add LinkedIn credentials (user needs to get these from LinkedIn Developer Portal).

```env
# LinkedIn Integration
LINKEDIN_CLIENT_ID=your_linkedin_client_id
LINKEDIN_CLIENT_SECRET=your_linkedin_client_secret
LINKEDIN_ACCESS_TOKEN=
LINKEDIN_REFRESH_TOKEN=
LINKEDIN_REDIRECT_URI=
```

---

## 🚀 Setup Instructions

### 1. **Create LinkedIn App**
1. Go to https://www.linkedin.com/developers/apps
2. Create a new app
3. Under "Auth" tab, add redirect URL: `https://agentanywhere.ai/socialanywhere/social-media/linkedin/callback`
4. Request these products:
   - Sign In with LinkedIn using OpenID Connect
   - Share on LinkedIn
5. Copy Client ID and Client Secret

### 2. **Configure Environment Variables**
```bash
LINKEDIN_CLIENT_ID=your_app_client_id
LINKEDIN_CLIENT_SECRET=your_app_client_secret
LINKEDIN_ACCESS_TOKEN=  # Will be filled after OAuth
LINKEDIN_REFRESH_TOKEN=  # Will be filled after OAuth (if available)
```

### 3. **OAuth Flow**
1. User clicks "Connect LinkedIn" in Settings
2. Redirects to LinkedIn authorization
3. User authorizes
4. Callback saves tokens automatically
5. Ready to post!

---

## 📊 Features Included

✅ **OAuth 2.0 Authentication** - Secure token-based auth  
✅ **Token Auto-Refresh** - Automatic token validation and refresh  
✅ **Text Posts** - Post text content to LinkedIn  
✅ **Image Posts** - Upload and post images with text  
✅ **Scheduled Posts** - Schedule posts for future publishing  
✅ **Connection Status** - Check LinkedIn connection status  
✅ **Error Handling** - Comprehensive error messages  
✅ **Auto-Detection** - Redirect URI auto-detection from domain  

---

## 🔧 Testing

After integration, test with:

```bash
# Check LinkedIn status
curl http://localhost:8000/socialanywhere/api/linkedin/status

# Test connection
curl http://localhost:8000/socialanywhere/social-media/linkedin/status

# Post to LinkedIn (after OAuth)
curl -X POST http://localhost:8000/socialanywhere/api/linkedin/post \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello LinkedIn! 🚀"}'
```

---

## ⚠️ Important Notes

1. **Refresh Tokens**: By default, LinkedIn doesn't provide refresh tokens. You need Marketing Developer Platform (MDP) approval for programmatic refresh tokens.

2. **Redirect URI**: Must match exactly in LinkedIn app settings and your environment.

3. **Scopes**: Current implementation uses:
   - `openid` - Required for authentication
   - `profile` - Basic profile info
   - `w_member_social` - Permission to post on behalf of user

4. **Image Upload**: Uses LinkedIn's 2-step upload process (register + upload binary)

---

## 🎯 Next Steps

1. Apply all modifications listed above
2. Rebuild Docker containers
3. Configure LinkedIn app credentials
4. Test OAuth flow
5. Test posting functionality

Would you like me to start applying these modifications automatically?

