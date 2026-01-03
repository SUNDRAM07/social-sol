# Testing check-connections Endpoint Locally

## Endpoint Details
- **URL**: `http://localhost:8000/socialanywhere/social-media/check-connections`
- **Method**: `GET`
- **Auth Required**: Yes (Bearer token)

## How to Test

### 1. Get Your Auth Token

First, log in to the application and get your JWT token:

**Option A: From Browser Console**
1. Open your browser's Developer Tools (F12)
2. Go to Application/Storage → Local Storage
3. Find `auth-storage` key
4. Copy the `token` value from the JSON

**Option B: From Network Tab**
1. Open Developer Tools → Network tab
2. Log in to the application
3. Find any API request
4. Look at the `Authorization` header
5. Copy the token (without "Bearer " prefix)

### 2. Test with cURL

```bash
# Replace YOUR_TOKEN_HERE with your actual JWT token
curl -X GET "http://localhost:8000/socialanywhere/social-media/check-connections" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json"
```

### 3. Test with Browser Console

Open browser console and run:

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

### 4. Test with Postman/Insomnia

1. Create a new GET request
2. URL: `http://localhost:8000/socialanywhere/social-media/check-connections`
3. Headers:
   - `Authorization`: `Bearer YOUR_TOKEN_HERE`
   - `Content-Type`: `application/json`

### 5. Expected Response

**If user has connections:**
```json
{
  "has_connections": true,
  "connected_platforms": ["facebook", "instagram"],
  "total_connections": 2,
  "user_id": "uuid-here",
  "user_email": "user@example.com"
}
```

**If user has no connections:**
```json
{
  "has_connections": false,
  "connected_platforms": [],
  "total_connections": 0,
  "user_id": "uuid-here",
  "user_email": "user@example.com"
}
```

**If authentication fails:**
```json
{
  "has_connections": false,
  "connected_platforms": [],
  "error": "error message here"
}
```

## Check Server Logs

The endpoint now logs detailed information. Check your server console for:
- `🔍 check-connections endpoint called`
- `✅ User authenticated: email (ID: uuid)`
- `Found X social media accounts`
- `Connected platforms: [...]`
- `Has connections: true/false`

## Troubleshooting

1. **401 Unauthorized**: Make sure your token is valid and not expired
2. **404 Not Found**: Check that the server is running on port 8000
3. **CORS Error**: Make sure you're testing from the same origin or CORS is configured
4. **Empty response**: Check server logs for errors

## Quick Test Script

Save this as `test_check_connections.js` and run with Node.js:

```javascript
const fetch = require('node-fetch');

// Replace with your actual token
const token = 'YOUR_TOKEN_HERE';

fetch('http://localhost:8000/socialanywhere/social-media/check-connections', {
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  }
})
.then(res => res.json())
.then(data => {
  console.log('\n=== Response ===');
  console.log(JSON.stringify(data, null, 2));
  console.log('\n=== Summary ===');
  console.log(`Has connections: ${data.has_connections}`);
  console.log(`Platforms: ${data.connected_platforms.join(', ') || 'None'}`);
  console.log(`Total: ${data.total_connections}`);
})
.catch(err => console.error('Error:', err));
```

Run with: `node test_check_connections.js`

