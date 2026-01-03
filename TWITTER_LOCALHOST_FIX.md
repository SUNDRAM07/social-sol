# Twitter OAuth Localhost Fix

## Problem
Twitter OAuth shows "Something went wrong" error when using localhost URLs.

## Solution

Twitter OAuth 2.0 **DOES support localhost**, but your app must be in **"Development" mode**.

### Steps to Fix:

1. **Go to Twitter Developer Portal**
   - Visit: https://developer.twitter.com/en/portal/dashboard
   - Click on your app

2. **Check App Environment**
   - Look for "App environment" or "Environment" setting
   - It should say **"Development"** (not "Production")
   - If it says "Production", you have two options:
     - **Option A**: Switch to Development mode (recommended for local testing)
     - **Option B**: Use production URLs only (will work after deployment)

3. **Configure Callback URLs**
   - Go to "User authentication settings"
   - Add BOTH URLs (one per line):
     ```
     http://localhost:8000/socialanywhere/social-media/twitter/callback
     https://yourdomain.com/socialanywhere/social-media/twitter/callback
     ```
   - Twitter accepts multiple callback URLs

4. **Verify Settings**
   - App type: **Web App**
   - App permissions: **Read and write**
   - App environment: **Development** (for localhost) or **Production** (for HTTPS only)

## Development vs Production Mode

### Development Mode ✅
- Allows localhost URLs (`http://localhost:8000`)
- Perfect for local testing
- Can add both localhost and production URLs
- **Use this for development**

### Production Mode ⚠️
- Only accepts HTTPS URLs
- Does NOT accept localhost
- Requires production domain
- **Use this only after deployment**

## After Deployment

Once you deploy to production:

1. Your app can stay in Development mode (supports both localhost and production)
2. OR switch to Production mode and use only production URLs
3. Update `PUBLIC_DOMAIN` in `.env` to your production domain
4. Update `USE_HTTPS=true` in `.env`
5. The production callback URL will work automatically

## Quick Checklist

- [ ] App is in **Development** mode (for localhost)
- [ ] Callback URL added: `http://localhost:8000/socialanywhere/social-media/twitter/callback`
- [ ] Production callback URL added: `https://yourdomain.com/socialanywhere/social-media/twitter/callback`
- [ ] App type is "Web App"
- [ ] App permissions include "Read and write"
- [ ] All required scopes are enabled

## Still Not Working?

1. Check server logs for the exact redirect URI being used
2. Verify it matches EXACTLY in Twitter app settings (including `http://` and port)
3. Make sure app is in Development mode
4. Try clearing browser cache and cookies
5. Check that `TWITTER_CLIENT_ID` and `TWITTER_CLIENT_SECRET` are correct


