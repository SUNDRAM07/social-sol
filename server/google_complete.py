from fastapi import APIRouter, Depends, HTTPException, status, Request as FastAPIRequest
from fastapi.responses import RedirectResponse
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta
import os
import json
import io
import time
import tempfile
import requests
from PIL import Image

router = APIRouter()

# This is the file that will store the user's access and refresh tokens.
# It is created automatically when the authorization flow completes for the first
# time.
TOKEN_FILE = 'token.json'
SCOPES = ['https://www.googleapis.com/auth/drive.metadata.readonly', 
          'https://www.googleapis.com/auth/drive', 
          'https://www.googleapis.com/auth/analytics.readonly', 
          'https://mail.google.com/',
          'https://www.googleapis.com/auth/calendar']

def get_google_flow():
    """
    Build a Google OAuth flow.
    Priority:
      1) Credentials.json file (existing behaviour)
      2) GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET from environment (.env)
    
    Automatically detects local vs production based on PUBLIC_DOMAIN and USE_HTTPS.
    """
    # Auto-detect environment and set redirect URI
    # For local development, check if we're actually running on localhost
    public_domain = os.getenv('PUBLIC_DOMAIN', '')
    use_https = os.getenv('USE_HTTPS', 'false').lower() == 'true'
    
    # Detect if we're running locally by checking the actual request context
    # If PUBLIC_DOMAIN is set but we're accessing via localhost, use local redirect
    is_local = (
        not public_domain or 
        'localhost' in public_domain.lower() or 
        public_domain == 'localhost:8000' or
        public_domain.startswith('127.0.0.1')
    )
    
    if is_local:
        default_redirect = 'http://localhost:8000/socialanywhere/oauth/callback'
    else:
        # Production: use PUBLIC_DOMAIN with https
        scheme = 'https' if use_https else 'http'
        default_redirect = f'{scheme}://{public_domain}/socialanywhere/oauth/callback'
    
    # Allow explicit override via env var
    redirect_uri = os.getenv('GOOGLE_REDIRECT_URI', default_redirect)
    print(f"🌍 Environment: {public_domain} (HTTPS: {use_https})")
    print(f"🔗 Using Google OAuth redirect URI: {redirect_uri}")

    if os.path.exists('Credentials.json'):
        print("Using Credentials.json for Google OAuth configuration")
        try:
            # Read and validate the JSON file
            with open('Credentials.json', 'r') as f:
                creds_data = json.load(f)
            
            # CRITICAL: Always override auth_uri to use Google's endpoints
            # This prevents issues if the JSON file has incorrect auth_uri values
            if 'web' in creds_data:
                creds_data['web']['auth_uri'] = "https://accounts.google.com/o/oauth2/auth"
                creds_data['web']['token_uri'] = "https://oauth2.googleapis.com/token"
                creds_data['web']['auth_provider_x509_cert_url'] = "https://www.googleapis.com/oauth2/v1/certs"
                # Ensure redirect_uri is set correctly
                if 'redirect_uris' not in creds_data['web']:
                    creds_data['web']['redirect_uris'] = []
                # Add our redirect URI if not already present
                if redirect_uri not in creds_data['web']['redirect_uris']:
                    creds_data['web']['redirect_uris'].append(redirect_uri)
            
            # Extract client_id and client_secret, then use env var method instead
            # This avoids tempfile issues and ensures we always use correct endpoints
            if 'web' in creds_data and 'client_id' in creds_data['web']:
                client_id = creds_data['web']['client_id']
                client_secret = creds_data['web'].get('client_secret', '')
                print(f"✅ Extracted credentials from Credentials.json, using Google endpoints")
                # Use the env var method which always uses correct Google endpoints
                # Temporarily set env vars for this request
                os.environ['GOOGLE_CLIENT_ID'] = client_id
                os.environ['GOOGLE_CLIENT_SECRET'] = client_secret
                # Fall through to use the env var method below
            else:
                raise ValueError("Credentials.json missing 'web.client_id'")
        except Exception as e:
            print(f"⚠️ Error reading Credentials.json: {e}")
            import traceback
            traceback.print_exc()
            print("Falling back to environment variables...")
            # Fall through to env var method

    # Fallback: use env vars
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")

    if not client_id or not client_secret:
        print("Google OAuth env vars not configured")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "Google OAuth is not configured. Either add a Credentials.json file "
                "or set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in your .env."
            ),
        )

    client_config = {
        "web": {
            "client_id": client_id,
            "project_id": os.getenv("GOOGLE_PROJECT_ID", "socialanywhere"),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_secret": client_secret,
            "redirect_uris": [redirect_uri],
        }
    }

    print("Using GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET from environment for Google OAuth")
    flow = Flow.from_client_config(
        client_config,
        scopes=SCOPES,
        redirect_uri=redirect_uri,
    )
    return flow

@router.get("/google/connect")
async def connect_google(flow: Flow = Depends(get_google_flow)):
    print("Connecting to Google...")
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent'
    )
    print(f"Redirecting to: {authorization_url}")
    return RedirectResponse(authorization_url)

# Callback endpoint for Google OAuth.
# We support BOTH paths to be robust against older redirect_uris:
#   - /socialanywhere/oauth/callback   (preferred, matches current redirect_uris)
#   - /oauth/callback                  (legacy)
@router.get("/socialanywhere/oauth/callback")
@router.get("/oauth/callback")
async def google_callback(code: str, request: FastAPIRequest, flow: Flow = Depends(get_google_flow)):
    print("Received callback from Google.")
    print(f"Code: {code}")
    try:
        flow.fetch_token(code=code)
        credentials = flow.credentials
        
        # Ensure no corrupted token file exists before writing
        if os.path.exists(TOKEN_FILE):
            if os.path.isdir(TOKEN_FILE):
                print(f"Removing corrupted token directory: {TOKEN_FILE}")
                import shutil
                try:
                    shutil.rmtree(TOKEN_FILE)
                except Exception as e:
                    # Try to rename if removal fails
                    backup_name = f"{TOKEN_FILE}_old_{int(time.time())}"
                    try:
                        os.rename(TOKEN_FILE, backup_name)
                        print(f"Renamed corrupted directory to: {backup_name}")
                    except Exception as rename_error:
                        print(f"Failed to clean up corrupted token file: {rename_error}")
                        raise HTTPException(
                            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Cannot clean up corrupted token file. Please check file permissions."
                        )
        
        # Write token with robust, cross-platform-safe logic
        temp_token_file = f"{TOKEN_FILE}.tmp"
        try:
            # Ensure parent directory exists
            token_dir = os.path.dirname(TOKEN_FILE) or "."
            os.makedirs(token_dir, exist_ok=True)

            # Write to temp file first
            with open(temp_token_file, 'w') as token:
                token.write(credentials.to_json())
                token.flush()  # Ensure data is written
                os.fsync(token.fileno())  # Force write to disk

            # Try to move temp -> final, handling EBUSY on some host/volume setups
            last_error = None
            for attempt in range(5):
                try:
                    # Remove existing token file/dir if present
                    if os.path.exists(TOKEN_FILE):
                        if os.path.isdir(TOKEN_FILE):
                            import shutil
                            shutil.rmtree(TOKEN_FILE)
                        else:
                            os.remove(TOKEN_FILE)
                    # Prefer atomic replace
                    try:
                        os.replace(temp_token_file, TOKEN_FILE)
                    except Exception:
                        # Fallback to move if replace not available
                        import shutil
                        shutil.move(temp_token_file, TOKEN_FILE)
                    print("Successfully fetched and stored token.")
                    last_error = None
                    break
                except Exception as e:
                    last_error = e
                    print(f"Warning: failed to finalize token file (attempt {attempt+1}/5): {e}")
                    time.sleep(0.3 * (attempt + 1))

            if last_error is not None:
                # If still failing, raise detailed error
                raise last_error

        except Exception as write_error:
            # Clean up temp file if write failed
            try:
                if os.path.exists(temp_token_file):
                    os.remove(temp_token_file)
            except Exception:
                pass
            raise write_error
            
    except Exception as e:
        print(f"Error fetching token: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching token: {e}"
        )
    # Use request host to preserve domain
    try:
        # Get base URL from request host header
        host = request.headers.get("host", "")
        scheme = request.url.scheme if hasattr(request.url, 'scheme') else "https" if request.headers.get("x-forwarded-proto") == "https" else "http"
        
        # Check if we have a forwarded host (from reverse proxy)
        forwarded_host = request.headers.get("x-forwarded-host")
        if forwarded_host:
            host = forwarded_host
        
        # Use PUBLIC_DOMAIN if set, otherwise use request host
        public_domain = os.getenv("PUBLIC_DOMAIN")
        if public_domain and public_domain != "localhost:8000":
            if not public_domain.startswith("http"):
                base_url = f"{scheme}://{public_domain}"
            else:
                base_url = public_domain
        elif host:
            base_url = f"{scheme}://{host}"
        else:
            base_url = "http://localhost:8000"
    except Exception as e:
        # Fallback to environment variable or localhost
        public_domain = os.getenv("PUBLIC_DOMAIN", "localhost:8000")
        if not public_domain.startswith("http"):
            base_url = f"http://{public_domain}"
        else:
            base_url = public_domain
    
    # Redirect to settings page with success message
    # Use hash-based message to avoid query param issues
    # For local development, frontend is typically on port 3000, backend on 8000
    # Check if we're in local dev mode
    public_domain = os.getenv("PUBLIC_DOMAIN", "localhost:8000")
    if "localhost" in public_domain or public_domain == "localhost:8000":
        # Local dev: redirect to frontend (port 3000) if available, otherwise backend
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
        redirect_url = f"{frontend_url}/socialanywhere/settings#google-connected"
    else:
        # Production: use the base_url (which should be the frontend domain)
        redirect_url = f"{base_url}/socialanywhere/settings#google-connected"
    
    print(f"🔄 Redirecting to: {redirect_url}")
    return RedirectResponse(url=redirect_url)

@router.get("/google/status")
async def get_google_status():
    """Report whether Google is actually connected.
    We validate token.json contents (must be a file with a refresh_token),
    not just existence, to avoid false positives.
    """
    try:
        if not os.path.exists(TOKEN_FILE):
            return {"connected": False}
        if os.path.isdir(TOKEN_FILE):
            # Corrupted state: a directory where a file should be
            return {"connected": False, "error": "token_is_directory"}
        # Try to parse token and check refresh_token
        with open(TOKEN_FILE, "r") as f:
            raw = f.read().strip() or "{}"
            data = json.loads(raw)
        has_refresh = bool(data.get("refresh_token"))
        return {"connected": has_refresh}
    except Exception as e:
        # Any error -> treat as not connected
        return {"connected": False, "error": str(e)}

@router.post("/google/disconnect")
async def disconnect_google():
    """Remove token.json to fully disconnect Google account."""
    try:
        if os.path.exists(TOKEN_FILE):
            if os.path.isdir(TOKEN_FILE):
                import shutil
                shutil.rmtree(TOKEN_FILE)
            else:
                os.remove(TOKEN_FILE)
        return {"success": True, "message": "Disconnected from Google"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to disconnect: {e}")

def get_google_service(service_name: str, version: str):
    creds = None
    if os.path.exists(TOKEN_FILE):
        # Enhanced token file corruption handling
        try:
            # Check if TOKEN_FILE is a directory instead of a file
            if os.path.isdir(TOKEN_FILE):
                print(f"Warning: {TOKEN_FILE} is a directory, not a file. Attempting to remove it.")
                import shutil
                try:
                    shutil.rmtree(TOKEN_FILE)
                    print(f"Successfully removed corrupted directory: {TOKEN_FILE}")
                except PermissionError as e:
                    print(f"Permission error removing directory {TOKEN_FILE}: {e}")
                    # Try to rename it instead of removing
                    backup_name = f"{TOKEN_FILE}_corrupted_{int(time.time())}"
                    try:
                        os.rename(TOKEN_FILE, backup_name)
                        print(f"Renamed corrupted directory to: {backup_name}")
                    except Exception as rename_error:
                        print(f"Failed to rename corrupted directory: {rename_error}")
                except Exception as e:
                    print(f"Error removing corrupted token directory: {e}")
                    # Try alternative cleanup method
                    backup_name = f"{TOKEN_FILE}_corrupted_{int(time.time())}"
                    try:
                        os.rename(TOKEN_FILE, backup_name)
                        print(f"Renamed corrupted directory to: {backup_name}")
                    except Exception as rename_error:
                        print(f"Failed to rename corrupted directory: {rename_error}")
                
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Google token file was corrupted and has been cleaned up. Please reconnect your account."
                )
            
            # Check if file is readable
            if not os.access(TOKEN_FILE, os.R_OK):
                print(f"Warning: {TOKEN_FILE} is not readable")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Google token file is not readable. Please reconnect your account."
                )
            
            # Try to load credentials
            try:
                creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
            except json.JSONDecodeError as e:
                print(f"Warning: {TOKEN_FILE} contains invalid JSON: {e}")
                # Move corrupted file and create fresh one
                backup_name = f"{TOKEN_FILE}_corrupted_{int(time.time())}"
                try:
                    os.rename(TOKEN_FILE, backup_name)
                    print(f"Renamed corrupted token file to: {backup_name}")
                except Exception:
                    pass
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Google token file is corrupted (invalid JSON). Please reconnect your account."
                )
            except Exception as e:
                print(f"Warning: Failed to load token file {TOKEN_FILE}: {e}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"Failed to load Google token file: {str(e)}. Please reconnect your account."
                )
            
            if not creds.refresh_token:
                print(f"Warning: {TOKEN_FILE} missing refresh token")
                try:
                    os.remove(TOKEN_FILE)
                except Exception as e:
                    print(f"Failed to remove token file: {e}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Missing refresh token. Please reconnect your account."
                )
                
        except HTTPException:
            # Re-raise HTTP exceptions
            raise
        except Exception as e:
            print(f"Unexpected error handling token file: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Unexpected error with Google token file: {str(e)}"
            )
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authorized with Google. Please connect your account."
            )
    return build(service_name, version, credentials=creds)

class Activity(BaseModel):
    time: int
    text: str

class Campaign(BaseModel):
    id: str
    productDescription: str
    generatedContent: str
    scheduledAt: Optional[str]
    status: str
    imageUrl: Optional[str]
    driveImageUrl: Optional[str] = None
    activity: List[Activity]

@router.post("/google-drive/save-campaign")
async def save_campaign_to_drive(campaign: Campaign, drive_service = Depends(lambda: get_google_service('drive', 'v3'))):
    print("Saving campaign to drive...")
    try:
        image_file_id = None
        if campaign.imageUrl:
            print("Uploading image to Google Drive...")
            
            # Handle local vs remote image URLs
            try:
                if campaign.imageUrl.startswith('/public/'):
                    # Local file path
                    local_path = campaign.imageUrl.replace('/public/', 'public/')
                    print(f"Reading local image file: {local_path}")
                    
                    if not os.path.exists(local_path):
                        raise FileNotFoundError(f"Local image file not found: {local_path}")
                    
                    image = Image.open(local_path)
                elif campaign.imageUrl.startswith('http://localhost:') or campaign.imageUrl.startswith('http://127.0.0.1:'):
                    # Local server URL - convert to file path
                    # Extract the filename from the URL, should work for both placeholder and generated images
                    filename = campaign.imageUrl.split('/')[-1]
                    local_path = f'public/{filename}'
                    print(f"Converting localhost URL to local path: {local_path}")
                    
                    if not os.path.exists(local_path):
                        raise FileNotFoundError(f"Local image file not found: {local_path}")
                    
                    image = Image.open(local_path)
                else:
                    # Remote URL - download with timeout
                    print(f"Downloading remote image: {campaign.imageUrl}")
                    response = requests.get(campaign.imageUrl, stream=True, timeout=30)
                    response.raise_for_status()
                    image = Image.open(response.raw)
                
                print("Converting image to JPEG...")
                
                # Resize image if too large to prevent hanging
                max_size = (1920, 1920)
                if image.size[0] > max_size[0] or image.size[1] > max_size[1]:
                    image.thumbnail(max_size, Image.Resampling.LANCZOS)
                    print(f"Resized image to {image.size}")
                
                # Convert to RGB if necessary
                if image.mode in ('RGBA', 'P'):
                    rgb_image = Image.new('RGB', image.size, (255, 255, 255))
                    rgb_image.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
                    image = rgb_image
                
                jpeg_image = io.BytesIO()
                image.save(jpeg_image, 'JPEG', quality=85, optimize=True)
                jpeg_image.seek(0)
                
                print(f"Image processed, size: {len(jpeg_image.getvalue())} bytes")

                image_file_metadata = {
                    'name': f'campaign_{campaign.id}_image.jpeg',
                    'mimeType': 'image/jpeg'
                }
                
                # Use simple upload for smaller files (< 5MB), resumable for larger
                file_size = len(jpeg_image.getvalue())
                resumable = file_size > 5 * 1024 * 1024  # 5MB threshold
                media = MediaIoBaseUpload(jpeg_image, mimetype='image/jpeg', resumable=resumable)
                
                print(f"Creating image file in Google Drive (resumable: {resumable})...")
                
                # Create with timeout handling
                request = drive_service.files().create(
                    body=image_file_metadata,
                    media_body=media,
                    fields='id'
                )
                
                if resumable:
                    # Handle resumable upload with retries
                    response = None
                    retry_count = 0
                    max_retries = 3
                    
                    while response is None and retry_count < max_retries:
                        try:
                            status, response = request.next_chunk()
                            if status:
                                print(f"Upload progress: {int(status.progress() * 100)}%")
                        except Exception as chunk_error:
                            retry_count += 1
                            print(f"Upload chunk failed (attempt {retry_count}): {chunk_error}")
                            if retry_count >= max_retries:
                                raise chunk_error
                    
                    image_file = response
                else:
                    # Simple upload
                    image_file = request.execute()
                
                image_file_id = image_file.get('id')
                print(f"Image uploaded with ID: {image_file_id}")
                
            except requests.exceptions.Timeout:
                print("Image download timed out, continuing without image...")
                image_file_id = None
            except requests.exceptions.RequestException as req_error:
                print(f"Image download failed: {req_error}, continuing without image...")
                image_file_id = None
            except Exception as img_error:
                print(f"Image processing/upload failed: {img_error}, continuing without image...")
                image_file_id = None

        print("Creating campaign JSON file...")
        file_metadata = {
            'name': f'campaign_{campaign.id}_{datetime.now().isoformat().replace(":", "-")}.json',
            'mimeType': 'application/json'
        }
        campaign_data = campaign.dict()
        campaign_data['createdAt'] = datetime.now().isoformat()
        if image_file_id:
            # Store Google Drive URL in JSON file for backup/sharing
            # Use the correct direct image URL format
            campaign_data['driveImageUrl'] = f"https://drive.google.com/file/d/{image_file_id}/view"
            campaign_data['imageFileId'] = image_file_id
            # Keep original localhost URL for UI display

        file_content = json.dumps(campaign_data, indent=2).encode('utf-8')
        
        # Use simple upload for JSON files (they're typically small)
        media = MediaIoBaseUpload(io.BytesIO(file_content), mimetype='application/json', resumable=False)

        print("Creating JSON file in Google Drive...")
        file = drive_service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()
        print(f"JSON file created with ID: {file.get('id')}")
        
        # Return updated campaign data including the Google Drive image URL
        response_data = {
            "success": True, 
            "fileId": file.get('id'), 
            "imageFileId": image_file_id
        }
        
        # Include Drive image info in response if image was uploaded
        # But don't update the imageUrl - keep localhost URL for UI display
        if image_file_id:
            response_data["driveImageUrl"] = f"https://drive.google.com/file/d/{image_file_id}/view"
            response_data["updatedCampaignData"] = campaign_data
        
        print(f"Returning response: {response_data}")
        return response_data
    except Exception as e:
        print(f"Error saving campaign to drive: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error saving campaign to drive: {e}"
        )

@router.post("/google-calendar/create-event")
async def create_calendar_event(campaign: Campaign, calendar_service = Depends(lambda: get_google_service('calendar', 'v3'))):
    print("Creating calendar event...")
    if not campaign.scheduledAt:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Campaign must have a scheduled date to create a calendar event."
        )

    try:
        # Parse the scheduled time
        start_time = datetime.fromisoformat(campaign.scheduledAt.replace('Z', '+00:00'))
        end_time = start_time + timedelta(minutes=30)
        
        # Create a more detailed event description
        description_parts = [
            f"📱 Social Media Post Reminder",
            f"📝 Content: {campaign.generatedContent[:100]}{'...' if len(campaign.generatedContent) > 100 else ''}",
            f"🎯 Product: {campaign.productDescription}",
            f"📊 Status: {campaign.status}"
        ]
        
        # Use Google Drive URL if available, otherwise use local URL
        image_url_for_calendar = getattr(campaign, 'driveImageUrl', None) or campaign.imageUrl
        if image_url_for_calendar:
            description_parts.append(f"🖼️ Image: {image_url_for_calendar}")
        
        event = {
            'summary': f"📱 Post: {campaign.productDescription[:50]}{'...' if len(campaign.productDescription) > 50 else ''}",
            'description': '\n'.join(description_parts),
            'start': {
                'dateTime': start_time.isoformat(),
                'timeZone': 'UTC',
            },
            'end': {
                'dateTime': end_time.isoformat(),
                'timeZone': 'UTC',
            },
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'popup', 'minutes': 10},
                    {'method': 'email', 'minutes': 60},
                ],
            },
            'colorId': '2',  # Green color for social media posts
        }

        created_event = calendar_service.events().insert(calendarId='primary', body=event).execute()
        print(f"Event created: {created_event.get('htmlLink')}")
        
        return {
            "success": True, 
            "eventLink": created_event.get('htmlLink'),
            "eventId": created_event.get('id'),
            "summary": created_event.get('summary')
        }
        
    except Exception as e:
        print(f"Error creating calendar event: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating calendar event: {e}"
        )

class BatchCalendarRequest(BaseModel):
    campaigns: List[Campaign]

@router.post("/google-calendar/create-batch-events")
async def create_batch_calendar_events(request: BatchCalendarRequest, calendar_service = Depends(lambda: get_google_service('calendar', 'v3'))):
    print(f"Creating batch calendar events for {len(request.campaigns)} campaigns...")
    
    if not request.campaigns:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No campaigns provided for batch event creation."
        )
    
    results = []
    success_count = 0
    
    for campaign in request.campaigns:
        try:
            if not campaign.scheduledAt:
                results.append({
                    "campaignId": campaign.id,
                    "success": False,
                    "error": "Campaign must have a scheduled date"
                })
                continue
            
            # Parse the scheduled time
            start_time = datetime.fromisoformat(campaign.scheduledAt.replace('Z', '+00:00'))
            end_time = start_time + timedelta(minutes=30)
            
            # Create event description
            description_parts = [
                f"📱 Social Media Post Reminder",
                f"📝 Content: {campaign.generatedContent[:100]}{'...' if len(campaign.generatedContent) > 100 else ''}",
                f"🎯 Product: {campaign.productDescription}",
                f"📊 Status: {campaign.status}"
            ]
            
            # Use Google Drive URL if available, otherwise use local URL
            image_url_for_calendar = getattr(campaign, 'driveImageUrl', None) or campaign.imageUrl
            if image_url_for_calendar:
                description_parts.append(f"🖼️ Image: {image_url_for_calendar}")
            
            event = {
                'summary': f"📱 Post: {campaign.productDescription[:50]}{'...' if len(campaign.productDescription) > 50 else ''}",
                'description': '\n'.join(description_parts),
                'start': {
                    'dateTime': start_time.isoformat(),
                    'timeZone': 'UTC',
                },
                'end': {
                    'dateTime': end_time.isoformat(),
                    'timeZone': 'UTC',
                },
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'popup', 'minutes': 10},
                        {'method': 'email', 'minutes': 60},
                    ],
                },
                'colorId': '2',  # Green color for social media posts
            }

            created_event = calendar_service.events().insert(calendarId='primary', body=event).execute()
            
            results.append({
                "campaignId": campaign.id,
                "success": True,
                "eventLink": created_event.get('htmlLink'),
                "eventId": created_event.get('id'),
                "summary": created_event.get('summary')
            })
            success_count += 1
            
        except Exception as e:
            print(f"Error creating calendar event for campaign {campaign.id}: {e}")
            results.append({
                "campaignId": campaign.id,
                "success": False,
                "error": str(e)
            })
    
    print(f"Batch calendar events created: {success_count}/{len(request.campaigns)} successful")
    
    return {
        "success": success_count > 0,
        "total": len(request.campaigns),
        "successful": success_count,
        "failed": len(request.campaigns) - success_count,
        "results": results
    }

@router.get("/google-calendar/upcoming-events")
async def get_upcoming_events(calendar_service = Depends(lambda: get_google_service('calendar', 'v3'))):
    """Get upcoming calendar events for the next 30 days"""
    try:
        now = datetime.utcnow()
        time_max = now + timedelta(days=30)
        
        events_result = calendar_service.events().list(
            calendarId='primary',
            timeMin=now.isoformat() + 'Z',
            timeMax=time_max.isoformat() + 'Z',
            maxResults=50,
            singleEvents=True,
            orderBy='startTime',
            q='📱 Post:'  # Filter for social media posts
        ).execute()
        
        events = events_result.get('items', [])
        
        return {
            "success": True,
            "events": [
                {
                    "id": event.get('id'),
                    "summary": event.get('summary'),
                    "start": event.get('start', {}).get('dateTime'),
                    "description": event.get('description'),
                    "htmlLink": event.get('htmlLink')
                }
                for event in events
            ],
            "total": len(events)
        }
        
    except Exception as e:
        print(f"Error fetching upcoming events: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching upcoming events: {e}"
        )
