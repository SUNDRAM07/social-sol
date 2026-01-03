# Google Calendar Setup Guide

This guide explains how to set up Google Calendar integration for both **local development** and **production**.

## 📋 Prerequisites

1. **Google Cloud Console** project with OAuth 2.0 credentials
2. **Client ID** and **Client Secret** from Google Cloud
3. **Authorized redirect URIs** configured in Google Cloud Console

## 🔧 Setup Steps

### 1. Google Cloud Console Configuration

In your Google Cloud Console → **APIs & Services → Credentials**:

**Add these Authorized redirect URIs:**
- **Local:** `http://localhost:8000/socialanywhere/oauth/callback`
- **Production:** `https://agentanywhere.ai/socialanywhere/oauth/callback`

### 2. Local Development Setup

#### Option A: Using Credentials.json (Recommended for local)

1. Download your OAuth 2.0 client JSON from Google Cloud Console
2. Save it as `Credentials.json` in the project root:
   ```
   C:\Users\kurub\Ram\socialanywhere.ai\Credentials.json
   ```
3. The JSON should contain:
   ```json
   {
     "web": {
       "client_id": "your-client-id.apps.googleusercontent.com",
       "client_secret": "your-client-secret",
       "redirect_uris": [
         "http://localhost:8000/socialanywhere/oauth/callback",
         "https://agentanywhere.ai/socialanywhere/oauth/callback"
       ]
     }
   }
   ```

#### Option B: Using .env file

Create/update `.env` in project root:

```env
# Google OAuth Configuration
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8000/socialanywhere/oauth/callback

# Environment detection (for local)
PUBLIC_DOMAIN=localhost:8000
USE_HTTPS=false
```

### 3. Production Setup

In your production environment (Azure/Docker), set these environment variables:

```env
# Google OAuth Configuration
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=https://agentanywhere.ai/socialanywhere/oauth/callback

# Environment detection (for production)
PUBLIC_DOMAIN=agentanywhere.ai
USE_HTTPS=true
```

**OR** use `Credentials.json` with production redirect URIs configured.

## 🧪 Testing Locally

### Quick Test Script

Run the PowerShell test script:

```powershell
.\test_google_connect.ps1
```

This will:
1. ✅ Check if backend is running
2. ✅ Check Google connection status
3. ✅ Test the connect endpoint
4. ✅ Open Google OAuth in browser if needed

### Manual Testing

1. **Start the backend:**
   ```powershell
   docker compose up
   ```

2. **Open in browser:**
   ```
   http://localhost:8000/socialanywhere/google/connect
   ```

3. **You should be redirected to:**
   ```
   https://accounts.google.com/o/oauth2/auth?...
   ```
   (NOT `agentanywhere.ai` - that's wrong!)

4. **Complete Google consent** → You'll be redirected back to:
   ```
   http://localhost:8000/socialanywhere/oauth/callback?code=...
   ```

5. **Check connection status:**
   ```
   http://localhost:8000/socialanywhere/google/status
   ```
   Should return: `{"connected": true}`

## 🚀 Production Deployment

### Docker Compose

The `docker-compose.yml` already includes Google OAuth env vars. Make sure:

1. **Credentials.json** is copied into the Docker image (handled by Dockerfile)
2. **OR** set environment variables in your production environment

### Environment Variables Priority

The code checks in this order:
1. `Credentials.json` file (if exists)
2. `GOOGLE_CLIENT_ID` + `GOOGLE_CLIENT_SECRET` from environment
3. Auto-detects redirect URI based on `PUBLIC_DOMAIN` and `USE_HTTPS`

## ✅ Verification

After setup, verify it works:

1. **Check status:**
   ```bash
   curl http://localhost:8000/socialanywhere/google/status
   ```

2. **In the app UI:**
   - Go to Settings → Google Calendar Integration
   - Click "Connect Google Calendar"
   - Should redirect to Google (not show 502 error)

3. **After connecting:**
   - You can create calendar events for scheduled posts
   - View upcoming events from Google Calendar
   - Events sync between your app and Google Calendar

## 🐛 Troubleshooting

### Error: "Credentials.json not found"
- **Solution:** Make sure `Credentials.json` is in project root (same level as `Dockerfile`)
- **OR** set `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` in `.env`

### Error: "redirect_uri_mismatch"
- **Solution:** The redirect URI in your code must **exactly match** one of the URIs in Google Cloud Console
- Check: Google Cloud → OAuth 2.0 Client → Authorized redirect URIs

### Error: "502 Bad Gateway" with `agentanywhere.ai`
- **Problem:** You're hitting production domain instead of Google
- **Solution:** Make sure you're using `http://localhost:8000` for local testing
- The redirect URL should start with `https://accounts.google.com/...`

### Backend not running
- **Solution:** Run `docker compose up` and wait for "Uvicorn running on http://0.0.0.0:8000"

## 📝 Notes

- The `token.json` file is created automatically after first successful OAuth
- This file contains your refresh token and is stored in the backend container
- For production, ensure `token.json` persists (use Docker volumes if needed)




