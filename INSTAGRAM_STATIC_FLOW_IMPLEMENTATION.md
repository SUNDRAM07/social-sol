# Instagram Static Credential Flow - Implementation Summary

## Overview
Instagram has been converted from OAuth dynamic flow to a **static credential entry** system where users manually enter their Instagram Business Account credentials.

## What Changed

### 1. Backend Changes

#### `server/social_media_routes.py`
- **OAuth flow disabled**: Commented out the entire `/instagram/callback` endpoint and OAuth authorization flow
- **Static credential endpoint**: Updated `/instagram/select-account` POST endpoint to:
  - Accept manual credentials (account_id, access_token, username)
  - Validate credentials against Instagram Graph API
  - Save to `social_media_accounts` database table
  - Support both new accounts and credential updates

#### `server/instagram_adapter.py`
- Updated constructor to accept `access_token` and `instagram_account_id` parameters
- Credentials can now be passed per-user instead of relying only on environment variables
- Backward compatible with env vars as fallback

#### `server/instagram_service.py`
- **Major refactor**: Service now accepts `user_id` parameter
- Added `_ensure_adapter()` async method to load credentials from database per user
- All methods converted to async to support database lookups
- Credentials loaded on-demand from `social_media_accounts` table
- Added `get_instagram_service(user_id)` helper function

#### Database Schema
- Uses existing `social_media_accounts` table (already supports Instagram)
- Credentials stored per user with fields:
  - `user_id`: Owner of the account
  - `platform`: 'instagram'
  - `account_id`: Instagram Business Account ID
  - `access_token`: Graph API access token
  - `username`: Instagram username (optional)
  - `metadata`: Additional info (account_type, media_count, source)
  - `is_active`: Whether account is currently active
  - `expires_at`: NULL for static credentials (no expiration)

### 2. Frontend Changes

#### `src/components/ui/SocialMediaConnectionModal.jsx`
- Added Instagram configuration to `PLATFORM_CONFIGS`:
  - Fields: Instagram Business Account ID, Access Token, Username (optional)
  - Visual: Instagram gradient color scheme
  - Description with link to Facebook Developer docs

#### `src/pages/Settings.jsx`
- Updated `handleSocialMediaConnect()`:
  - Instagram now opens credential entry modal instead of OAuth popup
  - Other platforms (Facebook, Twitter, Reddit) still use OAuth
- Added `handleSaveInstagramCredentials()`:
  - Calls `/social-media/instagram/select-account` endpoint
  - Validates and saves credentials
  - Shows success/error toasts
  - Refreshes platform status after save
- Renders `SocialMediaConnectionModal` for Instagram credential entry

## How It Works

### User Flow:
1. User clicks "Connect" on Instagram in Settings
2. Modal opens asking for:
   - Instagram Business Account ID
   - Access Token (from Facebook Graph API)
   - Username (optional)
3. User enters credentials and clicks "Save"
4. Frontend validates fields and sends to backend
5. Backend verifies credentials with Instagram Graph API
6. If valid, saves to database under user's account
7. Success message shown, modal closes
8. Instagram shows as connected in Settings

### Backend Flow:
1. `/instagram/select-account` receives credentials
2. Validates required fields (user_id, account_id, access_token)
3. Tests credentials against Instagram Graph API:
   - Calls `https://graph.facebook.com/v21.0/{account_id}`
   - Checks for valid response with username, account_type, etc.
4. Saves or updates record in `social_media_accounts` table
5. Deactivates any other Instagram accounts for this user
6. Returns success with account details

### Posting Flow:
1. When posting to Instagram, service needs `user_id`
2. `InstagramService` initialized with `user_id`
3. Service loads credentials from database automatically
4. Uses credentials to authenticate with Instagram Graph API
5. Posts content using same adapter as before

## Files Modified

### Backend
- `server/social_media_routes.py` - Disabled OAuth, updated select-account endpoint
- `server/instagram_adapter.py` - Added credential parameters
- `server/instagram_service.py` - Async user-scoped credential loading

### Frontend
- `src/components/ui/SocialMediaConnectionModal.jsx` - Added Instagram config
- `src/pages/Settings.jsx` - Modal handler and credential save logic

### Database
- No schema changes needed (uses existing `social_media_accounts` table)

## Benefits

1. **No OAuth complexity**: No callback URLs, state management, or app review needed
2. **Simpler setup**: Users just copy/paste credentials from Facebook Developer Console
3. **Per-user credentials**: Each user has their own Instagram account credentials in DB
4. **Better control**: Users can manually update/rotate tokens
5. **No expiration hassles**: Long-lived tokens don't auto-refresh, user manages them

## Getting Instagram Credentials

Users need to:
1. Go to Facebook Developer Console
2. Create/select an app with Instagram Graph API access
3. Get an Instagram Business Account ID
4. Generate a long-lived access token
5. Enter these values in the modal when connecting

## Testing

To test the static flow:
1. Go to Settings page
2. Click "Connect" on Instagram
3. Enter valid Instagram Business Account ID and Access Token
4. Click "Save"
5. Verify Instagram shows as connected
6. Try creating a campaign and posting to Instagram
7. Verify post appears on Instagram

## Migration Notes

- Old OAuth-based Instagram connections will continue to work if already in database
- New connections use static credential entry
- No data migration needed - both use same `social_media_accounts` table
- OAuth endpoints are commented out, not deleted, for easy rollback if needed

## Future Enhancements

- Add "Test Connection" button in modal before saving
- Show token expiration date if available
- Add instructions/wizard for getting credentials
- Support multiple Instagram accounts per user
- Token refresh reminders if expiration date is set


