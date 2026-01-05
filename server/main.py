from fastapi import FastAPI, HTTPException, Depends, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import requests
import os
import base64
import re
from datetime import datetime, timedelta
from dotenv import load_dotenv
import time
import hashlib
from PIL import Image, ImageDraw, ImageFont
import textwrap
from contextlib import asynccontextmanager
from google_complete import router as google_router
from dashboard_routes import router as dashboard_router

# Database imports
from database import startup_db, shutdown_db, get_database, get_sync_db
from database_service import db_service
from models import PostResponse as PostResponseModel, CalendarEventResponse, ApiUsage
from calendar_service import CalendarService
from env_manager import env_manager
from image_path_utils import convert_url_to_local_path

# Scheduler imports
from scheduler_service import scheduler_service, start_scheduler, stop_scheduler

# Load environment variables
load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application lifespan events (startup and shutdown)"""
    # Startup
    try:
        print("🔄 Starting database connection...")
        await startup_db()
        print("✅ Database connection initialized")
    except Exception as e:
        print(f"❌ Database startup failed: {e}")
        import traceback
        traceback.print_exc()
        # Continue anyway to allow app to start
    
    try:
        print("🔄 Starting scheduler service...")
        await start_scheduler()
        print("✅ Scheduler service started")
    except Exception as e:
        print(f"❌ Scheduler startup failed: {e}")
    
    yield  # Application runs here
    
    # Shutdown
    try:
        await stop_scheduler()
        print("✅ Scheduler service stopped")
    except Exception as e:
        print(f"❌ Scheduler shutdown failed: {e}")
    
    try:
        await shutdown_db()
        print("✅ Database connection closed")
    except Exception as e:
        print(f"❌ Database shutdown failed: {e}")

# Create main application
main_app = FastAPI(
    title="Instagram Post Generator API",
    description="Generate Instagram posts with AI",
    version="3.0.0",
    lifespan=lifespan
)

# CORS middleware - use same origins as root app
main_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all for sub-app, root app handles specific origins
    allow_credentials=False,  # Must be False when using "*"
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files directory
main_app.mount("/assets", StaticFiles(directory="static/assets"), name="assets")
# Mount frontend static files
main_app.mount("/static", StaticFiles(directory="static"), name="static")
# Mount public directory for uploaded and generated images (same as AI-generated images)
main_app.mount("/public", StaticFiles(directory="public"), name="public")

# Create root app and mount main app at /socialanywhere
app = FastAPI(lifespan=lifespan)

# Add CORS middleware to root app - ALLOW ALL ORIGINS for now
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,  # Must be False when using "*"
    allow_methods=["*"],
    allow_headers=["*"],
)


# Simple root endpoint for testing (health check is defined later in the file)
@app.get("/")
async def root():
    """Root endpoint for testing"""
    return {"status": "ok", "message": "Social Sol API is running"}

# Add middleware to fix redirects that use internal IP
@app.middleware("http")
async def fix_redirect_domain(request: Request, call_next):
    """Middleware to fix redirects that use internal IP addresses"""
    # Log request for debugging
    if request.url.path == "/socialanywhere":
        print(f"🌐 Middleware: Request to /socialanywhere")
        print(f"   Host: {request.headers.get('host', 'N/A')}")
        print(f"   X-Forwarded-Host: {request.headers.get('x-forwarded-host', 'N/A')}")
        print(f"   X-Forwarded-Proto: {request.headers.get('x-forwarded-proto', 'N/A')}")
    
    response = await call_next(request)
    
    # Check if this is a redirect response
    if hasattr(response, 'status_code') and response.status_code in [301, 302, 307, 308]:
        # Check if Location header contains internal IP or localhost
        location = response.headers.get("location", "")
        if location:
            print(f"🔍 Middleware detected redirect: {location}")
            
            # CRITICAL: Never modify Google OAuth URLs - they must always go to accounts.google.com
            # Check for Google OAuth endpoints (case-insensitive)
            location_lower = location.lower()
            if any(google_domain in location_lower for google_domain in [
                "accounts.google.com",
                "oauth2.googleapis.com",
                "www.googleapis.com",
                "googleapis.com/oauth2"
            ]):
                print(f"✅ Skipping middleware for Google OAuth URL (detected: {location[:50]}...)")
                return response
            
            # Check for any IP address pattern, localhost, or port numbers in URL
            ip_pattern = r'http://\d+\.\d+\.\d+\.\d+'
            has_internal_ip = (
                bool(re.search(ip_pattern, location)) or 
                "localhost" in location or 
                "127.0.0.1" in location or 
                ":8000" in location or
                location.startswith("http://4.")  # Specific IP pattern
            )
            
            if has_internal_ip:
                # Get the original host from request (prioritize forwarded headers)
                forwarded_host = request.headers.get("x-forwarded-host", "")
                host = forwarded_host if forwarded_host else request.headers.get("host", "")
                
                # Remove port number if present
                if ":" in host:
                    host = host.split(":")[0]
                
                # Get scheme - prioritize x-forwarded-proto
                forwarded_proto = request.headers.get("x-forwarded-proto", "")
                # Also check x-forwarded-ssl
                if not forwarded_proto:
                    forwarded_proto = request.headers.get("x-forwarded-ssl", "")
                    if forwarded_proto == "on":
                        forwarded_proto = "https"
                
                if forwarded_proto:
                    scheme = forwarded_proto.lower()
                elif hasattr(request.url, 'scheme'):
                    scheme = request.url.scheme
                else:
                    # Default to https for production domains (not localhost, not IP addresses)
                    is_production = host and host != "localhost" and not host.startswith("127.0.0.1") and not re.match(r'^\d+\.\d+\.\d+\.\d+$', host)
                    scheme = "https" if is_production else "http"
                
                # Use PUBLIC_DOMAIN if set, otherwise use request host
                public_domain = os.getenv("PUBLIC_DOMAIN")
                if public_domain and public_domain != "localhost:8000":
                    # Remove http:// or https:// prefix if present
                    domain = public_domain.replace("http://", "").replace("https://", "")
                    # Remove port if present
                    if ":" in domain:
                        domain = domain.split(":")[0]
                    base_url = f"{scheme}://{domain}"
                elif host:
                    base_url = f"{scheme}://{host}"
                else:
                    base_url = "http://localhost:8000"
                
                # Extract the path and query from the original location
                from urllib.parse import urlparse
                parsed = urlparse(location)
                
                # Ensure path starts with / if it doesn't
                path = parsed.path if parsed.path.startswith("/") else f"/{parsed.path}"
                
                new_location = f"{base_url}{path}"
                if parsed.query:
                    new_location += f"?{parsed.query}"
                if parsed.fragment:
                    new_location += f"#{parsed.fragment}"
                
                # Update the location header
                print(f"🔧 Fixed redirect: {location} -> {new_location}")
                response.headers["location"] = new_location
    
    return response

# Handle /socialanywhere without trailing slash - redirect preserving domain
# This must be defined BEFORE the mount to take precedence
@app.get("/socialanywhere")
async def redirect_socialanywhere(request: Request):
    """Redirect /socialanywhere to /socialanywhere/ preserving the original domain"""
    # Debug: Log all relevant headers
    print(f"🔍 Redirect handler called")
    print(f"   Host: {request.headers.get('host', 'N/A')}")
    print(f"   X-Forwarded-Host: {request.headers.get('x-forwarded-host', 'N/A')}")
    print(f"   X-Forwarded-Proto: {request.headers.get('x-forwarded-proto', 'N/A')}")
    print(f"   X-Forwarded-SSL: {request.headers.get('x-forwarded-ssl', 'N/A')}")
    print(f"   URL scheme: {getattr(request.url, 'scheme', 'N/A')}")
    
    # Get the original host from request headers (prioritize forwarded headers)
    forwarded_host = request.headers.get("x-forwarded-host", "")
    host = forwarded_host if forwarded_host else request.headers.get("host", "")
    
    # Remove port number if present (for clean redirects)
    if ":" in host:
        host = host.split(":")[0]
    
    # Get scheme - prioritize x-forwarded-proto, then check URL scheme
    forwarded_proto = request.headers.get("x-forwarded-proto", "")
    # Also check x-forwarded-ssl
    if not forwarded_proto:
        forwarded_ssl = request.headers.get("x-forwarded-ssl", "")
        if forwarded_ssl == "on":
            forwarded_proto = "https"
    
    if forwarded_proto:
        scheme = forwarded_proto.lower()
    elif hasattr(request.url, 'scheme'):
        scheme = request.url.scheme
    else:
        # Default to https for production domains (not localhost, not IP addresses)
        is_production = host and host != "localhost" and not host.startswith("127.0.0.1") and not re.match(r'^\d+\.\d+\.\d+\.\d+$', host)
        scheme = "https" if is_production else "http"
        print(f"   Detected production domain, using scheme: {scheme}")
    
    # Use PUBLIC_DOMAIN if set, otherwise use request host
    public_domain = os.getenv("PUBLIC_DOMAIN")
    if public_domain and public_domain != "localhost:8000":
        # Remove http:// or https:// prefix if present
        domain = public_domain.replace("http://", "").replace("https://", "")
        # Remove port if present
        if ":" in domain:
            domain = domain.split(":")[0]
        base_url = f"{scheme}://{domain}"
        print(f"   Using PUBLIC_DOMAIN: {domain}")
    elif host:
        base_url = f"{scheme}://{host}"
        print(f"   Using request host: {host}")
    else:
        base_url = "http://localhost:8000"
        print(f"   Using fallback: localhost:8000")
    
    redirect_url = f"{base_url}/socialanywhere/"
    print(f"🔀 Redirecting /socialanywhere to: {redirect_url}")
    return RedirectResponse(url=redirect_url, status_code=301)

app.mount("/socialanywhere", main_app)

# Serve privacy policy at root level (for direct domain access)
@app.get("/privacy-policy.html")
async def serve_privacy_policy_root():
    """Serve privacy policy HTML file at root level"""
    # Try multiple possible paths (relative to server directory and project root)
    possible_paths = [
        "static/privacy-policy.html",  # Production build location
        "../static/privacy-policy.html",  # From server directory
        "public/privacy-policy.html",  # Development location
        "../public/privacy-policy.html",  # From server directory
        "../socialanywhere.ai/public/privacy-policy.html",  # Absolute from server
        "server/public/privacy-policy.html",  # Server public directory
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return FileResponse(path, media_type="text/html")
    
    raise HTTPException(status_code=404, detail="Privacy policy not found")

# Custom endpoint to handle files with special characters in public directory
@main_app.get("/public/{filename:path}")
async def serve_public_file(filename: str):
    """Serve files from public directory, handling URL-encoded filenames and proper MIME types"""
    import urllib.parse
    import os
    
    print(f"🔍 Serving public file - Original filename: {filename}")
    
    # Decode the filename to handle special characters
    decoded_filename = urllib.parse.unquote(filename)
    print(f"🔍 Decoded filename: {decoded_filename}")
    
    # Construct the file path
    file_path = os.path.join("public", decoded_filename)
    if not os.path.exists(file_path):
        # Try without leading slash
        file_path = os.path.join("public", decoded_filename.lstrip("/"))
    
    if not os.path.exists(file_path):
        # Try original filename
        file_path = os.path.join("public", filename)
    
    print(f"🔍 Looking for file at: {file_path}")
    
    # Check if file exists
    if os.path.exists(file_path) and os.path.isfile(file_path):
        print(f"✅ Found file: {file_path}")
        
        # Determine MIME type based on file extension
        file_ext = os.path.splitext(file_path)[1].lower()
        mime_types = {
            '.mp4': 'video/mp4',
            '.webm': 'video/webm',
            '.mov': 'video/quicktime',
            '.gif': 'image/gif',  # Animated GIFs can be played as videos
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.svg': 'image/svg+xml'
        }
        
        media_type = mime_types.get(file_ext, 'application/octet-stream')
        
        # For video files and GIFs, add proper headers for streaming
        if file_ext in ['.mp4', '.webm', '.mov', '.gif']:
            return FileResponse(
                file_path,
                media_type=media_type,
                headers={
                    "Accept-Ranges": "bytes",
                    "Cache-Control": "public, max-age=3600"
                }
            )
        else:
            return FileResponse(file_path, media_type=media_type)
    else:
        print(f"❌ File not found: {file_path}")
        raise HTTPException(status_code=404, detail="File not found")

# Serve frontend index.html for all non-API routes


# Include Google integration router
main_app.include_router(google_router)

# Include social media routes
from social_media_routes import router as social_media_router
main_app.include_router(social_media_router)

# Include authentication routes
from auth_routes import router as auth_router
main_app.include_router(auth_router)
# Also include on root app for direct /auth/* access (without /socialanywhere prefix)
app.include_router(auth_router)

# Include idea generator routes
from idea_generator_routes import router as idea_generator_router
main_app.include_router(idea_generator_router)

# Include chat routes for conversational AI interface
from chat_routes import router as chat_router
main_app.include_router(chat_router)
app.include_router(chat_router)  # Also include on root for direct /chat/* access

# Import auth dependency after router is included
from auth_routes import get_current_user_dependency
from auth_service import auth_service

# Lifespan events are now handled in the lifespan context manager above

# API Keys
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
STABILITY_API_KEY = os.getenv("STABILITY_API_KEY")  # For image generation
CHATGPT_API_KEY = os.getenv("CHATGPT_API")  # For caption and image generation
# PiAPI for Gemini image generation (supports both new and legacy env var names)
PIAPI_API_KEY = os.getenv("PIAPI_API_KEY") or os.getenv("NANO_BANANA_API_KEY")


def log_api_usage(user_id: str, service: str, operation: str, tokens_used: int = 0, credits_used: int = 0, response_data: dict = None):
    """Log API usage to database"""
    try:
        print(f"🔍 Logging API usage - user_id: {user_id}, service: {service}, operation: {operation}, tokens: {tokens_used}, credits: {credits_used}")
        # Create a new session directly
        from database import SessionLocal
        db = SessionLocal()
        try:
            usage = ApiUsage(
                user_id=user_id,
                service=service,
                operation=operation,
                tokens_used=tokens_used,
                credits_used=credits_used,
                response_data=response_data
            )
            db.add(usage)
            db.commit()
            print(f"✅ Logged API usage: {service} - {tokens_used} tokens, {credits_used} credits")
        except Exception as db_error:
            print(f"❌ Database error in log_api_usage: {db_error}")
            db.rollback()
            raise db_error
        finally:
            db.close()
    except Exception as e:
        print(f"❌ Failed to log API usage: {e}")
        import traceback
        traceback.print_exc()


class PostRequest(BaseModel):
    description: str
    caption_provider: Optional[str] = "groq"  # chatgpt, groq
    image_provider: Optional[str] = "stability"  # stability, chatgpt, nano_banana
    platforms: Optional[List[str]] = ["instagram"]  # Array of platforms: instagram, facebook, twitter, reddit
    subreddit: Optional[str] = None  # For Reddit posts


class PostResponse(BaseModel):
    success: bool
    caption: Optional[str] = None
    image_path: Optional[str] = None
    error: Optional[str] = None


class BatchRequest(BaseModel):
    description: str
    days: int
    num_posts: int
    caption_provider: Optional[str] = "groq"  # chatgpt, groq
    image_provider: Optional[str] = "stability"  # stability, chatgpt, nano_banana
    asset_type: Optional[str] = "image"  # "image" or "video" - determines if we generate images or videos
    platforms: Optional[List[str]] = ["instagram"]  # Array of platforms: instagram, facebook, twitter, reddit
    subreddit: Optional[str] = None  # For Reddit posts
    campaign_name: Optional[str] = None  # Campaign name for the batch


class BatchItem(BaseModel):
    caption: Optional[str] = None
    image_path: Optional[str] = None
    scheduled_at: Optional[str] = None
    error: Optional[str] = None


class BatchResponse(BaseModel):
    success: bool
    items: List[BatchItem]
    error: Optional[str] = None
    batch_id: Optional[str] = None


def generate_caption_with_groq(description: str, user_id: str = None) -> str:
    """Generate Instagram caption using Groq API"""
    try:
        if not GROQ_API_KEY:
            raise Exception("Groq API key not found")

        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json",
        }

        data = {
            "messages": [
                {
                    "role": "system",
                    "content": "You are an expert Instagram caption writer. Create engaging, trendy captions with emojis and hashtags. Keep under 200 characters for better engagement.",
                },
                {
                    "role": "user",
                    "content": f"Write a catchy Instagram caption for: {description}. Include 3-5 relevant hashtags and emojis.",
                },
            ],
            "model": "llama-3.1-8b-instant",
            "max_tokens": 150,
            "temperature": 0.9,  # Higher temperature for more randomness
        }

        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=15,
        )

        if response.status_code == 200:
            result = response.json()
            print(f"🔍 Groq API Response: {result}")
            caption = result["choices"][0]["message"]["content"].strip()
            
            # Log usage if user_id is provided
            if user_id:
                usage_info = result.get("usage", {})
                tokens_used = usage_info.get("total_tokens", 0)
                log_api_usage(user_id, "groq", "caption", tokens_used, 0, result)
            
            return caption
        else:
            raise Exception(f"Groq API error: {response.status_code}")

    except Exception as e:
        print(f"Caption generation error: {e}")
        # Fallback caption
        return (
            f"✨ Check out this amazing {description}! Perfect for your lifestyle! 🚀 "
            "#Amazing #MustHave #Trending #NewPost #Discover"
        )


def generate_caption_with_chatgpt(description: str, user_id: str = None) -> str:
    """Generate Instagram caption using ChatGPT API"""
    try:
        if not CHATGPT_API_KEY:
            print("ChatGPT API key not found, using fallback caption")
            raise Exception("ChatGPT API key not found")

        headers = {
            "Authorization": f"Bearer {CHATGPT_API_KEY}",
            "Content-Type": "application/json",
        }

        data = {
            "model": "gpt-3.5-turbo",
            "messages": [
                {
                    "role": "system",
                    "content": "You are an expert Instagram caption writer. Create engaging, trendy captions with emojis and hashtags. Keep under 200 characters for better engagement.",
                },
                {
                    "role": "user",
                    "content": f"Write a catchy Instagram caption for: {description}. Include 3-5 relevant hashtags and emojis.",
                },
            ],
            "max_tokens": 150,
            "temperature": 0.7,
        }

        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=15,
        )

        if response.status_code == 200:
            result = response.json()
            print(f"🔍 ChatGPT API Response: {result}")
            caption = result["choices"][0]["message"]["content"].strip()
            print(f"✅ ChatGPT caption generated successfully")
            
            # Log usage if user_id is provided
            if user_id:
                usage_info = result.get("usage", {})
                tokens_used = usage_info.get("total_tokens", 0)
                log_api_usage(user_id, "chatgpt", "caption", tokens_used, 0, result)
            
            return caption
        elif response.status_code == 429:
            print("⚠️ ChatGPT API rate limit exceeded, using fallback caption")
            raise Exception(f"ChatGPT API rate limit exceeded")
        else:
            print(f"❌ ChatGPT API error {response.status_code}: {response.text[:200]}")
            raise Exception(f"ChatGPT API error: {response.status_code}")

    except Exception as e:
        print(f"ChatGPT caption generation error: {e}")
        # Enhanced fallback caption with variety
        import random
        fallback_captions = [
            f"✨ Discover the magic of {description}! Perfect for your lifestyle! 🚀 #Amazing #MustHave #Trending #NewPost #Discover",
            f"🌟 Introducing {description} - your new favorite! Don't miss out! 💫 #Trending #MustSee #NewArrivals #Lifestyle #Amazing", 
            f"🔥 Get ready for {description}! This is what you've been waiting for! ⭐ #Hot #Trending #NewDrop #Essential #MustHave",
            f"💎 Experience {description} like never before! Pure excellence! ✨ #Premium #Quality #NewPost #Trending #Discover"
        ]
        return random.choice(fallback_captions)


def generate_caption(description: str, provider: str = "groq", user_id: str = None) -> str:
    """Generate caption using specified provider"""
    if provider == "groq":
        return generate_caption_with_groq(description, user_id)
    elif provider == "chatgpt":
        return generate_caption_with_chatgpt(description, user_id)
    else:
        # Default to Groq
        return generate_caption_with_groq(description, user_id)


def create_placeholder_image(description: str) -> Optional[str]:
    """Create a placeholder image with the description text when AI generation fails."""
    try:
        # Create a 1024x1024 image
        img = Image.new('RGB', (1024, 1024), color=(70, 130, 180))  # Steel blue background
        draw = ImageDraw.Draw(img)
        
        # Try to load a font, fallback to default
        try:
            # Try different font paths for different systems
            font_paths = [
                '/System/Library/Fonts/Arial.ttf',  # macOS
                '/System/Library/Fonts/Helvetica.ttc',  # macOS
                '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',  # Linux
                '/Windows/Fonts/arial.ttf',  # Windows
            ]
            font = None
            for path in font_paths:
                if os.path.exists(path):
                    font = ImageFont.truetype(path, 48)
                    break
            
            if font is None:
                font = ImageFont.load_default()
        except Exception:
            font = ImageFont.load_default()
        
        # Wrap text to fit in image
        text = f"🎨 {description}"
        margin = 80
        max_width = 1024 - 2 * margin
        
        # Wrap text
        wrapper = textwrap.TextWrapper(width=30)  # Approximate character width
        lines = wrapper.wrap(text)
        
        # If text is too long, truncate
        if len(lines) > 12:
            lines = lines[:11] + ["..."]
        
        # Calculate text position
        total_height = len(lines) * 60  # Approximate line height
        start_y = (1024 - total_height) // 2
        
        # Draw each line centered
        for i, line in enumerate(lines):
            # Get text bounding box for centering
            try:
                bbox = draw.textbbox((0, 0), line, font=font)
                text_width = bbox[2] - bbox[0]
            except AttributeError:
                # Fallback for older Pillow versions
                text_width = len(line) * 20  # Rough estimate
            
            x = (1024 - text_width) // 2
            y = start_y + i * 60
            
            # Draw text with shadow for better visibility
            draw.text((x + 2, y + 2), line, font=font, fill=(0, 0, 0, 128))  # Shadow
            draw.text((x, y), line, font=font, fill=(255, 255, 255))  # Main text
        
        # Add a watermark
        watermark = "Generated by Social Media Agent"
        try:
            small_font = ImageFont.truetype(font_paths[0] if font_paths and os.path.exists(font_paths[0]) else None, 24)
        except:
            small_font = ImageFont.load_default()
        
        try:
            bbox = draw.textbbox((0, 0), watermark, font=small_font)
            wm_width = bbox[2] - bbox[0]
        except AttributeError:
            wm_width = len(watermark) * 12
        
        wm_x = (1024 - wm_width) // 2
        wm_y = 980
        draw.text((wm_x + 1, wm_y + 1), watermark, font=small_font, fill=(0, 0, 0, 64))
        draw.text((wm_x, wm_y), watermark, font=small_font, fill=(255, 255, 255, 180))
        
        # Save the image
        filename = f"placeholder_{hashlib.md5(description.encode()).hexdigest()[:8]}_{int(datetime.now().timestamp())}.png"
        filepath = f"public/{filename}"
        os.makedirs("public", exist_ok=True)
        img.save(filepath, 'PNG')
        
        print(f"Created placeholder image: {filepath}")
        return f"/public/{filename}"
        
    except Exception as e:
        print(f"Error creating placeholder image: {e}")
        return None


def generate_image_with_stability(description: str) -> Optional[str]:
    """Generate image using Stability AI API and store it in public/ with retries.
    Falls back to placeholder image if service is unavailable.

    Tuned prompts to stay faithful to the user description.
    """
    try:
        if not STABILITY_API_KEY:
            print("Stability API key not found, creating placeholder image...")
            return create_placeholder_image(description)

        # SDXL allowed dimensions include 1024x1024; stick to it to avoid 400s
        settings = [
            {"height": 1024, "width": 1024, "steps": 32, "cfg_scale": 8},
        ]

        # Try multiple Stability models in order of quality → accessibility
        model_endpoints = [
            "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image",
        ]

        for model_url in model_endpoints:
            for attempt, s in enumerate(settings, start=1):
                headers = {
                    "Authorization": f"Bearer {STABILITY_API_KEY}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                }
                data = {
                    "text_prompts": [
                        {
                            "text": (
                                f"Ultra-detailed, photorealistic square photo of {description}. "
                                "Subject clearly visible and centered, professional lighting, shallow depth of field, high dynamic range, Instagram aesthetic."
                            ),
                            "weight": 1,
                        },
                        {
                            "text": "unrelated mountains, random landscape, balloons, generic scenery, text, watermark, logo, blurry, low quality, duplicate",
                            "weight": -1,
                        },
                    ],
                    "cfg_scale": s["cfg_scale"],
                    "height": s["height"],
                    "width": s["width"],
                    "samples": 1,
                    "steps": s["steps"],
                }

                response = requests.post(
                    model_url,
                    headers=headers,
                    json=data,
                    timeout=60,
                )

                if response.status_code == 200:
                    result = response.json()
                    if not result.get("artifacts"):
                        # Some responses might structure differently; continue
                        pass
                    else:
                        image_data = base64.b64decode(result["artifacts"][0]["base64"])
                        filename = (
                            f"generated_{hashlib.md5(description.encode()).hexdigest()[:8]}_"
                            f"{int(datetime.now().timestamp())}.png"
                        )
                        filepath = f"public/{filename}"
                        os.makedirs("public", exist_ok=True)
                        with open(filepath, "wb") as f:
                            f.write(image_data)
                        return f"/public/{filename}"

                else:
                    # Log useful error body for debugging
                    try:
                        print(
                            f"Stability API error {response.status_code} at {model_url}: {response.text[:500]}"
                        )
                    except Exception:
                        pass

                # Backoff on failures (e.g., 429)
                time.sleep(1 + attempt)

        # If all attempts fail, create placeholder image
        print("All Stability AI attempts failed, creating placeholder image...")
        return create_placeholder_image(description)
    except Exception as e:
        print(f"Image generation error: {e}")
        print("Creating placeholder image as fallback...")
        return create_placeholder_image(description)


def generate_image_with_chatgpt(description: str) -> Optional[str]:
    """Generate image using ChatGPT DALL-E API and store it in public/.
    Falls back to placeholder image if service is unavailable.
    """
    try:
        if not CHATGPT_API_KEY:
            print("ChatGPT API key not found, creating placeholder image...")
            return create_placeholder_image(description)

        headers = {
            "Authorization": f"Bearer {CHATGPT_API_KEY}",
            "Content-Type": "application/json",
        }

        data = {
            "model": "dall-e-2",  # or "dall-e-3" if available
            "prompt": f"Ultra-detailed, photorealistic square photo of {description}. Subject clearly visible and centered, professional lighting, shallow depth of field, high dynamic range, Instagram aesthetic.",
            "n": 1,
            "size": "1024x1024",
            "response_format": "b64_json"
        }

        response = requests.post(
            "https://api.openai.com/v1/images/generations",
            headers=headers,
            json=data,
            timeout=60,
        )

        if response.status_code == 200:
            result = response.json()
            if result.get("data") and len(result["data"]) > 0:
                image_data = base64.b64decode(result["data"][0]["b64_json"])
                filename = (
                    f"chatgpt_{hashlib.md5(description.encode()).hexdigest()[:8]}_"
                    f"{int(datetime.now().timestamp())}.png"
                )
                filepath = f"public/{filename}"
                os.makedirs("public", exist_ok=True)
                with open(filepath, "wb") as f:
                    f.write(image_data)
                return f"/public/{filename}"
            else:
                raise Exception("No image data in ChatGPT response")
        else:
            raise Exception(f"ChatGPT API error: {response.status_code} - {response.text}")

    except Exception as e:
        print(f"ChatGPT image generation error: {e}")
        print("Creating placeholder image as fallback...")
        return create_placeholder_image(description)


def generate_image_with_nano_banana(description: str, user_id: str = None) -> Optional[str]:
    """Generate image via PiAPI (Gemini-2.5-flash-image) using unified task API.
    Falls back to placeholder image if service is unavailable.
    """
    try:
        if not PIAPI_API_KEY:
            print("PiAPI key not found (set PIAPI_API_KEY or NANO_BANANA_API_KEY), creating placeholder image...")
            return create_placeholder_image(description)

        # Build request per PiAPI docs: POST https://api.piapi.ai/api/v1/task
        url = "https://api.piapi.ai/api/v1/task"
        headers = {
            "X-API-Key": PIAPI_API_KEY,
            "Content-Type": "application/json",
        }
        payload = {
            "model": "gemini",
            "task_type": "gemini-2.5-flash-image",
            "input": {
                "prompt": description,
                "num_images": 1,
                "output_format": "png",
            }
        }

        create_resp = requests.post(url, headers=headers, json=payload, timeout=30)
        if create_resp.status_code != 200:
            raise Exception(f"PiAPI create task error: {create_resp.status_code} {create_resp.text[:200]}")
        create_result = create_resp.json()
        print(f"🔍 PiAPI Create Task Response: {create_result}")
        data = create_result.get("data") or {}
        task_id = data.get("task_id")
        if not task_id:
            raise Exception("PiAPI create task did not return task_id")

        # Poll for completion
        get_url = f"https://api.piapi.ai/api/v1/task/{task_id}"
        status = None
        output = None
        start = time.time()
        while time.time() - start < 90:  # up to 90s
            get_resp = requests.get(get_url, headers=headers, timeout=15)
            if get_resp.status_code != 200:
                time.sleep(2)
                continue
            g = get_resp.json().get("data") or {}
            status = g.get("status")
            if status == "completed":
                output = g.get("output") or {}
                print(f"🔍 PiAPI Task Completion Response: {get_resp.json()}")
                break
            if status in {"failed"}:
                err = (g.get("error") or {}).get("message") or "unknown error"
                raise Exception(f"PiAPI task failed: {err}")
            time.sleep(2)

        if status != "completed" or not output:
            raise Exception("PiAPI task did not complete in time")

        # Extract image url(s)
        image_url = output.get("image_url")
        if not image_url:
            urls = output.get("image_urls") or []
            image_url = urls[0] if urls else None
        if not image_url:
            raise Exception("PiAPI completed but no image URL in output")

        # Download and save image locally under public/
        img_resp = requests.get(image_url, timeout=60)
        if img_resp.status_code != 200:
            raise Exception(f"Failed to download image: {img_resp.status_code}")
        filename = (
            f"piapi_{hashlib.md5(description.encode()).hexdigest()[:8]}_"
            f"{int(datetime.now().timestamp())}.png"
        )
        filepath = f"public/{filename}"
        os.makedirs("public", exist_ok=True)
        with open(filepath, "wb") as f:
            f.write(img_resp.content)

        # Extract usage/credit information if available
        meta_info = g.get("meta", {})
        usage_info = meta_info.get("usage", {})
        credits_used = usage_info.get("consume", 0)  # PiAPI uses 'consume' field
        
        # Log usage if user_id is provided
        if user_id:
            log_api_usage(user_id, "piapi", "image", 0, credits_used, get_resp.json())
        
        print(f"✅ PiAPI image generated successfully: {filepath} - Credits used: {credits_used}")
        return f"/public/{filename}"

    except Exception as e:
        print(f"PiAPI image generation error: {e}")
        print("Creating placeholder image as fallback...")
        return create_placeholder_image(description)


def generate_image(description: str, provider: str = "stability", user_id: str = None) -> Optional[str]:
    """Generate image using specified provider"""
    if provider == "stability":
        return generate_image_with_stability(description)
    elif provider == "chatgpt":
        return generate_image_with_chatgpt(description)
    elif provider == "nano_banana":
        return generate_image_with_nano_banana(description, user_id)
    else:
        # Default to Stability
        return generate_image_with_stability(description)


def generate_video_with_huggingface(description: str, duration_seconds: int = 30) -> Optional[str]:
    """Generate 30-second video using Hugging Face's free Inference API with open-source models.
    Uses text-to-video models like AnimateDiff, ModelScope, or Zeroscope.
    """
    try:
        print(f"🎬 Generating 30-second video using Hugging Face API for: {description}")
        
        # Ensure public directory exists
        os.makedirs("public", exist_ok=True)
        
        # Try Hugging Face Inference API (free tier available)
        # Using open-source text-to-video models
        huggingface_api_url = "https://api-inference.huggingface.co/models"
        
        # Try multiple open-source video models (free, no API key required for some)
        video_models = [
            "cerspense/zeroscope_v2_576w",  # Zeroscope - open source, free
            "damo-vilab/text-to-video-ms-1.7b",  # ModelScope text-to-video
            "anotherjesse/zeroscope-v2-xl",  # Zeroscope XL
        ]
        
        prompt = f"{description}, high quality, 30 seconds, smooth animation, professional video"
        
        for model_name in video_models:
            try:
                print(f"🎬 Trying model: {model_name}")
                api_url = f"{huggingface_api_url}/{model_name}"
                
                headers = {
                    "Content-Type": "application/json",
                }
                
                # Some models might need API key, but many are free
                hf_token = os.getenv("HUGGINGFACE_API_KEY")
                if hf_token:
                    headers["Authorization"] = f"Bearer {hf_token}"
                
                payload = {
                    "inputs": prompt,
                    "parameters": {
                        "num_inference_steps": 50,
                        "guidance_scale": 7.5,
                    }
                }
                
                print(f"📡 Calling Hugging Face API: {api_url}")
                response = requests.post(
                    api_url,
                    headers=headers,
                    json=payload,
                    timeout=180  # 3 minutes for video generation
                )
                
                if response.status_code == 200:
                    # Save video file
                    video_filename = (
                        f"video_{hashlib.md5(description.encode()).hexdigest()[:8]}_"
                        f"{int(datetime.now().timestamp())}.mp4"
                    )
                    video_path = f"public/{video_filename}"
                    
                    with open(video_path, "wb") as f:
                        f.write(response.content)
                    
                    file_size = os.path.getsize(video_path)
                    if file_size > 0:
                        print(f"✅ Video generated successfully using {model_name}: {video_path} ({file_size} bytes)")
                        return f"/public/{video_filename}"
                    else:
                        print(f"⚠️ Video file is empty from {model_name}")
                        continue
                elif response.status_code == 503:
                    # Model is loading, try next model
                    print(f"⚠️ Model {model_name} is loading, trying next model...")
                    continue
                else:
                    print(f"⚠️ API error from {model_name}: {response.status_code} - {response.text[:200]}")
                    continue
                    
            except requests.exceptions.Timeout:
                print(f"⚠️ Timeout calling {model_name}, trying next model...")
                continue
            except Exception as e:
                print(f"⚠️ Error with {model_name}: {e}")
                continue
        
        # If all Hugging Face models fail, fall back to image-to-video conversion
        print("⚠️ All Hugging Face models failed, falling back to image-to-video conversion...")
        return generate_video_from_image_fallback(description, duration_seconds)
        
    except Exception as e:
        print(f"❌ Hugging Face video generation error: {e}")
        import traceback
        traceback.print_exc()
        # Fallback to image-to-video conversion
        return generate_video_from_image_fallback(description, duration_seconds)


def generate_video_from_image_fallback(description: str, duration_seconds: int = 30) -> Optional[str]:
    """Fallback: Generate video from image with animation (when API fails)"""
    try:
        print(f"🎬 Fallback: Creating video from image for: {description}")
        
        # Ensure public directory exists
        os.makedirs("public", exist_ok=True)
        
        # Step 1: Generate an image first
        image_path = generate_image_with_stability(description)
        if not image_path:
            print("⚠️ Failed to generate image for video, creating placeholder video...")
            return create_placeholder_video(description, duration_seconds)
        
        # Step 2: Convert image to video
        try:
            from PIL import Image as PILImage, ImageEnhance
            import subprocess
            
            # Normalize image path
            image_file = image_path.replace("/public/", "public/")
            if not os.path.exists(image_file):
                image_file = image_path.lstrip("/")
                if not os.path.exists(image_file):
                    print(f"⚠️ Image file not found: {image_file}")
                    return create_placeholder_video(description, duration_seconds)
            
            # Create video filename
            video_filename = (
                f"video_{hashlib.md5(description.encode()).hexdigest()[:8]}_"
                f"{int(datetime.now().timestamp())}.mp4"
            )
            video_path = f"public/{video_filename}"
            
            # Check if ffmpeg is available
            ffmpeg_available = False
            try:
                result = subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True, timeout=5)
                ffmpeg_available = True
                print("✅ ffmpeg is available")
            except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
                print("⚠️ ffmpeg not available, creating animated GIF video...")
            
            if ffmpeg_available:
                # Use ffmpeg to create a 30-second video from the image with zoom/pan effect
                try:
                    cmd = [
                        "ffmpeg",
                        "-loop", "1",
                        "-i", image_file,
                        "-vf", f"scale=1080:1080:force_original_aspect_ratio=decrease,pad=1080:1080:(ow-iw)/2:(oh-ih)/2,zoompan=z='zoom+0.002':d={duration_seconds * 25}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'",
                        "-c:v", "libx264",
                        "-t", str(duration_seconds),
                        "-pix_fmt", "yuv420p",
                        "-y",
                        video_path
                    ]
                    
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
                    if result.returncode == 0 and os.path.exists(video_path):
                        file_size = os.path.getsize(video_path)
                        if file_size > 0:
                            print(f"✅ Video generated successfully: {video_path} ({file_size} bytes)")
                            return f"/public/{video_filename}"
                        else:
                            print(f"⚠️ Video file is empty, falling back to GIF")
                    else:
                        print(f"⚠️ ffmpeg failed: {result.stderr[:200] if result.stderr else 'Unknown error'}")
                except Exception as e:
                    print(f"⚠️ ffmpeg error: {e}")
            
            # Fallback: Create animated GIF video (works everywhere)
            return create_simple_video_from_image(image_file, video_path, duration_seconds)
                
        except Exception as e:
            print(f"❌ Error creating video from image: {e}")
            import traceback
            traceback.print_exc()
            return create_placeholder_video(description, duration_seconds)
            
    except Exception as e:
        print(f"❌ Video generation fallback error: {e}")
        import traceback
        traceback.print_exc()
        return create_placeholder_video(description, duration_seconds)


def generate_video_with_modelscope(description: str, duration_seconds: int = 30) -> Optional[str]:
    """Generate 30-second video using open-source tools.
    Primary: Uses Hugging Face Inference API with open-source models.
    Fallback: Creates video from generated image with animation.
    """
    # Try Hugging Face first (real video generation)
    result = generate_video_with_huggingface(description, duration_seconds)
    if result:
        return result
    
    # If Hugging Face fails, use image-to-video fallback
    print("⚠️ Hugging Face video generation failed, using image-to-video fallback...")
    return generate_video_from_image_fallback(description, duration_seconds)


def create_simple_video_from_image(image_path: str, video_path: str, duration_seconds: int) -> Optional[str]:
    """Create a simple animated video from an image (GIF format)"""
    try:
        from PIL import Image as PILImage, ImageEnhance
        import random
        
        # Ensure public directory exists
        os.makedirs("public", exist_ok=True)
        
        # Load image
        if not os.path.exists(image_path):
            print(f"⚠️ Image not found: {image_path}")
            return create_placeholder_video("", duration_seconds)
            
        img = PILImage.open(image_path)
        img = img.resize((1080, 1080), PILImage.Resampling.LANCZOS)
        
        # Create animated GIF with smooth transitions
        frames = []
        fps = 2  # 2 frames per second for smooth animation
        num_frames = min(duration_seconds * fps, 60)  # Max 60 frames
        
        for i in range(num_frames):
            # Create smooth animation with zoom and brightness variation
            zoom_factor = 1.0 + (i / num_frames) * 0.1  # Gradual zoom
            brightness_variation = 1.0 + (random.random() - 0.5) * 0.15
            
            # Apply zoom
            new_size = (int(1080 * zoom_factor), int(1080 * zoom_factor))
            zoomed = img.resize(new_size, PILImage.Resampling.LANCZOS)
            
            # Crop to center
            left = (zoomed.width - 1080) // 2
            top = (zoomed.height - 1080) // 2
            frame = zoomed.crop((left, top, left + 1080, top + 1080))
            
            # Apply brightness variation
            enhancer = ImageEnhance.Brightness(frame)
            frame = enhancer.enhance(brightness_variation)
            
            frames.append(frame)
        
        # Save as animated GIF
        gif_filename = video_path.replace(".mp4", ".gif")
        frames[0].save(
            gif_filename,
            save_all=True,
            append_images=frames[1:],
            duration=int(1000 / fps),  # Duration per frame in milliseconds
            loop=0,
            optimize=False
        )
        
        file_size = os.path.getsize(gif_filename) if os.path.exists(gif_filename) else 0
        print(f"✅ Created animated GIF video: {gif_filename} ({file_size} bytes, {num_frames} frames)")
        return f"/public/{os.path.basename(gif_filename)}"
        
    except Exception as e:
        print(f"❌ Error creating simple video: {e}")
        import traceback
        traceback.print_exc()
        return create_placeholder_video("", duration_seconds)


def create_placeholder_video(description: str, duration_seconds: int) -> Optional[str]:
    """Create a placeholder video when generation fails"""
    try:
        from PIL import Image as PILImage, ImageDraw, ImageFont
        
        # Create a simple video placeholder (animated GIF)
        width, height = 1080, 1080
        frames = []
        num_frames = min(duration_seconds * 2, 60)
        
        for i in range(num_frames):
            # Create frame with gradient
            img = PILImage.new('RGB', (width, height), color=(50 + i % 50, 100 + i % 50, 150 + i % 50))
            draw = ImageDraw.Draw(img)
            
            # Add text
            try:
                font = ImageFont.truetype("arial.ttf", 60)
            except:
                font = ImageFont.load_default()
            
            text = description[:50] if description else "Video Placeholder"
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            position = ((width - text_width) // 2, (height - text_height) // 2)
            
            draw.text(position, text, fill=(255, 255, 255), font=font)
            frames.append(img)
        
        # Save as animated GIF
        filename = f"placeholder_video_{int(datetime.now().timestamp())}.gif"
        filepath = f"public/{filename}"
        os.makedirs("public", exist_ok=True)
        
        frames[0].save(
            filepath,
            save_all=True,
            append_images=frames[1:],
            duration=int(1000 / 2),  # 2 fps
            loop=0
        )
        
        print(f"✅ Created placeholder video: {filepath}")
        return f"/public/{filename}"
        
    except Exception as e:
        print(f"Error creating placeholder video: {e}")
        return None


def generate_video(description: str, provider: str = "huggingface", duration_seconds: int = 30, user_id: str = None) -> Optional[str]:
    """Generate video using specified provider"""
    if provider == "huggingface" or provider == "modelscope":
        # Use Hugging Face Inference API with open-source models
        return generate_video_with_modelscope(description, duration_seconds)
    else:
        # Default to Hugging Face
        return generate_video_with_modelscope(description, duration_seconds)


# Root endpoint removed to allow frontend serving


# Health endpoint at root level for Docker health checks
@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "groq_configured": bool(GROQ_API_KEY),
            "chatgpt_configured": bool(CHATGPT_API_KEY),
            "stability_configured": bool(STABILITY_API_KEY),
            "nano_banana_configured": bool(PIAPI_API_KEY),
        },
    }


@main_app.get("/api/usage-stats")
async def get_usage_stats(current_user = Depends(get_current_user_dependency)):
    """Get user's API usage statistics"""
    try:
        user_id = str(current_user.id) if current_user and hasattr(current_user, 'id') else None
        print(f"🔍 Usage stats - user_id: {user_id}, current_user type: {type(current_user)}")
        if not user_id:
            raise HTTPException(status_code=401, detail="User not authenticated")
        
        # Create a new session directly
        from database import SessionLocal
        db = SessionLocal()
        try:
            # Get total usage by service
            from sqlalchemy import func
            print(f"🔍 Querying usage stats for user_id: {user_id}")
            usage_stats = db.query(
                ApiUsage.service,
                func.sum(ApiUsage.tokens_used).label('total_tokens'),
                func.sum(ApiUsage.credits_used).label('total_credits'),
                func.count(ApiUsage.id).label('total_requests')
            ).filter(
                ApiUsage.user_id == user_id
            ).group_by(ApiUsage.service).all()
            print(f"🔍 Query result: {usage_stats}")
        finally:
            db.close()
        
        # Format the response
        stats = {}
        for stat in usage_stats:
            stats[stat.service] = {
                "tokens_used": stat.total_tokens or 0,
                "credits_used": stat.total_credits or 0,
                "requests_made": stat.total_requests or 0
            }
        
        print(f"🔍 Usage stats response: {stats}")
        return {"success": True, "usage": stats}
        
    except Exception as e:
        print(f"Error getting usage stats: {e}")
        return {"success": False, "error": str(e)}


@main_app.post("/api/test-usage-log")
async def test_usage_log(current_user = Depends(get_current_user_dependency)):
    """Test endpoint to manually log usage for testing"""
    try:
        user_id = current_user.get("id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User not authenticated")
        
        # Log some test usage
        log_api_usage(user_id, "groq", "caption", 120, 0, {"test": "data"})
        log_api_usage(user_id, "piapi", "image", 0, 300000, {"test": "data"})
        
        return {"success": True, "message": "Test usage logged successfully"}
        
    except Exception as e:
        return {"success": False, "error": str(e)}


@main_app.post("/generate-post", response_model=PostResponse)
async def generate_post(request: PostRequest, current_user = Depends(get_current_user_dependency)):
    """Generate Instagram post with image and caption"""
    try:
        if not request.description or len(request.description.strip()) < 3:
            raise HTTPException(
                status_code=400,
                detail="Description must be at least 3 characters long",
            )

        description = request.description.strip()

        # Generate caption using selected provider
        caption = generate_caption(description, request.caption_provider)

        # Generate image using selected provider
        image_path = generate_image(description, request.image_provider, str(current_user.id))

        if not image_path:
            return PostResponse(
                success=False, error="Failed to generate image. Please try again."
            )

        # Save to database
        try:
            # Get default campaign ID
            default_campaign_id = await db_service.get_default_campaign_id()
            
            # Create post record
            post_id = await db_service.create_post(
                original_description=description,
                caption=caption,
                image_path=image_path,
                campaign_id=default_campaign_id,
                platforms=request.platforms,
                subreddit=request.subreddit,
                user_id=str(current_user.id)
            )
            
            # Save image information
            if image_path:
                generation_method = request.image_provider or "stability"
                await db_service.save_image_info(
                    post_id=post_id,
                    file_path=image_path,
                    generation_method=generation_method,
                    generation_prompt=description
                )
            
            # Save caption information
            if caption:
                caption_method = request.caption_provider or "groq"
                await db_service.save_caption_info(
                    post_id=post_id,
                    content=caption,
                    generation_method=caption_method,
                    generation_prompt=f"Write a catchy Instagram caption for: {description}. Include 3-5 relevant hashtags and emojis."
                )
                
            print(f"Post saved to database with ID: {post_id}")
            
        except Exception as db_error:
            print(f"Database save error: {db_error}")
            # Continue without failing the request
            
        return PostResponse(success=True, caption=caption, image_path=image_path)

    except HTTPException:
        raise
    except Exception as e:
        return PostResponse(success=False, error=f"Error generating post: {str(e)}")


@main_app.post("/generate-caption", response_model=PostResponse)
async def generate_caption_endpoint(request: PostRequest):
    """Generate only Instagram caption"""
    try:
        if not request.description or len(request.description.strip()) < 3:
            raise HTTPException(
                status_code=400,
                detail="Description must be at least 3 characters long",
            )

        description = request.description.strip()
        caption = generate_caption(description, request.caption_provider)

        return PostResponse(success=True, caption=caption)

    except HTTPException:
        raise
    except Exception as e:
        return PostResponse(success=False, error=f"Error generating caption: {str(e)}")


@main_app.post("/generate-captions-batch")
async def generate_captions_batch(request: BatchRequest, authorization: Optional[str] = Header(None)):
    """Generate multiple captions only (for advanced mode)"""
    try:
        print(f"📝 Batch captions request: description='{request.description}', num_posts={request.num_posts}, provider='{request.caption_provider}'")
        description = (request.description or "").strip()
        if len(description) < 3:
            raise HTTPException(
                status_code=400, detail="Description must be at least 3 characters long"
            )
        if request.num_posts <= 0:
            raise HTTPException(
                status_code=400, detail="num_posts must be a positive integer"
            )
        if request.num_posts > 20:
            raise HTTPException(
                status_code=400, detail="num_posts is too large; max 20 per batch"
            )

        captions = []
        for i in range(request.num_posts):
            try:
                # Generate varied description for each caption
                if request.num_posts > 1:
                    varied_description = f"{description} - variation {i + 1}"
                else:
                    varied_description = description
                
                # Try to get user_id from authorization header if available
                user_id = None
                if authorization and authorization.startswith('Bearer '):
                    try:
                        token = authorization.replace('Bearer ', '')
                        current_user = await auth_service.get_current_user(token)
                        user_id = str(current_user.id) if current_user and hasattr(current_user, 'id') else None
                        print(f"🔍 Caption generation - user_id: {user_id}")
                    except Exception as e:
                        print(f"Failed to get user from token: {e}")
                        user_id = None
                caption = generate_caption(varied_description, request.caption_provider, user_id)
                captions.append(caption)
                
            except Exception as e:
                print(f"Error generating caption {i + 1}: {e}")
                captions.append(f"Error generating caption: {str(e)}")
        
        response = {"success": True, "captions": captions}
        print(f"📝 Batch captions response: {response}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        error_response = {"success": False, "error": f"Error generating captions: {str(e)}"}
        print(f"❌ Batch captions error: {error_response}")
        return error_response

@main_app.post("/generate-video-only")
async def generate_video_only(request: dict, current_user = Depends(get_current_user_dependency)):
    """Generate 30-second video only without creating a post"""
    try:
        description = request.get("description", "").strip()
        video_provider = request.get("video_provider", "modelscope")
        duration_seconds = request.get("duration_seconds", 30)
        
        if len(description) < 3:
            return {"success": False, "error": "Description must be at least 3 characters long"}
        
        user_id = str(current_user.id) if current_user and hasattr(current_user, 'id') else None
        video_path = generate_video(description, video_provider, duration_seconds, user_id)
        
        if not video_path:
            return {"success": False, "error": "Failed to generate video. Please try again."}
        
        return {
            "success": True,
            "video_path": video_path,
            "duration_seconds": duration_seconds
        }
    except Exception as e:
        print(f"Error generating video: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}


@main_app.post("/generate-image-only")
async def generate_image_only(request: dict, current_user = Depends(get_current_user_dependency)):
    """Generate image only without creating a post (for advanced mode)"""
    try:
        description = request.get("description", "").strip()
        image_provider = request.get("image_provider", "stability")
        
        if len(description) < 3:
            raise HTTPException(
                status_code=400, detail="Description must be at least 3 characters long"
            )
        
        # Generate image using selected provider with user_id for logging
        image_path = generate_image(description, image_provider, str(current_user.id))
        
        if not image_path:
            raise HTTPException(
                status_code=500, detail="Failed to generate image. Please try again."
            )
        
        return {"success": True, "image_path": image_path}
        
    except HTTPException:
        raise
    except Exception as e:
        return {"success": False, "error": f"Error generating image: {str(e)}"}

class UploadImageRequest(BaseModel):
    data_url: str
    description: Optional[str] = "custom_image"

@main_app.post("/upload-custom-image")
async def upload_custom_image(request: UploadImageRequest, current_user = Depends(get_current_user_dependency)):
    """Upload and save a custom image from data URL"""
    try:
        print(f"🔍 Upload custom image called by user: {current_user.id if current_user else 'None'}")
        data_url = request.data_url.strip() if request.data_url else ""
        description = request.description.strip() if request.description else "custom_image"
        print(f"🔍 Data URL length: {len(data_url)}, Description: {description[:50]}...")
        
        if not data_url or not data_url.startswith('data:image/'):
            raise HTTPException(
                status_code=400, detail="Invalid data URL. Must be a valid image data URL."
            )
        
        # Parse data URL
        try:
            header, data = data_url.split(',', 1)
            # Extract image format from header (e.g., "data:image/jpeg;base64")
            format_part = header.split(';')[0].split('/')[-1]
            if format_part not in ['jpeg', 'jpg', 'png', 'gif', 'webp']:
                format_part = 'png'  # Default to PNG
            
            # Decode base64 data
            image_data = base64.b64decode(data)
        except Exception as e:
            raise HTTPException(
                status_code=400, detail=f"Invalid data URL format: {str(e)}"
            )
        
        # Create filename with timestamp and hash
        timestamp = int(time.time())
        hash_suffix = hashlib.md5(image_data[:1000]).hexdigest()[:8]  # Use first 1KB for hash
        
        # Sanitize description for filename (remove special characters)
        import re
        sanitized_description = re.sub(r'[^\w\s-]', '', description).strip()
        sanitized_description = re.sub(r'[-\s]+', '_', sanitized_description)
        if not sanitized_description:
            sanitized_description = "custom_image"
        
        filename = f"custom_{sanitized_description}_{timestamp}_{hash_suffix}.{format_part}"
        
        # Ensure public directory exists (same location as AI-generated images)
        public_dir = "public"
        if not os.path.exists(public_dir):
            os.makedirs(public_dir)
            print(f"📁 Created public directory: {os.path.abspath(public_dir)}")
        
        # Save image file (same way as AI-generated images)
        file_path = os.path.join(public_dir, filename)
        with open(file_path, 'wb') as f:
            f.write(image_data)
        
        # Verify file was saved
        if not os.path.exists(file_path):
            raise HTTPException(status_code=500, detail="Failed to save image file")
        
        file_size = os.path.getsize(file_path)
        absolute_path = os.path.abspath(file_path)
        
        print(f"✅ Custom image uploaded successfully")
        print(f"   File path: {file_path}")
        print(f"   Absolute path: {absolute_path}")
        print(f"   File size: {file_size} bytes")
        print(f"   File exists: {os.path.exists(file_path)}")
        
        # Return the relative path for the frontend (same format as AI-generated images)
        relative_path = f"/public/{filename}"
        # Also return as image_url for compatibility
        image_url = relative_path
        
        print(f"   Relative path: {relative_path}")
        print(f"   Image URL: {image_url}")
        return {
            "success": True, 
            "image_path": relative_path,
            "image_url": image_url,  # Add image_url for frontend compatibility
            "url": image_url,  # Also include 'url' for compatibility
            "filename": filename
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error uploading custom image: {e}")
        return {"success": False, "error": f"Error uploading image: {str(e)}"}

def _compute_schedule_dates(num_posts: int, days: int) -> List[str]:
    """Distribute posts across the given days; allow multiple posts per day.
    
    Posts start from the next hour after current time.
    No posts scheduled after 10 PM (22:00).
    Example: If created at 2:30 PM, first post at 3:00 PM.
    """
    if num_posts <= 0:
        return []
    if days <= 0:
        days = 1

    # Define business hours (9 AM to 10 PM)
    EARLIEST_HOUR = 9
    LATEST_HOUR = 22  # 10 PM
    BUSINESS_HOURS_PER_DAY = LATEST_HOUR - EARLIEST_HOUR  # 13 hours

    # Start from next hour after current time, but not earlier than 9 AM
    now = datetime.now()
    next_hour = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    
    # If it's past 10 PM, start tomorrow at 9 AM
    if next_hour.hour > LATEST_HOUR:
        start_time = (next_hour + timedelta(days=1)).replace(hour=EARLIEST_HOUR)
    # If it's before 9 AM, start at 9 AM today
    elif next_hour.hour < EARLIEST_HOUR:
        start_time = next_hour.replace(hour=EARLIEST_HOUR)
    else:
        start_time = next_hour

    # Calculate optimal distribution
    posts_per_day = (num_posts + days - 1) // days  # Ceiling division
    
    # If too many posts for business hours, spread across more days
    if posts_per_day > BUSINESS_HOURS_PER_DAY:
        # Recalculate days to accommodate all posts within business hours
        days = (num_posts + BUSINESS_HOURS_PER_DAY - 1) // BUSINESS_HOURS_PER_DAY
        posts_per_day = (num_posts + days - 1) // days

    results: List[str] = []
    for i in range(num_posts):
        day_index = i // posts_per_day
        slot_index = i % posts_per_day

        # Start at the base time for this day
        schedule_time = start_time + timedelta(days=day_index)
        
        if posts_per_day == 1:
            # Single post per day, use the start time for each day
            # But ensure it's within business hours
            if schedule_time.hour < EARLIEST_HOUR:
                schedule_time = schedule_time.replace(hour=EARLIEST_HOUR)
            elif schedule_time.hour > LATEST_HOUR:
                schedule_time = schedule_time.replace(hour=LATEST_HOUR)
        else:
            # Multiple posts per day, distribute evenly within business hours
            base_hour = max(schedule_time.hour, EARLIEST_HOUR)
            hours_remaining_today = LATEST_HOUR - base_hour
            
            # If not enough hours left today for all posts, spread across more days
            if hours_remaining_today < posts_per_day - 1:
                # Redistribute posts across more days to stay within business hours
                # Move this post to the next day if needed
                if slot_index > hours_remaining_today:
                    extra_days = (slot_index - hours_remaining_today + BUSINESS_HOURS_PER_DAY - 1) // BUSINESS_HOURS_PER_DAY
                    schedule_time = (schedule_time + timedelta(days=extra_days)).replace(hour=EARLIEST_HOUR)
                    slot_index = slot_index % BUSINESS_HOURS_PER_DAY
                    base_hour = EARLIEST_HOUR
                    hours_remaining_today = BUSINESS_HOURS_PER_DAY
            
            # Calculate the target hour within business hours
            if posts_per_day > 1 and hours_remaining_today > 0:
                hour_spacing = max(1, hours_remaining_today // posts_per_day)
                target_hour = base_hour + (slot_index * hour_spacing)
                
                # Ensure we absolutely don't exceed business hours
                target_hour = min(target_hour, LATEST_HOUR)
                
                schedule_time = schedule_time.replace(hour=target_hour)

        results.append(schedule_time.isoformat())
    return results


@main_app.post("/generate-batch", response_model=BatchResponse)
async def generate_batch(request: BatchRequest, current_user = Depends(get_current_user_dependency)):
    """Generate multiple posts and return caption, image path, and scheduled time for each."""
    import time
    request_id = int(time.time() * 1000) % 10000
    asset_type_received = getattr(request, 'asset_type', 'NOT_SET') or 'NOT_SET'
    print(f"🔍 DEBUG [{request_id}]: Received request - num_posts: {request.num_posts}, days: {request.days}, description: {request.description}")
    print(f"🔍 DEBUG [{request_id}]: asset_type received: '{asset_type_received}' (type: {type(asset_type_received)})")
    try:
        
        description = (request.description or "").strip()
        if len(description) < 3:
            raise HTTPException(
                status_code=400, detail="Description must be at least 3 characters long"
            )
        if request.days <= 0:
            raise HTTPException(status_code=400, detail="Days must be a positive integer")
        if request.num_posts <= 0:
            raise HTTPException(
                status_code=400, detail="num_posts must be a positive integer"
            )
        if request.num_posts > 20:
            raise HTTPException(
                status_code=400, detail="num_posts is too large; max 20 per batch"
            )

        # Create batch operation record
        batch_id = None
        try:
            batch_id = await db_service.create_batch_operation(
                description=description,
                num_posts=request.num_posts,
                days_duration=request.days,
                created_by=str(current_user.id)
            )
            print(f"Created batch operation with ID: {batch_id}")
        except Exception as db_error:
            print(f"Error creating batch operation: {db_error}")

        # Get default campaign ID
        default_campaign_id = None
        try:
            default_campaign_id = await db_service.get_default_campaign_id()
        except Exception as db_error:
            print(f"Error getting default campaign: {db_error}")

        items: List[BatchItem] = []
        posts_generated = 0
        posts_failed = 0
        error_messages = []

        print(f"🔄 DEBUG [{request_id}]: Starting to generate {request.num_posts} posts")
        for i in range(request.num_posts):
            print(f"🔄 DEBUG [{request_id}]: Generating post {i+1} of {request.num_posts}")
            try:
                # Create variation for each post to make them unique
                if request.num_posts > 1:
                    # Add more diverse variations to ensure unique content
                    import random
                    import time
                    
                    variation_phrases = [
                        "premium edition", "limited time offer", "new arrival", "best seller",
                        "trending now", "exclusive", "special edition", "must have", "top rated",
                        "hot deal", "amazing quality", "perfect choice", "highly recommended",
                        "customer favorite", "award winning", "innovative design", "superior quality"
                    ]
                    
                    # Use both index and random selection for more variety
                    selected_phrase = variation_phrases[i % len(variation_phrases)]
                    varied_description = f"{description} - {selected_phrase}"
                    
                    # Add timestamp-based variation to ensure uniqueness
                    timestamp_variation = int(time.time() * 1000) % 1000
                    if timestamp_variation % 2 == 0:
                        varied_description += f" (variation {timestamp_variation})"
                else:
                    varied_description = description
                
                caption = generate_caption(varied_description, request.caption_provider)
                
                # Generate image or video based on asset_type
                # Get asset_type from request - Pydantic model should have this attribute
                asset_type = getattr(request, 'asset_type', None)
                if not asset_type or asset_type == '':
                    asset_type = 'image'  # Default to image if not set
                
                # Normalize to lowercase and strip whitespace
                asset_type = str(asset_type).lower().strip()
                if asset_type not in ['image', 'video']:
                    asset_type = 'image'  # Fallback to image if invalid
                
                print(f"🎯 DEBUG [{request_id}] Post {i+1}: asset_type = '{asset_type}'")
                print(f"   Request type: {type(request)}")
                print(f"   request.asset_type raw value: {getattr(request, 'asset_type', 'NOT_SET')}")
                
                # VIDEO GENERATION - COMMENTED OUT FOR NOW
                # if asset_type == "video":
                #     print(f"🎬 DEBUG [{request_id}] Post {i+1}: Generating 30-SECOND VIDEO for '{varied_description[:50]}...'")
                #     print(f"🎬 Using Hugging Face open-source video generation API...")
                #     image_path = generate_video(varied_description, "huggingface", 30, str(current_user.id))
                #     error_msg_prefix = "Failed to generate video"
                #     if image_path:
                #         print(f"✅ DEBUG [{request_id}] Post {i+1}: Video generated: {image_path}")
                #     else:
                #         print(f"❌ DEBUG [{request_id}] Post {i+1}: Video generation FAILED - returned None")
                # else:
                # Force image generation for now (video generation commented out)
                if asset_type == "video":
                    print(f"⚠️ VIDEO GENERATION DISABLED - Falling back to image generation")
                    asset_type = "image"  # Force image generation
                
                if True:  # Always generate images for now
                    print(f"🖼️ DEBUG [{request_id}] Post {i+1}: Generating IMAGE for '{varied_description[:50]}...'")
                    image_path = generate_image(varied_description, request.image_provider, str(current_user.id))
                    error_msg_prefix = "Failed to generate image"
                    if image_path:
                        print(f"✅ DEBUG [{request_id}] Post {i+1}: Image generated: {image_path}")
                    else:
                        print(f"❌ DEBUG [{request_id}] Post {i+1}: Image generation FAILED - returned None")
                
                # Add small delay to ensure timestamp variation works
                if request.num_posts > 1:
                    import time
                    time.sleep(0.1)  # 100ms delay between generations
                
                if not image_path:
                    error_msg = error_msg_prefix
                    items.append(
                        BatchItem(error=error_msg, scheduled_at=None)
                    )
                    posts_failed += 1
                    error_messages.append(f"Post {i+1}: {error_msg}")
                    continue
                
                # Save to database as DRAFT (no scheduling)
                try:
                    # Create post record as draft
                    post_id = await db_service.create_post(
                        campaign_name=request.campaign_name or "",
                        original_description=varied_description,  # Use varied description
                        caption=caption,
                        image_path=image_path,
                        scheduled_at=None,  # No scheduling - create as draft
                        campaign_id=default_campaign_id,
                        platforms=None,  # Platforms will be set when user selects them
                        status="draft",  # Explicitly set as draft
                        batch_id=batch_id,
                        user_id=str(current_user.id)
                    )
                    
                    # Save image information
                    image_generation_method = request.image_provider or "stability"
                    await db_service.save_image_info(
                        post_id=post_id,
                        file_path=image_path,
                        generation_method=image_generation_method,
                        generation_prompt=varied_description  # Use varied description
                    )
                    
                    # Save caption information
                    caption_generation_method = request.caption_provider or "groq"
                    await db_service.save_caption_info(
                        post_id=post_id,
                        content=caption,
                        generation_method=caption_generation_method,
                        generation_prompt=f"Write a catchy Instagram caption for: {varied_description}. Include 3-5 relevant hashtags and emojis."
                    )
                    
                    # Skip posting schedule - this is a draft post
                    # Scheduling will be done later when user clicks "Schedule" button
                    
                    posts_generated += 1
                    print(f"Batch post {i+1}/{request.num_posts} saved to database with ID: {post_id}")
                    
                except Exception as db_error:
                    print(f"Database save error for post {i+1}: {db_error}")
                    error_messages.append(f"Post {i+1}: Database save failed - {str(db_error)}")
                    # Continue without failing the request
                
                items.append(
                    BatchItem(
                        caption=caption, image_path=image_path, scheduled_at=None
                    )
                )
                
            except Exception as e:
                error_msg = str(e)
                items.append(BatchItem(error=error_msg, scheduled_at=None))
                posts_failed += 1
                error_messages.append(f"Post {i+1}: {error_msg}")

        # Update batch operation status
        if batch_id:
            try:
                status = "completed" if posts_failed == 0 else ("failed" if posts_generated == 0 else "completed")
                await db_service.update_batch_operation_progress(
                    batch_id=batch_id,
                    posts_generated=posts_generated,
                    posts_failed=posts_failed,
                    status=status,
                    error_messages=error_messages if error_messages else None
                )
                print(f"Updated batch operation {batch_id}: {posts_generated} generated, {posts_failed} failed")
            except Exception as db_error:
                print(f"Error updating batch operation: {db_error}")

        return BatchResponse(success=True, items=items, batch_id=batch_id)

    except HTTPException:
        raise
    except Exception as e:
        return BatchResponse(success=False, items=[], error=f"Error generating batch: {str(e)}")


@main_app.post("/api/batch/create")
async def create_batch_only(request: BatchRequest):
    """Create a batch operation without generating posts (for advanced mode)"""
    try:
        description = (request.description or "").strip()
        if len(description) < 3:
            raise HTTPException(
                status_code=400, detail="Description must be at least 3 characters long"
            )
        if request.days <= 0:
            raise HTTPException(status_code=400, detail="Days must be a positive integer")
        if request.num_posts <= 0:
            raise HTTPException(
                status_code=400, detail="num_posts must be a positive integer"
            )
        if request.num_posts > 20:
            raise HTTPException(
                status_code=400, detail="num_posts is too large; max 20 per batch"
            )

        # Create batch operation record only
        batch_id = await db_service.create_batch_operation(
            description=description,
            num_posts=request.num_posts,
            days_duration=request.days,
            created_by="api_user"
        )
        
        return {"success": True, "batch_id": batch_id}
        
    except HTTPException:
        raise
    except Exception as e:
        return {"success": False, "error": f"Error creating batch: {str(e)}"}


# Database management endpoints
@main_app.post("/api/posts")
async def create_post(post_data: dict, current_user = Depends(get_current_user_dependency)):
    """Create a new post in database and associate it with the current user"""
    try:
        # Get default campaign ID
        default_campaign_id = await db_service.get_default_campaign_id()
        
        # Parse scheduled_at if provided
        scheduled_at = None
        if post_data.get('scheduled_at'):
            from datetime import datetime
            scheduled_at = datetime.fromisoformat(post_data['scheduled_at'].replace('Z', '+00:00'))
        
        # Create post record with user_id so calendar queries work per-user
        post_id = await db_service.create_post(
            campaign_name=post_data.get('campaign_name', ''),
            original_description=post_data.get('original_description', ''),
            caption=post_data.get('caption', ''),
            image_path=post_data.get('image_path'),
            scheduled_at=scheduled_at,
            campaign_id=default_campaign_id,
            platforms=post_data.get('platforms'),
            subreddit=post_data.get('subreddit'),
            status=post_data.get('status', 'draft'),
            batch_id=post_data.get('batch_id'),
            user_id=str(current_user.id)
        )
        
        return {"success": True, "post_id": post_id}
    except Exception as e:
        return {"success": False, "error": str(e)}

@main_app.get("/api/posts")
async def get_recent_posts(limit: int = 10, current_user = Depends(get_current_user_dependency)):
    """Get recent posts from database"""
    try:
        posts = await db_service.get_recent_posts(limit=limit, user_id=str(current_user.id))
        return {"success": True, "posts": posts}
    except Exception as e:
        return {"success": False, "error": str(e)}

@main_app.put("/api/posts/{post_id}/schedule")
async def schedule_post(post_id: str, schedule_data: dict, current_user = Depends(get_current_user_dependency)):
    """Schedule an existing post and create calendar event"""
    try:
        # Parse scheduled_at
        scheduled_at = None
        if schedule_data.get('scheduled_at'):
            from datetime import datetime
            scheduled_at = datetime.fromisoformat(schedule_data['scheduled_at'].replace('Z', '+00:00'))
        
        if not scheduled_at:
            raise HTTPException(status_code=400, detail="scheduled_at is required")
        
# Update post schedule and create calendar event
        success = await db_service.update_post_schedule(
            post_id=post_id,
            scheduled_at=scheduled_at,
            status=schedule_data.get('status', 'scheduled'),
            platforms=schedule_data.get('platforms'),
            user_id=str(current_user.id)
        )
        
        if success:
            return {"success": True, "message": "Post scheduled successfully"}
        else:
            raise HTTPException(status_code=404, detail="Post not found or update failed")
    
    except HTTPException:
        raise
    except Exception as e:
        return {"success": False, "error": str(e)}


def _record_to_dict(record):
    """Convert a database Record object to a dictionary"""
    if record is None:
        return None
    if isinstance(record, dict):
        return record
    
    try:
        # For databases.backends.postgres.Record objects, try direct dict() conversion first
        # This is the most reliable method for databases library Record objects
        try:
            converted = dict(record)
            print(f"✅ Successfully converted Record to dict using dict() - {len(converted)} keys")
            return converted
        except Exception as dict_error:
            print(f"⚠️ dict() conversion failed: {dict_error}")
            import traceback
            print(f"⚠️ dict() traceback: {traceback.format_exc()}")
        
        # Fallback: Try to access as mapping using known field names
        result = {}
        # Use known field names from the SELECT query
        known_fields = ['id', 'caption', 'scheduled_at', 'status', 'platforms', 
                       'image_url', 'image_path', 'original_description', 'campaign_name', 
                       'created_at', 'updated_at', 'user_id']
        
        print(f"🔍 Attempting manual key extraction for {len(known_fields)} fields")
        for key in known_fields:
            try:
                # Try dictionary-style access first (most common for Record objects)
                if hasattr(record, '__getitem__'):
                    try:
                        value = record[key]
                        result[key] = value
                        continue
                    except (KeyError, TypeError, IndexError):
                        pass
                
                # Fallback to attribute access
                if hasattr(record, key):
                    try:
                        value = getattr(record, key, None)
                        if value is not None:
                            result[key] = value
                    except AttributeError:
                        pass
            except Exception as field_error:
                print(f"⚠️ Could not access field '{key}': {field_error}")
                continue
        
        if result:
            print(f"✅ Successfully converted Record to dict using manual extraction ({len(result)} keys)")
            print(f"   Keys: {list(result.keys())}")
            return result
        else:
            print(f"⚠️ No fields extracted from Record - returning None")
            return None
            
    except Exception as e:
        print(f"⚠️ Error converting record: {e}")
        import traceback
        print(f"⚠️ Full traceback: {traceback.format_exc()}")
        return None

@main_app.put("/api/posts/{post_id}")
async def update_post(post_id: str, update_data: dict, current_user = Depends(get_current_user_dependency)):
    """Update a post in database and sync calendar events"""
    try:
        print(f"🔍 Update post called: post_id={post_id}, update_data={update_data}")
        print(f"🔍 Current user: {current_user.id if current_user else 'None'}")
        # Update post in database
        query = "UPDATE posts SET"
        values = {"post_id": post_id}
        updates = []
        
        scheduled_at_updated = False
        status_updated = False
        platforms_updated = False
        images_payload = update_data.pop("images", None) if "images" in update_data else None
        
        # Build dynamic update query
        if "caption" in update_data:
            updates.append("caption = :caption")
            values["caption"] = update_data["caption"]
            
        if "scheduled_at" in update_data:
            scheduled_at = update_data["scheduled_at"]
            if scheduled_at is None:
                # Handle null values properly
                updates.append("scheduled_at = NULL")
            else:
                updates.append("scheduled_at = :scheduled_at")
                if isinstance(scheduled_at, str):
                    scheduled_at = datetime.fromisoformat(scheduled_at.replace('Z', '+00:00'))
                values["scheduled_at"] = scheduled_at
            scheduled_at_updated = True
            
        if "status" in update_data:
            updates.append("status = :status")
            values["status"] = update_data["status"]
            status_updated = True
            
        if "original_description" in update_data:
            updates.append("original_description = :original_description")
            values["original_description"] = update_data["original_description"]
            
        if "platforms" in update_data:
            updates.append("platforms = :platforms")
            values["platforms"] = update_data["platforms"]
            platforms_updated = True
            
        if "image_path" in update_data:
            # Handle null values properly - use NULL in SQL for None values
            if update_data["image_path"] is None:
                updates.append("image_path = NULL")
            else:
                updates.append("image_path = :image_path")
                values["image_path"] = update_data["image_path"]
            
        if "image_url" in update_data:
            # Handle null values properly - use NULL in SQL for None values
            if update_data["image_url"] is None:
                updates.append("image_url = NULL")
            else:
                updates.append("image_url = :image_url")
                values["image_url"] = update_data["image_url"]
            
        if not updates:
            return {"success": True, "message": "No updates provided"}
            
        # Add updated_at timestamp
        updates.append("updated_at = NOW()")
        
        query += " " + ", ".join(updates) + " WHERE id = :post_id"
        
        from database import db_manager
        await db_manager.execute_query(query, values)
        
        # Fetch and return the updated post data
        fetch_query = """
            SELECT id, caption, scheduled_at, status, platforms, image_url, image_path,
                   original_description, campaign_name, created_at, updated_at
            FROM posts WHERE id = :post_id
        """
        updated_post = await db_manager.fetch_one(fetch_query, {"post_id": post_id})
        print(f"🔍 Fetched updated_post type: {type(updated_post)}")
        print(f"🔍 Fetched updated_post: {updated_post}")
        
        # Convert updated_post to dict using helper function
        updated_post = _record_to_dict(updated_post)
        if updated_post:
            print(f"✅ Converted updated_post to dict: {len(updated_post)} keys")
            print(f"   Image URL: {updated_post.get('image_url', 'None')}")
            print(f"   Image Path: {updated_post.get('image_path', 'None')}")
        else:
            print(f"❌ Failed to convert updated_post to dict - returning None")
            # If conversion failed, fetch again and try a different approach
            try:
                # Try fetching as a simple query that returns a dict
                simple_query = """
                    SELECT id::text, caption, scheduled_at, status, platforms, 
                           image_url, image_path, original_description, campaign_name, 
                           created_at, updated_at
                    FROM posts WHERE id = :post_id
                """
                simple_result = await db_manager.fetch_one(simple_query, {"post_id": post_id})
                if simple_result:
                    # Try accessing fields directly
                    updated_post = {
                        'id': str(simple_result.get('id') if hasattr(simple_result, 'get') else getattr(simple_result, 'id', None)),
                        'caption': simple_result.get('caption') if hasattr(simple_result, 'get') else getattr(simple_result, 'caption', None),
                        'scheduled_at': simple_result.get('scheduled_at') if hasattr(simple_result, 'get') else getattr(simple_result, 'scheduled_at', None),
                        'status': simple_result.get('status') if hasattr(simple_result, 'get') else getattr(simple_result, 'status', None),
                        'platforms': simple_result.get('platforms') if hasattr(simple_result, 'get') else getattr(simple_result, 'platforms', None),
                        'image_url': simple_result.get('image_url') if hasattr(simple_result, 'get') else getattr(simple_result, 'image_url', None),
                        'image_path': simple_result.get('image_path') if hasattr(simple_result, 'get') else getattr(simple_result, 'image_path', None),
                        'original_description': simple_result.get('original_description') if hasattr(simple_result, 'get') else getattr(simple_result, 'original_description', None),
                        'campaign_name': simple_result.get('campaign_name') if hasattr(simple_result, 'get') else getattr(simple_result, 'campaign_name', None),
                        'created_at': simple_result.get('created_at') if hasattr(simple_result, 'get') else getattr(simple_result, 'created_at', None),
                        'updated_at': simple_result.get('updated_at') if hasattr(simple_result, 'get') else getattr(simple_result, 'updated_at', None),
                    }
                    print(f"✅ Fallback conversion successful: {len(updated_post)} keys")
            except Exception as fallback_error:
                print(f"❌ Fallback conversion also failed: {fallback_error}")
        
        updated_images = None
        if images_payload is not None:
            try:
                updated_images = await db_service.update_post_images(post_id, images_payload)
            except Exception as image_error:
                print(f"❌ Failed to update images for post {post_id}: {image_error}")
                import traceback
                traceback.print_exc()
        
        # Sync calendar events if scheduled_at, status, or platforms were updated
        if scheduled_at_updated or status_updated or platforms_updated:
            try:
                # Get the updated post data
                post_query = """
                    SELECT id, user_id, campaign_name, original_description, caption, 
                           scheduled_at, status, platforms
                    FROM posts WHERE id = :post_id
                """
                post_result = await db_manager.fetch_one(post_query, {"post_id": post_id})
                print(f"🔍 Fetched post_result type: {type(post_result)}")
                
                # Convert post_result to dict using helper function
                post_result = _record_to_dict(post_result)
                print(f"✅ Converted post_result to dict: {post_result is not None}")
                
                if post_result and post_result.get('scheduled_at') and post_result.get('status') == 'scheduled':
                    # Check if calendar event exists
                    event_query = "SELECT id FROM calendar_events WHERE post_id = :post_id"
                    existing_event = await db_manager.fetch_one(event_query, {"post_id": post_id})
                    
                    # Convert existing_event to dict using helper function
                    existing_event = _record_to_dict(existing_event)
                    
                    # post_result is now guaranteed to be a dict or None
                    user_id_val = post_result.get('user_id') if post_result else None
                    user_id = str(current_user.id) if current_user else (str(user_id_val) if user_id_val else '')
                    
                    # Create meaningful title
                    event_title = ''
                    campaign_name = post_result.get('campaign_name') if post_result else None
                    original_desc = post_result.get('original_description') if post_result else None
                    caption = post_result.get('caption') if post_result else None
                    
                    if campaign_name and str(campaign_name).strip():
                        event_title = str(campaign_name).strip()
                    elif original_desc and len(str(original_desc).strip()) > 10:
                        desc = str(original_desc).strip()
                        event_title = f"{desc[:50]}..." if len(desc) > 50 else desc
                    elif caption and str(caption).strip():
                        cap = str(caption).strip()
                        event_title = f"{cap[:40]}..." if len(cap) > 40 else cap
                    else:
                        event_title = "Social Media Post"
                    
                    if existing_event:
                        # Update existing calendar event
                        update_event_query = """
                            UPDATE calendar_events 
                            SET start_time = :start_time,
                                end_time = :end_time,
                                status = :status,
                                title = :title,
                                description = :description,
                                event_metadata = :event_metadata,
                                updated_at = NOW()
                            WHERE post_id = :post_id
                        """
                        
                        # post_result is now guaranteed to be a dict or None
                        scheduled_at = post_result.get('scheduled_at') if post_result else None
                        status = post_result.get('status') if post_result else None
                        platforms = post_result.get('platforms') if post_result else None
                        description = (post_result.get('caption') or post_result.get('original_description')) if post_result else None
                        event_metadata = {"platforms": platforms or []}
                        
                        await db_manager.execute_query(update_event_query, {
                            "post_id": post_id,
                            "start_time": scheduled_at,
                            "end_time": scheduled_at,
                            "status": status,
                            "title": event_title,
                            "description": description or "",
                            "event_metadata": event_metadata
                        })
                        print(f"✅ Updated calendar event for post {post_id}")
                    else:
                        # Create new calendar event if post is scheduled
                        # post_result is now guaranteed to be a dict or None
                        scheduled_at = post_result.get('scheduled_at') if post_result else None
                        status = post_result.get('status') if post_result else None
                        platforms = post_result.get('platforms') if post_result else None
                        description = (post_result.get('caption') or post_result.get('original_description')) if post_result else None
                        
                        await db_service.create_calendar_event(
                            post_id=post_id,
                            user_id=user_id,
                            title=event_title,
                            description=description or "",
                            start_time=scheduled_at,
                            end_time=scheduled_at,
                            status=status,
                            platforms=platforms or []
                        )
                        print(f"✅ Created calendar event for post {post_id}")
            except Exception as calendar_error:
                print(f"⚠️ Warning: Failed to sync calendar event for post {post_id}: {calendar_error}")
                # Don't fail the update if calendar sync fails
        
        # Convert updated_post to dict if it's a Record object
        if updated_post:
            if hasattr(updated_post, '_asdict'):
                updated_post = updated_post._asdict()
            elif not isinstance(updated_post, dict):
                updated_post = dict(updated_post)
        else:
            updated_post = {}

        # Attach images to response
        if updated_images is not None:
            updated_post["images"] = updated_images
        else:
            try:
                updated_post["images"] = await db_service.get_images_for_post(post_id)
            except Exception as image_fetch_error:
                print(f"⚠️ Failed to fetch images for response: {image_fetch_error}")
        
        # Normalize primary image fields for response
        image_url = updated_post.get("image_url")
        image_path = updated_post.get("image_path")
        if image_path:
            normalized_path = convert_url_to_local_path(image_path)
            updated_post["image_path"] = normalized_path
            if not image_url:
                updated_post["image_url"] = f"/{normalized_path.lstrip('/')}"
        if image_url:
            updated_post["image_url"] = image_url if image_url.startswith("/") else f"/{image_url.lstrip('/')}"

        print(f"✅ Update successful for post {post_id}")
        return {
            "success": True, 
            "message": "Post updated successfully",
            "post": updated_post
        }
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"❌ Error updating post {post_id}: {e}")
        print(f"❌ Traceback: {error_trace}")
        return {"success": False, "error": str(e), "traceback": error_trace}

@main_app.get("/api/posts/{post_id}")
async def get_post_by_id(post_id: str):
    """Get a specific post by ID"""
    try:
        post = await db_service.get_post_by_id(post_id)
        if not post:
            raise HTTPException(status_code=404, detail="Post not found")
        return {"success": True, "post": post}
    except HTTPException:
        raise
    except Exception as e:
        return {"success": False, "error": str(e)}

@main_app.delete("/api/posts/{post_id}")
async def delete_post(post_id: str):
    """Delete a post and all its associated data"""
    try:
        success = await db_service.delete_post(post_id)
        if not success:
            raise HTTPException(status_code=404, detail="Post not found or could not be deleted")
        return {"success": True, "message": "Post deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        return {"success": False, "error": str(e)}


@main_app.delete("/api/posts/clear-all")
async def clear_all_posts():
    """Clear all posts from the database (for testing purposes)"""
    try:
        success = await db_service.clear_all_posts()
        if not success:
            raise HTTPException(status_code=500, detail="Failed to clear all posts")
        return {"success": True, "message": "All posts cleared successfully"}
    except HTTPException:
        raise
    except Exception as e:
        return {"success": False, "error": str(e)}


@main_app.get("/api/scheduled-posts")
async def get_scheduled_posts(current_user = Depends(get_current_user_dependency)):
    """Get posts that are scheduled for posting"""
    try:
        posts = await db_service.get_scheduled_posts(user_id=str(current_user.id))
        return {"success": True, "scheduled_posts": posts}
    except Exception as e:
        return {"success": False, "error": str(e)}


@main_app.get("/api/batch/{batch_id}/status")
async def get_batch_status(batch_id: str):
    """Get batch operation status"""
    try:
        batch_info = await db_service.get_batch_operation_status(batch_id)
        if not batch_info:
            raise HTTPException(status_code=404, detail="Batch operation not found")
        return {"success": True, "batch": batch_info}
    except HTTPException:
        raise
    except Exception as e:
        return {"success": False, "error": str(e)}


@main_app.get("/api/batch/{batch_id}/posts")
async def get_batch_posts(batch_id: str):
    """Get all posts for a specific batch"""
    try:
        posts = await db_service.get_posts_by_batch_id(batch_id)
        return {"success": True, "posts": posts}
    except Exception as e:
        return {"success": False, "error": str(e)}


class ScheduleBatchRequest(BaseModel):
    platforms: List[str]
    days: int


class GenerateScheduleRequest(BaseModel):
    num_posts: int
    days: int


@main_app.post("/api/generate-schedule")
async def generate_schedule_dates(request: GenerateScheduleRequest):
    """Generate optimal schedule dates for posts without requiring a batch"""
    try:
        if request.num_posts <= 0:
            raise HTTPException(status_code=400, detail="num_posts must be positive")
        if request.days <= 0:
            raise HTTPException(status_code=400, detail="days must be positive")
        if request.num_posts > 50:
            raise HTTPException(status_code=400, detail="num_posts cannot exceed 50")
        
        schedule_times = _compute_schedule_dates(request.num_posts, request.days)
        
        return {
            "success": True, 
            "schedule_times": schedule_times,
            "num_posts": request.num_posts,
            "days": request.days
        }
        
    except HTTPException:
        raise
    except Exception as e:
        return {"success": False, "error": str(e)}


@main_app.post("/api/batch/{batch_id}/schedule")
async def schedule_batch_posts(batch_id: str, request: ScheduleBatchRequest, current_user = Depends(get_current_user_dependency)):
    """Schedule all posts in a batch"""
    try:
        # Generate schedule times based on number of posts and days
        posts = await db_service.get_posts_by_batch_id(batch_id)
        if not posts:
            raise HTTPException(status_code=404, detail="No posts found in batch")
        
        num_posts = len(posts)
        schedule_times = _compute_schedule_dates(num_posts, request.days)
        
        success = await db_service.schedule_batch_posts(
            batch_id=batch_id,
            platforms=request.platforms,
            schedule_times=schedule_times,
            days=request.days,
            user_id=str(current_user.id)  # 🔧 Pass current user ID
        )
        
        if success:
            return {"success": True, "message": f"Scheduled {num_posts} posts across {request.days} days"}
        else:
            raise HTTPException(status_code=500, detail="Failed to schedule batch posts")
            
    except HTTPException:
        raise
    except Exception as e:
        return {"success": False, "error": str(e)}


@main_app.get("/api/stats")
async def get_database_stats():
    """Get database statistics"""
    try:
        stats = await db_service.get_database_stats()
        return {"success": True, "stats": stats}
    except Exception as e:
        return {"success": False, "error": str(e)}


@main_app.get("/api/database/info")
async def get_database_info():
    """Get database connection information"""
    try:
        from database import get_database_info
        info = get_database_info()
        return {"success": True, "database_info": info}
    except Exception as e:
        return {"success": False, "error": str(e)}


# Calendar Event API Endpoints
class CalendarEventRequest(BaseModel):
    title: str
    description: Optional[str] = None
    start_time: str  # ISO format datetime
    end_time: Optional[str] = None  # ISO format datetime
    all_day: bool = False
    location: Optional[str] = None
    color: str = "#3174ad"
    reminder_minutes: int = 15
    post_id: Optional[str] = None


class CalendarEventUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    all_day: Optional[bool] = None
    location: Optional[str] = None
    color: Optional[str] = None
    reminder_minutes: Optional[int] = None
    status: Optional[str] = None


def get_calendar_service():
    """Get calendar service with a live DB session for the duration of the request.
    Do not close the session here; the CalendarService methods manage transactions.
    """
    from database import get_sync_db
    db = next(get_sync_db())
    # IMPORTANT: Do not close here; callers need an active session
    return CalendarService(db)


@main_app.get("/api/calendar/events")
async def get_calendar_events(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    status: Optional[str] = None,
    post_id: Optional[str] = None,
    current_user = Depends(get_current_user_dependency)
):
    """Get calendar events with optional filtering"""
    try:
        calendar_service = get_calendar_service()
        
        # Parse dates if provided
        parsed_start_date = None
        parsed_end_date = None
        
        if start_date:
            parsed_start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        if end_date:
            parsed_end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        
        events = calendar_service.get_events(
            start_date=parsed_start_date,
            end_date=parsed_end_date,
            status=status,
            post_id=post_id,
            user_id=str(current_user.id)
        )
        
        return {"success": True, "events": [event.dict() for event in events]}
    except Exception as e:
        return {"success": False, "error": str(e)}


@main_app.get("/api/calendar/events/{event_id}")
async def get_calendar_event(event_id: str):
    """Get a specific calendar event by ID"""
    try:
        calendar_service = get_calendar_service()
        event = calendar_service.get_event(event_id)
        
        if not event:
            raise HTTPException(status_code=404, detail="Calendar event not found")
            
        return {"success": True, "event": event.dict()}
    except HTTPException:
        raise
    except Exception as e:
        return {"success": False, "error": str(e)}


@main_app.post("/api/calendar/events")
async def create_calendar_event(request: CalendarEventRequest, current_user = Depends(get_current_user_dependency)):
    """Create a new calendar event"""
    try:
        calendar_service = get_calendar_service()
        
        event_data = {
            "title": request.title,
            "description": request.description,
            "start_time": request.start_time,
            "end_time": request.end_time,
            "all_day": request.all_day,
            "location": request.location,
            "color": request.color,
            "reminder_minutes": request.reminder_minutes,
            "post_id": request.post_id,
            "user_id": str(current_user.id)  # Add current user ID
        }
        
        event = calendar_service.create_event(event_data)
        
        return {"success": True, "event": event.dict()}
    except Exception as e:
        return {"success": False, "error": str(e)}


@main_app.put("/api/calendar/events/{event_id}")
async def update_calendar_event(event_id: str, request: CalendarEventUpdateRequest):
    """Update a calendar event"""
    try:
        calendar_service = get_calendar_service()
        
        # Build update data from non-None fields
        update_data = {}
        for field, value in request.dict().items():
            if value is not None:
                update_data[field] = value
        
        event = calendar_service.update_event(event_id, update_data)
        
        if not event:
            raise HTTPException(status_code=404, detail="Calendar event not found")
            
        return {"success": True, "event": event.dict()}
    except HTTPException:
        raise
    except Exception as e:
        return {"success": False, "error": str(e)}


@main_app.delete("/api/calendar/events/{event_id}")
async def delete_calendar_event(event_id: str):
    """Delete a calendar event"""
    try:
        calendar_service = get_calendar_service()
        
        success = calendar_service.delete_event(event_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Calendar event not found")
            
        return {"success": True, "message": "Event deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        return {"success": False, "error": str(e)}


@main_app.get("/api/calendar/events/post/{post_id}")
async def get_events_for_post(post_id: str):
    """Get all calendar events for a specific post"""
    try:
        calendar_service = get_calendar_service()
        events = calendar_service.get_events_for_post(post_id)
        
        return {"success": True, "events": [event.dict() for event in events]}
    except Exception as e:
        return {"success": False, "error": str(e)}


@main_app.post("/api/calendar/events/from-post/{post_id}")
async def create_event_from_post(post_id: str, additional_data: Optional[Dict[str, Any]] = None):
    """Create a calendar event from an existing post"""
    try:
        calendar_service = get_calendar_service()
        event = calendar_service.create_event_from_post(post_id, additional_data or {})
        
        return {"success": True, "event": event.dict()}
    except Exception as e:
        return {"success": False, "error": str(e)}


@main_app.get("/api/calendar/events/upcoming")
async def get_upcoming_events(days_ahead: int = 30):
    """Get upcoming calendar events"""
    try:
        calendar_service = get_calendar_service()
        events = calendar_service.get_upcoming_events(days_ahead)
        
        return {"success": True, "events": [event.dict() for event in events]}
    except Exception as e:
        return {"success": False, "error": str(e)}


@main_app.post("/api/calendar/sync-all-posts")
async def sync_all_calendar_with_posts():
    """Sync calendar events with scheduled posts for all users (no auth required)"""
    try:
        # Get all scheduled posts that don't have calendar events
        scheduled_posts_query = """
            SELECT p.id, p.user_id, p.campaign_name, p.original_description, p.caption, 
                   p.scheduled_at, p.platforms
            FROM posts p
            LEFT JOIN calendar_events c ON c.post_id = p.id
            WHERE p.status = 'scheduled' 
              AND p.scheduled_at IS NOT NULL 
              AND p.user_id IS NOT NULL
              AND c.post_id IS NULL
            ORDER BY p.scheduled_at ASC
        """
        
        from database import db_manager
        results = await db_manager.fetch_all(scheduled_posts_query)
        
        created_count = 0
        failed_count = 0
        
        for post in results:
            try:
                # Create meaningful title from campaign name or description
                event_title = ''
                if post.get('campaign_name') and post['campaign_name'].strip():
                    event_title = post['campaign_name'].strip()
                elif post.get('original_description') and len(post['original_description'].strip()) > 10:
                    desc = post['original_description'].strip()
                    event_title = f"{desc[:50]}..." if len(desc) > 50 else desc
                elif post.get('caption') and post['caption'].strip():
                    caption = post['caption'].strip()
                    event_title = f"{caption[:40]}..." if len(caption) > 40 else caption
                else:
                    event_title = "Social Media Post"
                
                # Create calendar event
                await db_service.create_calendar_event(
                    post_id=str(post['id']),
                    user_id=str(post['user_id']),
                    title=event_title,
                    description=post['caption'] or post['original_description'] or "",
                    start_time=post['scheduled_at'],
                    end_time=post['scheduled_at'],
                    status='scheduled',
                    platforms=post['platforms'] or []
                )
                
                created_count += 1
                print(f"🔄 Auto-synced calendar event for post {post['id']}: {event_title}")
                
            except Exception as post_error:
                failed_count += 1
                print(f"⚠️ Failed to sync calendar event for post {post['id']}: {post_error}")
        
        return {
            "success": True, 
            "stats": {
                "created": created_count,
                "failed": failed_count,
                "message": f"Synced {created_count} calendar events, {failed_count} failed"
            }
        }
        
    except Exception as e:
        print(f"Error syncing all calendar with posts: {e}")
        return {"success": False, "error": str(e)}

@main_app.post("/api/calendar/sync-with-posts")
async def sync_calendar_with_posts(current_user = Depends(get_current_user_dependency)):
    """Sync calendar events with scheduled posts"""
    try:
        # Get all scheduled posts for the current user that don't have calendar events
        scheduled_posts_query = """
            SELECT p.id, p.user_id, p.campaign_name, p.original_description, p.caption, 
                   p.scheduled_at, p.platforms, p.image_path
            FROM posts p
            LEFT JOIN calendar_events c ON c.post_id = p.id
            WHERE p.status = 'scheduled' 
              AND p.scheduled_at IS NOT NULL 
              AND p.user_id = :user_id
              AND c.post_id IS NULL
            ORDER BY p.scheduled_at ASC
        """
        
        from database import db_manager
        results = await db_manager.fetch_all(scheduled_posts_query, {"user_id": str(current_user.id)})
        
        created_count = 0
        failed_count = 0
        
        for post in results:
            try:
                # Create meaningful title from campaign name or description
                event_title = ''
                if post.get('campaign_name') and post['campaign_name'].strip() and post['campaign_name'] != 'Untitled Campaign':
                    event_title = post['campaign_name'].strip()
                elif post.get('original_description') and len(post['original_description'].strip()) > 10:
                    desc = post['original_description'].strip()
                    # Avoid UUID-like strings
                    if not (desc.startswith('Post ') and len(desc.split('-')) > 3):
                        event_title = f"{desc[:50]}..." if len(desc) > 50 else desc
                    else:
                        event_title = "Campaign Post"
                elif post.get('caption') and post['caption'].strip():
                    caption = post['caption'].strip()
                    event_title = f"{caption[:40]}..." if len(caption) > 40 else caption
                else:
                    event_title = "Social Media Campaign"
                
                # Create calendar event
                await db_service.create_calendar_event(
                    post_id=str(post['id']),
                    user_id=str(post['user_id']),
                    title=event_title,
                    description=post['caption'] or post['original_description'] or "",
                    start_time=post['scheduled_at'],
                    end_time=post['scheduled_at'],
                    status='scheduled',
                    platforms=post['platforms'] or []
                )
                
                created_count += 1
                print(f"✅ Created calendar event for post {post['id']}: {event_title}")
                
            except Exception as post_error:
                failed_count += 1
                print(f"❌ Failed to create calendar event for post {post['id']}: {post_error}")
        
        return {
            "success": True, 
            "stats": {
                "created": created_count,
                "failed": failed_count,
                "message": f"Created {created_count} calendar events, {failed_count} failed"
            }
        }
        
    except Exception as e:
        print(f"Error syncing calendar with posts: {e}")
        return {"success": False, "error": str(e)}

@main_app.post("/api/calendar/auto-sync")
async def auto_sync_calendar_events():
    """Automatically sync calendar events for all users (called on startup)"""
    try:
        # Get all scheduled posts that don't have calendar events
        scheduled_posts_query = """
            SELECT p.id, p.user_id, p.campaign_name, p.original_description, p.caption, 
                   p.scheduled_at, p.platforms
            FROM posts p
            LEFT JOIN calendar_events c ON c.post_id = p.id
            WHERE p.status = 'scheduled' 
              AND p.scheduled_at IS NOT NULL 
              AND p.user_id IS NOT NULL
              AND c.post_id IS NULL
            ORDER BY p.scheduled_at ASC
        """
        
        from database import db_manager
        results = await db_manager.fetch_all(scheduled_posts_query)
        
        created_count = 0
        failed_count = 0
        
        for post in results:
            try:
                # Create meaningful title from campaign name or description
                event_title = ''
                if post.get('campaign_name') and post['campaign_name'].strip():
                    event_title = post['campaign_name'].strip()
                elif post.get('original_description') and len(post['original_description'].strip()) > 10:
                    desc = post['original_description'].strip()
                    event_title = f"{desc[:50]}..." if len(desc) > 50 else desc
                elif post.get('caption') and post['caption'].strip():
                    caption = post['caption'].strip()
                    event_title = f"{caption[:40]}..." if len(caption) > 40 else caption
                else:
                    event_title = "Social Media Post"
                
                # Create calendar event
                await db_service.create_calendar_event(
                    post_id=str(post['id']),
                    user_id=str(post['user_id']),
                    title=event_title,
                    description=post['caption'] or post['original_description'] or "",
                    start_time=post['scheduled_at'],
                    end_time=post['scheduled_at'],
                    status='scheduled',
                    platforms=post['platforms'] or []
                )
                
                created_count += 1
                print(f"🔄 Auto-created calendar event for post {post['id']}: {event_title}")
                
            except Exception as post_error:
                failed_count += 1
                print(f"⚠️ Failed to auto-create calendar event for post {post['id']}: {post_error}")
        
        if created_count > 0:
            print(f"✅ Auto-sync completed: Created {created_count} calendar events, {failed_count} failed")
        
        return {
            "success": True, 
            "stats": {
                "created": created_count,
                "failed": failed_count,
                "message": f"Auto-created {created_count} calendar events"
            }
        }
        
    except Exception as e:
        print(f"Error in auto-sync calendar: {e}")
        return {"success": False, "error": str(e)}


# Facebook Analytics endpoints
from facebook_analytics_service import facebook_analytics
from facebook_manager import facebook_manager

# Reddit service
from reddit_service import reddit_service

@main_app.get("/api/analytics/overview")
async def get_analytics_overview(
    platform: Optional[str] = "facebook",
    account_id: Optional[str] = None,
    current_user = Depends(get_current_user_dependency)
):
    """Get comprehensive analytics overview for the current user's connected account"""
    try:
        user_id = str(current_user.id) if current_user and hasattr(current_user, 'id') else None
        if not user_id:
            return {"success": False, "error": "User not authenticated"}
        
        from database_service import db_service
        
        # Get the user's account for the specified platform
        if account_id:
            account = await db_service.get_social_media_account(user_id, platform=platform, account_id=account_id)
        else:
            account = await db_service.get_social_media_account(user_id, platform=platform)
        
        if not account:
            return {"success": False, "error": f"No {platform} account found. Please connect your {platform} account."}
        
        # Set credentials based on platform
        if platform == "facebook":
            facebook_analytics.configure_from_credentials(
                page_id=account["account_id"],
                access_token=account["access_token"],
                metadata=account.get("metadata")
            )
            # Don't write to .env - credentials should only be in database
            # Only client ID/secret should be in .env
            
            if not facebook_analytics.is_configured():
                return {"success": False, "error": "Facebook analytics not configured"}
            
            analytics_data = facebook_analytics.get_comprehensive_analytics()
            return {"success": True, "data": analytics_data}
        else:
            return {"success": False, "error": f"Analytics not yet implemented for {platform}"}
        
    except Exception as e:
        return {"success": False, "error": str(e)}

@main_app.get("/api/analytics/followers")
async def get_followers(
    platform: Optional[str] = "facebook",
    account_id: Optional[str] = None,
    current_user = Depends(get_current_user_dependency)
):
    """Get page followers count for the current user's connected account"""
    try:
        user_id = str(current_user.id) if current_user and hasattr(current_user, 'id') else None
        if not user_id:
            return {"success": False, "error": "User not authenticated"}
        
        from database_service import db_service
        
        # Get the user's account for the specified platform
        if account_id:
            account = await db_service.get_social_media_account(user_id, platform=platform, account_id=account_id)
        else:
            account = await db_service.get_social_media_account(user_id, platform=platform)
        
        if not account:
            return {"success": False, "error": f"No {platform} account found. Please connect your {platform} account."}
        
        if platform == "facebook":
            facebook_analytics.configure_from_credentials(
                page_id=account["account_id"],
                access_token=account["access_token"],
                metadata=account.get("metadata")
            )
            
            if not facebook_analytics.is_configured():
                return {"success": False, "error": "Facebook analytics not configured"}
            
            result = facebook_analytics.get_page_followers()
            # Ensure followers is returned as a number, not empty
            followers_count = result.get("followers", 0) if result else 0
            error_msg = result.get("error") if result else None
            
            return {
                "success": True, 
                "followers": followers_count,
                "configured": True,
                "error": error_msg
            }
        else:
            return {"success": False, "error": f"Analytics not yet implemented for {platform}"}
        
    except Exception as e:
        return {"success": False, "error": str(e)}

@main_app.get("/api/analytics/demographics")
async def get_demographics(
    platform: Optional[str] = "facebook",
    account_id: Optional[str] = None,
    current_user = Depends(get_current_user_dependency)
):
    """Get audience demographics for the current user's connected account"""
    try:
        user_id = str(current_user.id) if current_user and hasattr(current_user, 'id') else None
        if not user_id:
            return {"success": False, "error": "User not authenticated"}
        
        from database_service import db_service
        
        # Get the user's account for the specified platform
        if account_id:
            account = await db_service.get_social_media_account(user_id, platform=platform, account_id=account_id)
        else:
            account = await db_service.get_social_media_account(user_id, platform=platform)
        
        if not account:
            return {"success": False, "error": f"No {platform} account found. Please connect your {platform} account."}
        
        if platform == "facebook":
            facebook_analytics.configure_from_credentials(
                page_id=account["account_id"],
                access_token=account["access_token"],
                metadata=account.get("metadata")
            )
            
            if not facebook_analytics.is_configured():
                return {"success": False, "error": "Facebook analytics not configured"}
            
            result = facebook_analytics.get_audience_demographics()
            return {"success": True, **result, "configured": True}
        else:
            return {"success": False, "error": f"Analytics not yet implemented for {platform}"}
        
    except Exception as e:
        return {"success": False, "error": str(e)}

@main_app.get("/api/analytics/posts")
async def get_posts_analytics(
    limit: int = 10,
    platform: Optional[str] = "facebook",
    account_id: Optional[str] = None,
    current_user = Depends(get_current_user_dependency)
):
    """Get analyzed posts with engagement metrics for the current user's connected account"""
    try:
        user_id = str(current_user.id) if current_user and hasattr(current_user, 'id') else None
        if not user_id:
            return {"success": False, "error": "User not authenticated"}
        
        from database_service import db_service
        
        # Get the user's account for the specified platform
        if account_id:
            account = await db_service.get_social_media_account(user_id, platform=platform, account_id=account_id)
        else:
            account = await db_service.get_social_media_account(user_id, platform=platform)
        
        if not account:
            return {"success": False, "error": f"No {platform} account found. Please connect your {platform} account."}
        
        if platform == "facebook":
            facebook_analytics.configure_from_credentials(
                page_id=account["account_id"],
                access_token=account["access_token"],
                metadata=account.get("metadata")
            )
            
            if not facebook_analytics.is_configured():
                return {"success": False, "error": "Facebook analytics not configured"}
            
            posts = facebook_analytics.analyze_posts(limit)
            return {"success": True, "posts": posts, "configured": True}
        else:
            return {"success": False, "error": f"Analytics not yet implemented for {platform}"}
        
    except Exception as e:
        return {"success": False, "error": str(e)}

@main_app.get("/api/analytics/posts/best")
async def get_best_post(
    limit: int = 10,
    platform: Optional[str] = "facebook",
    account_id: Optional[str] = None,
    current_user = Depends(get_current_user_dependency)
):
    """Get best performing post for the current user's connected account"""
    try:
        user_id = str(current_user.id) if current_user and hasattr(current_user, 'id') else None
        if not user_id:
            return {"success": False, "error": "User not authenticated"}
        
        from database_service import db_service
        
        # Get the user's account for the specified platform
        if account_id:
            account = await db_service.get_social_media_account(user_id, platform=platform, account_id=account_id)
        else:
            account = await db_service.get_social_media_account(user_id, platform=platform)
        
        if not account:
            return {"success": False, "error": f"No {platform} account found. Please connect your {platform} account."}
        
        if platform == "facebook":
            facebook_analytics.configure_from_credentials(
                page_id=account["account_id"],
                access_token=account["access_token"],
                metadata=account.get("metadata")
            )
            
            if not facebook_analytics.is_configured():
                return {"success": False, "error": "Facebook analytics not configured"}
            
            best_post = facebook_analytics.get_best_performing_post(limit)
            return {"success": True, "post": best_post, "configured": True}
        else:
            return {"success": False, "error": f"Analytics not yet implemented for {platform}"}
        
    except Exception as e:
        return {"success": False, "error": str(e)}

@main_app.get("/api/analytics/posts/worst")
async def get_worst_post(
    limit: int = 10,
    platform: Optional[str] = "facebook",
    account_id: Optional[str] = None,
    current_user = Depends(get_current_user_dependency)
):
    """Get worst performing post for the current user's connected account"""
    try:
        user_id = str(current_user.id) if current_user and hasattr(current_user, 'id') else None
        if not user_id:
            return {"success": False, "error": "User not authenticated"}
        
        from database_service import db_service
        
        # Get the user's account for the specified platform
        if account_id:
            account = await db_service.get_social_media_account(user_id, platform=platform, account_id=account_id)
        else:
            account = await db_service.get_social_media_account(user_id, platform=platform)
        
        if not account:
            return {"success": False, "error": f"No {platform} account found. Please connect your {platform} account."}
        
        if platform == "facebook":
            facebook_analytics.configure_from_credentials(
                page_id=account["account_id"],
                access_token=account["access_token"],
                metadata=account.get("metadata")
            )
            
            if not facebook_analytics.is_configured():
                return {"success": False, "error": "Facebook analytics not configured"}
            
            worst_post = facebook_analytics.get_worst_performing_post(limit)
            return {"success": True, "post": worst_post, "configured": True}
        else:
            return {"success": False, "error": f"Analytics not yet implemented for {platform}"}
        
    except Exception as e:
        return {"success": False, "error": str(e)}

@main_app.get("/api/analytics/metrics")
async def get_available_metrics():
    """Get available analytics metrics"""
    try:
        metrics = facebook_analytics.get_available_metrics()
        return {
            "success": True, 
            **metrics, 
            "configured": facebook_analytics.is_configured()
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}

@main_app.get("/api/analytics/status")
async def get_analytics_status():
    """Get analytics service configuration status"""
    try:
        is_configured = facebook_analytics.is_configured()
        return {
            "success": True,
            "configured": is_configured,
            "page_id_present": bool(facebook_analytics.page_id),
            "access_token_present": bool(facebook_analytics.access_token),
            "service_ready": is_configured
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}

# Facebook endpoints removed - stub responses for frontend compatibility
@main_app.post("/api/facebook/publish")
async def publish_to_facebook_stub(request: dict):
    """Stub endpoint - Facebook integration removed"""
    return {"success": False, "error": "Facebook integration has been disabled"}


@main_app.post("/api/facebook/schedule")
async def schedule_facebook_post_stub(request: dict):
    """Stub endpoint - Facebook integration removed"""
    return {"success": False, "error": "Facebook integration has been disabled"}


@main_app.delete("/api/facebook/schedule/{post_id}")
async def cancel_scheduled_facebook_post_stub(post_id: str):
    """Stub endpoint - Facebook integration removed"""
    return {"success": False, "error": "Facebook integration has been disabled"}


@main_app.get("/api/facebook/status")
async def get_facebook_service_status():
    """Get Facebook service status and configuration"""
    return {
        "success": True,
        "facebook_configured": True,
        "instagram_configured": False,
        "service_status": {
            "access_token_present": True,
            "page_id_present": True,
            "instagram_id_present": False
        }
    }


@main_app.get("/api/facebook/page-info")
async def get_facebook_page_info(
    account_id: Optional[str] = None,
    current_user = Depends(get_current_user_dependency)
):
    """Get Facebook page information"""
    try:
        user_id = str(current_user.id) if current_user and hasattr(current_user, "id") else None
        if not user_id:
            return {"success": False, "error": "User not authenticated"}

        configured = await facebook_manager.configure_for_user(user_id, account_id)
        if not configured:
            return {
                "success": False,
                "error": "No Facebook account found. Please connect your Facebook page from the Settings screen."
            }

        verification = facebook_manager.verify_credentials()
        if not verification.get("success"):
            return {"success": False, "error": verification.get("error")}
        
        return {
            "success": True,
            "page_id": verification.get("page_id"),
            "page_name": verification.get("page_name"),
            "configured": True
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@main_app.post("/api/facebook/post")
async def post_to_facebook_endpoint(
    request: dict,
    account_id: Optional[str] = None,
    current_user = Depends(get_current_user_dependency)
):
    """Post content to Facebook"""
    try:
        user_id = str(current_user.id) if current_user and hasattr(current_user, "id") else None
        if not user_id:
            return {"success": False, "error": "User not authenticated"}

        configured = await facebook_manager.configure_for_user(user_id, account_id)
        if not configured:
            return {
                "success": False,
                "error": "No Facebook account connected. Please connect your Facebook page in Settings."
            }

        message = request.get("message", "")
        image_url = request.get("image_url")
        image_path = request.get("image_path")
        scheduled_time = request.get("scheduled_time")
        
        if not message:
            return {"success": False, "error": "Message is required"}
        
        # Handle scheduled posts
        if scheduled_time:
            try:
                scheduled_dt = datetime.fromisoformat(scheduled_time.replace('Z', '+00:00'))
                result = facebook_manager.post_text(message, scheduled_dt)
            except ValueError:
                return {"success": False, "error": "Invalid scheduled_time format"}
        elif image_path:
            result = facebook_manager.post_photo_from_file(image_path, message)
        elif image_url:
            result = facebook_manager.post_photo(image_url, message)
        else:
            result = facebook_manager.post_text(message)
        
        return result
        
    except Exception as e:
        return {"success": False, "error": str(e)}


@main_app.get("/api/facebook/posts")
async def get_facebook_posts(
    limit: int = 25,
    include_insights: bool = True,
    account_id: Optional[str] = None,
    current_user = Depends(get_current_user_dependency)
):
    """Get Facebook posts with optional insights"""
    try:
        user_id = str(current_user.id) if current_user and hasattr(current_user, "id") else None
        if not user_id:
            return {"success": False, "error": "User not authenticated"}

        configured = await facebook_manager.configure_for_user(user_id, account_id)
        if not configured:
            return {
                "success": False,
                "error": "No Facebook account connected. Please connect your Facebook page in Settings."
            }

        result = facebook_manager.get_posts(limit, include_insights)
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}


@main_app.get("/api/facebook/analytics")
async def get_facebook_analytics(
    account_id: Optional[str] = None,
    current_user = Depends(get_current_user_dependency)
):
    """Get comprehensive Facebook analytics for the current user's account"""
    try:
        user_id = str(current_user.id) if current_user and hasattr(current_user, 'id') else None
        if not user_id:
            return {"success": False, "error": "User not authenticated"}
        
        configured = await facebook_manager.configure_for_user(user_id, account_id)
        if not configured:
            return {"success": False, "error": "No Facebook account found. Please connect your Facebook account."}
        
        result = facebook_manager.get_comprehensive_analytics()
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}


@main_app.get("/api/facebook/insights/{post_id}")
async def get_facebook_post_insights(
    post_id: str,
    account_id: Optional[str] = None,
    current_user = Depends(get_current_user_dependency)
):
    """Get insights for a specific Facebook post"""
    try:
        user_id = str(current_user.id) if current_user and hasattr(current_user, "id") else None
        if not user_id:
            return {"success": False, "error": "User not authenticated"}

        configured = await facebook_manager.configure_for_user(user_id, account_id)
        if not configured:
            return {
                "success": False,
                "error": "No Facebook account connected. Please connect your Facebook page in Settings."
            }

        result = facebook_manager.get_post_insights(post_id)
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}


@main_app.get("/api/facebook/post/{post_id}/insights")
async def get_facebook_post_insights_stub(post_id: str):
    """Stub endpoint - Facebook integration removed"""
    return {"success": False, "error": "Facebook integration has been disabled"}


@main_app.get("/api/scheduler/status")
async def get_scheduler_status():
    """Get current scheduler service status"""
    try:
        status = await scheduler_service.get_scheduler_status()
        return {"success": True, "status": status}
        
    except Exception as e:
        return {"success": False, "error": str(e)}


# Reddit API Endpoints
@main_app.get("/api/reddit/status")
async def get_reddit_status():
    """Get Reddit service status"""
    try:
        status = reddit_service.get_service_status()
        return {"success": True, "status": status}
    except Exception as e:
        return {"success": False, "error": str(e)}


@main_app.post("/api/reddit/post")
async def post_to_reddit(request: dict):
    """Post content to Reddit"""
    try:
        title = request.get("title", "")
        content = request.get("content", "")
        subreddit = request.get("subreddit", "test")
        
        if not title or not content:
            return {"success": False, "error": "Title and content are required"}
        
        result = reddit_service.post_to_reddit(title, content, subreddit)
        return result
        
    except Exception as e:
        return {"success": False, "error": str(e)}


@main_app.post("/api/reddit/schedule")
async def schedule_reddit_post(request: dict):
    """Schedule a Reddit post"""
    try:
        title = request.get("title", "")
        content = request.get("content", "")
        scheduled_time = request.get("scheduled_time", "")
        subreddit = request.get("subreddit", "test")
        
        if not all([title, content, scheduled_time]):
            return {"success": False, "error": "Title, content, and scheduled_time are required"}
        
        result = reddit_service.schedule_reddit_post(title, content, scheduled_time, subreddit)
        return result
        
    except Exception as e:
        return {"success": False, "error": str(e)}


@main_app.get("/api/reddit/scheduled")
async def get_scheduled_reddit_posts():
    """Get scheduled Reddit posts"""
    try:
        result = reddit_service.get_scheduled_posts()
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}


@main_app.post("/api/reddit/publish/{post_id}")
async def publish_scheduled_reddit_post(post_id: str):
    """Publish a scheduled Reddit post"""
    try:
        result = reddit_service.publish_scheduled_post(post_id)
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}


@main_app.get("/api/reddit/analytics/{post_id}")
async def get_reddit_analytics(post_id: str):
    """Get Reddit post analytics"""
    try:
        result = reddit_service.get_reddit_analytics(post_id)
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}


# Reddit Analytics Endpoints
from reddit_analytics_service import reddit_analytics_service

@main_app.get("/api/reddit/account/info")
async def get_reddit_account_info(current_user = Depends(get_current_user_dependency)):
    """Get Reddit account information for the current user's account"""
    try:
        user_id = str(current_user.id) if current_user and hasattr(current_user, 'id') else None
        if not user_id:
            return {"success": False, "error": "User not authenticated"}
        
        from database_service import db_service
        # Get the user's Reddit account from unified database table
        account = await db_service.get_social_media_account(user_id, platform="reddit")
        
        if not account:
            return {"success": False, "error": "No Reddit account found. Please connect your Reddit account."}
        
        # Initialize service with user's credentials from database
        from reddit_analytics_service import RedditAnalyticsService
        reddit_service = RedditAnalyticsService(
            access_token=account.get('access_token'),
            refresh_token=account.get('refresh_token'),
            username=account.get('username') or account.get('metadata', {}).get('reddit_username')
        )
        result = reddit_service.get_account_info()
        return result
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}


@main_app.get("/api/reddit/account/analytics")
async def get_reddit_account_analytics(current_user = Depends(get_current_user_dependency)):
    """Get comprehensive Reddit account analytics for the current user's account"""
    try:
        user_id = str(current_user.id) if current_user and hasattr(current_user, 'id') else None
        if not user_id:
            return {"success": False, "error": "User not authenticated"}
        
        from database_service import db_service
        # Get the user's Reddit account from unified database table
        account = await db_service.get_social_media_account(user_id, platform="reddit")
        
        if not account:
            return {"success": False, "error": "No Reddit account found. Please connect your Reddit account."}
        
        # Initialize service with user's credentials from database
        from reddit_analytics_service import RedditAnalyticsService
        reddit_service = RedditAnalyticsService(
            access_token=account.get('access_token'),
            refresh_token=account.get('refresh_token'),
            username=account.get('username') or account.get('metadata', {}).get('reddit_username')
        )
        result = reddit_service.get_account_analytics()
        return result
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}


@main_app.get("/api/reddit/posts/my")
async def get_my_reddit_posts(limit: int = 25, sort: str = "new", current_user = Depends(get_current_user_dependency)):
    """Get your own Reddit posts"""
    try:
        user_id = str(current_user.id) if current_user and hasattr(current_user, 'id') else None
        if not user_id:
            return {"success": False, "error": "User not authenticated"}
        
        from database_service import db_service
        account = await db_service.get_social_media_account(user_id, platform="reddit")
        
        if not account:
            return {"success": False, "error": "No Reddit account found. Please connect your Reddit account."}
        
        from reddit_analytics_service import RedditAnalyticsService
        reddit_service = RedditAnalyticsService(
            access_token=account.get('access_token'),
            refresh_token=account.get('refresh_token'),
            username=account.get('username') or account.get('metadata', {}).get('reddit_username')
        )
        result = reddit_service.get_my_posts(limit=limit, sort=sort)
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}


@main_app.get("/api/reddit/comments/my")
async def get_my_reddit_comments(limit: int = 25, sort: str = "new", current_user = Depends(get_current_user_dependency)):
    """Get your own Reddit comments"""
    try:
        user_id = str(current_user.id) if current_user and hasattr(current_user, 'id') else None
        if not user_id:
            return {"success": False, "error": "User not authenticated"}
        
        from database_service import db_service
        account = await db_service.get_social_media_account(user_id, platform="reddit")
        
        if not account:
            return {"success": False, "error": "No Reddit account found. Please connect your Reddit account."}
        
        from reddit_analytics_service import RedditAnalyticsService
        reddit_service = RedditAnalyticsService(
            access_token=account.get('access_token'),
            refresh_token=account.get('refresh_token'),
            username=account.get('username') or account.get('metadata', {}).get('reddit_username')
        )
        result = reddit_service.get_my_comments(limit=limit, sort=sort)
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}


@main_app.get("/api/reddit/post/{post_id}/analytics")
async def get_reddit_post_analytics(post_id: str, current_user = Depends(get_current_user_dependency)):
    """Get detailed analytics for a specific Reddit post"""
    try:
        user_id = str(current_user.id) if current_user and hasattr(current_user, 'id') else None
        if not user_id:
            return {"success": False, "error": "User not authenticated"}
        
        from database_service import db_service
        account = await db_service.get_social_media_account(user_id, platform="reddit")
        
        if not account:
            return {"success": False, "error": "No Reddit account found. Please connect your Reddit account."}
        
        from reddit_analytics_service import RedditAnalyticsService
        reddit_service = RedditAnalyticsService(
            access_token=account.get('access_token'),
            refresh_token=account.get('refresh_token'),
            username=account.get('username') or account.get('metadata', {}).get('reddit_username')
        )
        result = reddit_service.get_post_analytics(post_id)
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}


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


# Twitter Analytics Endpoints
from twitter_analytics_service import twitter_analytics_service

# Instagram Analytics Endpoints
from instagram_analytics_service import instagram_analytics_service

async def _configure_twitter_service_for_user(user_id: str, account_id: Optional[str] = None) -> bool:
    """Configure Twitter analytics service with user's account credentials"""
    try:
        from database_service import db_service
        
        # Get the user's Twitter account from unified database table
        account = await db_service.get_social_media_account(user_id, platform="twitter", account_id=account_id)
        
        if account:
            metadata = account.get("metadata", {})
            access_token = account.get("access_token")
            bearer_token = metadata.get("bearer_token")
            
            print(f"🔧 Configuring Twitter service for user {user_id}")
            print(f"   Account ID: {account.get('account_id')}")
            print(f"   Username: {account.get('username')}")
            print(f"   Has access_token: {bool(access_token)}")
            print(f"   Has bearer_token: {bool(bearer_token)}")
            print(f"   Access token length: {len(access_token) if access_token else 0}")
            
            # Check if token might be expired
            expires_at = account.get("expires_at")
            if expires_at:
                from datetime import datetime
                if isinstance(expires_at, str):
                    expires_at = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                if datetime.now() >= expires_at:
                    print(f"⚠️ Twitter access token expired at {expires_at}, attempting refresh...")
                    # Try to refresh the token
                    refresh_token = account.get("refresh_token")
                    if refresh_token:
                        try:
                            from twitter_oauth_helper import refresh_access_token
                            new_token_data = refresh_access_token(refresh_token)
                            access_token = new_token_data.get("access_token")
                            print(f"✅ Token refreshed successfully")
                            # Update database with new token
                            # TODO: Update database with new access_token and expires_at
                        except Exception as refresh_error:
                            print(f"❌ Failed to refresh token: {refresh_error}")
            
            # Configure service with OAuth 2.0 access token (preferred) or bearer token
            twitter_analytics_service.configure(
                access_token=access_token,  # OAuth 2.0 access token
                bearer_token=bearer_token,  # Fallback bearer token
                consumer_key=metadata.get("consumer_key"),  # OAuth 1.0a (if available)
                consumer_secret=metadata.get("consumer_secret"),  # OAuth 1.0a (if available)
                access_token_secret=account.get("refresh_token"),  # OAuth 1.0a access token secret
                username=account.get("username"),
                user_id=account.get("account_id")
            )
            return True
        else:
            print(f"⚠️ No Twitter account found for user {user_id}, account_id: {account_id}")
        return False
    except Exception as e:
        print(f"❌ Error configuring Twitter service: {e}")
        import traceback
        traceback.print_exc()
        return False

@main_app.get("/api/twitter/account/info")
async def get_twitter_account_info(
    account_id: Optional[str] = None,
    current_user = Depends(get_current_user_dependency)
):
    """Get Twitter account information for the current user's account"""
    try:
        user_id = str(current_user.id) if current_user and hasattr(current_user, 'id') else None
        if not user_id:
            return {"success": False, "error": "User not authenticated"}
        
        # Configure service with user's credentials
        configured = await _configure_twitter_service_for_user(user_id, account_id)
        if not configured:
            # Fallback to env vars for backwards compatibility
            creds = env_manager.check_platform_credentials('twitter')
            if not creds['has_credentials']:
                return {"success": False, "error": "No Twitter account found. Please connect your Twitter account."}
        
        result = twitter_analytics_service.get_account_info()
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}


@main_app.get("/api/twitter/account/analytics")
async def get_twitter_account_analytics(
    account_id: Optional[str] = None,
    current_user = Depends(get_current_user_dependency)
):
    """Get comprehensive Twitter account analytics for the current user's account"""
    try:
        user_id = str(current_user.id) if current_user and hasattr(current_user, 'id') else None
        if not user_id:
            return {"success": False, "error": "User not authenticated"}
        
        # Configure service with user's credentials
        configured = await _configure_twitter_service_for_user(user_id, account_id)
        if not configured:
            # Fallback to env vars for backwards compatibility
            creds = env_manager.check_platform_credentials('twitter')
            if not creds['has_credentials']:
                return {"success": False, "error": "No Twitter account found. Please connect your Twitter account."}
        
        result = twitter_analytics_service.get_account_analytics()
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}


@main_app.get("/api/twitter/posts/my")
async def get_my_twitter_posts(limit: int = 25):
    """Get your own Twitter posts"""
    try:
        result = twitter_analytics_service.get_my_tweets(limit=limit)
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}


@main_app.get("/api/twitter/post/{tweet_id}/analytics")
async def get_twitter_post_analytics(tweet_id: str):
    """Get detailed analytics for a specific Twitter post"""
    try:
        result = twitter_analytics_service.get_tweet_analytics(tweet_id)
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}


@main_app.get("/api/twitter/post/{tweet_id}/replies")
async def get_twitter_post_replies(tweet_id: str, limit: int = 25):
    """Get replies to a specific Twitter post"""
    try:
        result = twitter_analytics_service.get_tweet_replies(tweet_id, limit=limit)
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}


# Instagram Analytics Endpoints
from instagram_weekly_posts import instagram_weekly_posts_service


async def _configure_instagram_service_for_user(user_id: str, account_id: Optional[str] = None):
    """Load Instagram credentials from DB and configure analytics service."""
    account = await db_service.get_social_media_account(
        user_id,
        platform="instagram",
        account_id=account_id
    )
    if not account:
        return None

    instagram_analytics_service.configure(
        access_token=account["access_token"],
        account_id=account["account_id"]
    )
    return account

@main_app.get("/api/social-media/accounts")
async def get_all_social_media_accounts(
    platform: Optional[str] = None,
    include_inactive: Optional[bool] = False,
    current_user = Depends(get_current_user_dependency)
):
    """Get all connected social media accounts for the current user, optionally filtered by platform"""
    try:
        user_id = str(current_user.id) if current_user and hasattr(current_user, 'id') else None
        if not user_id:
            return {"success": False, "error": "User not authenticated"}
        
        from database_service import db_service
        active_only = not include_inactive
        accounts = await db_service.get_social_media_accounts(user_id, platform=platform, active_only=active_only)
        
        # Format accounts and remove sensitive data
        # Also filter by is_active as a defensive measure (even though database query should handle it)
        formatted_accounts = []
        for account in accounts:
            # Skip inactive accounts if active_only is True (defensive filtering)
            if active_only and not account.get("is_active", True):
                continue
            # Handle created_at and expires_at - they might already be strings or datetime objects
            created_at = account.get("created_at")
            if created_at:
                if isinstance(created_at, str):
                    created_at_str = created_at
                elif hasattr(created_at, 'isoformat'):
                    created_at_str = created_at.isoformat()
                else:
                    created_at_str = str(created_at)
            else:
                created_at_str = None
            
            expires_at = account.get("expires_at")
            if expires_at:
                if isinstance(expires_at, str):
                    expires_at_str = expires_at
                elif hasattr(expires_at, 'isoformat'):
                    expires_at_str = expires_at.isoformat()
                else:
                    expires_at_str = str(expires_at)
            else:
                expires_at_str = None
            
            formatted_account = {
                "id": str(account.get("id")),
                "platform": account.get("platform"),
                "account_id": account.get("account_id"),
                "username": account.get("username"),
                "display_name": account.get("display_name"),
                "is_primary": account.get("is_primary", False),
                "is_active": account.get("is_active", True),
                "created_at": created_at_str,
                "expires_at": expires_at_str,
                "metadata": account.get("metadata", {})
            }
            formatted_accounts.append(formatted_account)
        
        return {"success": True, "accounts": formatted_accounts}
    except Exception as e:
        return {"success": False, "error": str(e)}

@main_app.delete("/api/social-media/accounts/{account_id}")
async def disconnect_social_media_account(
    account_id: str,
    current_user = Depends(get_current_user_dependency)
):
    """Disconnect a specific social media account by ID"""
    try:
        from database import database
        
        user_id = str(current_user.id) if current_user and hasattr(current_user, 'id') else None
        if not user_id:
            return {"success": False, "error": "User not authenticated"}
        
        print(f"🔌 Disconnect request: account_id={account_id}, user_id={user_id}")
        
        # First check if account exists and belongs to user
        existing = await database.fetch_one(
            """SELECT id, platform, display_name, username, is_active 
               FROM social_media_accounts 
               WHERE id = :account_id AND user_id = :user_id""",
            {"account_id": account_id, "user_id": user_id}
        )
        
        if not existing:
            return {"success": False, "error": "Account not found"}
        
        # Convert Record to dict to safely access values
        existing_dict = dict(existing) if existing else {}
        if not existing_dict.get("is_active", True):
            return {"success": False, "error": "Account is already disconnected"}
        
        # Deactivate the account
        await database.execute(
            """UPDATE social_media_accounts 
               SET is_active = FALSE, updated_at = NOW() 
               WHERE id = :account_id AND user_id = :user_id""",
            {"account_id": account_id, "user_id": user_id}
        )
        
        print(f"✅ Account {account_id} disconnected successfully")
        
        return {
            "success": True,
            "message": "Account disconnected successfully"
        }
    except Exception as e:
        import traceback
        error_msg = f"Error disconnecting account {account_id}: {str(e)}"
        print(f"❌ {error_msg}")
        print(traceback.format_exc())
        return {"success": False, "error": error_msg}

@main_app.get("/api/instagram/accounts")
async def get_instagram_accounts(current_user = Depends(get_current_user_dependency)):
    """Get all connected Instagram accounts for the current user"""
    try:
        user_id = str(current_user.id) if current_user and hasattr(current_user, 'id') else None
        if not user_id:
            return {"success": False, "error": "User not authenticated"}
        
        from database_service import db_service
        accounts = await db_service.get_social_media_accounts(user_id, platform="instagram")
        
        # Remove sensitive access_token from response and transform to legacy format
        result = []
        for account in accounts:
            result.append({
                "id": account.get("id"),
                "instagram_account_id": account.get("account_id"),
                "instagram_username": account.get("username"),
                "facebook_page_id": account.get("metadata", {}).get("facebook_page_id"),
                "expires_at": account.get("expires_at"),
                "scopes": account.get("scopes"),
                "created_at": account.get("created_at"),
                "updated_at": account.get("updated_at")
            })
        
        return {"success": True, "accounts": result}
    except Exception as e:
        return {"success": False, "error": str(e)}

@main_app.get("/api/instagram/account/info")
async def get_instagram_account_info(
    account_id: Optional[str] = None,
    current_user = Depends(get_current_user_dependency)
):
    """Get Instagram account information for the current user's account"""
    try:
        user_id = str(current_user.id) if current_user and hasattr(current_user, 'id') else None
        if not user_id:
            return {"success": False, "error": "User not authenticated"}

        account = await _configure_instagram_service_for_user(user_id, account_id)
        if not account:
            return {"success": False, "error": "No Instagram account found. Please connect your Instagram account."}
        
        result = instagram_analytics_service.get_account_info()
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}
        
@main_app.get("/api/instagram/weekly-posts")
async def get_instagram_weekly_posts(
    account_id: Optional[str] = None,
    current_user = Depends(get_current_user_dependency)
):
    """Get Instagram posts from the current week"""
    try:
        user_id = str(current_user.id) if current_user and hasattr(current_user, 'id') else None
        if not user_id:
            return {"success": False, "error": "User not authenticated"}

        account = await _configure_instagram_service_for_user(user_id, account_id)
        if not account:
            return {"success": False, "error": "No Instagram account found. Please connect your Instagram account."}

        result = instagram_weekly_posts_service.get_weekly_posts()
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}


@main_app.get("/api/instagram/account/analytics")
async def get_instagram_account_analytics(
    account_id: Optional[str] = None,
    current_user = Depends(get_current_user_dependency)
):
    """Get comprehensive Instagram account analytics for the current user's account"""
    try:
        user_id = str(current_user.id) if current_user and hasattr(current_user, 'id') else None
        if not user_id:
            return {"success": False, "error": "User not authenticated"}
        
        account = await _configure_instagram_service_for_user(user_id, account_id)
        if not account:
            return {"success": False, "error": "No Instagram account found. Please connect your Instagram account."}
        
        result = instagram_analytics_service.get_comprehensive_analytics()
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}


@main_app.get("/api/instagram/media")
async def get_instagram_media(
    limit: int = 25,
    account_id: Optional[str] = None,
    current_user = Depends(get_current_user_dependency)
):
    """Get your Instagram media posts for the current user's account"""
    try:
        user_id = str(current_user.id) if current_user and hasattr(current_user, 'id') else None
        if not user_id:
            return {"success": False, "error": "User not authenticated"}
        
        account = await _configure_instagram_service_for_user(user_id, account_id)
        if not account:
            return {"success": False, "error": "No Instagram account found. Please connect your Instagram account."}
        
        result = instagram_analytics_service.get_media_list(limit=limit)
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}


@main_app.get("/api/instagram/post/{media_id}/analytics")
async def get_instagram_post_analytics(
    media_id: str,
    account_id: Optional[str] = None,
    current_user = Depends(get_current_user_dependency)
):
    """Get detailed analytics for a specific Instagram post"""
    try:
        user_id = str(current_user.id) if current_user and hasattr(current_user, 'id') else None
        if not user_id:
            return {"success": False, "error": "User not authenticated"}

        account = await _configure_instagram_service_for_user(user_id, account_id)
        if not account:
            return {"success": False, "error": "No Instagram account found. Please connect your Instagram account."}

        result = instagram_analytics_service.get_post_analytics(media_id)
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}


@main_app.get("/api/instagram/insights/account")
async def get_instagram_account_insights(
    account_id: Optional[str] = None,
    current_user = Depends(get_current_user_dependency)
):
    """Get Instagram account-level insights"""
    try:
        user_id = str(current_user.id) if current_user and hasattr(current_user, 'id') else None
        if not user_id:
            return {"success": False, "error": "User not authenticated"}

        account = await _configure_instagram_service_for_user(user_id, account_id)
        if not account:
            return {"success": False, "error": "No Instagram account found. Please connect your Instagram account."}

        result = instagram_analytics_service.get_account_insights()
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}


@main_app.get("/api/instagram/insights/media/{media_id}")
async def get_instagram_media_insights(
    media_id: str,
    account_id: Optional[str] = None,
    current_user = Depends(get_current_user_dependency)
):
    """Get detailed insights for a specific Instagram media post"""
    try:
        user_id = str(current_user.id) if current_user and hasattr(current_user, 'id') else None
        if not user_id:
            return {"success": False, "error": "User not authenticated"}

        account = await _configure_instagram_service_for_user(user_id, account_id)
        if not account:
            return {"success": False, "error": "No Instagram account found. Please connect your Instagram account."}

        result = instagram_analytics_service.get_media_insights(media_id)
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}


@main_app.get("/api/instagram/cache/clear")
async def clear_instagram_cache():
    """Clear Instagram analytics cache"""
    try:
        instagram_analytics_service.clear_cache()
        return {"success": True, "message": "Instagram analytics cache cleared"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@main_app.get("/api/instagram/cache/stats")
async def get_instagram_cache_stats():
    """Get Instagram analytics cache statistics"""
    try:
        result = instagram_analytics_service.get_cache_stats()
        return {"success": True, "cache_stats": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


# Twitter API Endpoints
@main_app.get("/api/twitter/status")
async def get_twitter_status():
    """Get Twitter service status"""
    try:
        from twitter_service import TwitterService
        twitter_service = TwitterService()
        return {
            "success": True,
            "configured": twitter_service.is_configured(),
            "connection_test": twitter_service.test_connection()
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@main_app.post("/api/twitter/post")
async def post_to_twitter(request: dict):
    """Post content to Twitter"""
    try:
        from twitter_service import TwitterService
        twitter_service = TwitterService()
        
        content = request.get("content", "")
        image_path = request.get("image_path")
        
        if not content:
            return {"success": False, "error": "Content is required"}
        
        result = twitter_service.post_to_twitter(content, image_path)
        return result
        
    except Exception as e:
        return {"success": False, "error": str(e)}


@main_app.post("/api/twitter/schedule")
async def schedule_twitter_post(request: dict):
    """Schedule a Twitter post"""
    try:
        from database_service import db_service
        
        content = request.get("content", "")
        scheduled_at = request.get("scheduled_at")
        image_path = request.get("image_path")
        
        if not content:
            return {"success": False, "error": "Content is required"}
        
        if not scheduled_at:
            return {"success": False, "error": "Scheduled time is required"}
        
        # Create post in database
        default_campaign_id = await db_service.get_default_campaign_id()
        
        from datetime import datetime
        scheduled_datetime = datetime.fromisoformat(scheduled_at.replace('Z', '+00:00'))
        
        post_id = await db_service.create_post(
            original_description=content,
            caption=content,
            image_path=image_path,
            scheduled_at=scheduled_datetime,
            campaign_id=default_campaign_id,
            platform="twitter",
            status="scheduled"
        )
        
        return {
            "success": True,
            "post_id": post_id,
            "message": "Twitter post scheduled successfully"
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}


@main_app.get("/api/twitter/scheduled")
async def get_scheduled_twitter_posts():
    """Get scheduled Twitter posts"""
    try:
        from database_service import db_service
        posts = await db_service.get_scheduled_posts()
        twitter_posts = [post for post in posts if post.get("platform") == "twitter"]
        return {"success": True, "posts": twitter_posts}
    except Exception as e:
        return {"success": False, "error": str(e)}


@main_app.post("/api/twitter/publish/{post_id}")
async def publish_scheduled_twitter_post(post_id: str):
    """Publish a scheduled Twitter post"""
    try:
        from twitter_service import TwitterService
        from database_service import db_service
        
        # Get post details
        post = await db_service.get_post_by_id(post_id)
        if not post:
            return {"success": False, "error": "Post not found"}
        
        if post.get("platform") != "twitter":
            return {"success": False, "error": "Post is not a Twitter post"}
        
        twitter_service = TwitterService()
        result = twitter_service.post_to_twitter(
            content=post.get("caption", ""),
            image_path=post.get("image_path")
        )
        
        if result.get("success"):
            # Update post status
            await db_service.update_post_status(post_id, "published")
            return result
        else:
            return result
            
    except Exception as e:
        return {"success": False, "error": str(e)}


@main_app.get("/api/twitter/user/{username}")
async def get_twitter_user_info(username: str):
    """Get Twitter user information"""
    try:
        from twitter_service import TwitterService
        twitter_service = TwitterService()
        result = twitter_service.get_user_info(username)
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}


@main_app.get("/api/twitter/user/{username}/tweets")
async def get_twitter_user_tweets(username: str, max_results: int = 10):
    """Get tweets from a Twitter user"""
    try:
        from twitter_service import TwitterService
        twitter_service = TwitterService()
        result = twitter_service.get_user_tweets(username, max_results)
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}


@main_app.post("/api/scheduler/start")
async def start_scheduler_service():
    """Manually start the scheduler service"""
    try:
        await scheduler_service.start()
        return {"success": True, "message": "Scheduler started"}
        
    except Exception as e:
        return {"success": False, "error": str(e)}


@main_app.post("/api/scheduler/stop")
async def stop_scheduler_service():
    """Manually stop the scheduler service"""
    try:
        await scheduler_service.stop()
        return {"success": True, "message": "Scheduler stopped"}
        
    except Exception as e:
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    import uvicorn

    # Check required environment variables with enhanced warnings
    print("\n🔍 API Key Status Check:")
    
    if not GROQ_API_KEY:
        print("⚠️  GROQ_API_KEY not found. Groq caption generation will not work.")
    else:
        print("✅ GROQ_API_KEY configured")
        
    if not CHATGPT_API_KEY:
        print("⚠️  CHATGPT_API not found. ChatGPT caption and image generation will not work.")
    else:
        print("✅ CHATGPT_API configured")
        if CHATGPT_API_KEY.startswith('sk-proj-'):
            print("   📝 Using project-scoped OpenAI API key")
        
    if not STABILITY_API_KEY:
        print("⚠️  STABILITY_API_KEY not found. Stability AI image generation will not work.")
    else:
        print("✅ STABILITY_API_KEY configured")
        
    if not PIAPI_API_KEY:
        print("⚠️  PIAPI_API_KEY (or NANO_BANANA_API_KEY) not found. PiAPI Gemini image generation will not work.")
    else:
        print("✅ PIAPI_API_KEY configured (PiAPI Gemini image generation)")
    
    # Check Reddit API credentials
    reddit_client_id = os.getenv("REDDIT_CLIENT_ID")
    reddit_client_secret = os.getenv("REDDIT_CLIENT_SECRET")
    reddit_access_token = os.getenv("REDDIT_ACCESS_TOKEN")
    
    if not reddit_client_id or not reddit_client_secret:
        print("⚠️  REDDIT_CLIENT_ID or REDDIT_CLIENT_SECRET not found. Reddit integration will not work.")
    else:
        print("✅ Reddit API credentials configured")
        
    if not reddit_access_token:
        print("⚠️  REDDIT_ACCESS_TOKEN not found. Reddit posting will not work.")
    else:
        print("✅ Reddit access token configured")
    
    print("\n🚀 Starting Social Media Agent API...\n")
    # Disable reload in Docker/production for stability
    # Reload causes connection issues in Docker, especially on Windows
    reload_enabled = False
    # Use PORT env var (Railway sets this) or default to 8000
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=reload_enabled)

# Trending topics endpoints
from trending_topics_service import trending_service
import logging

# Include dashboard router
main_app.include_router(dashboard_router)

# Setup logging
logger = logging.getLogger(__name__)

@main_app.get("/api/trending/ai-topics")
async def get_ai_trending_topics(category: Optional[str] = None):
    """Get AI-powered trending topics with optional category filter"""
    try:
        result = trending_service.get_trending_topics(category)
        return result
    except Exception as e:
        logger.error(f"Error getting trending topics: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@main_app.post("/api/trending/refresh")
async def refresh_trending_topics():
    """Force refresh trending topics (bypass cache)"""
    try:
        result = trending_service.refresh_topics()
        return result
    except Exception as e:
        logger.error(f"Error refreshing trending topics: {e}")
        return {
            "success": False,
            "error": str(e)
        }

# Frontend serving - must be after all API routes
@main_app.get("/api/info")
async def api_info():
    """API information endpoint"""
    return {
        "message": "Instagram Post Generator API v3.0",
        "status": "running",
        "endpoints": [
            "/api/info",
            "/health",
            "/generate-post",
            "/generate-caption",
            "/generate-batch",
        ],
    }

# Mount static files for direct asset access
main_app.mount("/assets", StaticFiles(directory="static/assets"), name="assets")
main_app.mount("/icons", StaticFiles(directory="static/icons"), name="icons")

# Serve privacy policy directly
@main_app.get("/privacy-policy.html")
async def serve_privacy_policy():
    """Serve privacy policy HTML file"""
    # Try multiple possible paths (relative to server directory and project root)
    possible_paths = [
        "static/privacy-policy.html",  # Production build location
        "../static/privacy-policy.html",  # From server directory
        "public/privacy-policy.html",  # Development location
        "../public/privacy-policy.html",  # From server directory
        "../socialanywhere.ai/public/privacy-policy.html",  # Absolute from server
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return FileResponse(path, media_type="text/html")
    
    raise HTTPException(status_code=404, detail="Privacy policy not found")

@main_app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
async def serve_frontend(path: str = "", request: Request = None):
    """Serve frontend files, fallback to index.html for SPA routing"""
    # Handle API routes that should return 404 instead of frontend
    # Only allow GET requests to fall through to frontend serving
    if path.startswith("api/"):
        if path != "api/info" and request and request.method != "GET":
            # For non-GET requests to API paths, return 404 (route not found)
            # This prevents 405 errors when API routes don't match
            raise HTTPException(status_code=404, detail="API endpoint not found")
        elif path != "api/info":
            # For GET requests to API paths, also return 404
            raise HTTPException(status_code=404, detail="API endpoint not found")
    
    # Handle special FastAPI endpoints
    if path in ["docs", "openapi.json", "redoc"]:
        raise HTTPException(status_code=404, detail="API documentation not found")
    
    # Only serve frontend for GET requests
    if request and request.method != "GET":
        raise HTTPException(status_code=404, detail="Endpoint not found")
    
    # Serve root or empty path as index.html
    if not path or path == "":
        if os.path.exists("static/index.html"):
            return FileResponse("static/index.html")
        else:
            raise HTTPException(status_code=404, detail="Frontend not found")
    
    # Try to serve the requested static file
    file_path = f"static/{path}"
    if os.path.exists(file_path) and os.path.isfile(file_path):
        return FileResponse(file_path)
    
    # For SPA routing (React Router), serve index.html for any other path
    if os.path.exists("static/index.html"):
        return FileResponse("static/index.html")
    else:
        raise HTTPException(status_code=404, detail="Frontend not found")
