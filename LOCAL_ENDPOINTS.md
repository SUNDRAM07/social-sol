# Local API Endpoints Reference

## Base URL
```
http://localhost:8000/socialanywhere
```

## Authentication Endpoints

### POST `/auth/google`
**Description:** Authenticate with Google OAuth token
```bash
curl -X POST "http://localhost:8000/socialanywhere/auth/google" \
  -H "Content-Type: application/json" \
  -d '{"token": "YOUR_GOOGLE_TOKEN"}'
```

### GET `/auth/me`
**Description:** Get current authenticated user
```bash
curl -X GET "http://localhost:8000/socialanywhere/auth/me" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### POST `/auth/logout`
**Description:** Logout user
```bash
curl -X POST "http://localhost:8000/socialanywhere/auth/logout"
```

### DELETE `/auth/delete-account`
**Description:** Delete user account
```bash
curl -X DELETE "http://localhost:8000/socialanywhere/auth/delete-account" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

---

## Social Media Platform Endpoints

### GET `/social-media/check-connections`
**Description:** Check if user has any connected platforms
```bash
curl -X GET "http://localhost:8000/socialanywhere/social-media/check-connections" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json"
```

**Response:**
```json
{
  "has_connections": true,
  "connected_platforms": ["facebook", "instagram"],
  "total_connections": 2
}
```

### GET `/social-media/status`
**Description:** Get connection status for all platforms
```bash
curl -X GET "http://localhost:8000/socialanywhere/social-media/status" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### GET `/social-media/{platform}/status`
**Description:** Get connection status for a specific platform
**Platforms:** `facebook`, `instagram`, `twitter`, `reddit`, `linkedin`
```bash
# Example: Check Facebook status
curl -X GET "http://localhost:8000/socialanywhere/social-media/facebook/status" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### GET `/social-media/platforms`
**Description:** Get list of supported platforms
```bash
curl -X GET "http://localhost:8000/socialanywhere/social-media/platforms"
```

### POST `/social-media/{platform}/connect`
**Description:** Connect a platform
```bash
curl -X POST "http://localhost:8000/socialanywhere/social-media/facebook/connect" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"credentials": {}}'
```

### POST `/social-media/{platform}/disconnect`
**Description:** Disconnect a platform
```bash
curl -X POST "http://localhost:8000/socialanywhere/social-media/facebook/disconnect" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### OAuth Callbacks
- `GET /social-media/facebook/callback`
- `GET /social-media/instagram/callback`
- `GET /social-media/twitter/callback`
- `GET /social-media/reddit/callback`
- `GET /social-media/linkedin/callback`

---

## Post Management Endpoints

### POST `/generate-post`
**Description:** Generate a single post
```bash
curl -X POST "http://localhost:8000/socialanywhere/generate-post" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Post description",
    "caption_provider": "groq",
    "image_provider": "stability_ai",
    "platforms": ["instagram", "facebook"]
  }'
```

### POST `/generate-batch`
**Description:** Generate multiple posts
```bash
curl -X POST "http://localhost:8000/socialanywhere/generate-batch" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Campaign description",
    "num_posts": 10,
    "days_duration": 7,
    "caption_provider": "groq",
    "image_provider": "stability_ai",
    "platforms": ["instagram", "facebook"]
  }'
```

### GET `/api/posts`
**Description:** Get all posts
```bash
curl -X GET "http://localhost:8000/socialanywhere/api/posts?limit=50" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### POST `/api/posts`
**Description:** Create a new post
```bash
curl -X POST "http://localhost:8000/socialanywhere/api/posts" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "original_description": "Post description",
    "platforms": ["instagram"]
  }'
```

### GET `/api/posts/{post_id}`
**Description:** Get a specific post
```bash
curl -X GET "http://localhost:8000/socialanywhere/api/posts/POST_ID" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### PUT `/api/posts/{post_id}`
**Description:** Update a post
```bash
curl -X PUT "http://localhost:8000/socialanywhere/api/posts/POST_ID" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"caption": "Updated caption"}'
```

### DELETE `/api/posts/{post_id}`
**Description:** Delete a post
```bash
curl -X DELETE "http://localhost:8000/socialanywhere/api/posts/POST_ID" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### GET `/api/scheduled-posts`
**Description:** Get all scheduled posts
```bash
curl -X GET "http://localhost:8000/socialanywhere/api/scheduled-posts" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

---

## Calendar Endpoints

### GET `/api/calendar/events`
**Description:** Get calendar events
```bash
curl -X GET "http://localhost:8000/socialanywhere/api/calendar/events" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### POST `/api/calendar/events`
**Description:** Create a calendar event
```bash
curl -X POST "http://localhost:8000/socialanywhere/api/calendar/events" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Event title",
    "start_time": "2024-01-01T10:00:00Z",
    "end_time": "2024-01-01T11:00:00Z"
  }'
```

---

## Google Integration Endpoints

### GET `/google/status`
**Description:** Check Google Drive/Calendar connection status
```bash
curl -X GET "http://localhost:8000/socialanywhere/google/status"
```

### GET `/google/connect`
**Description:** Connect Google account
```bash
curl -X GET "http://localhost:8000/socialanywhere/google/connect"
```

### POST `/google-drive/save-campaign`
**Description:** Save campaign to Google Drive
```bash
curl -X POST "http://localhost:8000/socialanywhere/google-drive/save-campaign" \
  -H "Content-Type: application/json" \
  -d '{"campaign_data": {}}'
```

### POST `/google-calendar/create-event`
**Description:** Create Google Calendar event
```bash
curl -X POST "http://localhost:8000/socialanywhere/google-calendar/create-event" \
  -H "Content-Type: application/json" \
  -d '{"event_data": {}}'
```

---

## Analytics Endpoints

### GET `/api/analytics/overview`
**Description:** Get analytics overview
```bash
curl -X GET "http://localhost:8000/socialanywhere/api/analytics/overview"
```

### GET `/api/analytics/posts`
**Description:** Get analytics for posts
```bash
curl -X GET "http://localhost:8000/socialanywhere/api/analytics/posts?limit=10"
```

### GET `/api/analytics/followers`
**Description:** Get followers count
```bash
curl -X GET "http://localhost:8000/socialanywhere/api/analytics/followers"
```

---

## Idea Generator Endpoints

### POST `/api/idea-generator/generate`
**Description:** Generate content ideas
```bash
curl -X POST "http://localhost:8000/socialanywhere/api/idea-generator/generate" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Topic description",
    "platforms": ["instagram"]
  }'
```

---

## Health & Utility Endpoints

### GET `/health`
**Description:** Health check endpoint
```bash
curl -X GET "http://localhost:8000/socialanywhere/health"
```

### GET `/api/usage-stats`
**Description:** Get API usage statistics
```bash
curl -X GET "http://localhost:8000/socialanywhere/api/usage-stats" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

---

## Testing the check-connections Endpoint

### Method 1: Using cURL
```bash
# First, get your JWT token from browser localStorage
# Then run:
curl -X GET "http://localhost:8000/socialanywhere/social-media/check-connections" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json"
```

### Method 2: Using Browser Console
```javascript
// Get token from localStorage
const authData = localStorage.getItem('auth-storage');
const parsed = JSON.parse(authData);
const token = parsed.state.token;

// Make request
fetch('http://localhost:8000/socialanywhere/social-media/check-connections', {
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  }
})
.then(res => res.json())
.then(data => {
  console.log('Response:', data);
  console.log('Has connections:', data.has_connections);
  console.log('Connected platforms:', data.connected_platforms);
})
.catch(err => console.error('Error:', err));
```

### Method 3: Using Postman/Insomnia
1. Create a new GET request
2. URL: `http://localhost:8000/socialanywhere/social-media/check-connections`
3. Headers:
   - `Authorization`: `Bearer YOUR_JWT_TOKEN`
   - `Content-Type`: `application/json`

---

## Quick Test Script

Save as `test_local_endpoints.sh`:

```bash
#!/bin/bash

# Replace with your actual JWT token
TOKEN="YOUR_JWT_TOKEN"
BASE_URL="http://localhost:8000/socialanywhere"

echo "Testing check-connections endpoint..."
curl -X GET "${BASE_URL}/social-media/check-connections" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  | jq .

echo -e "\n\nTesting health endpoint..."
curl -X GET "${BASE_URL}/health" | jq .

echo -e "\n\nTesting platforms endpoint..."
curl -X GET "${BASE_URL}/social-media/platforms" | jq .
```

Run with: `chmod +x test_local_endpoints.sh && ./test_local_endpoints.sh`

---

## Notes

- All endpoints require authentication except:
  - `/health`
  - `/social-media/platforms`
  - OAuth callback endpoints
  - Public endpoints

- Replace `YOUR_JWT_TOKEN` with your actual JWT token from localStorage
- Replace `YOUR_GOOGLE_TOKEN` with your Google OAuth token
- Replace `POST_ID` with actual post UUID
- All timestamps should be in ISO 8601 format

