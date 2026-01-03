# 🔗 LinkedIn Integration Setup Instructions

## ✅ **Production URL Configuration**

Your app is running at: **`https://agentanywhere.ai/socialanywhere/login`**

The LinkedIn OAuth redirect URI is automatically configured as:
**`https://agentanywhere.ai/socialanywhere/social-media/linkedin/callback`**

---

## 📋 **Step-by-Step Setup**

### **1. Create LinkedIn App**

1. Go to https://www.linkedin.com/developers/apps
2. Click **"Create app"**
3. Fill in app details:
   - **App name:** Social Anywhere (or your preferred name)
   - **LinkedIn Page:** Select your LinkedIn page (optional)
   - **Privacy Policy URL:** Your privacy policy URL
   - **App logo:** Upload your app logo (optional)

### **2. Configure OAuth Settings**

1. In your LinkedIn app, go to **"Auth"** tab
2. Under **"Redirect URLs"**, add:
   ```
   https://agentanywhere.ai/socialanywhere/social-media/linkedin/callback
   ```
3. Also add for local testing (optional):
   ```
   http://localhost:8000/socialanywhere/social-media/linkedin/callback
   ```

### **3. Request API Products**

1. Go to **"Products"** tab
2. Request these products:
   - ✅ **Sign In with LinkedIn using OpenID Connect** (for authentication)
   - ✅ **Share on LinkedIn** (for posting content)
3. Wait for approval (usually instant for basic products)

### **4. Get Credentials**

1. Go to **"Auth"** tab
2. Copy:
   - **Client ID** (e.g., `86abcdefghijklmnop`)
   - **Client Secret** (e.g., `GOCSPX-abcdefghijklmnop`)

### **5. Configure Environment Variables**

Add to your `.env` file:

```env
# LinkedIn Integration
LINKEDIN_CLIENT_ID=your_client_id_here
LINKEDIN_CLIENT_SECRET=your_client_secret_here
LINKEDIN_ACCESS_TOKEN=
LINKEDIN_REFRESH_TOKEN=

# Domain Configuration (already set)
PUBLIC_DOMAIN=agentanywhere.ai
USE_HTTPS=true
```

### **6. Add LinkedIn Icon**

1. Download LinkedIn icon: https://brand.linkedin.com/content/dam/me/brand/en-us/brand-home/logos/In-Blue-Logo.png.ee65001.png
2. Resize to 64x64 pixels
3. Save as `public/icons/linkedin.png`

Or use this command to download:
```bash
cd public/icons
curl -o linkedin.png "https://brand.linkedin.com/content/dam/me/brand/en-us/brand-home/logos/In-Blue-Logo.png.ee65001.png"
# Then resize to 64x64 if needed
```

### **7. Rebuild and Deploy**

```bash
# Rebuild containers
docker-compose build

# Restart services
docker-compose up -d

# Check logs
docker logs social-media-agent --tail 50
```

---

## 🧪 **Testing**

### **1. Test OAuth Connection**

1. Go to: `https://agentanywhere.ai/socialanywhere/settings`
2. Find **LinkedIn** card
3. Click **"Connect"** button
4. You should be redirected to LinkedIn authorization page
5. Authorize the app
6. You should be redirected back to Settings page
7. LinkedIn status should show **"Active"** ✅

### **2. Test Posting**

1. Go to: `https://agentanywhere.ai/socialanywhere/create-campaign`
2. Create a campaign
3. Select **LinkedIn** as platform
4. Generate and schedule a post
5. Verify post appears on your LinkedIn profile

### **3. Check Status**

```bash
# Check LinkedIn service status
curl https://agentanywhere.ai/socialanywhere/api/linkedin/status
```

Expected response:
```json
{
  "success": true,
  "status": {
    "status": "connected",
    "message": "LinkedIn service is ready"
  }
}
```

---

## 🔍 **Troubleshooting**

### **Issue: "Redirect URI mismatch"**

**Solution:**
- Verify redirect URI in LinkedIn app exactly matches: `https://agentanywhere.ai/socialanywhere/social-media/linkedin/callback`
- Check for trailing slashes or typos
- Wait a few minutes after updating (LinkedIn may cache)

### **Issue: "Invalid client_id"**

**Solution:**
- Verify `LINKEDIN_CLIENT_ID` in `.env` file
- Check for extra spaces or quotes
- Restart Docker containers after updating `.env`

### **Issue: "Access token expired"**

**Solution:**
- Re-authenticate by clicking "Connect" again in Settings
- Token will be automatically refreshed if refresh token is available
- For programmatic refresh tokens, you may need Marketing Developer Platform (MDP) approval

### **Issue: LinkedIn icon not showing**

**Solution:**
- Verify `public/icons/linkedin.png` exists
- Check file permissions
- Clear browser cache
- Verify icon is 64x64 pixels

---

## 📝 **Important Notes**

1. **Redirect URI must match exactly** - LinkedIn is very strict about this
2. **HTTPS required for production** - LinkedIn OAuth requires HTTPS in production
3. **Scopes** - Current implementation uses:
   - `openid` - For authentication
   - `profile` - For user profile info
   - `w_member_social` - For posting on behalf of user
4. **Refresh Tokens** - By default, LinkedIn doesn't provide refresh tokens. You need Marketing Developer Platform (MDP) approval for programmatic refresh tokens.

---

## 🎯 **Production URL Summary**

- **App URL:** `https://agentanywhere.ai/socialanywhere/login`
- **Settings URL:** `https://agentanywhere.ai/socialanywhere/settings`
- **LinkedIn Callback:** `https://agentanywhere.ai/socialanywhere/social-media/linkedin/callback`
- **API Status:** `https://agentanywhere.ai/socialanywhere/api/linkedin/status`

---

## ✅ **Verification Checklist**

- [ ] LinkedIn app created at https://www.linkedin.com/developers/apps
- [ ] Redirect URI added: `https://agentanywhere.ai/socialanywhere/social-media/linkedin/callback`
- [ ] API products requested: Sign In with LinkedIn, Share on LinkedIn
- [ ] Client ID and Client Secret copied
- [ ] Environment variables set in `.env` file
- [ ] LinkedIn icon added to `public/icons/linkedin.png`
- [ ] Docker containers rebuilt and restarted
- [ ] OAuth flow tested in Settings page
- [ ] Posting tested via Create Campaign
- [ ] Status endpoint returns "connected"

---

## 🚀 **Ready to Use!**

Once all steps are complete, LinkedIn integration will work seamlessly with your production app at `https://agentanywhere.ai/socialanywhere/login`!

The dynamic OAuth redirect URI automatically detects your domain, so it works in both production and local development environments.

