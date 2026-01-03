# Twitter OAuth 2.0 Setup Instructions

## Step 1: Create a Twitter App

1. Go to https://developer.twitter.com/en/portal/dashboard
2. Sign in with your Twitter account
3. Click **"Create App"** or **"New App"**
4. Fill in the form:
   - **App name**: Your app name (e.g., "SocialAnywhere AI")
   - **App description**: Brief description of your app
   - **Website URL**: Your website URL (optional)
   - **Callback URLs**: ⚠️ **IMPORTANT** - See Step 2 below
   - **App permissions**: Select **"Read and Write"** (or higher if needed)

## Step 2: Configure OAuth 2.0 Settings

⚠️ **IMPORTANT**: Twitter OAuth 2.0 requires the app to be in **"Development" mode** to use localhost URLs.

1. After creating the app, go to **"User authentication settings"**
2. Click **"Set up"** or **"Edit"**
3. Configure OAuth 2.0:
   - **App permissions**: 
     - ✅ Read users
     - ✅ Read and write Tweets
     - ✅ Read and write Direct Messages (optional)
   - **Type of App**: Select **"Web App"**
   - **App environment**: Make sure your app is in **"Development"** mode (not Production)
     - Development mode allows localhost URLs
     - Production mode requires HTTPS URLs only
   - **Callback URI / Redirect URL**: ⚠️ **IMPORTANT** - Add BOTH URLs (one per line):

### For Local Development (localhost):
```
http://localhost:8000/socialanywhere/social-media/twitter/callback
```

### For Production (add this too):
```
https://yourdomain.com/socialanywhere/social-media/twitter/callback
```

**Note**: You can add multiple callback URLs (one per line). Twitter will accept any of them.

4. Click **"Save"**

### ⚠️ Common Issue: "Something went wrong" Error

If you see "Something went wrong" or "You weren't able to give access to the App":

1. **Check App Mode**: Your app MUST be in "Development" mode to use localhost
   - Go to your app settings
   - Check the "App environment" - it should say "Development"
   - If it says "Production", you need to switch to Development mode (or use production URLs)

2. **Verify Callback URL**: The callback URL must match EXACTLY
   - Check server logs for the exact redirect URI being used
   - Make sure it's added in Twitter app settings (exact match, including `http://` and port)

3. **Check Scopes**: Make sure all required scopes are enabled:
   - `tweet.read`
   - `tweet.write`
   - `users.read`
   - `offline.access`

## Step 3: Get Your Credentials

After setting up OAuth 2.0, you'll see:
- **Client ID**: The OAuth 2.0 Client ID (looks like: `abc123xyz...`)
- **Client Secret**: The OAuth 2.0 Client Secret (looks like: `def456uvw...`)

⚠️ **Note**: These are different from OAuth 1.0a credentials (Consumer Key/Secret).

## Step 4: Configure Environment Variables

Add these to your `.env` file:

```env
TWITTER_CLIENT_ID=your_oauth2_client_id_here
TWITTER_CLIENT_SECRET=your_oauth2_client_secret_here
TWITTER_REDIRECT_URI=http://localhost:8000/socialanywhere/social-media/twitter/callback
PUBLIC_DOMAIN=localhost:8000
```

**Notes:**
- `TWITTER_CLIENT_ID`: OAuth 2.0 Client ID (NOT Consumer Key)
- `TWITTER_CLIENT_SECRET`: OAuth 2.0 Client Secret (NOT Consumer Secret)
- `TWITTER_REDIRECT_URI`: Only set this if you want to override the default
- `PUBLIC_DOMAIN`: Set to your domain (e.g., `localhost:8000` for local, `yourdomain.com` for production)

## Step 5: Verify Setup

1. Start your server
2. Try connecting Twitter from your app
3. Check server logs - you should see:
   ```
   🔗 Twitter OAuth Redirect URI: http://localhost:8000/socialanywhere/social-media/twitter/callback
   📝 ⚠️  IMPORTANT: Add this EXACT URL to your Twitter app settings!
   ```

## Common Errors and Solutions

### Error: "invalid redirect_uri parameter"

**Cause:** The redirect URI in your Twitter app settings doesn't match what your app is sending.

**Solution:**
1. Check your server logs for the exact redirect URI being used
2. Go to https://developer.twitter.com/en/portal/dashboard
3. Click on your app
4. Go to "User authentication settings"
5. Make sure the callback URL field contains the EXACT URL from the logs
6. Save and try again

### Error: "invalid_client"

**Cause:** Client ID or Client Secret is incorrect.

**Solution:**
1. Verify `TWITTER_CLIENT_ID` and `TWITTER_CLIENT_SECRET` in your `.env` file
2. Make sure you're using OAuth 2.0 credentials (not OAuth 1.0a Consumer Key/Secret)
3. Make sure there are no extra spaces or quotes
4. Get fresh credentials from Twitter Developer Portal if needed

### Error: "access_denied"

**Cause:** User denied permission or app doesn't have required scopes.

**Solution:**
1. Make sure your app type is set to "Web App" in User authentication settings
2. Make sure app permissions include "Read and Write"
3. User must approve all requested permissions

## OAuth 2.0 vs OAuth 1.0a

This implementation uses **OAuth 2.0 with PKCE** (Proof Key for Code Exchange), which is:
- ✅ More secure (PKCE prevents authorization code interception)
- ✅ Simpler for web apps
- ✅ Recommended by Twitter for new apps

**Note:** If you have existing OAuth 1.0a credentials (Consumer Key/Secret), you'll need to create OAuth 2.0 credentials separately in the Twitter Developer Portal.

## Testing

1. Go to your app's settings page
2. Click "Connect Twitter"
3. You should be redirected to Twitter's authorization page
4. After approving, you should be redirected back to your app
5. Check that Twitter is now connected in your settings
6. Try accessing Twitter analytics to verify it works

## Production Deployment

When deploying to production:

1. Update `PUBLIC_DOMAIN` in `.env` to your production domain
2. Add your production redirect URI to Twitter app settings:
   ```
   https://yourdomain.com/socialanywhere/social-media/twitter/callback
   ```
3. Make sure your production server is accessible via HTTPS
4. Update `USE_HTTPS=true` in `.env` if using HTTPS
5. Update `TWITTER_REDIRECT_URI` in `.env` to match production URL

## Support

If you continue to have issues:
1. Check server logs for detailed error messages
2. Verify all environment variables are set correctly
3. Make sure your Twitter app is set to "Web App" type
4. Ensure redirect URI matches exactly (no trailing slashes, correct protocol)
5. Verify you're using OAuth 2.0 credentials (not OAuth 1.0a)

