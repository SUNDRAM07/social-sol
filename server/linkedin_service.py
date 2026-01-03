"""
LinkedIn Service for Social Media Agent
Integrates LinkedIn posting functionality into the main social media agent
"""

import os
import logging
import json
import requests
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from linkedin_token_refresh import LinkedInTokenRefresh

logger = logging.getLogger(__name__)

class LinkedInService:
    """Service class for LinkedIn operations in the social media agent"""
    
    def __init__(self):
        """Initialize LinkedIn service"""
        self.adapter = None
        self.api_base = "https://api.linkedin.com/v2"
        
        # Initialize token refresh service
        self.token_service = LinkedInTokenRefresh()
        
        self._initialize_adapter()
    
    def _initialize_adapter(self):
        """Initialize LinkedIn adapter with token management"""
        try:
            # Test connection and refresh token if needed
            if self.token_service.test_connection():
                logger.info("✅ LinkedIn service initialized successfully")
                self.adapter = True
            else:
                logger.warning("⚠️ LinkedIn service not connected - credentials may be missing or invalid")
                self.adapter = False
        except Exception as e:
            logger.error(f"❌ Failed to initialize LinkedIn service: {e}")
            self.adapter = False

    def _get_headers(self) -> dict:
        """Get headers with valid access token"""
        return self.token_service.get_headers()

    def _get_user_urn(self) -> Optional[str]:
        """Get the current user's LinkedIn URN (person ID)"""
        try:
            headers = self._get_headers()
            
            # For OpenID Connect, use /v2/userinfo to get the user ID (sub)
            response = requests.get(
                "https://api.linkedin.com/v2/userinfo",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                user_data = response.json()
                # OpenID Connect returns 'sub' as the user ID
                person_id = user_data.get('sub')
                if person_id:
                    return f"urn:li:person:{person_id}"
                return None
            else:
                logger.error(f"Failed to get user URN: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"Error getting user URN: {e}")
            return None
    
    def _register_image_upload(self, author_urn: str) -> Optional[Dict[str, Any]]:
        """
        Step 1: Register an image upload with LinkedIn
        Returns upload URL and asset URN
        """
        try:
            headers = self._get_headers()
            headers["Content-Type"] = "application/json"
            
            # Register upload request
            register_data = {
                "registerUploadRequest": {
                    "recipes": [
                        "urn:li:digitalmediaRecipe:feedshare-image"
                    ],
                    "owner": author_urn,
                    "serviceRelationships": [
                        {
                            "relationshipType": "OWNER",
                            "identifier": "urn:li:userGeneratedContent"
                        }
                    ]
                }
            }
            
            response = requests.post(
                f"{self.api_base}/assets?action=registerUpload",
                headers=headers,
                json=register_data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                upload_url = result['value']['uploadMechanism']['com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest']['uploadUrl']
                asset_urn = result['value']['asset']
                logger.info(f"✅ LinkedIn image upload registered: {asset_urn}")
                return {
                    "upload_url": upload_url,
                    "asset_urn": asset_urn
                }
            else:
                logger.error(f"Failed to register image upload: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error registering image upload: {e}")
            return None
    
    def _upload_image_binary(self, upload_url: str, image_path: str) -> bool:
        """
        Step 2: Upload the image binary to LinkedIn
        """
        try:
            # Read image file
            with open(image_path, 'rb') as image_file:
                image_data = image_file.read()
            
            # Upload to LinkedIn
            headers = {
                "Authorization": f"Bearer {self.token_service.access_token}"
            }
            
            response = requests.put(
                upload_url,
                headers=headers,
                data=image_data,
                timeout=60
            )
            
            if response.status_code == 201:
                logger.info(f"✅ Image uploaded successfully to LinkedIn")
                return True
            else:
                logger.error(f"Failed to upload image: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error uploading image binary: {e}")
            return False

    def test_connection(self) -> Dict[str, Any]:
        """Test LinkedIn connection"""
        try:
            if self.token_service.test_connection():
                return {"status": "connected", "message": "LinkedIn connection successful"}
            else:
                return {"status": "disconnected", "message": "LinkedIn connection failed - please re-authenticate"}
        except Exception as e:
            return {"status": "error", "message": f"LinkedIn connection error: {e}"}

    def post_to_linkedin(self, text: str, image_url: Optional[str] = None) -> Dict[str, Any]:
        """
        Post content to LinkedIn personal profile with optional image
        
        Args:
            text: Post text content
            image_url: Optional image URL (local file path)
        
        Returns:
            Dict with success status, post_id, url, etc.
        """
        try:
            if not self.adapter:
                return {"success": False, "message": "LinkedIn service not initialized"}

            headers = self._get_headers()
            
            # Get user URN
            author_urn = self._get_user_urn()
            if not author_urn:
                return {
                    "success": False,
                    "message": "Failed to get user information. Please re-authenticate."
                }
            
            # Handle image upload if image_url is provided
            media_asset_urn = None
            if image_url:
                logger.info(f"📸 Uploading image to LinkedIn: {image_url}")
                
                # Step 1: Register the upload
                upload_info = self._register_image_upload(author_urn)
                if not upload_info:
                    return {
                        "success": False,
                        "message": "Failed to register image upload with LinkedIn"
                    }
                
                # Step 2: Upload the image binary
                upload_success = self._upload_image_binary(
                    upload_info["upload_url"],
                    image_url
                )
                if not upload_success:
                    return {
                        "success": False,
                        "message": "Failed to upload image to LinkedIn"
                    }
                
                media_asset_urn = upload_info["asset_urn"]
                logger.info(f"✅ Image uploaded successfully: {media_asset_urn}")
            
            # Prepare UGC post payload
            post_data = {
                "author": author_urn,
                "lifecycleState": "PUBLISHED",
                "specificContent": {
                    "com.linkedin.ugc.ShareContent": {
                        "shareCommentary": {
                            "text": text
                        },
                        "shareMediaCategory": "IMAGE" if media_asset_urn else "NONE"
                    }
                },
                "visibility": {
                    "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
                }
            }
            
            # Add media if we have an image
            if media_asset_urn:
                post_data["specificContent"]["com.linkedin.ugc.ShareContent"]["media"] = [
                    {
                        "status": "READY",
                        "description": {
                            "text": "Image"
                        },
                        "media": media_asset_urn,
                        "title": {
                            "text": "Image"
                        }
                    }
                ]
            
            # Submit post
            response = requests.post(
                f"{self.api_base}/ugcPosts",
                headers=headers,
                json=post_data,
                timeout=30
            )

            if response.status_code == 201:
                result = response.json()
                post_id = result.get('id')
                
                # Extract post ID from URN if needed
                if post_id and post_id.startswith('urn:li:ugcPost:'):
                    # Extract the numeric ID
                    post_id_short = post_id.split(':')[-1]
                    post_url = f"https://www.linkedin.com/feed/update/{post_id_short}"
                else:
                    post_url = f"https://www.linkedin.com/feed/update/{post_id}"
                
                return {
                    "success": True,
                    "message": "Post submitted successfully",
                    "url": post_url,
                    "post_id": post_id
                }
            elif response.status_code == 401:
                # Token expired or invalid
                return {
                    "success": False,
                    "message": "LinkedIn access token expired. Please re-authenticate.",
                    "requires_reauth": True
                }
            else:
                error_data = response.json() if response.content else {}
                error_msg = error_data.get('message', f'HTTP {response.status_code}')
                
                logger.error(f"LinkedIn API error: {error_msg}")
                return {
                    "success": False,
                    "message": f"LinkedIn API error: {error_msg}",
                    "status_code": response.status_code
                }

        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Network error posting to LinkedIn: {e}")
            return {"success": False, "message": f"Network error: {str(e)}"}
        except Exception as e:
            logger.error(f"❌ Error posting to LinkedIn: {e}")
            return {"success": False, "message": f"Posting error: {e}"}

    def get_service_status(self) -> Dict[str, Any]:
        """Get the current status of the LinkedIn service"""
        try:
            if not all([self.token_service.client_id, self.token_service.client_secret]):
                return {
                    "status": "disconnected",
                    "message": "Missing LinkedIn credentials. Please set LINKEDIN_CLIENT_ID and LINKEDIN_CLIENT_SECRET environment variables."
                }

            if self.token_service.test_connection():
                return {
                    "status": "connected",
                    "message": "LinkedIn service is ready",
                    "token_info": "Access token will auto-validate when needed"
                }
            else:
                return {
                    "status": "disconnected", 
                    "message": "LinkedIn connection failed - please re-authenticate"
                }
        except Exception as e:
            return {
                "status": "error",
                "message": f"LinkedIn service error: {e}"
            }

    def is_configured(self) -> bool:
        """Check if LinkedIn service is properly configured"""
        return self.adapter is not None and self.adapter

# Create global instance
linkedin_service = LinkedInService()

