1. Overview & Goals
Objective: Develop a centralized Software-as-a-Service (SaaS) platform providing content creators and clipping specialists with access to raw video segments from major streaming platforms (TikTok, Instagram, YouTube initially) and sophisticated, real-time analytics on clip trends, creator performance, and content engagement, functioning as an intelligence hub analogous to a "Bloomberg Terminal for viral clips".  
Scope:
In Scope: Core web application (user auth, subscriptions, payments), data ingestion from TikTok/Instagram/YouTube APIs , focus on "Brain Rot"  style content niches, raw clip discovery/download, Creator CRM dashboard (authenticated data), analytics dashboard ("Bloomberg" view), external API (read-access initially), VPS-based infrastructure.  
Out of Scope (Initial): User uploading/hosting of edited clips, in-platform video editing, advanced predictive modeling, direct editing software integration, support for platforms beyond the initial three, features reliant on data not reliably accessible via official APIs.
Success Criteria:
Achieve target user acquisition and retention metrics.
Maintain high data accuracy and low latency in analytics reporting (< X ms target).
Positive user feedback scores (> Y on usability/value surveys).
Maintain compliance with platform API terms of service.   
Demonstrate stable external API adoption (target Z active integrations).
2. Context & Architecture
Overall System Context: This platform is a standalone SaaS application. It interacts externally with social media platform APIs (TikTok, Instagram, YouTube) for data ingestion and potentially with payment gateways. Internally, it comprises distinct modules for frontend UI, backend API services, data processing, analytics, and database management. It does not directly depend on other pre-existing internal MCDs at this stage. **Crucially, authentication and API interactions with external platforms will rely on user-provided developer credentials (Client ID/Secret) stored securely in the database.**
Mermaid Architecture Diagram(s):
Code snippet

graph TD;
    subgraph External Services
        TikTok_API;
        Instagram_API[Instagram Graph API];
        YouTube_API;
        Payment_Gateway[Payment Gateway];
    end

    subgraph Clip_Analytics_Platform
        Frontend[Web Frontend UI];
        Backend_API;
        User_Auth;
        Data_Ingestion;
        Video_Processing;
        Analytics_Engine[Analytics Engine];
        Databases;
        External_API_Gateway[External API Gateway];
    end

    Frontend --> Backend_API;
    Backend_API --> User_Auth;
    Backend_API --> Data_Ingestion;
    Backend_API --> Video_Processing;
    Backend_API --> Analytics_Engine;
    Backend_API --> Databases;
    Backend_API --> External_API_Gateway;
    Backend_API --> Payment_Gateway;

    Data_Ingestion --> TikTok_API;
    Data_Ingestion --> Instagram_API;
    Data_Ingestion --> YouTube_API;
    Data_Ingestion --> Databases;

    Video_Processing --> Databases;

    Analytics_Engine --> Databases;

    External_API_Gateway --> Backend_API;

*(Diagram Explanation): The diagram shows the user interacting with the Frontend UI, which communicates with the Backend API Gateway. The Backend orchestrates calls to various internal services (Auth, Ingestion, Processing, Analytics) and external services (Platform APIs, Payment Gateway). Data flows from external APIs via the Ingestion service into the Databases, is processed by the Video Processing and Analytics Engines, and results are served back through the Backend API to the Frontend or the External API Gateway.* **OAuth flows and data ingestion rely on fetching and using the specific user's stored developer credentials (Client ID/Secret) from the Databases (`platform_accounts`) to interact with external APIs.**
Technology Stack: (Potential - TBD)
Hosting: VPS (e.g., AWS Lightsail, DigitalOcean, Google Cloud Compute Engine) , Linux OS.   
Backend: Python (Django/Flask) or Node.js (Express).
Frontend: React, Vue, or Angular.
Database: PostgreSQL (Relational), MongoDB (NoSQL - optional), TimescaleDB/InfluxDB (Time-Series - optional).
Video Processing: FFmpeg library/tooling.
Containerization: Docker (Recommended).   
Key Concepts & Terminology:
Raw Clip: Unedited video segment extracted directly from source VOD/stream.
Brain Rot Content: Specific short-form video style characterized by multi-layered stimuli, rapid pacing, often using memes/repetitive audio.   
Hashing/Fingerprinting: Algorithmic techniques (e.g., perceptual hashing) used by platforms to detect duplicate content.   
Creator CRM: Platform section for authenticated creators to monitor their cross-platform performance.
Analytics Dashboard: Platform section displaying aggregated market trends and insights ("Bloomberg" view).   
VPS: Virtual Private Server - isolated virtual server environment on shared hardware.   
API: Application Programming Interface - rules for software communication.
*   *User-Provided Credentials:* Client ID and Client Secret obtained by the end-user from registering their *own* developer application with an external platform (e.g., TikTok). Stored encrypted in `platform_accounts`.
*   *Platform-Level Credentials:* (Standard OAuth approach - **NOT used for user data connections in this architecture**) Credentials for a single app registered by the SaaS platform owner, typically stored in environment variables.
3. Functional Requirements / User Stories
User Management & Authentication:
As a new user, I want to register for an account (email/password or social) so I can access the platform.
AC1: Registration form accepts valid inputs.
AC2: Successful registration logs the user in or sends verification email.
AC3: Appropriate user record created in the database.
As a registered user, I want to log in securely so I can access my account and features.
AC1: Login form accepts credentials.
AC2: Valid credentials grant access.
AC3: Invalid credentials show an error message.
As a user, I want to view and select subscription plans so I can access desired features.
AC1: Plans page displays available tiers and features.
AC2: User can select a plan to proceed to payment.
As a user, I want to manage my subscription and payment details securely.
AC1: User can view current subscription status.
AC2: User can update payment method via integrated gateway.
AC3: User can cancel or change subscription plan.
As a creator user, I want to connect my TikTok, Instagram, and YouTube accounts via OAuth so the platform can fetch my performance data.
AC1: Dedicated section allows initiating OAuth flow for each platform.
AC2: Successful OAuth flow stores necessary tokens securely.
AC3: Connection status is displayed for linked accounts.
AC4: User can disconnect linked accounts.
As a creator user, I want to securely provide and update the Client ID and Client Secret for my developer application for each external platform (TikTok, Instagram, YouTube) via the Account Settings page. AC: Credentials encrypted and stored in `PlatformAccounts`. Status updated to 'pending' validation.
As a creator user, I am informed about the status (e.g., 'valid', 'invalid') of my provided developer credentials. AC: Status displayed in Account Settings.
As a creator user, I want to connect my TikTok, Instagram, and YouTube accounts via OAuth, **which uses my previously provided developer credentials**, so the platform can fetch my performance data. AC: OAuth flow completes, tokens stored securely, connection status displayed.
  
Clip Discovery & Raw Clip Access:
As a user, I want to search for creators monitored by the platform so I can find their content.
AC1: Search input accepts creator names.
AC2: Search results display matching monitored creators.
As a user, I want to view a list of recent streams/VODs for a selected creator so I can choose content to clip.
AC1: List displays VOD metadata (title, date, duration, thumbnail).
  
As a user, I want to interact with a VOD timeline (if feasible) to define start/end points for a raw clip so I can select the exact segment I need.
AC1: Visual timeline allows selection.
AC2: Start/end times are captured accurately.
As a user, I want to download the selected raw video segment so I can edit it externally.
AC1: Download request is initiated for the selected segment.
AC2: System checks user subscription/credits before processing.
AC3: A secure download link for the raw clip is provided upon successful processing.
As a premium user, I want to see indicators for potentially trending clips so I can prioritize high-potential content.
AC1: Visual cues (e.g., icons, highlighting) appear on relevant clips in lists/timelines.
Analytics Dashboard ("Bloomberg" View):
As a user, I want to view a dashboard with aggregated trend data (trending creators, topics, clips) so I can understand the market.
AC1: Dashboard displays ranked lists and charts for key trends.
AC2: Data reflects recent activity within a defined timeframe.
  
As a user, I want to view time-series charts showing performance trends (e.g., velocity, clipper count) for creators/topics so I can analyze momentum.
AC1: Line/bar charts visualize selected metrics over time.
AC2: Charts are interactive (hover, zoom).
  
As a user, I want to filter the analytics dashboard (by platform, date, creator, topic) so I can focus on relevant data.
AC1: Filter controls are available and functional.
AC2: Dashboard data updates based on applied filters.
Creator CRM Dashboard (Authenticated View):
As an authenticated creator, I want to access a private dashboard summarizing my linked accounts' performance so I can track my growth.
AC1: Dashboard displays aggregated KPIs (followers, views, likes, etc.).
AC2: Data is sourced only from the user's authenticated accounts.
  
As an authenticated creator, I want to view performance trends over time for my accounts so I can analyze my progress.
AC1: Charts display key metrics (e.g., follower growth, engagement rate) over selected periods.
As an authenticated creator, I want to see a list of my recent posts with individual metrics so I can identify top-performing content.
AC1: Table lists recent posts/videos with associated views, likes, comments.
API Access (for Authorized Systems):
As an authorized system, I want to authenticate securely (e.g., API key) so I can access the platform's data programmatically.
AC1: Authentication mechanism validates API keys.
AC2: Unauthorized requests are rejected.
As an authorized system, I want to query for new VODs/streams from monitored creators so I can automate content discovery.
AC1: API endpoint returns list of new VODs based on query parameters (e.g., creator ID, timestamp).
As an authorized system, I want to query for trending analytics data so I can incorporate market intelligence.
AC1: API endpoint returns current trending clips/creators/topics.
The system shall enforce rate limits on the external API to ensure stability.
AC1: Requests exceeding the limit receive an appropriate error code (e.g., 429).
4. Design Specification
4.1. UI/UX Design (Frontend):
Wireframes/Mockups: (To Be Created - Link/Description Placeholder). Initial designs should focus on clarity, data density (for analytics), and workflow efficiency for clip selection. Inspiration from financial terminals  and social media analytics tools [25-33].   
UI Components (Conceptual): LoginForm, RegistrationForm, SubscriptionSelector, AccountLinker, CreatorSearch, VODList, VODPlayerInterface (with timeline selection), ClipDownloadButton, AnalyticsDashboard, AnalyticsChart (Line, Bar), AnalyticsTable, CRMDashboard, CRMMetricsDisplay, APIManagementPanel.
Styling Notes: Utilize a consistent design system (e.g., Material UI, Tailwind CSS). Prioritize responsive design for desktop browsers. Ensure clear data visualization principles are followed for charts and graphs.
4.2. API Design (Backend/Shared):
Approach: Primarily RESTful APIs for internal frontend-backend communication and external access.
Example Endpoints & Methods:
POST /api/auth/register
POST /api/auth/login
GET /api/auth/user (Requires Auth)
POST /api/auth/link/{platform} (Requires Auth, initiates OAuth)
GET /api/creators?search={query} (Requires Auth)
GET /api/creators/{creatorId}/vods (Requires Auth)
POST /api/clips/request (Requires Auth) - Request body: { "vodId": "...", "startTime":..., "endTime":... }
GET /api/clips/status/{requestId} (Requires Auth)
GET /api/clips/download/{requestId} (Requires Auth, returns secure URL)
GET /api/analytics/trends?type={clips|creators|topics}&platform={all|tiktok|...}&period={24h|7d|...} (Requires Auth)
GET /api/crm/performance?period={7d|30d|...} (Requires Auth, uses user's linked accounts)
GET /ext-api/v1/trends?type=... (Requires API Key Auth)
GET /ext-api/v1/vods?creatorId=...&since=... (Requires API Key Auth)
Add `POST /api/credentials/{platform}`, `GET /api/credentials/status`
Example Request/Response Schemas (Conceptual):
Request: POST /api/clips/request
JSON

{
  "vodId": "some_vod_identifier",
  "startTime": 12345.67, // seconds from start
  "endTime": 12390.12   // seconds from start
}
Response: POST /api/clips/request (Success: 202 Accepted)
JSON

{
  "requestId": "unique_request_id_123",
  "status": "pending",
  "estimatedCompletion": "2025-04-29T17:05:00Z"
}
Response: GET /api/analytics/trends?type=creators (Success: 200 OK)
JSON

{
  "data":,
  "generatedAt": "2025-04-29T16:55:00Z"
}
Error Responses: Define standard error response format (e.g., { "error": { "code": "AUTH_REQUIRED", "message": "Authentication required for this endpoint." } }). Include specific codes for common errors (400 Bad Request, 401 Unauthorized, 403 Forbidden, 404 Not Found, 429 Rate Limited, 500 Internal Server Error).
4.3. Data Model / Schema (Backend): (Conceptual - See Chapter 4.4 for detailed fields)
Users: Stores user account info, credentials, subscription status, API keys.
Creators: Stores monitored creator profiles and platform identifiers.
StreamVODs: Stores metadata for indexed streams/VODs.
RawClipRequests: Tracks user requests for raw clip downloads (status, timestamps, segment info).
AnalyticsDataPoints: Stores time-series data for analytics metrics.
PlatformAccounts: Securely stores **user-provided developer Client ID/Secret (encrypted)** AND resulting user platform credentials (tokens, scopes, encrypted).
Subscriptions: Manages user subscription plans and billing cycles.
4.4. Logic & Flow:
Core Logic Areas: Data Ingestion (**fetching user credentials from DB first**, API polling, error handling, token refresh), Raw Clip Extraction (validation, VOD retrieval, segmentation, secure storage), Analytics Engine (metric calculation, trend identification, aggregation), Monetization Enforcement (subscription/credit checks), Authorization/Authentication (**OAuth flows using user-provided credentials fetched from DB**, API key validation, access control).
Raw Clip Extraction Workflow (Sequence Diagram):
Code snippet

sequenceDiagram
    participant User
    participant Frontend
    participant BackendAPI
    participant VideoProcessingService
    participant Storage

    User->>Frontend: Selects VOD segment & clicks Download
    Frontend->>BackendAPI: POST /api/clips/request (vodId, start, end)
    BackendAPI->>BackendAPI: Validate User Auth & Subscription/Credits
    alt Valid Request
        BackendAPI->>VideoProcessingService: Initiate Clip Extraction (vodId, start, end)
        VideoProcessingService->>Storage: Retrieve Source VOD (if needed)
        VideoProcessingService->>VideoProcessingService: Process video (extract segment)
        VideoProcessingService->>Storage: Store Raw Clip Temporarily
        VideoProcessingService->>BackendAPI: Notify Completion (clip URL/ID)
        BackendAPI->>Frontend: Return Success (requestId, status: processing/ready)
        loop Poll Status or Wait for Notification
            Frontend->>BackendAPI: GET /api/clips/status/{requestId}
            BackendAPI-->>Frontend: Return Status (pending/ready/error)
        end
        alt Clip Ready
            Frontend->>BackendAPI: GET /api/clips/download/{requestId}
            BackendAPI->>Storage: Generate Secure Download URL
            BackendAPI-->>Frontend: Return Secure URL
            User->>Frontend: Clicks Download Link
            Frontend->>Storage: Initiate Download via Secure URL
        end
    else Invalid Request (e.g., no credits)
        BackendAPI-->>Frontend: Return Error (e.g., 403 Forbidden)
    end

Business Rules: Enforce subscription limits on downloads/API usage. Handle API rate limits gracefully. Ensure compliance with platform API terms. Implement secure handling of user credentials and payment information. Users responsible for credential validity. Implement validation checks.
5. Implementation Details & File Structure
Target Directory/Module: (Example Structure)
/src/backend/features/auth
/src/backend/features/ingestion
/src/backend/features/clipping
/src/backend/features/analytics
/src/backend/services/database
/src/backend/services/payment
/src/frontend/src/features/auth
/src/frontend/src/features/discovery
/src/frontend/src/features/analytics
/src/frontend/src/features/crm
File Structure Plan: (Example for /src/backend/features/auth)
/src/backend/features/auth/
├── controllers/       # Handles incoming API requests
│   ├── auth.controller.ts
│   └── oauth.controller.ts
├── services/          # Business logic
│   ├── auth.service.ts
│   └── token.service.ts
├── routes/            # API route definitions
│   └── auth.routes.ts
├── interfaces/        # TypeScript interfaces/types
│   └── auth.interfaces.ts
└── utils/             # Helper functions
    └── password.util.ts
Dependencies: (High-Level Examples)
Backend: Node.js framework (Express?), ORM (Prisma/TypeORM?), Database client (pg, mongodb?), Video processing library (fluent-ffmpeg?), Authentication library (Passport.js?), Payment SDK (Stripe Node?).
Frontend: React/Vue/Angular, State management (Redux/Zustand/Vuex?), UI component library, HTTP client (axios?).
Environment Variables: DATABASE_URL, JWT_SECRET, ~~TIKTOK_CLIENT_ID~~, ~~TIKTOK_CLIENT_SECRET~~, ~~INSTAGRAM_CLIENT_ID~~, ~~INSTAGRAM_CLIENT_SECRET~~, ~~YOUTUBE_CLIENT_ID~~, ~~YOUTUBE_CLIENT_SECRET~~ (Removed for user connections, may be needed for public data), PAYMENT_GATEWAY_SECRET_KEY, VPS_SSH_HOST, VPS_SSH_USER, EXTERNAL_API_RATE_LIMIT, `SUPABASE_SERVICE_ROLE_KEY`, `PGPSODIUM_KEY_ID`.
6. Implementation Units & Tasks (Agent Instructions)
(Based on Phased Rollout - Focus on Phase 1)

Unit 1: Core Infrastructure & User Auth Setup
File(s): /src/backend/features/auth, /src/frontend/src/features/auth, Infrastructure config (Dockerfiles, CI/CD scripts).
Purpose: Establish basic project structure, user registration, login, and account management backend/frontend components. Set up initial VPS environment.   
Agent Task(s):
ACTION: SETUP_PROJECT_STRUCTURE (Backend: Node.js/Express, Frontend: React/Vite).
ACTION: CREATE_DATABASE_SCHEMA (Users table: ID, email, password_hash, subscription_level).
ACTION: IMPLEMENT_BACKEND_AUTH_API (/register, /login endpoints, JWT generation/validation).
ACTION: IMPLEMENT_FRONTEND_AUTH_FORMS (Login, Registration components).
ACTION: IMPLEMENT_FRONTEND_AUTH_STATE (Manage user login status).
ACTION: SETUP_VPS_ENVIRONMENT (Install OS, Docker, Nginx, basic security).
ACTION: CREATE_BASIC_CI_CD_PIPELINE (Lint, test, build, deploy to VPS).
Unit 2: Platform Account Linking (OAuth)
File(s): /src/backend/features/auth/controllers/oauth.controller.ts, /src/backend/features/auth/services/token.service.ts, /src/frontend/src/features/crm/components/AccountLinker.tsx, /src/backend/models/PlatformAccount.model.ts.
Purpose: Implement OAuth 2.0 flows for TikTok, Instagram, and YouTube to allow users to connect their accounts. Securely store access/refresh tokens.
Agent Task(s):
ACTION: REGISTER_APPS_ON_PLATFORMS (TikTok Dev Portal, Facebook Dev Portal, Google Cloud Console) to get Client IDs/Secrets.
ACTION: IMPLEMENT_BACKEND_OAUTH_CALLBACK_HANDLERS for each platform (/api/auth/callback/{platform}).
ACTION: IMPLEMENT_TOKEN_STORAGE_SERVICE (Securely store encrypted tokens in PlatformAccounts table).
ACTION: IMPLEMENT_TOKEN_REFRESH_LOGIC (Handle token expiration).
ACTION: CREATE_FRONTEND_ACCOUNT_LINKING_UI (Buttons to initiate OAuth flow, display connection status).
Unit 3: Creator CRM Data Ingestion (Authenticated)
File(s): /src/backend/features/ingestion/services/tiktok.service.ts, .../instagram.service.ts, .../youtube.service.ts, /src/backend/jobs/crm_data_sync.job.ts.
Purpose: Fetch basic profile and performance data (views, likes, comments) from the user's linked accounts using the stored tokens and relevant APIs.   
Agent Task(s):
ACTION: IMPLEMENT_API_CLIENTS for TikTok Display API, Instagram Graph API, YouTube Data API using stored tokens.
ACTION: DEFINE_DATA_FETCHING_LOGIC for user profile, post lists, and basic metrics.
ACTION: CREATE_DATABASE_SCHEMA_EXTENSIONS (Store fetched metrics linked to User/PlatformAccount).
ACTION: IMPLEMENT_BACKGROUND_JOB (Scheduled task) to periodically sync data for connected users.
ACTION: HANDLE_API_ERRORS_AND_RATE_LIMITS gracefully during ingestion.
Unit 4: Creator CRM Frontend Dashboard
File(s): /src/frontend/src/features/crm/pages/CRMDashboardPage.tsx, /src/frontend/src/features/crm/components/MetricsDisplay.tsx, /src/frontend/src/features/crm/components/PerformanceChart.tsx.
Purpose: Display the fetched, authenticated performance data to the user in a clear dashboard format.
Agent Task(s):
ACTION: CREATE_BACKEND_API_ENDPOINT (GET /api/crm/performance) to serve aggregated/formatted data.
ACTION: BUILD_FRONTEND_DASHBOARD_LAYOUT.
ACTION: IMPLEMENT_DATA_VISUALIZATIONS (Scorecards for KPIs, Charts for trends).
ACTION: FETCH_DATA_FROM_BACKEND and display in components.
ACTION: ADD_TIME_PERIOD_SELECTOR to filter CRM data.
(Subsequent Units would cover Phases 2, 3, 4: Clip Discovery/Download, Advanced Analytics, External API)

7. Relationships & Dependencies
Internal Dependencies:
Unit 2 (OAuth) depends on Unit 1 (User Auth).
Unit 3 (Ingestion) depends on Unit 2 (OAuth Tokens).
Unit 4 (CRM Frontend) depends on Unit 3 (Ingested Data) and Unit 1 (Backend API).
Clip Download feature depends on User Auth and potentially Subscription status.
Analytics Engine depends on Data Ingestion.
External API depends on Backend API and Analytics Engine.
External Dependencies:
Critical reliance on TikTok, Instagram, YouTube APIs (availability, terms, rate limits).   
Dependency on chosen VPS provider for infrastructure.   
Dependency on Payment Gateway API.
Data Flow Summary: External Platform APIs -> Data Ingestion Service -> Databases -> Analytics Engine / Video Processing Service -> Backend API -> Frontend UI / External API Gateway. User authentication data flows between Frontend, Backend API, and User Auth Service.
8. Testing Notes (Optional)
Unit Tests: Focus on testing individual functions/modules: API client logic, analytics calculations, authentication helpers, data transformation utilities. Mock external API calls.
Integration Tests: Test interactions between services: Frontend <-> Backend API, Backend API <-> Database, Data Ingestion <-> External APIs (requires careful setup/mocking), Clip Request -> Processing -> Download Link generation. Test OAuth flows.
Manual Testing: End-to-end user flows: Registration, Login, Account Linking, Clip Discovery & Download, Viewing Analytics, Viewing CRM data, Subscription Management. Test across different browsers. Verify data accuracy in dashboards. Test API rate limit handling.
9. Agent Instructions & Considerations
Processing Order: Implement Units sequentially following the Phased Rollout plan (Phase 1 first: Units 1-4, then Phase 2, etc.). Within a phase, some parallel work might be possible (e.g., frontend/backend for a feature), but ensure backend APIs are ready before frontend integration.
File Locking: Use check file status before modifying files, especially if multiple agents/developers might work concurrently (less likely in early phases but good practice).
Assistance/Partitioning: Complex areas requiring careful implementation or potential assistance requests include:
Navigating specific platform API intricacies, authentication, and rate limits.   
Efficient video processing pipeline for raw clip extraction.
Scalable design of the analytics engine and database queries.
Secure implementation of payment gateway integration.
Code Style: Adhere to established project linting (e.g., ESLint, Prettier) and formatting rules. Follow consistent naming conventions and commenting practices.
*   **System Architecture**: Describe the high-level architecture (SaaS, Modules, Data Flow) including **Supabase, Vault, and external API interactions using user-provided credentials.**
*   The platform will **securely store user-provided developer credentials (Client ID/Secret) using Supabase Vault** and utilize these for accessing external platform APIs on the user's behalf.
*(Diagram Explanation): User interacts with React/HeroUI Frontend, using Supabase SDK for Auth/DB (with RLS). Frontend calls Backend API (VPS/Functions) for complex tasks (ingestion, video processing, heavy analytics, external API). Backend uses Supabase DB/Auth, **securely retrieving user credentials from Vault when needed**. Data ingestion pulls from external APIs into Supabase DB. Note the distinction between data accessed via user OAuth (Authenticated Path for CRM) and data sourced publicly (Public Path for "Bloomberg" view).** OAuth flows and data ingestion rely on fetching and securely decrypting the specific user's developer credentials (Client ID/Secret) from Supabase Vault via references in `platform_accounts` to interact with external APIs.** Public Path for "Bloomberg" view (which may still use platform-level API keys if accessing purely public, non-user-specific data).*
*   **User-Provided Credentials:** Client ID and Client Secret obtained by the end-user from registering their *own* developer application with an external platform (e.g., TikTok). Stored securely **via Supabase Vault**, with references stored in the `platform_accounts` table.
*   **Supabase Vault:** Supabase's secure secret management service.
*   **2.2 User Story:** As a creator user, I want to securely provide and update the Client ID and Client Secret for my developer application for each external platform (TikTok, Instagram, YouTube) via the Account Settings page.
*   **2.3 Acceptance Criteria:**
    *   Input fields for Client ID and Secret are available for each supported platform in the user's account settings.
    *   On submission, credentials are **validated (if possible) and securely stored via Supabase Vault.**
    *   The `platform_accounts` table is updated with the **Vault secret reference (UUID)** and a status of 'pending validation'.
    *   User receives confirmation of successful storage.
    *   UI displays the status (e.g., 'pending', 'valid', 'invalid') of the stored credentials.
*   **3.2 User Story:** As a creator user, I want to connect my TikTok, Instagram, and YouTube accounts via OAuth, **which uses my previously provided developer credentials (retrieved securely from Vault)**, so the platform can fetch my performance data.
*   **3.3 Acceptance Criteria:**
    *   'Connect' button for each platform initiates the standard OAuth 2.0 flow.
    *   The backend uses the **user's stored (and Vault-retrieved) developer credentials** to make the necessary OAuth requests.
    *   Upon successful authorization, the platform securely stores the resulting access and refresh tokens **(potentially also in Vault)**, linking them to the user and the specific `platform_accounts` entry.
    *   The connection status is updated and displayed in the UI (e.g., 'Connected', 'Disconnected').
    *   User can disconnect the account, which revokes tokens and updates the status.
POST /api/credentials/{platform}
*   Description: Securely stores user-provided developer credentials **using Supabase Vault**.
*   Auth: Required (User JWT)
*   Request Body: `{ "client_id": "string", "client_secret": "string" }`
*   Response (Success): `{ "status": "pending_validation", "vault_secret_id": "uuid" }`
*   Response (Error): Standard error format.
GET /api/credentials/status
*   Description: Retrieves the validation status of stored credentials for the user.
*   Auth: Required (User JWT)
*   Response (Success): `{ "platform": "tiktok", "status": "valid" }, { "platform": "youtube", "status": "invalid", "reason": "API error..." } ]`
*   `platform_accounts`
    *   `id` (uuid, pk)
    *   `user_id` (uuid, fk -> auth.users)
    *   `platform_name` (text, e.g., 'tiktok', 'youtube')
    *   `developer_credentials_vault_id` (uuid, **Reference to the secret in vault.secrets containing client_id/secret**)
    *   `access_token_vault_id` (uuid, nullable, **Reference to the secret in vault.secrets containing access token**)
    *   `refresh_token_vault_id` (uuid, nullable, **Reference to the secret in vault.secrets containing refresh token**)
    *   `scopes` (text[], nullable)
    *   `status` (text, e.g., 'pending_validation', 'valid', 'invalid', 'connected', 'disconnected')
    *   `last_validated_at` (timestampz, nullable)
    *   `created_at` (timestampz)
    *   `updated_at` (timestampz)
*   **Data Ingestion Flow:**
    1.  Scheduler (e.g., Supabase Cron Job) triggers ingestion for a user/platform.
    2.  Backend service retrieves the `platform_accounts` record for the user/platform.
    3.  **Retrieves necessary tokens/credentials from Supabase Vault using the stored UUIDs.**
    4.  Makes requests to the external platform API using the retrieved credentials/tokens.
    5.  Handles token refresh if necessary (**updating the token secret in Vault**).
    6.  Processes the API response.
    7.  Stores relevant data points in Supabase tables (e.g., `analytics_reports`).
    8.  Handles errors (API errors, rate limits, invalid credentials - updating `platform_accounts.status`).
*   **Credential Validation Flow:**
    1.  User submits credentials via `POST /api/credentials/{platform}`.
    2.  Backend securely stores credentials in **Supabase Vault**.
    3.  Creates/updates `platform_accounts` record with Vault reference and 'pending_validation' status.
    4.  (Optional/Platform-Dependent) A background job attempts a simple API call (e.g., get app details) using the stored credentials (retrieved from Vault) to validate them.
    5.  Updates `platform_accounts.status` to 'valid' or 'invalid' based on the validation attempt.
*   **OAuth Connection Flow:**
    1.  User clicks 'Connect' in Frontend UI.
    2.  Frontend redirects to `GET /api/auth/link/{platform}`.
    3.  Backend retrieves the **user's developer credentials from Vault** using the reference in `platform_accounts`.
    4.  Backend constructs the platform's OAuth authorization URL using the retrieved credentials and redirects the user.
    5.  User authorizes on the platform site.
    6.  Platform redirects back to the configured callback URL (`/api/auth/callback/{platform}`).
    7.  Backend callback handler receives the authorization code.
    8.  Backend exchanges the code for access/refresh tokens using the **user's developer credentials (retrieved from Vault)**.
    9.  Backend securely stores the tokens **(likely in Vault)** and updates the `platform_accounts` record (Vault references, status='connected', scopes).
    10. Redirects user back to the frontend settings page.
DATABASE_URL=
JWT_SECRET=
SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=
# PGP_SODIUM_KEY_ID= # If using pgsodium directly, likely managed by Supabase Vault now
PAYMENT_GATEWAY_SECRET_KEY=
VPS_SSH_HOST=
VPS_SSH_USER=
EXTERNAL_API_RATE_LIMIT=
# TIKTOK_CLIENT_ID= # Generally removed - user provides
# TIKTOK_CLIENT_SECRET=
# INSTAGRAM_CLIENT_ID=
# INSTAGRAM_CLIENT_SECRET=
# YOUTUBE_CLIENT_ID=
# YOUTUBE_CLIENT_SECRET=