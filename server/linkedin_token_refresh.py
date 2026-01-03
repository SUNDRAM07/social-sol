"""
LinkedIn Token Refresh Service
Handles LinkedIn access token validation and refresh logic
"""

import os
import logging
import requests
from typing import Optional
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LinkedInTokenRefresh:
    """LinkedIn token refresh service - handles access token validation and refresh"""
    
    def __init__(self):
        self.client_id = os.getenv('LINKEDIN_CLIENT_ID')
        self.client_secret = os.getenv('LINKEDIN_CLIENT_SECRET')
        self.access_token = os.getenv('LINKEDIN_ACCESS_TOKEN')
        self.refresh_token = os.getenv('LINKEDIN_REFRESH_TOKEN')  # May be None if not MDP approved
        self.api_base = "https://api.linkedin.com/v2"

    def refresh_access_token(self) -> bool:
        """Refresh the LinkedIn access token using the refresh token"""
        if not self.refresh_token or self.refresh_token == "N/A":
            logger.warning("⚠️ No refresh token available - user will need to re-authenticate")
            return False

        try:
            logger.info("🔄 Refreshing LinkedIn access token...")
            
            from linkedin_oauth_helper import refresh_access_token
            
            token_data = refresh_access_token(self.refresh_token)
            
            new_access_token = token_data.get('access_token')
            new_refresh_token = token_data.get('refresh_token', self.refresh_token)
            
            if new_access_token:
                # Update environment variables
                os.environ['LINKEDIN_ACCESS_TOKEN'] = new_access_token
                if new_refresh_token != self.refresh_token:
                    os.environ['LINKEDIN_REFRESH_TOKEN'] = new_refresh_token
                
                # Update instance variables
                self.access_token = new_access_token
                self.refresh_token = new_refresh_token
                
                logger.info("✅ LinkedIn access token refreshed successfully")
                return True
            else:
                logger.error(f"❌ No access token in response: {token_data}")
                return False

        except Exception as e:
            logger.error(f"❌ Exception during token refresh: {e}")
            return False

    def _reload_token_from_env(self):
        """Reload token from environment variables (in case it was updated)"""
        # Always reload from .env file to ensure we have the latest token
        # This is important because tokens can be updated after the service is initialized
        try:
            from dotenv import load_dotenv
            # Reload .env file to pick up new values (override existing env vars)
            load_dotenv(override=True)
            self.access_token = os.getenv('LINKEDIN_ACCESS_TOKEN')
            self.refresh_token = os.getenv('LINKEDIN_REFRESH_TOKEN')
        except Exception as e:
            # Fallback to just reading from os.environ if dotenv fails
            self.access_token = os.getenv('LINKEDIN_ACCESS_TOKEN')
            self.refresh_token = os.getenv('LINKEDIN_REFRESH_TOKEN')
            logger.debug(f"Using environment variables directly: {e}")

    def is_access_token_valid(self) -> bool:
        """Check if current access token is valid"""
        # Reload token from environment in case it was updated
        self._reload_token_from_env()
        
        if not self.access_token:
            logger.warning("No LinkedIn access token found in environment")
            return False

        try:
            headers = {
                "Authorization": f"Bearer {self.access_token}"
            }
            
            # For OpenID Connect scopes (openid, profile), use /v2/userinfo
            # This is the correct endpoint for modern LinkedIn OAuth
            userinfo_response = requests.get(
                "https://api.linkedin.com/v2/userinfo",
                headers=headers,
                timeout=10
            )
            
            if userinfo_response.status_code == 200:
                logger.info("✅ LinkedIn token validated successfully via /v2/userinfo")
                return True
            elif userinfo_response.status_code == 401:
                logger.warning("LinkedIn token expired or invalid (401)")
                return False
            else:
                # Log error for debugging
                try:
                    error_data = userinfo_response.json()
                    logger.error(f"LinkedIn token validation failed: {userinfo_response.status_code} - {error_data}")
                except:
                    logger.error(f"LinkedIn token validation failed: {userinfo_response.status_code} - {userinfo_response.text[:200]}")
                return False
                
        except Exception as e:
            logger.warning(f"Access token validation failed: {e}")
            return False

    def get_valid_access_token(self) -> Optional[str]:
        """Get a valid access token, refreshing if necessary"""
        # Reload token from environment in case it was updated
        self._reload_token_from_env()
        
        if not self.is_access_token_valid():
            logger.info("Access token invalid, attempting refresh...")
            if not self.refresh_access_token():
                logger.error("Failed to refresh access token - user needs to re-authenticate")
                return None
        
        return self.access_token

    def get_headers(self) -> dict:
        """Get headers with valid access token"""
        token = self.get_valid_access_token()
        if not token:
            return {
                "Authorization": "Bearer invalid_token",
                "X-Restli-Protocol-Version": "2.0.0"
            }
        
        return {
            "Authorization": f"Bearer {token}",
            "X-Restli-Protocol-Version": "2.0.0"
        }

    def test_connection(self) -> bool:
        """Test LinkedIn connection"""
        try:
            # Reload token from environment first
            self._reload_token_from_env()
            headers = self.get_headers()
            
            # Use /v2/userinfo for OpenID Connect tokens
            response = requests.get(
                "https://api.linkedin.com/v2/userinfo",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                user_info = response.json()
                user_id = user_info.get('sub', 'Unknown')  # OpenID Connect uses 'sub' for user ID
                user_name = user_info.get('name', user_info.get('given_name', ''))
                logger.info(f"✅ LinkedIn connected successfully (User: {user_name}, ID: {user_id})")
                return True
            else:
                error_msg = response.text if response.text else f"HTTP {response.status_code}"
                logger.error(f"❌ LinkedIn connection failed: {response.status_code} - {error_msg}")
                return False
        except Exception as e:
            logger.error(f"❌ LinkedIn connection error: {e}")
            return False

if __name__ == "__main__":
    # Test the token refresh
    service = LinkedInTokenRefresh()
    
    if not all([service.client_id, service.client_secret]):
        logger.error("❌ Missing LinkedIn credentials in environment variables")
        exit(1)
    
    logger.info("🧪 Testing LinkedIn token refresh...")
    
    if service.test_connection():
        logger.info("✅ LinkedIn integration working!")
    else:
        logger.error("❌ LinkedIn integration failed")
        exit(1)

