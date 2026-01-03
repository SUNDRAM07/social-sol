import os
import re
from typing import Dict, Optional, List
from pathlib import Path


class EnvManager:
    """Manages environment variable files securely"""
    
    def __init__(self, env_file_path: str = ".env", create_if_missing: bool = False):
        self.env_file_path = Path(env_file_path)
        if create_if_missing:
            self.ensure_env_file_exists()
    
    def ensure_env_file_exists(self):
        """Create .env file if it doesn't exist"""
        if not self.env_file_path.exists():
            self.env_file_path.touch()
    
    def read_env_vars(self) -> Dict[str, str]:
        """Read all environment variables from .env file"""
        env_vars = {}
        
        if not self.env_file_path.exists():
            return env_vars
        
        try:
            with open(self.env_file_path, 'r', encoding='utf-8') as file:
                for line_num, line in enumerate(file, 1):
                    line = line.strip()
                    
                    # Skip empty lines and comments
                    if not line or line.startswith('#'):
                        continue
                    
                    # Parse KEY=VALUE format
                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        
                        # Remove quotes if present
                        if value.startswith('"') and value.endswith('"'):
                            value = value[1:-1]
                        elif value.startswith("'") and value.endswith("'"):
                            value = value[1:-1]
                        
                        env_vars[key] = value
        
        except Exception as e:
            print(f"Error reading .env file: {e}")
        
        return env_vars
    
    def update_env_vars(self, updates: Dict[str, str]) -> bool:
        """Update environment variables in .env file"""
        try:
            # Read current content
            lines = []
            existing_keys = set()
            
            if self.env_file_path.exists():
                with open(self.env_file_path, 'r', encoding='utf-8') as file:
                    lines = file.readlines()
            
            # Process existing lines and update values
            for i, line in enumerate(lines):
                stripped_line = line.strip()
                
                # Skip empty lines and comments
                if not stripped_line or stripped_line.startswith('#'):
                    continue
                
                # Parse existing KEY=VALUE
                if '=' in stripped_line:
                    key = stripped_line.split('=', 1)[0].strip()
                    existing_keys.add(key)
                    
                    # Update if key is in updates
                    if key in updates:
                        # Escape quotes in the value
                        value = updates[key].replace('"', '\\"')
                        lines[i] = f'{key}="{value}"\n'
            
            # Add new variables that weren't found
            for key, value in updates.items():
                if key not in existing_keys:
                    # Escape quotes in the value
                    value = value.replace('"', '\\"')
                    lines.append(f'{key}="{value}"\n')
            
            # Write back to file
            with open(self.env_file_path, 'w', encoding='utf-8') as file:
                file.writelines(lines)
            
            # Update current process environment
            for key, value in updates.items():
                os.environ[key] = value
            
            return True
        
        except Exception as e:
            print(f"Error updating .env file: {e}")
            return False
    
    def remove_env_vars(self, keys_to_remove: list) -> bool:
        """Remove environment variables from .env file"""
        try:
            if not self.env_file_path.exists():
                return True
            
            lines = []
            with open(self.env_file_path, 'r', encoding='utf-8') as file:
                lines = file.readlines()
            
            # Filter out lines with keys to remove
            filtered_lines = []
            for line in lines:
                stripped_line = line.strip()
                
                # Keep empty lines and comments
                if not stripped_line or stripped_line.startswith('#'):
                    filtered_lines.append(line)
                    continue
                
                # Parse KEY=VALUE
                if '=' in stripped_line:
                    key = stripped_line.split('=', 1)[0].strip()
                    if key not in keys_to_remove:
                        filtered_lines.append(line)
                    else:
                        # Remove from current process environment
                        if key in os.environ:
                            del os.environ[key]
            
            # Write back filtered content
            with open(self.env_file_path, 'w', encoding='utf-8') as file:
                file.writelines(filtered_lines)
            
            return True
        
        except Exception as e:
            print(f"Error removing .env variables: {e}")
            return False
    
    def get_platform_env_keys(self, platform: str) -> list:
        """Get the environment variable keys for a specific platform"""
        platform_keys = {
            'facebook': [
                'FACEBOOK_PAGE_ID',
                'FACEBOOK_ACCESS_TOKEN'
            ],
            'instagram': [
                'INSTAGRAM_ACCESS_TOKEN',
                'INSTAGRAM_ACCOUNT_ID',
                'INSTAGRAM_FACEBOOK_PAGE_ID'
            ],
            'twitter': [
                'TWITTER_CONSUMER_KEY',
                'TWITTER_CONSUMER_SECRET', 
                'TWITTER_ACCESS_TOKEN',
                'TWITTER_ACCESS_TOKEN_SECRET',
                'TWITTER_BEARER_TOKEN',
                'TWITTER_CLIENT_ID',
                'TWITTER_CLIENT_SECRET',
                'TWITTER_USERNAME'
            ],
            'reddit': [
                'REDDIT_CLIENT_ID',
                'REDDIT_CLIENT_SECRET',
                'REDDIT_USERNAME',
                'REDDIT_PASSWORD',
                'REDDIT_USER_AGENT',
                'REDDIT_ACCESS_TOKEN',
                'REDDIT_REFRESH_TOKEN'
            ],
            'linkedin': [
                'LINKEDIN_CLIENT_ID',
                'LINKEDIN_CLIENT_SECRET',
                'LINKEDIN_ACCESS_TOKEN',
                'LINKEDIN_REFRESH_TOKEN'
            ]
        }
        return platform_keys.get(platform, [])
    
    def check_platform_credentials(self, platform: str) -> Dict[str, bool]:
        """Check if platform credentials are available"""
        platform_keys = self.get_platform_env_keys(platform)
        env_vars = self.read_env_vars()
        
        # Required keys for each platform (minimum needed for connection)
        required_keys = {
            'facebook': ['FACEBOOK_PAGE_ID', 'FACEBOOK_ACCESS_TOKEN'],
            'instagram': ['INSTAGRAM_ACCESS_TOKEN', 'INSTAGRAM_ACCOUNT_ID'],
            'twitter': ['TWITTER_CONSUMER_KEY', 'TWITTER_CONSUMER_SECRET', 
                       'TWITTER_ACCESS_TOKEN', 'TWITTER_ACCESS_TOKEN_SECRET',
                       'TWITTER_BEARER_TOKEN', 'TWITTER_CLIENT_ID', 'TWITTER_CLIENT_SECRET', 'TWITTER_USERNAME'],
            'reddit': ['REDDIT_CLIENT_ID', 'REDDIT_CLIENT_SECRET', 'REDDIT_USERNAME', 'REDDIT_PASSWORD',
                      'REDDIT_USER_AGENT', 'REDDIT_ACCESS_TOKEN', 'REDDIT_REFRESH_TOKEN'],
            'linkedin': ['LINKEDIN_CLIENT_ID', 'LINKEDIN_CLIENT_SECRET', 'LINKEDIN_ACCESS_TOKEN']
        }
        
        platform_required = required_keys.get(platform, [])
        has_required = all(key in env_vars and env_vars[key].strip() for key in platform_required)
        
        return {
            'has_credentials': has_required,
            'available_keys': [key for key in platform_keys if key in env_vars and env_vars[key].strip()],
            'missing_keys': [key for key in platform_required if key not in env_vars or not env_vars[key].strip()]
        }
    
    def get_reddit_accounts_by_user(self, user_id: str) -> List[Dict]:
        """
        Get all Reddit accounts for a specific user from database
        Returns list of dicts with account details
        """
        # For now, return empty list - will be implemented with actual database
        # This is a placeholder for the database query
        return []
    
    def save_reddit_account(self, user_id: str, reddit_user_id: str, 
                           reddit_username: str, access_token: str, 
                           refresh_token: str, expires_in: int, scopes: str):
        """
        Save or update Reddit account credentials in database
        """
        from datetime import datetime, timedelta
        
        expires_at = datetime.now() + timedelta(seconds=expires_in)
        
        # For now, just print - will be implemented with actual database
        print(f"Would save Reddit account for user {user_id}: {reddit_username}")
        print(f"Access token expires at: {expires_at}")
        print(f"Scopes: {scopes}")
        
        # TODO: Implement actual database save
        # This would be the database upsert query:
        # INSERT INTO reddit_accounts (user_id, reddit_user_id, reddit_username, access_token, refresh_token, expires_at, scopes, updated_at)
        # VALUES (%s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
        # ON CONFLICT (user_id, reddit_user_id) DO UPDATE SET ...

    def save_facebook_page(self, user_id: str, page_id: str, access_token: str, expires_in: Optional[int] = None):
        """Save Facebook page credentials (placeholder for database integration)"""
        # TODO: Implement database storage for Facebook pages
        # For now, just log the page info
        print(f"Facebook page saved: user_id={user_id}, page_id={page_id}, expires_in={expires_in}")
        return True


# Global instance - use .env in current directory, but don't create it automatically
env_manager = EnvManager('.env', create_if_missing=False)