# Google Calendar Integration - Production Setup Guide

## Required Environment Variables for Production

Add these variables to your `.env` file for production deployment:

```env
# ============================================
# Google Calendar Integration (Required)
# ============================================

# Google OAuth Credentials (REQUIRED)
# Get these from: https://console.cloud.google.com/apis/credentials
GOOGLE_CLIENT_ID=your_google_client_id_here
GOOGLE_CLIENT_SECRET=your_google_client_secret_here

# Production Domain Configuration (REQUIRED)
# Set to your production domain (without http:// or https://)
PUBLIC_DOMAIN=yourdomain.com
USE_HTTPS=true

# Optional: Override redirect URI (auto-detected if not set)
# Format: https://yourdomain.com/socialanywhere/oauth/callback
GOOGLE_REDIRECT_URI=https://yourdomain.com/socialanywhere/oauth/callback

# Optional: Google Project ID (defaults to "socialanywhere")
GOOGLE_PROJECT_ID=your-project-id
```

## Step-by-Step Setup Instructions

### 1. Create Google Cloud Project & OAuth Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the following APIs:
   - **Google Calendar API**
   - **Google Drive API** (if using Drive integration)
4. Go to **APIs & Services** → **Credentials**
5. Click **Create Credentials** → **OAuth client ID**
6. Choose **Web application**
7. Configure OAuth consent screen if prompted:
   - User Type: External (or Internal if using Google Workspace)
   - App name: Your app name
   - Authorized domains: Your production domain
   - Scopes: Add these scopes:
     - `https://www.googleapis.com/auth/calendar`
     - `https://www.googleapis.com/auth/drive` (if using Drive)
     - `https://www.googleapis.com/auth/drive.metadata.readonly`
8. Add **Authorized redirect URIs**:
   ```
   https://yourdomain.com/socialanywhere/oauth/callback
   ```
   ⚠️ **IMPORTANT**: Replace `yourdomain.com` with your actual production domain

### 2. Get Your Credentials

After creating the OAuth client:
- **Client ID**: Copy from the credentials page (looks like: `123456789-abc123...apps.googleusercontent.com`)
- **Client Secret**: Copy the secret (looks like: `GOCSPX-abc123...`)

### 3. Configure Environment Variables

Add to your `.env` file:

```env
# Google OAuth
GOOGLE_CLIENT_ID=123456789-abc123def456.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-abc123def456xyz789

# Production Domain
PUBLIC_DOMAIN=yourdomain.com
USE_HTTPS=true
```

### 4. Verify Redirect URI Configuration

The redirect URI is automatically set to:
```
https://yourdomain.com/socialanywhere/oauth/callback
```

**Make sure this EXACT URL is added to your Google OAuth client's authorized redirect URIs!**

### 5. Test the Integration

1. Deploy your application with the environment variables set
2. Navigate to Settings → Google Calendar
3. Click "Connect Now"
4. You should be redirected to Google OAuth consent screen
5. After authorization, you'll be redirected back to your app

## Environment Variable Reference

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `GOOGLE_CLIENT_ID` | ✅ Yes | OAuth 2.0 Client ID from Google Cloud Console | `123456789-abc...apps.googleusercontent.com` |
| `GOOGLE_CLIENT_SECRET` | ✅ Yes | OAuth 2.0 Client Secret from Google Cloud Console | `GOCSPX-abc123...` |
| `PUBLIC_DOMAIN` | ✅ Yes | Your production domain (without protocol) | `yourdomain.com` |
| `USE_HTTPS` | ✅ Yes | Set to `true` for production | `true` |
| `GOOGLE_REDIRECT_URI` | ❌ Optional | Override auto-detected redirect URI | `https://yourdomain.com/socialanywhere/oauth/callback` |
| `GOOGLE_PROJECT_ID` | ❌ Optional | Google Cloud Project ID (defaults to "socialanywhere") | `my-project-id` |

## Important Notes

1. **Redirect URI Must Match Exactly**: The redirect URI in your Google OAuth client must match exactly (including `https://`, domain, and path)

2. **HTTPS Required**: Production deployments should use HTTPS (`USE_HTTPS=true`)

3. **Scopes**: The following scopes are automatically requested:
   - `https://www.googleapis.com/auth/calendar` (Calendar access)
   - `https://www.googleapis.com/auth/drive` (Drive access, if using)
   - `https://www.googleapis.com/auth/drive.metadata.readonly` (Drive metadata)

4. **Token Storage**: OAuth tokens are stored in `token.json` file on the server. Make sure this file is:
   - Not committed to version control (add to `.gitignore`)
   - Secured with proper file permissions
   - Backed up if needed

## Troubleshooting

### Error: "redirect_uri_mismatch"
- **Solution**: Make sure the redirect URI in Google Cloud Console matches exactly: `https://yourdomain.com/socialanywhere/oauth/callback`
- Check that `PUBLIC_DOMAIN` is set correctly (without `http://` or `https://`)
- Verify `USE_HTTPS=true` is set

### Error: "Google OAuth is not configured"
- **Solution**: Make sure `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` are set in your `.env` file
- Restart your application after adding environment variables

### Error: "invalid_client"
- **Solution**: Verify your `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` are correct
- Make sure you copied the full values without extra spaces

## Security Best Practices

1. **Never commit credentials**: Add `.env` to `.gitignore`
2. **Use environment variables**: Don't hardcode credentials in code
3. **Rotate secrets**: Regularly rotate your OAuth client secrets
4. **Limit scopes**: Only request the scopes you actually need
5. **Monitor usage**: Check Google Cloud Console for unusual activity

## Example Production .env

```env
# Google Calendar Integration
GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-your-google-client-secret

# Domain Configuration
PUBLIC_DOMAIN=agentanywhere.ai
USE_HTTPS=true

# Optional: Explicit redirect URI (auto-detected if not set)
# GOOGLE_REDIRECT_URI=https://agentanywhere.ai/socialanywhere/oauth/callback
```

