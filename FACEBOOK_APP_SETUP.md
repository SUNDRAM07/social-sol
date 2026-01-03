# 🔗 Facebook & Instagram App Configuration Guide

## ⚠️ **Error: "The domain of this URL isn't included in the app's domains"**

This error occurs when your redirect URI domain is not configured in your Facebook App settings. Follow the steps below to fix it.

---

## 📋 **Step-by-Step Configuration**

### **1. Get Your Redirect URI**

Your redirect URIs are automatically generated based on your `PUBLIC_DOMAIN` environment variable:

**For Facebook:**
```
https://agentanywhere.ai/socialanywhere/social-media/facebook/callback
```

**For Instagram:**
```
https://agentanywhere.ai/socialanywhere/social-media/instagram/callback
```

**Note:** If you're using a different domain, check your `.env` file for `PUBLIC_DOMAIN` value.

---

### **2. Configure Facebook App Settings**

1. Go to [Facebook Developers](https://developers.facebook.com/apps/)
2. Select your app (or create a new one)
3. Go to **Settings** → **Basic**

#### **A. Add App Domain**

In the **App Domains** field, add:
```
agentanywhere.ai
```

**Important:** 
- Add only the domain (without `http://` or `https://`)
- Add only the root domain (not subdomains unless needed)
- For localhost development, you can't add `localhost` - use ngrok or deploy to a public server

#### **B. Add Valid OAuth Redirect URIs**

Scroll down to **Valid OAuth Redirect URIs** and click **Add URI**, then add:

```
https://agentanywhere.ai/socialanywhere/social-media/facebook/callback
https://agentanywhere.ai/socialanywhere/social-media/instagram/callback
```

**For localhost development (if using ngrok):**
```
https://your-ngrok-url.ngrok.io/socialanywhere/social-media/facebook/callback
https://your-ngrok-url.ngrok.io/socialanywhere/social-media/instagram/callback
```

#### **C. Save Changes**

Click **Save Changes** at the bottom of the page.

---

### **3. Configure Site URL (Optional but Recommended)**

In **Settings** → **Basic**, find **Site URL** and add:
```
https://agentanywhere.ai
```

---

### **4. Verify Environment Variables**

Make sure your `.env` file has:

```env
# Domain Configuration
PUBLIC_DOMAIN=agentanywhere.ai
USE_HTTPS=true

# Facebook App Credentials
FACEBOOK_APP_ID=your_app_id_here
FACEBOOK_APP_SECRET=your_app_secret_here
```

---

### **5. For Localhost Development**

If you're testing locally, you have two options:

#### **Option A: Use ngrok (Recommended)**

1. Install ngrok: https://ngrok.com/
2. Run: `ngrok http 8000`
3. Copy the HTTPS URL (e.g., `https://abc123.ngrok.io`)
4. Set in `.env`:
   ```env
   PUBLIC_DOMAIN=abc123.ngrok.io
   USE_HTTPS=true
   ```
5. Add the ngrok URL to Facebook App settings as described above

#### **Option B: Use Production Domain**

If you have a production domain, use that for testing. Facebook doesn't allow `localhost` in App Domains.

---

## 🔍 **Troubleshooting**

### **Error: "Invalid redirect_uri"**

- Make sure the redirect URI in your code **exactly matches** what's in Facebook App settings
- Check for trailing slashes (should NOT have one)
- Verify `PUBLIC_DOMAIN` and `USE_HTTPS` are set correctly
- Check server logs for the actual redirect URI being used

### **Error: "App Not Setup"**

- Make sure your Facebook App is in **Development** or **Live** mode
- Verify `FACEBOOK_APP_ID` and `FACEBOOK_APP_SECRET` are correct
- Check that the app has the required permissions enabled

### **Error: "Domain not verified"**

- For production domains, Facebook may require domain verification
- Go to **Settings** → **Basic** → **Add Platform** → **Website**
- Follow the domain verification process

---

## 📝 **Quick Checklist**

- [ ] App Domain added: `agentanywhere.ai`
- [ ] Facebook redirect URI added: `https://agentanywhere.ai/socialanywhere/social-media/facebook/callback`
- [ ] Instagram redirect URI added: `https://agentanywhere.ai/socialanywhere/social-media/instagram/callback`
- [ ] Site URL set: `https://agentanywhere.ai`
- [ ] Environment variables configured in `.env`
- [ ] Changes saved in Facebook App settings
- [ ] App is in Development or Live mode

---

## 🔗 **Useful Links**

- [Facebook App Dashboard](https://developers.facebook.com/apps/)
- [Facebook OAuth Documentation](https://developers.facebook.com/docs/facebook-login/web)
- [Instagram Graph API Setup](https://developers.facebook.com/docs/instagram-api/getting-started)

---

## 💡 **Pro Tips**

1. **Always use HTTPS** in production - Facebook requires it
2. **Test with ngrok first** before deploying to production
3. **Keep redirect URIs consistent** - don't change them after users have connected
4. **Use environment variables** - never hardcode domains in code
5. **Check server logs** - they show the exact redirect URI being used

---

## 🆘 **Still Having Issues?**

1. Check server logs for the exact redirect URI being generated
2. Verify the redirect URI in Facebook App settings matches exactly (case-sensitive)
3. Make sure there are no extra spaces or characters
4. Try removing and re-adding the redirect URI in Facebook App settings
5. Clear browser cache and try again


