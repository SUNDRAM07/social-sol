"""
Image Path Utilities for Social Media Agent
Provides consistent URL-to-local-path conversion across all platforms
"""

import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def convert_url_to_local_path(image_path: Optional[str]) -> Optional[str]:
    """
    Convert various image URL formats to local file paths
    
    Handles:
    - /public/filename.jpg -> public/filename.jpg
    - public/filename.jpg -> public/filename.jpg (no change)
    - http://localhost:8000/public/filename.jpg -> public/filename.jpg
    - http://localhost:5173/public/filename.jpg -> public/filename.jpg
    - http://localhost:XXXX/public/filename.jpg -> public/filename.jpg
    - filename.jpg -> public/filename.jpg (assume public folder)
    
    Args:
        image_path: The image path/URL to convert
        
    Returns:
        Local file path relative to server root, or None if input is None
        
    Examples:
        >>> convert_url_to_local_path("/public/image.jpg")
        "public/image.jpg"
        >>> convert_url_to_local_path("http://localhost:8000/public/image.jpg")
        "public/image.jpg"
        >>> convert_url_to_local_path("public/image.jpg")
        "public/image.jpg"
    """
    if not image_path:
        return None
    
    # Remove any whitespace
    image_path = image_path.strip()
    
    if not image_path:
        return None
    
    # Case 1: Already starts with public/
    if image_path.startswith("public/"):
        return image_path
    
    # Case 2: Starts with /public/
    if image_path.startswith("/public/"):
        return image_path[1:]  # Remove leading slash
    
    # Case 3: Full localhost URL with specific port
    if image_path.startswith("http://localhost:8000/public/"):
        return image_path.replace("http://localhost:8000/", "")
    
    # Case 4: Any localhost URL with public folder
    if image_path.startswith("http://localhost:") and "/public/" in image_path:
        # Extract everything after /public/
        try:
            local_part = image_path.split("/public/", 1)[1]
            return f"public/{local_part}"
        except IndexError:
            logger.warning(f"Failed to parse localhost URL: {image_path}")
            return f"public/{image_path}"
    
    # Case 5: Other HTTP URLs (external images) - return as-is for downloading
    if image_path.startswith("http://") or image_path.startswith("https://"):
        return image_path
    
    # Case 6: Relative path without public/ prefix - assume it's in public folder
    if not image_path.startswith("/"):
        return f"public/{image_path}"
    
    # Case 7: Absolute path starting with / - assume it's relative to server root
    return image_path[1:]  # Remove leading slash


def validate_local_image_path(image_path: Optional[str]) -> bool:
    """
    Validate that a local image path exists and is readable
    
    Args:
        image_path: Local file path to validate
        
    Returns:
        True if file exists and is readable, False otherwise
    """
    if not image_path:
        return False
    
    try:
        return os.path.exists(image_path) and os.path.isfile(image_path) and os.access(image_path, os.R_OK)
    except Exception as e:
        logger.warning(f"Error validating image path {image_path}: {e}")
        return False


def get_image_info(image_path: Optional[str]) -> dict:
    """
    Get information about an image file
    
    Args:
        image_path: Local file path to analyze
        
    Returns:
        Dictionary with image info (exists, size, readable, etc.)
    """
    info = {
        "path": image_path,
        "exists": False,
        "readable": False,
        "size": None,
        "error": None
    }
    
    if not image_path:
        info["error"] = "No path provided"
        return info
    
    try:
        if os.path.exists(image_path):
            info["exists"] = True
            info["readable"] = os.access(image_path, os.R_OK)
            if info["readable"]:
                try:
                    stat_info = os.stat(image_path)
                    info["size"] = stat_info.st_size
                except Exception as e:
                    info["error"] = f"Failed to get file stats: {e}"
        else:
            info["error"] = "File does not exist"
            
    except Exception as e:
        info["error"] = f"Error checking file: {e}"
    
    return info


# Platform-specific helpers that use the common conversion logic
def convert_image_path_for_facebook(image_path: Optional[str]) -> Optional[str]:
    """Convert image path for Facebook posting"""
    return convert_url_to_local_path(image_path)


def convert_image_path_for_twitter(image_path: Optional[str]) -> Optional[str]:
    """Convert image path for Twitter posting"""
    return convert_url_to_local_path(image_path)


def convert_image_path_for_reddit(image_path: Optional[str]) -> Optional[str]:
    """Convert image path for Reddit posting"""
    return convert_url_to_local_path(image_path)