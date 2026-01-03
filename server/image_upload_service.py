"""
Image Upload Service for Social Media Agent
Handles uploading images to public hosting services for Instagram API compatibility
"""

import os
import logging
import requests
import time
import hashlib
import hmac
from typing import Dict, Any, Optional
from PIL import Image
import base64
from io import BytesIO

logger = logging.getLogger(__name__)

class ImageUploadService:
    """Service for uploading images to public hosting services"""
    
    def __init__(self):
        self.imgur_client_id = os.getenv("IMGUR_CLIENT_ID")
        self.cloudinary_url = os.getenv("CLOUDINARY_URL")
        self.aws_s3_bucket = os.getenv("AWS_S3_BUCKET")
        self.aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
        self.aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    
    def upload_to_imgur(self, image_path: str) -> Optional[str]:
        """
        Upload image to Imgur (free image hosting)
        
        Args:
            image_path: Local path to image file
            
        Returns:
            Public URL of uploaded image, or None if upload fails
        """
        # Try with client ID if configured, otherwise use anonymous upload
        if not self.imgur_client_id:
            logger.info("IMGUR_CLIENT_ID not configured, trying anonymous upload")
            return self._upload_to_imgur_anonymous(image_path)
        
        try:
            # Prepare image data
            with open(image_path, 'rb') as image_file:
                image_data = base64.b64encode(image_file.read()).decode('utf-8')
            
            # Upload to Imgur
            headers = {
                'Authorization': f'Client-ID {self.imgur_client_id}',
                'Content-Type': 'application/json'
            }
            
            data = {
                'image': image_data,
                'type': 'base64'
            }
            
            response = requests.post(
                'https://api.imgur.com/3/image',
                headers=headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    image_url = result['data']['link']
                    logger.info(f"✅ Image uploaded to Imgur: {image_url}")
                    return image_url
                else:
                    logger.error(f"Imgur upload failed: {result.get('data', {}).get('error', 'Unknown error')}")
            else:
                logger.error(f"Imgur API error: {response.status_code} - {response.text}")
                
        except Exception as e:
            logger.error(f"Error uploading to Imgur: {e}")
        
        return None
    
    def _upload_to_imgur_anonymous(self, image_path: str) -> Optional[str]:
        """
        Upload image to Imgur anonymously (no API key required)
        
        Args:
            image_path: Local path to image file
            
        Returns:
            Public URL of uploaded image, or None if upload fails
        """
        try:
            # Prepare image data
            with open(image_path, 'rb') as image_file:
                image_data = base64.b64encode(image_file.read()).decode('utf-8')
            
            # Upload to Imgur anonymously
            headers = {
                'Content-Type': 'application/json'
            }
            
            data = {
                'image': image_data,
                'type': 'base64'
            }
            
            response = requests.post(
                'https://api.imgur.com/3/image',
                headers=headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    image_url = result['data']['link']
                    logger.info(f"✅ Image uploaded to Imgur (anonymous): {image_url}")
                    return image_url
                else:
                    logger.error(f"Imgur anonymous upload failed: {result.get('data', {}).get('error', 'Unknown error')}")
            else:
                logger.error(f"Imgur anonymous API error: {response.status_code} - {response.text}")
                
        except Exception as e:
            logger.error(f"Error uploading to Imgur anonymously: {e}")
        
        return None
    
    def upload_to_cloudinary(self, image_path: str) -> Optional[str]:
        """
        Upload image to Cloudinary using upload preset (simpler method)
        
        Args:
            image_path: Local path to image file
            
        Returns:
            Public URL of uploaded image, or None if upload fails
        """
        if not self.cloudinary_url:
            logger.warning("CLOUDINARY_URL not configured")
            return None
        
        try:
            # Parse Cloudinary URL: cloudinary://api_key:api_secret@cloud_name
            if '://' in self.cloudinary_url:
                # Extract cloud name from URL
                url_parts = self.cloudinary_url.replace('cloudinary://', '').split('@')
                if len(url_parts) == 2:
                    cloud_name = url_parts[1]
                else:
                    logger.error("Invalid CLOUDINARY_URL format")
                    return None
            else:
                logger.error("CLOUDINARY_URL must start with 'cloudinary://'")
                return None
            
            # Get upload preset from environment or use default
            upload_preset = os.getenv("CLOUDINARY_UPLOAD_PRESET", "ml_default")
            
            # Upload to Cloudinary using upload preset (no signature needed)
            with open(image_path, 'rb') as image_file:
                files = {'file': image_file}
                data = {
                    'upload_preset': upload_preset,
                    'folder': 'social_media_agent'
                }
                
                response = requests.post(
                    f'https://api.cloudinary.com/v1_1/{cloud_name}/image/upload',
                    files=files,
                    data=data,
                    timeout=30
                )
            
            if response.status_code == 200:
                result = response.json()
                image_url = result.get('secure_url')
                if image_url:
                    logger.info(f"✅ Image uploaded to Cloudinary: {image_url}")
                    return image_url
                else:
                    logger.error(f"Cloudinary upload failed: {result}")
            else:
                logger.error(f"Cloudinary API error: {response.status_code} - {response.text}")
                logger.error("Note: You may need to create an upload preset in your Cloudinary dashboard")
                
        except Exception as e:
            logger.error(f"Error uploading to Cloudinary: {e}")
        
        return None
    
    def upload_to_public_hosting(self, image_path: str) -> Optional[str]:
        """
        Upload image to the first available public hosting service
        
        Args:
            image_path: Local path to image file
            
        Returns:
            Public URL of uploaded image, or None if all uploads fail
        """
        # Try different hosting services in order of preference
        upload_methods = [
            ("Cloudinary", self.upload_to_cloudinary),
            ("Imgur", self.upload_to_imgur),
        ]
        
        for service_name, upload_method in upload_methods:
            logger.info(f"Attempting to upload to {service_name}...")
            try:
                result = upload_method(image_path)
                if result:
                    return result
            except Exception as e:
                logger.warning(f"Failed to upload to {service_name}: {e}")
                continue
        
        logger.error("All image upload methods failed")
        return None
    
    def get_public_image_url(self, image_path: str) -> Optional[str]:
        """
        Get a public URL for an image, uploading if necessary
        
        Args:
            image_path: Local path to image file
            
        Returns:
            Public URL of the image, or None if unable to get public URL
        """
        # If it's already a public URL, return as-is
        if image_path.startswith(("http://", "https://")):
            return image_path
        
        # Check if we have a public domain configured
        public_domain = os.getenv("PUBLIC_DOMAIN")
        
        # If we have a public domain (not localhost), use it
        if public_domain and public_domain != "localhost:8000":
            if image_path.startswith("/public/"):
                return f"https://{public_domain}{image_path}"
            elif image_path.startswith("public/"):
                return f"https://{public_domain}/{image_path}"
            else:
                return f"https://{public_domain}/public/{image_path}"
        
        # Otherwise, upload to public hosting
        logger.info("No public domain configured, uploading to public hosting service...")
        return self.upload_to_public_hosting(image_path)


# Global image upload service instance
image_upload_service = ImageUploadService()
