"""
Reddit OAuth2 Helper Functions
Implements dynamic Reddit OAuth2 flow similar to Facebook/Instagram
"""

import os
import requests
import base64
from typing import Dict, Optional, List
from datetime import datetime, timedelta
from urllib.parse import quote_plus

REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
# Build redirect URI dynamically
public_domain = os.getenv("PUBLIC_DOMAIN", "localhost:8000")
use_https = os.getenv("USE_HTTPS", "false").lower() == "true"

# Always use http:// for localhost (localhost doesn't have SSL by default)
if "localhost" in public_domain.lower() or public_domain.startswith("127.0.0.1"):
    scheme = "http"
    use_https = False
else:
    scheme = "https" if use_https else "http"

if use_https and ":" not in public_domain:
    domain_with_port = public_domain
elif ":" in public_domain:
    domain_with_port = public_domain
else:
    port = os.getenv("PORT", "8000")
    domain_with_port = f"{public_domain}:{port}"

REDDIT_REDIRECT_URI = os.getenv("REDDIT_REDIRECT_URI", f"{scheme}://{domain_with_port}/socialanywhere/social-media/reddit/callback")
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT", "SocialMediaAgent/1.0 by u/SuspiciousPapaya3497")

def get_reddit_auth_url(state: str, scopes: List[str] = None) -> str:
    """
    Generate Reddit OAuth authorization URL
    
    Args:
        state: Random state string for CSRF protection
        scopes: List of permission scopes (default: identity, read, submit)
    
    Returns:
        Authorization URL string
    """
    if scopes is None:
        # Request comprehensive scopes for full app functionality
        # identity: Get username and account info
        # read: Read posts and comments
        # submit: Submit posts and comments
        # history: Access user's post/comment history (needed for analytics)
        # mysubreddits: Access subscribed subreddits
        # vote: Upvote/downvote posts and comments
        scopes = ["identity", "read", "submit", "history", "mysubreddits", "vote"]
    
    scope_string = " ".join(scopes)
    
    # URL encode the redirect URI (required by Reddit)
    redirect_uri_encoded = quote_plus(REDDIT_REDIRECT_URI)
    
    # Log the redirect URI for debugging
    print(f"🔗 Reddit OAuth Redirect URI: {REDDIT_REDIRECT_URI}")
    print(f"📝 ⚠️  IMPORTANT: Add this EXACT URL to your Reddit app settings!")
    print(f"📝   1. Go to: https://www.reddit.com/prefs/apps")
    print(f"📝   2. Click on your app")
    print(f"📝   3. In 'redirect uri' field, add: {REDDIT_REDIRECT_URI}")
    print(f"📝   4. Save and try again")
    print(f"📝 Redirect URI (encoded): {redirect_uri_encoded}")
    
    auth_url = (
        f"https://www.reddit.com/api/v1/authorize?"
        f"client_id={REDDIT_CLIENT_ID}"
        f"&response_type=code"
        f"&state={state}"
        f"&redirect_uri={redirect_uri_encoded}"
        f"&duration=permanent"  # Request permanent refresh token
        f"&scope={scope_string}"
    )
    
    return auth_url
    
def exchange_code_for_tokens(code: str) -> Dict:
    """
    Exchange authorization code for access and refresh tokens
    
    Args:
        code: Authorization code from Reddit callback
    
    Returns:
        Dict with access_token, refresh_token, expires_in, scope
    """
    if not REDDIT_CLIENT_ID or not REDDIT_CLIENT_SECRET:
        raise ValueError("REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET must be set")
    
    # Reddit requires HTTP Basic Authentication
    auth_string = f"{REDDIT_CLIENT_ID}:{REDDIT_CLIENT_SECRET}"
    auth_bytes = auth_string.encode('ascii')
    auth_base64 = base64.b64encode(auth_bytes).decode('ascii')
    
    headers = {
        "Authorization": f"Basic {auth_base64}",
        "User-Agent": REDDIT_USER_AGENT
    }
    
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDDIT_REDIRECT_URI
    }
    
    print(f"🔐 Exchanging Reddit code for tokens...")
    print(f"📝 Redirect URI: {REDDIT_REDIRECT_URI}")
    print(f"📝 Client ID: {REDDIT_CLIENT_ID}")
    print(f"📝 User-Agent: {REDDIT_USER_AGENT}")
    
    response = requests.post(
        "https://www.reddit.com/api/v1/access_token",
        headers=headers,
        data=data
    )
    
    # Check for errors before raising
    if response.status_code != 200:
        try:
            error_data = response.json()
            error_msg = error_data.get("error", "Unknown error")
            error_description = error_data.get("error_description", "")
            raise Exception(f"Reddit API error ({response.status_code}): {error_msg}. {error_description}")
        except ValueError:
            # Response is not JSON
            raise Exception(f"Reddit API error ({response.status_code}): {response.text}")
    
    response.raise_for_status()
    return response.json()

def refresh_access_token(refresh_token: str) -> Dict:
    """
    Use refresh token to get new access token
    
    Args:
        refresh_token: Valid refresh token
    
    Returns:
        Dict with new access_token and expires_in
    """
    auth_string = f"{REDDIT_CLIENT_ID}:{REDDIT_CLIENT_SECRET}"
    auth_bytes = auth_string.encode('ascii')
    auth_base64 = base64.b64encode(auth_bytes).decode('ascii')
    
    headers = {
        "Authorization": f"Basic {auth_base64}",
        "User-Agent": REDDIT_USER_AGENT
    }
    
    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token
    }
    
    response = requests.post(
        "https://www.reddit.com/api/v1/access_token",
        headers=headers,
        data=data
    )
    
    response.raise_for_status()
    return response.json()

def get_reddit_user_info(access_token: str) -> Dict:
    """
    Get authenticated user's Reddit profile info
    
    Args:
        access_token: Valid access token
    
    Returns:
        Dict with user profile data (id, name, etc.)
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
        "User-Agent": REDDIT_USER_AGENT
    }
    
    response = requests.get(
        "https://oauth.reddit.com/api/v1/me",
        headers=headers
    )
    
    response.raise_for_status()
    return response.json()

def is_token_expired(expires_at: datetime) -> bool:
    """Check if token has expired"""
    return datetime.now() >= expires_at

def get_valid_access_token(account_data: Dict) -> str:
    """
    Get valid access token, refreshing if necessary
    
    Args:
        account_data: Dict with access_token, refresh_token, expires_at
    
    Returns:
        Valid access token string
    """
    expires_at = account_data.get("expires_at")
    
    # If token expires in less than 5 minutes, refresh it
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    
    if is_token_expired(expires_at - timedelta(minutes=5)):
        # Refresh the token
        refresh_token = account_data.get("refresh_token")
        token_data = refresh_access_token(refresh_token)
        
        # Note: Reddit refresh tokens are consumed and new ones issued
        # Update your database with new tokens here
        return token_data["access_token"]
    
    return account_data["access_token"]