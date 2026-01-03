# Reddit OAuth Setup Instructions

## Step 1: Create a Reddit App

1. Go to https://www.reddit.com/prefs/apps
2. Scroll down and click **"create another app..."** or **"create app"**
3. Fill in the form:
   - **Name**: Your app name (e.g., "SocialAnywhere AI")
   - **App type**: Select **"web app"**
   - **Description**: Brief description of your app
   - **About URL**: Your website URL (optional)
   - **Redirect URI**: ⚠️ **IMPORTANT** - See Step 2 below

## Step 2: Add Redirect URI

**You MUST add this EXACT redirect URI to your Reddit app:**

### For Local Development (localhost):
```
http://localhost:8000/socialanywhere/social-media/reddit/callback
```

### For Production:
If you're deploying to a production domain, add:
```
https://yourdomain.com/socialanywhere/social-media/reddit/callback
```

**How to add:**
1. In the Reddit app creation/edit page, find the **"redirect uri"** field
2. Paste the exact URL above (for localhost or your production domain)
3. Click **"create app"** or **"update"**

⚠️ **IMPORTANT NOTES:**
- The redirect URI must match **EXACTLY** (including `http://` vs `https://`, port number, and path)
- Reddit is case-sensitive for redirect URIs
- You can add multiple redirect URIs (one per line) if you need both localhost and production
- No trailing slashes allowed

## Step 3: Get Your Credentials

After creating the app, you'll see:
- **Client ID**: The string under your app name (looks like: `3NFlIcb7GV-8upi42FG_4g`)
- **Client Secret**: The "secret" field (looks like: `abc123xyz...`)

## Step 4: Configure Environment Variables

Add these to your `.env` file:

```env
REDDIT_CLIENT_ID=your_client_id_here
REDDIT_CLIENT_SECRET=your_client_secret_here
REDDIT_REDIRECT_URI=http://localhost:8000/socialanywhere/social-media/reddit/callback
REDDIT_USER_AGENT=SocialMediaAgent/1.0 by u/YourRedditUsername
PUBLIC_DOMAIN=localhost:8000
```

**Notes:**
- `REDDIT_USER_AGENT`: Format is `AppName/Version by u/YourRedditUsername`
  - Replace `YourRedditUsername` with your actual Reddit username
  - This is required by Reddit API
- `REDDIT_REDIRECT_URI`: Only set this if you want to override the default
- `PUBLIC_DOMAIN`: Set to your domain (e.g., `localhost:8000` for local, `yourdomain.com` for production)

## Step 5: Verify Setup

1. Start your server
2. Try connecting Reddit from your app
3. Check server logs - you should see:
   ```
   🔗 Reddit OAuth Redirect URI: http://localhost:8000/socialanywhere/social-media/reddit/callback
   📝 Make sure this EXACT URL is registered in your Reddit app settings
   ```

## Common Errors and Solutions

### Error: "invalid redirect_uri parameter"

**Cause:** The redirect URI in your Reddit app settings doesn't match what your app is sending.

**Solution:**
1. Check your server logs for the exact redirect URI being used
2. Go to https://www.reddit.com/prefs/apps
3. Click on your app
4. Make sure the redirect URI field contains the EXACT URL from the logs
5. Save and try again

### Error: "invalid_client"

**Cause:** Client ID or Client Secret is incorrect.

**Solution:**
1. Verify `REDDIT_CLIENT_ID` and `REDDIT_CLIENT_SECRET` in your `.env` file
2. Make sure there are no extra spaces or quotes
3. Get fresh credentials from Reddit if needed

### Error: "access_denied"

**Cause:** User denied permission or app doesn't have required scopes.

**Solution:**
1. Make sure your app type is set to "web app" (not "script" or "installed")
2. User must approve all requested permissions

## Testing

1. Go to your app's settings page
2. Click "Connect Reddit"
3. You should be redirected to Reddit's authorization page
4. After approving, you should be redirected back to your app
5. Check that Reddit is now connected in your settings

## Production Deployment

When deploying to production:

1. Update `PUBLIC_DOMAIN` in `.env` to your production domain
2. Add your production redirect URI to Reddit app settings:
   ```
   https://yourdomain.com/socialanywhere/social-media/reddit/callback
   ```
3. Make sure your production server is accessible via HTTPS
4. Update `USE_HTTPS=true` in `.env` if using HTTPS

## Support

If you continue to have issues:
1. Check server logs for detailed error messages
2. Verify all environment variables are set correctly
3. Make sure your Reddit app is set to "web app" type
4. Ensure redirect URI matches exactly (no trailing slashes, correct protocol)

