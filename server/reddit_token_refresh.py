import os
import requests
import base64
import logging
from typing import Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RedditTokenRefresh:
    """Simple Reddit token refresh service - only handles access token automation"""
    
    def __init__(self):
        self.client_id = os.getenv('REDDIT_CLIENT_ID')
        self.client_secret = os.getenv('REDDIT_CLIENT_SECRET')
        self.refresh_token = os.getenv('REDDIT_REFRESH_TOKEN')
        self.access_token = os.getenv('REDDIT_ACCESS_TOKEN')
        self.user_agent = os.getenv('REDDIT_USER_AGENT', 'Social Media Agent v2/1.0 by u/SuspiciousPapaya3497')
        self.api_base = "https://oauth.reddit.com"

    def refresh_access_token(self) -> bool:
        """Refresh the Reddit access token using the refresh token"""
        if not self.refresh_token or self.refresh_token == "N/A":
            logger.error("❌ No refresh token available")
            return False

        try:
            logger.info("🔄 Refreshing Reddit access token...")
            
            # Create auth header
            auth_string = f'{self.client_id}:{self.client_secret}'
            auth_header = base64.b64encode(auth_string.encode()).decode()

            headers = {
                'User-Agent': self.user_agent,
                'Authorization': f'Basic {auth_header}',
                'Content-Type': 'application/x-www-form-urlencoded'
            }

            data = {
                'grant_type': 'refresh_token',
                'refresh_token': self.refresh_token
            }

            response = requests.post('https://www.reddit.com/api/v1/access_token',
                                   headers=headers, data=data, timeout=30)

            if response.status_code == 200:
                tokens = response.json()
                new_access_token = tokens.get('access_token')
                new_refresh_token = tokens.get('refresh_token', self.refresh_token)

                if new_access_token:
                    # Update environment variables
                    os.environ['REDDIT_ACCESS_TOKEN'] = new_access_token
                    if new_refresh_token != self.refresh_token:
                        os.environ['REDDIT_REFRESH_TOKEN'] = new_refresh_token
                    
                    # Update instance variables
                    self.access_token = new_access_token
                    self.refresh_token = new_refresh_token
                    
                    logger.info("✅ Reddit access token refreshed successfully")
                    return True
                else:
                    logger.error(f"❌ No access token in response: {response.text}")
                    return False
            else:
                logger.error(f"❌ Failed to refresh token: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            logger.error(f"❌ Exception during token refresh: {e}")
            return False

    def is_access_token_valid(self) -> bool:
        """Check if current access token is valid"""
        if not self.access_token:
            return False

        try:
            headers = {
                "User-Agent": self.user_agent,
                "Authorization": f"Bearer {self.access_token}"
            }
            response = requests.get(f"{self.api_base}/api/v1/me", headers=headers, timeout=5)
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Access token validation failed: {e}")
            return False

    def get_valid_access_token(self) -> Optional[str]:
        """Get a valid access token, refreshing if necessary"""
        if not self.is_access_token_valid():
            logger.info("Access token invalid, refreshing...")
            if not self.refresh_access_token():
                logger.error("Failed to refresh access token")
                return None
        
        return self.access_token

    def get_headers(self) -> dict:
        """Get headers with valid access token"""
        token = self.get_valid_access_token()
        if not token:
            return {
                "User-Agent": self.user_agent,
                "Authorization": "Bearer invalid_token"
            }
        
        return {
            "User-Agent": self.user_agent,
            "Authorization": f"Bearer {token}"
        }

    def test_connection(self) -> bool:
        """Test Reddit connection"""
        try:
            headers = self.get_headers()
            response = requests.get(f"{self.api_base}/api/v1/me", headers=headers, timeout=10)
            
            if response.status_code == 200:
                user_info = response.json()
                username = user_info.get('name', 'Unknown')
                logger.info(f"✅ Reddit connected as: {username}")
                return True
            else:
                logger.error(f"❌ Reddit connection failed: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"❌ Reddit connection error: {e}")
            return False

if __name__ == "__main__":
    # Test the token refresh
    service = RedditTokenRefresh()
    
    if not all([service.client_id, service.client_secret, service.refresh_token]):
        logger.error("❌ Missing Reddit credentials in environment variables")
        exit(1)
    
    logger.info("🧪 Testing Reddit token refresh...")
    
    if service.test_connection():
        logger.info("✅ Reddit integration working!")
    else:
        logger.error("❌ Reddit integration failed")
        exit(1)
