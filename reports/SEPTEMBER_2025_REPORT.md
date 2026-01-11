# MONTHLY TRAINING REPORT - SEPTEMBER 2025

---

## STUDENT DETAILS

| Field                    | Details                                                         |
| ------------------------ | --------------------------------------------------------------- |
| **Name**                 | Sundram Mahajan                                                 |
| **Registration No.**     | 12222340                                                        |
| **Programme**            | B.Tech Computer Science Engineering                             |
| **Month/Year**           | September 2025                                                  |
| **Project Title**        | SocialAnywhere.AI - AI-Powered Social Media Management Platform |
| **Company/Organization** | Shephertz Technologies                                          |

---

## 1. INTRODUCTION

September focused heavily on building the authentication system - both static (email/password) and dynamic (OAuth) login methods. This month involved significant work on the user interface and connecting the frontend to backend APIs. Multiple UI iterations were made based on feedback and usability testing.

---

## 2. OBJECTIVES FOR THE MONTH

1. Implement static login (email/password authentication)
2. Integrate Google OAuth for social login
3. Build registration and login UI
4. Create dashboard layout
5. Connect frontend to backend APIs
6. Begin exploring social media platform APIs

---

## 3. WORK ACCOMPLISHED

### 3.1 Static Login Implementation (Email/Password)

#### Backend Authentication Service

Built a complete authentication service with the following features:

**User Registration:**
- Email validation (format and uniqueness check)
- Password strength requirements (minimum 8 characters, special characters)
- Password hashing using Argon2 (more secure than bcrypt)
- Automatic user profile creation upon registration

**User Login:**
- Email/password verification
- JWT (JSON Web Token) generation for session management
- Token expiration handling (24-hour validity)
- Refresh token mechanism for extended sessions

**Security Measures Implemented:**
| Security Feature         | Implementation                         |
| ------------------------ | -------------------------------------- |
| Password Hashing         | Argon2id algorithm                     |
| Token Security           | JWT with HS256 signing                 |
| Input Validation         | Pydantic models with strict validation |
| SQL Injection Prevention | Parameterized queries via SQLAlchemy   |
| Rate Limiting            | Basic rate limiting on auth endpoints  |

#### Frontend Login Forms

**First UI Iteration - Basic Form:**
- Simple form with email and password fields
- Basic validation messages
- Plain styling with minimal CSS
- **Feedback received:** Too basic, not professional looking

**Second UI Iteration - Improved Design:**
- Added form field icons
- Implemented real-time validation
- Added "Remember Me" checkbox
- Better error message display
- **Feedback received:** Better but still needs visual polish

**Third UI Iteration - Professional Look:**
- Gradient background
- Card-based form layout
- Smooth transitions and animations
- Password visibility toggle
- Loading states on buttons
- **Status:** Approved for production

### 3.2 Google OAuth Integration

#### Why Google OAuth?
- Users prefer quick login without creating new passwords
- Reduces friction in user onboarding
- Provides verified email addresses
- Industry standard for modern applications

#### Implementation Steps

**Step 1: Google Cloud Console Setup**
- Created new project in Google Cloud Console
- Enabled Google+ API and OAuth consent screen
- Generated OAuth 2.0 Client ID and Secret
- Configured authorized redirect URIs

**Step 2: Backend OAuth Handler**
- Created OAuth callback endpoint
- Implemented token exchange flow
- User profile fetching from Google
- Automatic account creation for new Google users
- Account linking for existing users with same email

**Step 3: Frontend Google Button**
- Integrated Google Sign-In button
- Handled OAuth popup flow
- Token transmission to backend
- Session management after successful login

#### Challenges with Google OAuth

| Issue                 | Description                        | Resolution                          |
| --------------------- | ---------------------------------- | ----------------------------------- |
| Redirect URI Mismatch | Google rejecting callbacks         | Added exact URLs to authorized list |
| Token Expiration      | Access tokens expiring quickly     | Implemented refresh token flow      |
| CORS Errors           | Browser blocking OAuth requests    | Configured proper CORS headers      |
| Popup Blocked         | Some browsers blocking OAuth popup | Added fallback redirect method      |

### 3.3 User Interface Development

#### Dashboard - Version 1.0
**Features:**
- Welcome message with user name
- Quick stats cards (placeholder data)
- Recent activity section
- Sidebar navigation

**Problems Identified:**
- Layout broke on mobile devices
- Color scheme was too bright
- Navigation was confusing
- Too much whitespace

#### Dashboard - Version 2.0
**Improvements Made:**
- Responsive grid layout using CSS Grid
- Darker color palette (easier on eyes)
- Collapsible sidebar for mobile
- Better content organization
- Added user avatar display

#### Navigation Structure Finalized

```
├── Dashboard (Home)
├── Create Post
│   ├── Text Post
│   ├── Image Post
│   └── Schedule Post
├── My Posts
│   ├── Published
│   ├── Scheduled
│   └── Drafts
├── Accounts
│   ├── Connected Accounts
│   └── Add New Account
├── Analytics (Coming Soon)
└── Settings
    ├── Profile
    ├── Preferences
    └── Account Security
```

### 3.4 API Integration (Frontend ↔ Backend)

#### API Client Setup
Created a centralized API client with:
- Base URL configuration
- Automatic token attachment
- Error handling wrapper
- Request/response interceptors
- Retry logic for failed requests

#### Endpoints Connected This Month

| Endpoint       | Method | Purpose           | Status    |
| -------------- | ------ | ----------------- | --------- |
| /auth/register | POST   | User registration | ✅ Working |
| /auth/login    | POST   | User login        | ✅ Working |
| /auth/google   | POST   | Google OAuth      | ✅ Working |
| /auth/me       | GET    | Get current user  | ✅ Working |
| /auth/logout   | POST   | User logout       | ✅ Working |
| /auth/refresh  | POST   | Refresh token     | ✅ Working |

### 3.5 Database Implementation

#### Tables Created

**Users Table (Final Schema):**
```
users
├── id (UUID, Primary Key)
├── email (VARCHAR, Unique, Not Null)
├── password_hash (VARCHAR, Nullable - for OAuth users)
├── name (VARCHAR, Not Null)
├── avatar_url (VARCHAR, Nullable)
├── google_id (VARCHAR, Nullable, Unique)
├── is_verified (BOOLEAN, Default: False)
├── created_at (TIMESTAMP)
└── updated_at (TIMESTAMP)
```

**Sessions Table:**
```
sessions
├── id (UUID, Primary Key)
├── user_id (UUID, Foreign Key)
├── token (VARCHAR, Unique)
├── expires_at (TIMESTAMP)
└── created_at (TIMESTAMP)
```

### 3.6 Initial Platform Research

Started researching social media platform APIs:

| Platform     | API Status | Complexity | Notes                                  |
| ------------ | ---------- | ---------- | -------------------------------------- |
| Twitter/X    | Available  | Medium     | Requires developer account approval    |
| LinkedIn     | Available  | Medium     | Limited to basic features on free tier |
| Meta (FB/IG) | Available  | HIGH       | Requires extensive app review          |
| Reddit       | Available  | Low        | Simple OAuth flow                      |
| YouTube      | Available  | High       | Multiple scopes needed                 |

**Meta Warning Identified:** Discovered that Meta requires extensive app review process, business verification, and can take weeks/months for approval. Flagged this as a major risk for project timeline.

---

## 4. CHALLENGES FACED

### Challenge 1: Password Security Implementation
**Problem:** Needed to implement secure password hashing without slowing down the application.
**Solution:** Used Argon2 with optimized parameters - secure enough for production while maintaining reasonable response times.

### Challenge 2: JWT Token Management
**Problem:** Tokens were being lost on page refresh.
**Solution:** Implemented secure token storage in localStorage with automatic refresh mechanism. Added token validation on app initialization.

### Challenge 3: UI Consistency
**Problem:** Different team members creating inconsistent UI elements.
**Solution:** Started creating a component library with standardized buttons, inputs, cards, and typography.

### Challenge 4: Google OAuth Popup Issues
**Problem:** Safari and some browsers blocking OAuth popup windows.
**Solution:** Implemented fallback to full-page redirect OAuth flow when popup is blocked.

---

## 5. FEATURES COMPLETED

| Feature                | Description                             | Status        |
| ---------------------- | --------------------------------------- | ------------- |
| **Email Registration** | Users can register with email/password  | ✅ Complete    |
| **Email Login**        | Secure login with password verification | ✅ Complete    |
| **Google OAuth**       | One-click Google sign-in                | ✅ Complete    |
| **Password Reset**     | Request password reset via email        | 🔄 In Progress |
| **User Dashboard**     | Basic dashboard layout                  | ✅ Complete    |
| **Responsive Design**  | Mobile-friendly layouts                 | ✅ Complete    |
| **Protected Routes**   | Authentication-required pages           | ✅ Complete    |

---

## 6. UI SCREENSHOTS & ITERATIONS

### Login Page Evolution

| Version | Changes                         | Feedback                      |
| ------- | ------------------------------- | ----------------------------- |
| V1.0    | Basic form, no styling          | "Too plain, needs branding"   |
| V1.5    | Added logo, basic colors        | "Better but fields too small" |
| V2.0    | Card layout, larger fields      | "Add social login buttons"    |
| V2.5    | Google OAuth button added       | "Background too plain"        |
| V3.0    | Gradient background, animations | "Approved!"                   |

### Dashboard Evolution

| Version | Changes                   | Feedback                           |
| ------- | ------------------------- | ---------------------------------- |
| V1.0    | Basic layout, white theme | "Too bright, hard to use for long" |
| V1.5    | Darker theme introduced   | "Sidebar navigation confusing"     |
| V2.0    | Reorganized navigation    | "Need better mobile support"       |
| V2.5    | Responsive grid layout    | "Approved!"                        |

---

## 7. LEARNING OUTCOMES

1. **Authentication Systems** - Deep understanding of auth flows, JWT, OAuth 2.0
2. **Security Best Practices** - Password hashing, token security, CORS
3. **UI/UX Iteration** - Importance of user feedback in design
4. **API Design** - RESTful endpoint design and documentation
5. **State Management** - Managing user sessions across page loads
6. **Responsive Design** - CSS Grid and mobile-first approach

---

## 8. NEXT MONTH'S PLAN

1. Implement Twitter/X OAuth and posting integration
2. Begin LinkedIn integration
3. Start Meta (Facebook/Instagram) app review process
4. Add post creation functionality
5. Implement media upload feature

---

## 9. HOURS LOG

| Week      | Hours   | Activities                    |
| --------- | ------- | ----------------------------- |
| Week 1    | 28      | Static login implementation   |
| Week 2    | 30      | Google OAuth integration      |
| Week 3    | 25      | UI development and iterations |
| Week 4    | 27      | API integration, testing      |
| **Total** | **110** |                               |

---



