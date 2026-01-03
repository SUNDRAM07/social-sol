"""
Twitter OAuth 2.0 Helper Functions with PKCE
Implements dynamic Twitter OAuth 2.0 flow with PKCE (similar to Reddit)
"""

import os
import requests
import base64
import secrets
import hashlib
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
from urllib.parse import quote_plus, urlencode

TWITTER_CLIENT_ID = os.getenv("TWITTER_CLIENT_ID")
TWITTER_CLIENT_SECRET = os.getenv("TWITTER_CLIENT_SECRET")

# Build redirect URI dynamically
public_domain = os.getenv("PUBLIC_DOMAIN", "localhost:8000")
use_https = os.getenv("USE_HTTPS", "false").lower() == "true"

# Always use http:// for localhost
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

TWITTER_REDIRECT_URI = os.getenv("TWITTER_REDIRECT_URI", f"{scheme}://{domain_with_port}/socialanywhere/social-media/twitter/callback")

def generate_code_verifier() -> str:
    """Generate a code verifier for PKCE"""
    return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')

def generate_code_challenge(verifier: str) -> str:
    """Generate code challenge from verifier using SHA256"""
    sha256_hash = hashlib.sha256(verifier.encode('utf-8')).digest()
    return base64.urlsafe_b64encode(sha256_hash).decode('utf-8').rstrip('=')

def get_twitter_auth_url(state: str, code_verifier: str) -> Tuple[str, str]:
    """
    Generate Twitter OAuth 2.0 authorization URL with PKCE
    
    Args:
        state: Random state string for CSRF protection
        code_verifier: Code verifier for PKCE (will be stored in state)
    
    Returns:
        Tuple of (authorization_url, code_verifier) - store code_verifier for token exchange
    """
    if not TWITTER_CLIENT_ID:
        raise ValueError("TWITTER_CLIENT_ID must be set")
    
    # Generate code challenge from verifier
    code_challenge = generate_code_challenge(code_verifier)
    
    # Twitter OAuth 2.0 scopes
    scopes = [
        "tweet.read",
        "tweet.write",
        "users.read",
        "offline.access"  # For refresh token
    ]
    scope_string = " ".join(scopes)
    
    # URL encode parameters
    redirect_uri_encoded = quote_plus(TWITTER_REDIRECT_URI)
    state_encoded = quote_plus(state)
    code_challenge_encoded = quote_plus(code_challenge)
    scope_encoded = quote_plus(scope_string)
    
    # Log the redirect URI for debugging
    print(f"🔗 Twitter OAuth Redirect URI: {TWITTER_REDIRECT_URI}")
    print(f"📝 ⚠️  IMPORTANT: Add this EXACT URL to your Twitter app settings!")
    print(f"📝   1. Go to: https://developer.twitter.com/en/portal/dashboard")
    print(f"📝   2. Click on your app")
    print(f"📝   3. Go to 'User authentication settings'")
    print(f"📝   4. Make sure app is in 'Development' mode (required for localhost)")
    print(f"📝   5. Add callback URL: {TWITTER_REDIRECT_URI}")
    print(f"📝   6. You can add multiple URLs (localhost for dev, production for deploy)")
    print(f"📝   7. Save and try again")
    
    # Warn if using localhost but might be in production mode
    if "localhost" in TWITTER_REDIRECT_URI.lower():
        print(f"⚠️  Using localhost URL - Make sure your Twitter app is in 'Development' mode!")
        print(f"⚠️  Production mode only accepts HTTPS URLs (not localhost)")
    
    auth_url = (
        f"https://twitter.com/i/oauth2/authorize?"
        f"response_type=code"
        f"&client_id={TWITTER_CLIENT_ID}"
        f"&redirect_uri={redirect_uri_encoded}"
        f"&scope={scope_encoded}"
        f"&state={state_encoded}"
        f"&code_challenge={code_challenge_encoded}"
        f"&code_challenge_method=S256"
    )
    
    return auth_url, code_verifier

def exchange_code_for_tokens(code: str, code_verifier: str) -> Dict:
    """
    Exchange authorization code for access and refresh tokens
    
    Args:
        code: Authorization code from Twitter callback
        code_verifier: Code verifier used in authorization request
    
    Returns:
        Dict with access_token, refresh_token, expires_in, scope, token_type
    """
    if not TWITTER_CLIENT_ID or not TWITTER_CLIENT_SECRET:
        raise ValueError("TWITTER_CLIENT_ID and TWITTER_CLIENT_SECRET must be set")
    
    # Prepare Basic Auth header
    auth_string = f"{TWITTER_CLIENT_ID}:{TWITTER_CLIENT_SECRET}"
    auth_bytes = auth_string.encode('ascii')
    auth_base64 = base64.b64encode(auth_bytes).decode('ascii')
    
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Basic {auth_base64}"
    }
    
    data = {
        "code": code,
        "grant_type": "authorization_code",
        "client_id": TWITTER_CLIENT_ID,
        "redirect_uri": TWITTER_REDIRECT_URI,
        "code_verifier": code_verifier
    }
    
    print(f"🔐 Exchanging Twitter code for tokens...")
    print(f"📝 Redirect URI: {TWITTER_REDIRECT_URI}")
    print(f"📝 Client ID: {TWITTER_CLIENT_ID}")
    
    response = requests.post(
        "https://api.twitter.com/2/oauth2/token",
        headers=headers,
        data=data,
        timeout=30
    )
    
    # Check for errors
    if response.status_code != 200:
        try:
            error_data = response.json()
            error_msg = error_data.get("error", "Unknown error")
            error_description = error_data.get("error_description", "")
            raise Exception(f"Twitter API error ({response.status_code}): {error_msg}. {error_description}")
        except ValueError:
            raise Exception(f"Twitter API error ({response.status_code}): {response.text}")
    
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
    if not TWITTER_CLIENT_ID or not TWITTER_CLIENT_SECRET:
        raise ValueError("TWITTER_CLIENT_ID and TWITTER_CLIENT_SECRET must be set")
    
    auth_string = f"{TWITTER_CLIENT_ID}:{TWITTER_CLIENT_SECRET}"
    auth_bytes = auth_string.encode('ascii')
    auth_base64 = base64.b64encode(auth_bytes).decode('ascii')
    
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Basic {auth_base64}"
    }
    
    data = {
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
        "client_id": TWITTER_CLIENT_ID
    }
    
    response = requests.post(
        "https://api.twitter.com/2/oauth2/token",
        headers=headers,
        data=data,
        timeout=30
    )
    
    response.raise_for_status()
    return response.json()

def get_twitter_user_info(access_token: str) -> Dict:
    """
    Get authenticated user's Twitter profile info
    
    Args:
        access_token: Valid access token
    
    Returns:
        Dict with user profile data (id, name, username, etc.)
    """
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    
    # Get user info using Twitter API v2
    response = requests.get(
        "https://api.twitter.com/2/users/me?user.fields=id,name,username,profile_image_url,verified",
        headers=headers,
        timeout=30
    )
    
    if response.status_code != 200:
        try:
            error_data = response.json()
            error_msg = error_data.get("error", "Unknown error")
            raise Exception(f"Twitter API error ({response.status_code}): {error_msg}")
        except ValueError:
            raise Exception(f"Twitter API error ({response.status_code}): {response.text}")
    
    response.raise_for_status()
    data = response.json()
    
    # Extract user data
    user_data = data.get("data", {})
    return {
        "id": user_data.get("id"),
        "name": user_data.get("name"),
        "username": user_data.get("username"),
        "profile_image_url": user_data.get("profile_image_url"),
        "verified": user_data.get("verified", False)
    }

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
        
        # Note: Update your database with new tokens here
        return token_data["access_token"]
    
    return account_data["access_token"]

