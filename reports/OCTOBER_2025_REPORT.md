# MONTHLY TRAINING REPORT - OCTOBER 2025

---

## STUDENT DETAILS

| Field                    | Details                                                         |
| ------------------------ | --------------------------------------------------------------- |
| **Name**                 | Sundram Mahajan                                                 |
| **Registration No.**     | 12222340                                                        |
| **Programme**            | B.Tech Computer Science Engineering                             |
| **Month/Year**           | October 2025                                                    |
| **Project Title**        | SocialAnywhere.AI - AI-Powered Social Media Management Platform |
| **Company/Organization** | Shephertz Technologies                                          |

---

## 1. INTRODUCTION

October was a pivotal month focused on integrating social media platforms. Successfully connected Twitter/X and LinkedIn. Began the Meta (Facebook/Instagram) integration process but encountered significant challenges with their app review system. Also integrated Reddit as a bonus platform. Multiple UI improvements were made to accommodate new features.

---

## 2. OBJECTIVES FOR THE MONTH

1. Complete Twitter/X OAuth and posting integration
2. Implement LinkedIn OAuth and posting
3. Begin Meta (Facebook/Instagram) integration
4. Add Reddit integration
5. Build post creation interface
6. Implement media upload functionality

---

## 3. WORK ACCOMPLISHED

### 3.1 Twitter/X Integration

#### Developer Account Setup
- Applied for Twitter Developer Account
- Submitted application explaining use case
- Received approval after 3 days (faster than expected)
- Generated API keys and Bearer tokens

#### OAuth 2.0 Implementation

**Authorization Flow:**
1. User clicks "Connect Twitter" button
2. Redirected to Twitter authorization page
3. User grants permissions (read, write, offline_access)
4. Callback receives authorization code
5. Exchange code for access token and refresh token
6. Store tokens securely in database

**Scopes Requested:**
| Scope          | Purpose                        |
| -------------- | ------------------------------ |
| tweet.read     | Read user's tweets             |
| tweet.write    | Post tweets on behalf of user  |
| users.read     | Get user profile information   |
| offline.access | Refresh tokens without re-auth |

#### Posting Functionality

**Features Implemented:**
- Text-only tweets (up to 280 characters)
- Tweets with images (up to 4 images)
- Character counter with visual warning
- Media upload to Twitter's media endpoint
- Post scheduling (store in DB, post via scheduler)

**Technical Details:**
- Used Twitter API v2 (latest version)
- Implemented chunked media upload for large files
- Added retry logic for rate limit handling
- Created tweet preview component

#### Twitter Integration Challenges

| Issue          | Impact                         | Resolution                              |
| -------------- | ------------------------------ | --------------------------------------- |
| Rate Limits    | 50 tweets/24hrs on free tier   | Implemented queue system with delays    |
| Media Upload   | Different endpoint than tweets | Separate upload, then attach media_id   |
| Token Refresh  | Tokens expire after 2 hours    | Background job to refresh before expiry |
| Thread Support | Users wanted thread posting    | Added thread creation feature           |

### 3.2 LinkedIn Integration

#### App Registration
- Created LinkedIn Developer Application
- Configured OAuth 2.0 settings
- Requested required permissions (profile, email, posting)

#### OAuth Implementation

**Permissions Required:**
| Permission      | Purpose                |
| --------------- | ---------------------- |
| r_liteprofile   | Basic profile data     |
| r_emailaddress  | User's email           |
| w_member_social | Post on behalf of user |

**Unique LinkedIn Challenges:**

1. **UGC (User Generated Content) Posts:**
   LinkedIn uses a specific UGC format for posts, different from other platforms.

2. **Image Handling:**
   LinkedIn requires registering an upload, uploading to their Azure blob storage, then referencing the asset in the post.

3. **Company Pages vs Personal:**
   Different APIs for posting to personal profile vs company pages.

#### Features Implemented

| Feature            | Status          | Notes                        |
| ------------------ | --------------- | ---------------------------- |
| Personal Post      | ✅ Working       | Text + single image          |
| Multi-image Post   | ✅ Working       | Up to 9 images               |
| Link Preview       | ✅ Working       | Automatic URL card           |
| Company Page Post  | ⏸️ Paused        | Requires additional approval |
| Article Publishing | ❌ Not Available | API deprecated               |

### 3.3 Meta (Facebook/Instagram) Integration - MAJOR CHALLENGES

#### Initial Optimism
Started the Meta integration expecting similar process to Twitter/LinkedIn. Quickly discovered Meta has the most restrictive and complex approval process.

#### App Setup Process

**Step 1: Meta for Developers Account**
- Created developer account at developers.facebook.com
- Set up new application
- Configured basic settings

**Step 2: Required Permissions Identification**

For Facebook posting, we needed:
| Permission            | Type     | Review Required  |
| --------------------- | -------- | ---------------- |
| pages_manage_posts    | Extended | Yes - App Review |
| pages_read_engagement | Extended | Yes - App Review |
| pages_show_list       | Extended | Yes - App Review |
| public_profile        | Standard | No               |
| email                 | Standard | No               |

For Instagram posting:
| Permission                | Type     | Review Required  |
| ------------------------- | -------- | ---------------- |
| instagram_basic           | Extended | Yes - App Review |
| instagram_content_publish | Extended | Yes - App Review |
| instagram_manage_insights | Extended | Yes - App Review |

**Step 3: App Review Submission - First Attempt**

Submitted app for review with:
- Video demonstration of the app
- Written explanation of use case
- Privacy policy URL
- Terms of service URL
- Test user credentials

**Result: REJECTED**

**Rejection Reasons:**
1. "Video demonstration unclear" - They couldn't understand the flow
2. "Need to show complete user journey" - From login to posting
3. "Business verification incomplete" - Needed additional documents

#### Second Submission Attempt

Created more detailed video showing:
- User registration process
- Account connection flow
- Post creation with platform selection
- Scheduling functionality
- How data is used

**Result: REJECTED AGAIN**

**New Rejection Reasons:**
1. "App does not provide unique value" - They said similar apps exist
2. "Insufficient business documentation"
3. "Need to explain data retention policy"

#### Decision Made
After two rejections and 3+ weeks of back-and-forth, decided to:
1. **Continue development** without Meta approval
2. **Document the integration code** so it's ready when approved
3. **Focus on platforms that work** (Twitter, LinkedIn, Reddit)
4. **Resubmit in future** with stronger business case

**Lesson Learned:** Meta's approval process is designed for established businesses, not startups or student projects. This is a known industry problem.

### 3.4 Reddit Integration

#### Why Reddit?
After Meta frustrations, decided to add Reddit as an alternative platform. Reddit has:
- Simple OAuth flow
- Developer-friendly API
- No extensive app review
- Strong communities for content distribution

#### Implementation

**OAuth Scopes:**
| Scope        | Purpose                           |
| ------------ | --------------------------------- |
| identity     | Get user info                     |
| submit       | Post content                      |
| read         | Read subreddits                   |
| mysubreddits | List user's subscribed subreddits |

**Features Built:**
- Connect Reddit account
- View subscribed subreddits
- Post to subreddits (text and link posts)
- Subreddit rules fetching (important for compliance)

**Reddit-Specific Considerations:**
| Feature            | Implementation                         |
| ------------------ | -------------------------------------- |
| Rate Limits        | 60 requests/minute - implemented queue |
| Karma Requirements | Some subreddits require minimum karma  |
| Post Flairs        | Fetch and display available flairs     |
| Content Policies   | Show subreddit rules before posting    |

### 3.5 UI Improvements This Month

#### Account Connection Page - Complete Redesign

**Version 3.0 → Version 4.0 Changes:**

| Aspect   | Before               | After                       |
| -------- | -------------------- | --------------------------- |
| Layout   | List of buttons      | Platform cards with status  |
| Visual   | Plain icons          | Colored platform icons      |
| Feedback | No connection status | Real-time connection status |
| Actions  | Just "Connect"       | Connect/Disconnect/Refresh  |

**New Account Card Features:**
- Platform logo and color branding
- Connection status indicator (green dot = connected)
- Account name/handle display when connected
- Last sync timestamp
- "Disconnect" option with confirmation
- Token refresh button for expired tokens

#### Post Creation Interface

**Major UI Overhaul:**

**Previous Design Issues:**
- Single textarea for all platforms
- No platform-specific preview
- Character limits not obvious
- Media upload was hidden

**New Design Features:**
- Platform selector with toggle switches
- Per-platform character counter
- Live preview for each platform
- Drag-and-drop media upload
- Preview how post will look on each platform
- Scheduling calendar integration

#### Dashboard Updates

Added new dashboard widgets:
1. **Connected Accounts Overview** - Quick view of all connected platforms
2. **Scheduled Posts Calendar** - Visual calendar of upcoming posts
3. **Recent Activity Feed** - Latest posted content and engagement
4. **Quick Post Button** - Start creating post from dashboard

### 3.6 Media Upload System

Implemented robust media handling:

**Supported Formats:**
| Type   | Formats             | Max Size                  |
| ------ | ------------------- | ------------------------- |
| Images | JPG, PNG, GIF, WebP | 5MB                       |
| Videos | MP4, MOV            | 50MB (platform dependent) |

**Upload Flow:**
1. Client-side validation (format, size)
2. Compression for large images
3. Upload to temporary storage
4. Platform-specific processing
5. Upload to each selected platform
6. Store platform media IDs

---

## 4. CHALLENGES FACED

### Challenge 1: Meta App Review Process
**Problem:** Multiple rejections, unclear requirements, weeks of delays.
**Solution:** Documented everything, prepared for future resubmission, focused on other platforms.
**Lesson:** Some platform integrations require business validation that student projects cannot easily provide.

### Challenge 2: Different API Structures
**Problem:** Every platform has completely different API design.
**Solution:** Created abstraction layer - unified interface for all platforms, platform-specific adapters underneath.

### Challenge 3: Media Upload Complexity
**Problem:** Each platform has different media requirements and upload processes.
**Solution:** Built centralized media processor that converts/resizes media per platform requirements.

### Challenge 4: Rate Limit Management
**Problem:** Different rate limits across platforms, easy to hit limits.
**Solution:** Implemented global rate limiter with platform-specific configurations.

---

## 5. PLATFORM INTEGRATION STATUS

| Platform  | OAuth | Posting | Media | Scheduling | Status                   |
| --------- | ----- | ------- | ----- | ---------- | ------------------------ |
| Twitter/X | ✅     | ✅       | ✅     | ✅          | **Complete**             |
| LinkedIn  | ✅     | ✅       | ✅     | ✅          | **Complete**             |
| Facebook  | ⏸️     | ⏸️       | ⏸️     | ⏸️          | **Blocked - App Review** |
| Instagram | ⏸️     | ⏸️       | ⏸️     | ⏸️          | **Blocked - App Review** |
| Reddit    | ✅     | ✅       | ❌     | ✅          | **Partial**              |

---

## 6. LEARNING OUTCOMES

1. **OAuth 2.0 Mastery** - Implemented OAuth for 4 different platforms
2. **API Integration Patterns** - Learned to work with varied API designs
3. **Platform Policies** - Understanding of each platform's rules and limits
4. **Error Handling** - Graceful handling of API failures and rejections
5. **User Experience** - Importance of feedback during async operations
6. **Business Reality** - Some integrations require business credentials

---

## 7. UI SCREENSHOTS & ITERATIONS

### 7.1 Account Connection Page

| Version     | Screenshot Description      | Changes Made                               |
| ----------- | --------------------------- | ------------------------------------------ |
| V3.0 → V4.0 | Account Management Redesign | Changed from button list to platform cards |

**Account Connection Page Features Visible:**
- Platform cards with brand colors (Twitter blue, LinkedIn blue, Reddit orange)
- Connection status indicator (green dot when connected)
- Account username display after connection
- "Connect" / "Disconnect" toggle buttons
- Last sync timestamp
- Token refresh option

### 7.2 Twitter/X Integration Screenshots

| Screenshot                  | Description                                       |
| --------------------------- | ------------------------------------------------- |
| **Twitter OAuth Screen**    | Twitter authorization page asking for permissions |
| **Twitter Connected State** | Account card showing connected @username          |
| **Tweet Composer**          | Text area with 280 character counter              |
| **Media Upload**            | Image preview in tweet composer                   |

### 7.3 LinkedIn Integration Screenshots

| Screenshot                | Description                            |
| ------------------------- | -------------------------------------- |
| **LinkedIn OAuth**        | LinkedIn permission request screen     |
| **LinkedIn Profile Card** | Connected account showing profile name |
| **LinkedIn Post Preview** | How post will appear on LinkedIn       |

### 7.4 Reddit Integration Screenshots

| Screenshot             | Description                                 |
| ---------------------- | ------------------------------------------- |
| **Reddit OAuth**       | Reddit authorization page                   |
| **Subreddit Selector** | Dropdown showing subscribed subreddits      |
| **Reddit Post Form**   | Title + content fields with subreddit rules |

### 7.5 Meta Rejection Evidence

| Screenshot                 | Description                                      |
| -------------------------- | ------------------------------------------------ |
| **First Rejection Email**  | Meta email stating rejection reasons             |
| **Second Rejection Email** | Second attempt rejection with new feedback       |
| **Third Rejection Email**  | Final rejection - decision to remove integration |
| **Meta Developer Console** | App review status showing "Rejected"             |

### 7.6 Post Creation Interface Evolution

| Version | Changes                                        | Status              |
| ------- | ---------------------------------------------- | ------------------- |
| V1.0    | Single textarea, no platform selection         | ❌ Rejected          |
| V2.0    | Added platform checkboxes                      | ❌ Needs improvement |
| V3.0    | Platform toggle switches, character counters   | ✅ Approved          |
| V4.0    | Side-by-side editor + preview, drag-drop media | ✅ Final             |

**Post Creation UI Features:**
- Platform selector with colored toggle switches
- Per-platform character counter (280 for Twitter, 3000 for LinkedIn)
- Real-time preview panel showing how post looks on each platform
- Drag-and-drop media zone
- Schedule picker with calendar
- "Post Now" vs "Schedule" options

### 7.7 Media Upload Interface

| Screenshot                 | Description                                 |
| -------------------------- | ------------------------------------------- |
| **Drag-Drop Zone**         | Empty state with upload instructions        |
| **Image Preview**          | Uploaded images with remove button          |
| **Upload Progress**        | Progress bar during upload                  |
| **Multi-Platform Preview** | Same image shown in Twitter/LinkedIn format |

---

## 8. NEXT MONTH'S PLAN

1. Add AI-powered caption generation (Groq API)
2. Implement post scheduling backend
3. Build analytics foundation
4. Explore YouTube integration
5. Continue Meta resubmission process
6. UI polish and bug fixes

---

## 8. HOURS LOG

| Week      | Hours   | Activities                         |
| --------- | ------- | ---------------------------------- |
| Week 1    | 32      | Twitter integration complete       |
| Week 2    | 30      | LinkedIn integration               |
| Week 3    | 28      | Meta struggles, Reddit integration |
| Week 4    | 25      | UI improvements, media upload      |
| **Total** | **115** |                                    |

---

## 10. SUPERVISOR REMARKS

*(To be filled by supervisor)*

---

## 11. DECLARATION

I hereby declare that the above report is a true account of the work done by me during October 2025.

**Date:** ____________________

**Signature:** ____________________

**Student Name:** Sundram Mahajan

---


