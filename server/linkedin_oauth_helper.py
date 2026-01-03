"""
LinkedIn OAuth2 Helper Functions
Implements dynamic LinkedIn OAuth2 flow similar to Reddit
"""

import os
import requests
from typing import Dict, Optional, List
from urllib.parse import urlencode

LINKEDIN_CLIENT_ID = os.getenv("LINKEDIN_CLIENT_ID")
LINKEDIN_CLIENT_SECRET = os.getenv("LINKEDIN_CLIENT_SECRET")

# Auto-detect redirect URI from PUBLIC_DOMAIN and USE_HTTPS, similar to Facebook
def _get_linkedin_redirect_uri():
    """Auto-detect LinkedIn redirect URI from environment variables"""
    # Check if explicitly set
    explicit_uri = os.getenv("LINKEDIN_REDIRECT_URI")
    if explicit_uri:
        return explicit_uri
    
    # Auto-detect from PUBLIC_DOMAIN and USE_HTTPS
    public_domain = os.getenv("PUBLIC_DOMAIN", "localhost:8000")
    use_https = os.getenv("USE_HTTPS", "false").lower() == "true"
    
    scheme = "https" if use_https else "http"
    # Handle port in domain
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
    
    return f"{scheme}://{domain_with_port}/socialanywhere/social-media/linkedin/callback"

LINKEDIN_REDIRECT_URI = _get_linkedin_redirect_uri()

def get_linkedin_auth_url(state: str, scopes: List[str] = None) -> str:
    """
    Generate LinkedIn OAuth authorization URL
    
    Args:
        state: Random state string for CSRF protection
        scopes: List of permission scopes (default: openid, profile, w_member_social)
                Note: Only request scopes that are enabled for your app in LinkedIn Developer Portal
    
    Returns:
        Authorization URL string
    """
    if scopes is None:
        # Use OpenID Connect scopes (openid, profile) + posting permission (w_member_social)
        # Only request scopes that are available without special approval
        scopes = ["openid", "profile", "w_member_social"]
    
    scope_string = " ".join(scopes)
    
    params = {
        "response_type": "code",
        "client_id": LINKEDIN_CLIENT_ID,
        "redirect_uri": LINKEDIN_REDIRECT_URI,
        "state": state,
        "scope": scope_string
    }
    
    auth_url = f"https://www.linkedin.com/oauth/v2/authorization?{urlencode(params)}"
    
    return auth_url

def exchange_code_for_tokens(code: str) -> Dict:
    """
    Exchange authorization code for access and refresh tokens
    
    Args:
        code: Authorization code from LinkedIn callback
    
    Returns:
        Dict with access_token, refresh_token (if available), expires_in, scope
    """
    url = "https://www.linkedin.com/oauth/v2/accessToken"
    
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": LINKEDIN_REDIRECT_URI,
        "client_id": LINKEDIN_CLIENT_ID,
        "client_secret": LINKEDIN_CLIENT_SECRET
    }
    
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    response = requests.post(url, headers=headers, data=data)
    response.raise_for_status()
    return response.json()

def get_linkedin_user_info(access_token: str) -> Dict:
    """
    Get authenticated user's LinkedIn profile info
    
    Args:
        access_token: Valid access token
    
    Returns:
        Dict with user profile data (id, firstName, lastName, etc.)
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
        "X-Restli-Protocol-Version": "2.0.0"
    }
    
    # Try OpenID Connect UserInfo endpoint first (for openid/profile scopes)
    try:
        response = requests.get(
            "https://api.linkedin.com/v2/userinfo",
            headers=headers,
            timeout=10
        )
        if response.status_code == 200:
            user_data = response.json()
            # OpenID Connect UserInfo returns 'sub' as the user ID
            # Convert to expected format
            return {
                "id": user_data.get("sub", ""),
                "localizedFirstName": user_data.get("given_name", ""),
                "localizedLastName": user_data.get("family_name", ""),
                "email": user_data.get("email", "")
            }
    except Exception as e:
        # Fallback to /v2/me with minimal projection
        pass
    
    # Fallback: Use /v2/me with minimal projection (just ID)
    # This works with both OpenID Connect and legacy scopes
    response = requests.get(
        "https://api.linkedin.com/v2/me?projection=(id)",
        headers=headers,
        timeout=10
    )
    
    response.raise_for_status()
    user_data = response.json()
    
    # If we only got ID, try to get basic info
    if "id" in user_data and len(user_data) == 1:
        # Try to get name fields
        try:
            name_response = requests.get(
                "https://api.linkedin.com/v2/me?projection=(localizedFirstName,localizedLastName)",
                headers=headers,
                timeout=10
            )
            if name_response.status_code == 200:
                name_data = name_response.json()
                user_data.update(name_data)
        except:
            pass  # If we can't get name, that's okay - we have the ID which is what we need
    
    return user_data

def refresh_access_token(refresh_token: str) -> Dict:
    """
    Use refresh token to get new access token (if refresh token is available)
    Note: Programmatic refresh tokens require MDP approval
    
    Args:
        refresh_token: Valid refresh token
    
    Returns:
        Dict with new access_token and expires_in
    """
    url = "https://www.linkedin.com/oauth/v2/accessToken"
    
    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": LINKEDIN_CLIENT_ID,
        "client_secret": LINKEDIN_CLIENT_SECRET
    }
    
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    response = requests.post(url, headers=headers, data=data)
    response.raise_for_status()
    return response.json()

