# MONTHLY TRAINING REPORT - AUGUST 2025

---

## STUDENT DETAILS

| Field                    | Details                                                         |
| ------------------------ | --------------------------------------------------------------- |
| **Name**                 | Sundram Mahajan                                                 |
| **Registration No.**     | 12222340                                                        |
| **Programme**            | B.Tech Computer Science Engineering                             |
| **Month/Year**           | August 2025                                                     |
| **Project Title**        | SocialAnywhere.AI - AI-Powered Social Media Management Platform |
| **Company/Organization** | Shephertz Technologies                                          |

---

## 1. INTRODUCTION

This month marked the beginning of the SocialAnywhere.AI project - an ambitious undertaking to build a comprehensive AI-powered social media management platform. The primary focus was on project planning, technology selection, and laying the foundation for future development.

---

## 2. OBJECTIVES FOR THE MONTH

1. Understand the project requirements and scope
2. Select appropriate technology stack
3. Set up development environment
4. Design initial database schema
5. Create project structure and architecture

---

## 3. WORK ACCOMPLISHED

### 3.1 Project Planning & Requirements Analysis

#### Understanding the Vision
The project aims to solve a common problem faced by social media managers and content creators - managing multiple social media accounts efficiently. The platform would enable users to:

- Create content once and post to multiple platforms
- Schedule posts for optimal engagement times
- Generate AI-powered captions and content
- Track analytics across platforms
- Manage multiple social media accounts from a single dashboard

#### Target Platforms Identified
| Platform  | Priority | Complexity                  |
| --------- | -------- | --------------------------- |
| Twitter/X | High     | Medium                      |
| LinkedIn  | High     | Medium                      |
| Facebook  | High     | High (OAuth complexity)     |
| Instagram | Medium   | High (Meta approval needed) |
| Reddit    | Medium   | Low                         |
| YouTube   | Low      | High                        |

### 3.2 Technology Stack Selection

After extensive research and discussion, the following technologies were selected:

#### Frontend Decision Process
Initially considered multiple options:

| Option   | Pros                             | Cons                       | Decision   |
| -------- | -------------------------------- | -------------------------- | ---------- |
| Next.js  | SSR, SEO friendly                | Overkill for dashboard app | ❌ Rejected |
| Vue.js   | Easy learning curve              | Smaller ecosystem          | ❌ Rejected |
| React.js | Large ecosystem, component-based | Requires additional setup  | ✅ Selected |

**Final Frontend Stack:**
- React.js 18 with Vite (faster than Create React App)
- Zustand for state management (simpler than Redux)
- React Router for navigation
- CSS3 with custom design system

#### Backend Decision Process

| Option          | Pros                       | Cons                   | Decision   |
| --------------- | -------------------------- | ---------------------- | ---------- |
| Node.js/Express | JavaScript everywhere      | Callback complexity    | ❌ Rejected |
| Django          | Batteries included         | Too heavy for API-only | ❌ Rejected |
| FastAPI         | Async, fast, modern Python | Newer framework        | ✅ Selected |

**Final Backend Stack:**
- Python 3.11 with FastAPI
- PostgreSQL for database
- SQLAlchemy/databases for async DB operations
- Pydantic for data validation

### 3.3 Development Environment Setup

#### Tools Configured
- VS Code with Python and React extensions
- Git repository initialized
- PostgreSQL local installation
- Postman for API testing
- Node.js and npm for frontend

#### Project Structure Created

```
socialanywhere.ai/
├── server/                 # Backend (FastAPI)
│   ├── main.py            # Entry point
│   ├── database.py        # DB connections
│   ├── auth_routes.py     # Authentication
│   └── requirements.txt   # Python dependencies
├── src/                   # Frontend (React)
│   ├── components/        # Reusable components
│   ├── pages/            # Page components
│   ├── store/            # State management
│   └── lib/              # Utilities
├── public/               # Static assets
└── package.json          # Node dependencies
```

### 3.4 Database Schema Design

#### Initial Entity Relationship Planning

**Users Table:**
- id (Primary Key)
- email (Unique)
- password_hash
- name
- created_at
- updated_at

**Social Media Accounts Table:**
- id (Primary Key)
- user_id (Foreign Key)
- platform (twitter, linkedin, facebook, etc.)
- access_token
- refresh_token
- account_name
- connected_at

**Posts Table:**
- id (Primary Key)
- user_id (Foreign Key)
- content
- media_urls
- platforms (array)
- scheduled_time
- status (draft, scheduled, published, failed)
- created_at

### 3.5 Initial UI Wireframing

Created basic wireframes for:
1. **Login/Register Page** - Simple form-based authentication
2. **Dashboard** - Overview of connected accounts and recent posts
3. **Create Post** - Multi-platform post composer
4. **Schedule** - Calendar view of scheduled posts
5. **Analytics** - Basic metrics display

---

## 4. CHALLENGES FACED

### Challenge 1: Technology Selection Overwhelm
**Problem:** Too many framework options available, difficult to decide.
**Solution:** Created comparison matrices, researched industry trends, and chose based on project-specific requirements rather than popularity.

### Challenge 2: Understanding OAuth Flows
**Problem:** Different platforms have different OAuth implementations.
**Solution:** Started studying OAuth 2.0 documentation for each platform. Realized Meta (Facebook/Instagram) would be the most complex due to their app review process.

### Challenge 3: Database Design Complexity
**Problem:** Designing a schema flexible enough for multiple platforms.
**Solution:** Used a generic "social_media_accounts" table with platform-agnostic fields and platform-specific JSON storage for additional data.

---

## 5. LEARNING OUTCOMES

1. **Project Architecture** - Learned how to structure a full-stack application
2. **Technology Evaluation** - Developed skills in comparing and selecting technologies
3. **FastAPI Basics** - Understood async Python web development
4. **React Project Setup** - Configured Vite-based React application
5. **Database Design** - Planned relational database schema

---

## 6. TOOLS & RESOURCES USED

| Resource              | Purpose                       |
| --------------------- | ----------------------------- |
| FastAPI Documentation | Backend framework learning    |
| React.dev             | Frontend framework reference  |
| Figma                 | UI wireframing                |
| dbdiagram.io          | Database schema visualization |
| GitHub                | Version control               |

---

## 7. NEXT MONTH'S PLAN

1. Implement user authentication (registration, login)
2. Set up Google OAuth integration
3. Build initial UI components
4. Connect frontend to backend APIs
5. Begin Twitter/X integration research

---

## 8. HOURS LOG

| Week      | Hours  | Activities                                  |
| --------- | ------ | ------------------------------------------- |
| Week 1    | 20     | Project understanding, requirement analysis |
| Week 2    | 25     | Technology research and selection           |
| Week 3    | 22     | Environment setup, project structure        |
| Week 4    | 23     | Database design, initial coding             |
| **Total** | **90** |                                             |

---

## 9. SUPERVISOR REMARKS

*(To be filled by supervisor)*

---

## 10. DECLARATION

I hereby declare that the above report is a true account of the work done by me during August 2025.

**Date:** ____________________

**Signature:** ____________________

**Student Name:** Sundram Mahajan

---


