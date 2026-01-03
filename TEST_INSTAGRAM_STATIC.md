# Testing Instagram Static Credential Flow

## Prerequisites
1. Instagram Business Account
2. Facebook Developer App with Instagram Graph API access
3. Long-lived access token
4. Instagram Business Account ID

## Get Your Credentials

### Step 1: Get Instagram Business Account ID
```bash
# Using Graph API Explorer or curl:
curl -X GET "https://graph.facebook.com/v21.0/me/accounts?access_token=YOUR_USER_TOKEN"

# Find your Facebook Page, then get Instagram Business Account:
curl -X GET "https://graph.facebook.com/v21.0/PAGE_ID?fields=instagram_business_account&access_token=YOUR_TOKEN"
```

### Step 2: Generate Long-Lived Access Token
```bash
# Exchange short-lived token for long-lived token (60 days):
curl -X GET "https://graph.facebook.com/v21.0/oauth/access_token?grant_type=fb_exchange_token&client_id=YOUR_APP_ID&client_secret=YOUR_APP_SECRET&fb_exchange_token=SHORT_LIVED_TOKEN"
```

## Manual Testing via API

### Test 1: Save Instagram Credentials
```bash
curl -X POST "http://localhost:8000/socialanywhere/social-media/instagram/select-account" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "demo_user_123",
    "account_id": "YOUR_INSTAGRAM_BUSINESS_ACCOUNT_ID",
    "access_token": "YOUR_LONG_LIVED_ACCESS_TOKEN",
    "username": "your_instagram_handle"
  }'
```

Expected Response:
```json
{
  "success": true,
  "message": "Instagram account 'your_instagram_handle' connected successfully.",
  "connected": true,
  "details": {
    "account_id": "...",
    "username": "your_instagram_handle"
  }
}
```

### Test 2: Check Connection Status
```bash
curl "http://localhost:8000/socialanywhere/social-media/instagram/status"
```

Expected Response:
```json
{
  "connected": true,
  "has_credentials": true,
  "platform": "instagram",
  "last_checked": "2024-01-01T12:00:00Z",
  "details": {
    "accounts": [...],
    "test_first_account": true,
    "account_count": 1
  }
}
```

### Test 3: Verify in Database
```sql
SELECT 
  platform, 
  account_id, 
  username, 
  is_active,
  created_at,
  metadata
FROM social_media_accounts
WHERE platform = 'instagram' AND user_id = 'demo_user_123';
```

## UI Testing

### Test 1: Connect Instagram
1. Navigate to Settings page: `http://localhost:8000/socialanywhere/settings`
2. Find Instagram in Social Media Connections section
3. Click "Connect" button
4. Modal should open with fields:
   - Instagram Business Account ID
   - Access Token
   - Username (optional)
5. Enter your credentials
6. Click "Save"
7. Should see success toast
8. Instagram should show as "Connected" with green checkmark

### Test 2: View Connected Account
1. After connecting, Settings should display:
   - ✓ Connected status
   - Your Instagram username
   - Account details
   - "Disconnect" button

### Test 3: Disconnect and Reconnect
1. Click "Disconnect" button
2. Confirm disconnection
3. Instagram should show "Not Connected"
4. Click "Connect" again
5. Enter credentials (can be same or different)
6. Should connect successfully

### Test 4: Post to Instagram
1. Go to Create Campaign page
2. Create a new post
3. Select Instagram as platform
4. Add image and caption
5. Schedule or publish immediately
6. Verify post appears on Instagram
7. Check database for post record

## Troubleshooting

### Error: "Invalid Instagram credentials"
- Verify Account ID is correct
- Check that Access Token hasn't expired
- Ensure token has `instagram_business_content_publish` scope

### Error: "Instagram API error: ..."
- Check if Instagram Business Account is set up correctly
- Verify Facebook Page is connected to Instagram account
- Ensure app has necessary permissions

### Error: "Failed to save Instagram account to database"
- Check database connection
- Verify `social_media_accounts` table exists
- Check user_id is valid

### Modal doesn't open
- Check browser console for errors
- Verify `SocialMediaConnectionModal` is imported
- Check that modal state is properly managed

## Verification Checklist

- [ ] Modal opens when clicking "Connect" on Instagram
- [ ] All required fields shown (Account ID, Access Token)
- [ ] Optional username field visible
- [ ] Validation shows errors for empty required fields
- [ ] API call succeeds with valid credentials
- [ ] Success toast appears after saving
- [ ] Modal closes after successful save
- [ ] Settings page shows Instagram as connected
- [ ] Username displayed correctly
- [ ] Can disconnect and reconnect
- [ ] Credentials saved in database
- [ ] Can post to Instagram using saved credentials
- [ ] Analytics still work with static credentials

## Notes

- Only one Instagram account per user is active at a time
- Tokens don't auto-refresh (user manages token rotation)
- Credentials stored securely in database
- Each user has their own Instagram credentials
- No OAuth callback URLs or app review needed


