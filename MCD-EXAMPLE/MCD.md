**Main Context Document: Centralized Video Clip Analytics Platform**

**(Introduction Note:** This document serves as the Main Context Document (MCD), a comprehensive operational blueprint designed to minimize ambiguity and provide a single source of truth for development. It applies the principles of Cognitive Empathy, translating human intent into the explicit, structured information required for reliable system implementation, bridging the gap between intuitive human communication and the deterministic needs of system logic, as detailed in the foundational report "Defining and Structuring a Main Context Document...".)

**1. Overview & Goals**

*   **Project Vision:** To establish a premier, centralized Software-as-a-Service (SaaS) platform using **Supabase (Database/Auth)** and a **React Vite/HeroUI frontend**. This platform equips content creators, clipping specialists, and potentially AI systems with efficient access to **raw video segments** from major streaming platforms (initially TikTok, Instagram, YouTube) and provides sophisticated, real-time analytics on clip trends, creator performance, and content engagement within the "Brain Rot" and adjacent digital content ecosystems. The platform aims to function as an indispensable intelligence hub, analogous to a **"Bloomberg Terminal for viral clips"**.
    *   *Context:* This vision represents a strategic pivot from an initial concept of a pre-edited clip marketplace. The pivot was driven by understanding the technical constraints of platform **duplicate content hashing/fingerprinting**, recognizing that providing raw materials empowers users to create unique content, thus avoiding platform penalties. The core value proposition lies in providing these raw materials combined with actionable market intelligence.
*   **Primary Goals:**
    *   Aggregate and index stream/VOD metadata from designated creators across target platforms, subject to **API availability and permissions**.
    *   Develop an intuitive interface (React/HeroUI) for users to discover relevant content and precisely select segments for download as raw video clips.
    *   Implement a robust analytics engine providing real-time and historical insights into clip popularity, velocity, creator influence, and topic trends, leveraging **Supabase** for data storage.
    *   Offer a consolidated Creator CRM dashboard for users to monitor and analyze their own cross-platform performance metrics (TikTok, Instagram, YouTube) via authenticated API connections, secured by **Supabase Auth and RLS**.
    *   Design and expose a secure, well-documented external API for programmatic access by authorized third-party applications.
    *   Establish a sustainable business model based on user value (likely subscription tiers).
*   **Scope:**
    *   *In Scope (Initial):*
        *   Core Platform: Web application (React Vite/HeroUI), user registration/authentication (**Supabase Auth**), subscription management, payment gateway integration.
        *   Data Sources: Initial focus on TikTok, Instagram, YouTube APIs, acknowledging **significant feasibility constraints** detailed in Sec 2.
        *   Content Focus: Primarily streams, VODs relevant to "Brain Rot" and similar niches.
        *   Features: **Raw clip** discovery/download, Creator CRM dashboard (authenticated data via **Supabase**), analytics dashboard ("Bloomberg" view - scope dependent on public data access), external API (read-access initially).
        *   Infrastructure: **Supabase** for DB/Auth/Functions (where applicable), **VPS** for specialized backend services (e.g., video processing).
    *   *Out of Scope (Initial):*
        *   User uploading/hosting of *edited* clips.
        *   In-platform video editing.
        *   Advanced predictive modeling (explicitly deferred).
        *   Direct editing software integration.
        *   Support for platforms beyond the initial three.
        *   Features relying heavily on data not reliably accessible via official APIs or compliant alternative methods (especially for the public "Bloomberg" view).
*   **Success Criteria:**
    *   Achieve target user acquisition and retention metrics.
    *   Maintain high data accuracy and low latency for analytics reporting.
    *   Positive user feedback scores (> Y) regarding usability (HeroUI), clip accessibility, and analytics value.
    *   Successfully navigate and maintain compliance with platform API terms of service.
    *   Demonstrate API stability and adoption by intended third-party systems.
    *   Reliable integration with **Supabase** for Auth and Database operations, including effective RLS implementation.
    *   Successfully mitigate risks associated with **external API limitations**.

**2. Context & Architecture**

*   **Overall System Context:** A cloud-hosted, multi-tenant SaaS application. Frontend built with **React Vite/HeroUI**, utilizing **Supabase** for primary Database (PostgreSQL), Auth, and potentially Functions. Interacts externally with social media APIs (TikTok, Instagram, YouTube) and payment gateways. Backend logic may reside in **Supabase Functions** or dedicated services hosted on a **VPS** (e.g., for FFmpeg). **Crucially, authentication and API interactions with external platforms (TikTok, etc.) will rely on user-provided developer credentials (Client ID/Secret) stored securely in the database, rather than platform-level secrets.**
    *   *Context:* The detailed nature of this MCD is driven by **Cognitive Empathy**, recognizing the need for explicit instructions for system development. The platform's strategic positioning aligns more closely with a premium **"Bloomberg Terminal"** model (focused analytics, raw materials) rather than a free, broad "Wikipedia" model, influencing feature prioritization and monetization. **The decision to use user-provided credentials significantly impacts user experience and security posture, requiring careful implementation.**
*   **Key Concepts & Terminology:**
    *   *MCD (Main Context Document):* This document; the operational blueprint.
    *   *Cognitive Empathy:* Understanding the system's perspective to provide clear instructions.
    *   *Raw Clip:* Unedited video segment extracted directly from source VOD/stream.
    *   *Brain Rot Content:* Specific short-form video style characterized by multi-layered stimuli, rapid pacing, often using memes/repetitive audio.
    *   *Hashing/Fingerprinting:* Algorithmic techniques (e.g., perceptual hashing) used by platforms to detect duplicate content.
    *   *Creator CRM:* Platform section for authenticated creators to monitor their cross-platform performance.
    *   *Analytics Dashboard:* Platform section displaying aggregated market trends and insights ("Bloomberg" view).
    *   *Authenticated Data Path:* Data acquisition relying on user OAuth permissions (e.g., for CRM). Generally richer data.
    *   *Public Data Path:* Data acquisition relying on public API endpoints or other methods (e.g., for "Bloomberg" view). Generally more limited data.
    *   *Supabase:* Backend-as-a-Service used for DB, Auth, Functions, Storage.
    *   *RLS (Row Level Security):* Supabase feature for fine-grained data access control.
    *   *HeroUI:* UI component library used with Tailwind CSS.
    *   *Vite:* Frontend build tool.
    *   *VPS (Virtual Private Server):* Hosting for specialized backend services.
    *   *User-Provided Credentials:** Client ID and Client Secret obtained by the end-user from registering their *own* developer application with an external platform (e.g., TikTok). Stored securely in **Supabase Vault**, with references (UUIDs) stored in the `platform_accounts` table.
    *   *Supabase Vault:** Secure storage service within Supabase used for sensitive data like API keys and secrets.
    *   *Platform-Level Credentials:* (Standard OAuth approach - **NOT used for user data connections in this architecture**) Credentials for a single app registered by the SaaS platform owner, typically stored in environment variables.
*   **Mermaid Architecture Diagram(s):**

    ```mermaid
    graph TD;
        subgraph External Services
            TikTok_API;
            Instagram_API[Instagram Graph API];
            YouTube_API;
            Payment_Gateway[Payment Gateway];
            Supabase_Auth[Supabase Auth];
            Supabase_DB[Supabase Database (Postgres)];
            Supabase_Functions[Supabase Functions (Optional)];
        end

        subgraph Clip_Analytics_Platform
            Frontend[React Vite Frontend (HeroUI)];
            Backend_API[Backend API (VPS/Functions)];
            Data_Ingestion;
            Video_Processing;
            Analytics_Engine[Analytics Engine];
            External_API_Gateway[External API Gateway];
        end

        Frontend --> Supabase_Auth;
        Frontend --> Supabase_DB; # Via Supabase SDK with RLS
        Frontend --> Backend_API;
        Frontend --> Supabase_Functions; # Via Supabase SDK

        Backend_API --> Data_Ingestion;
        Backend_API --> Video_Processing; # Likely on VPS
        Backend_API --> Analytics_Engine; # Potentially heavy lifting on VPS
        Backend_API --> Supabase_DB; # Using Service Role Key securely
        Backend_API --> External_API_Gateway;
        Backend_API --> Payment_Gateway;
        Backend_API --> Supabase_Auth; # For server-side auth checks

        Data_Ingestion --> TikTok_API;
        Data_Ingestion --> Instagram_API;
        Data_Ingestion --> YouTube_API;
        Data_Ingestion --> Supabase_DB;

        Video_Processing --> Supabase_DB; # Storing clip metadata/status

        Analytics_Engine --> Supabase_DB;

        External_API_Gateway --> Backend_API;

        Supabase_Functions --> Supabase_DB; # Using secure client
        Supabase_Functions --> Supabase_Auth;
        Supabase_Functions --> External Services; # e.g., calling Platform APIs
    ```
    *(Diagram Explanation): The diagram shows the user interacting with the Frontend UI, which communicates with the Backend API Gateway. The Backend orchestrates calls to various internal services (Auth, Ingestion, Processing, Analytics) and external services (Platform APIs, Payment Gateway). Data flows from external APIs via the Ingestion service into the Databases, is processed by the Video Processing and Analytics Engines, and results are served back through the Backend API to the Frontend or the External API Gateway.* **OAuth flows and data ingestion rely on fetching and securely decrypting the specific user's developer credentials (Client ID/Secret, stored as references in `platform_accounts` pointing to `vault.secrets`) to interact with external APIs.**

*   **Technology Stack:**
    *   Hosting: **Supabase** (Frontend Hosting, DB, Auth, Functions); **VPS** (e.g., DigitalOcean) for backend services (FFmpeg, heavy analytics); Linux OS.
    *   Backend: **Supabase Functions** (TypeScript/Deno) where feasible; **Node.js (Express) or Python (Flask/Django)** on VPS for heavier tasks.
    *   Frontend: **React (Vite)**.
    *   UI Library: **HeroUI** (with **Tailwind CSS**).
    *   Database: **Supabase (PostgreSQL)**.
    *   Authentication: **Supabase Auth**.
    *   Video Processing: **FFmpeg** library/tooling (run via Backend API on VPS).
    *   Containerization: **Docker** (Recommended for backend services on VPS).

*   **API Feasibility & Data Acquisition Strategy (Critical Context - MODIFIED):**
    *   The platform's functionality, especially the "Bloomberg" analytics view, is **critically dependent** on data sourced from external platform APIs using **user-provided developer credentials**.
    *   **Significant User Burden & Limitations Exist:** Users must register and manage developer apps on each platform. Access scope, rate limits, eligibility, etc., are now tied to the *user's* developer account and app status, not the platform's. Unofficial methods remain **out of scope**.
    *   **User-Centric Authenticated Data Path:** For the Creator CRM. Relies on users providing valid Client ID/Secret for their developer app on the external platform. The backend uses these credentials to initiate OAuth, obtain user-specific tokens (stored encrypted), and access the user's data via APIs like TikTok Display, Instagram Graph, YouTube Data. The richness and reliability of data depend entirely on the user successfully managing their developer app and its permissions.
    *   **Public Data Path:** For the "Bloomberg" analytics view. This path *might* still use platform-level API keys (if needed and available) stored in environment variables if it accesses purely public, aggregated, non-user-specific data endpoints. However, if public trend analysis relies on aggregating data fetched via *user* credentials, its scope is limited by the number of users who connect valid credentials.
    *   **Risk Mitigation & Security:** This user-centric credential model introduces significant risks. **Storing user-provided Client Secrets (even encrypted) requires extreme security diligence.** The platform must clearly communicate the user's responsibility for managing their developer apps. The platform's ability to provide CRM features is entirely dependent on the user providing and maintaining valid credentials.

*   **Table 1: Platform API Capabilities & Constraints (Summary - MODIFIED CONTEXT):**

    | Platform  | API Name(s) Relevant        | Key Functions/Endpoints        | Data Potentially Accessible (Examples)                                  | Access Requirements / Notes                                                                                             | Key Limitations / Costs                                                                                                                               |
    | :-------- | :-------------------------- | :----------------------------- | :---------------------------------------------------------------------- | :---------------------------------------------------------------------------------------------------------------------- | :---------------------------------------------------------------------------------------------------------------------------------------------------- |
    | TikTok    | Login Kit, Display API      | User Auth, User Info, Videos | Basic Profile, User's Public Videos (Metadata)                          | Dev Account, App Review, User OAuth (specific scopes)                                                                   | Read-only, limited data (no comments/analytics), user's own content focus.                                                                            |
    | TikTok    | Data Portability API        | Data Export                    | User's Data Archive (Posts, Activity, DMs)                              | Specific Application/Approval, User OAuth, Geographic Limits (EEA/UK initially)                                         | Asynchronous export, complex process, not real-time.                                                                                                  |
    | TikTok    | Research API                | Aggregated Public Data         | Anonymized Profiles, Videos, Comments                                   | Restricted to approved researchers (non-profit/academic).                                                               | Not generally available for commercial use.                                                                                                           |
    | Instagram | Basic Display API           | User Profile, Media            | Basic Profile, User's Photos/Videos                                     | User OAuth, App Review.                                                                                                 | Read-only, no Insights/Comments, for non-Pro accounts (Limited use).                                                                                  |
    | Instagram | **Instagram Graph API**     | User, Media, Hashtags, Insights | **Pro Account Profile, Media (Reels), Comments, Mentions, Analytics** | **FB Dev Acc, FB Page linked to IG Pro, User OAuth (FB Login), App Review (permissions)**                               | **Complex setup, requires IG Pro Account, Rate Limits (BUC/Platform), API evolving.** **Primary API for IG CRM & potential public data.**             |
    | YouTube   | **YouTube Data API v3**     | Search, Videos, Channels, Analytics | **Video/Channel Metadata, Comments, User's Analytics (via OAuth)**    | **Google Cloud Project, API Key (public), User OAuth (private/analytics), App Verification**                            | **Quota system (units/day) can be restrictive. Analytics require user permission.** **Primary API for YT CRM & potential public data.**                 |
    *(Note: This is a summary. APIs are subject to change. Thorough investigation and compliance are mandatory.)*
    *   **Access Requirements / Notes:** **Crucially, access now depends on the *end-user* successfully registering *their own developer app* on the respective platform (TikTok Dev, FB Dev, Google Cloud), obtaining Client ID/Secret, and providing these to our platform. Our platform then uses *these user credentials* to initiate the User OAuth flow outlined in the table.** The complexity and review processes mentioned now fall upon the end-user creating their app.
    *   **Key Limitations / Costs:** Quotas, rate limits, data access limitations are now tied to the *user's developer app*, not a central platform app.

**3. Functional Requirements / User Stories**

*(Note: These requirements derive from the deconstructed brainstorming session, aiming for maximum clarity to avoid ambiguity, guided by Cognitive Empathy.)*

*   **User Management & Authentication (Leveraging Supabase Auth):**
    *   As a new user, I can register (email/password or social via Supabase Auth) using HeroUI components. AC: Supabase handles flow, user record created.
    *   As a registered user, I can log in securely (via Supabase Auth) using HeroUI components. AC: Supabase session established.
    *   As a user, I can view subscription plans (using HeroUI). AC: Tiers displayed.
    *   As a user, I can manage my subscription/payment (updates Supabase DB via backend). AC: Status viewable, payment updatable, plan changeable.
    *   As a creator user, I can connect my TikTok, Instagram (Pro), and YouTube accounts via OAuth, **which uses my previously provided developer credentials (retrieved securely from Vault)**, so the platform can fetch my performance data. AC: OAuth flow completes, tokens stored securely **(also potentially in Vault)**, connection status displayed. User can disconnect.
    *   As a creator user, I want to securely provide and update the Client ID and Client Secret for my developer application for each external platform (TikTok, Instagram, YouTube) via the Account Settings page. AC: Credentials encrypted **via Supabase Vault** and references stored in `platform_accounts`. Status updated to 'pending' validation.
    *   As a creator user, I am informed about the status (e.g., 'valid', 'invalid') of my provided developer credentials. AC: Status displayed in Account Settings.
*   **Clip Discovery & Raw Clip Access:**
    *   As a user, I can search for monitored creators (data from Supabase DB). AC: Search works, results shown.
    *   As a user, I can view recent streams/VODs for a creator (metadata from Supabase DB). AC: List displayed.
    *   As a user, I can interact with a VOD timeline (if feasible) to define start/end points for a **raw clip**. AC: Selection possible, times captured.
    *   As a user, I can download the selected **raw video segment** (request via Backend API). AC: Request initiated, subscription checked (Supabase DB), secure link provided. *Context: Providing raw clips requires the user to perform editing externally to create unique content and avoid platform hashing penalties.*
    *   As a premium user, I can see indicators (HeroUI icons) for potentially trending clips (based on analytics in Supabase DB). AC: Indicators appear.
*   **Analytics Dashboard ("Bloomberg" View):**
    *   As a user, I can view a dashboard with aggregated trend data (using HeroUI components). AC: Dashboard displays rankings/charts. *Caveat: Data scope/granularity depends heavily on Public Data Path feasibility (Sec 2).*
    *   As a user, I can view time-series charts for performance trends (creators/topics). AC: Charts visualize metrics (from Supabase DB), interactive.
    *   As a user, I can filter the analytics dashboard (HeroUI controls). AC: Filters work, data updates (queries Supabase DB). *Context: The "Bloomberg" analogy implies sophisticated, potentially premium analytics, distinct from basic listings.*
*   **Creator CRM Dashboard (Authenticated View):**
    *   As an authenticated creator, I can access a private dashboard summarizing my linked accounts' performance (data from Supabase DB, secured by RLS/Backend checks). AC: Dashboard displays KPIs (followers, views, etc.). *Context: This uses the Authenticated Data Path via user OAuth, allowing richer, reliable data for the user's own accounts.*
    *   As an authenticated creator, I can view performance trends over time for my accounts (charts using data from Supabase DB). AC: Charts display metrics over time.
    *   As an authenticated creator, I can see a list of my recent posts with individual metrics (HeroUI table using data from Supabase DB). AC: Table lists posts/metrics.
*   **API Access (for Authorized Systems):**
    *   As an authorized system (e.g., AI clipper), I can authenticate securely (API key validated against Supabase DB via Backend API). AC: Auth works, unauthorized rejected.
    *   As an authorized system, I can query for new VODs/streams (via Backend API, data from Supabase DB). AC: Endpoint returns VOD list.
    *   As an authorized system, I can query for trending analytics data (via Backend API, data from Supabase DB). AC: Endpoint returns trends.
    *   The system shall enforce rate limits on the external API. AC: Rate limit errors (429) returned correctly.

**4. Design Specification**

*   **4.1. UI/UX Design (Frontend - React/HeroUI):**
    *   Wireframes/Mockups: (To Be Created). Utilize **HeroUI** components for clean, modern look. Focus on clarity, data density (for analytics), workflow efficiency. Inspiration from financial terminals & social media analytics tools.
    *   UI Components: Built using **HeroUI** (Buttons, Modals, Forms, Tables, Chart wrappers) for: Auth Forms (Supabase UI or custom), SubscriptionSelector, AccountLinker (now includes credential input/status), CreatorSearch, VODList, VODPlayerInterface, ClipDownloadButton, AnalyticsDashboard, AnalyticsChart, AnalyticsTable, CRMDashboard, CRMMetricsDisplay, APIManagementPanel.
    *   Styling: **Tailwind CSS** utility classes, configured for HeroUI. Responsive design prioritized. Clear data visualization principles.
*   **4.2. API Design (Backend/Shared):**
    *   Approach: RESTful APIs for Backend API (VPS/Functions). Frontend interacts directly with Supabase Auth/DB via SDK (with RLS) and with Backend API for other tasks.
    *   Example Endpoints (Backend API): ... Add endpoints like `POST /api/auth/login`, `GET /api/auth/user`, `POST /api/auth/link/{platform}`, **POST /api/credentials/{platform} (Requires Auth)**, **GET /api/credentials/status (Requires Auth)**, `GET /api/creators?search={query}` ...
    *   Example Schemas (Backend API): (See previous version).
    *   Error Responses: Standard format. Include Supabase-specific errors where relevant. Handle API limitation errors gracefully.
*   **4.3. Data Model / Schema (Supabase - PostgreSQL):**
    *   Tables: `users` (Supabase Auth), `profiles` (extends users, stores subscription, API keys - RLS protected), `Creators`, `source_content` (replaces `StreamVODs`), `RawClipRequests`, `AnalyticsDataPoints`, `PlatformAccounts` (**stores encrypted user-provided Client ID/Secret AND resulting user tokens**, RLS protected), `Subscriptions`, `api_keys`.
    *   Design: Define primary/foreign keys, indexes. **Implement comprehensive RLS policies** for data security, especially `profiles`, `PlatformAccounts`. **Implement SECURITY DEFINER functions for accessing encrypted credentials/tokens.**
*   **4.4. Logic, Flow, and Business Rules:**
    *   Core Logic: Data Ingestion (**securely fetching user credential references from `platform_accounts` and decrypting secrets from Vault**, API polling, error handling, token refresh), Raw Clip Extraction (validation, VOD retrieval, segmentation, secure storage), Analytics Engine (metric calculation, trend identification, aggregation), Monetization Enforcement (subscription/credit checks), Authorization/Authentication (**OAuth flows using user-provided credentials retrieved securely from Vault**, API key validation, access control).
    *   Raw Clip Extraction Workflow: (No change needed in diagram itself, but underlying credential handling changes).
    *   Business Rules: Enforce subscription limits (check Supabase data). Handle external API rate limits. Ensure API compliance. **Securely handle and encrypt user-provided Client ID/Secret AND resulting user tokens in Supabase DB**. Utilize Supabase RLS extensively. Users are responsible for the validity of their provided developer credentials. Implement validation checks for credentials.
*   **Table 2: Key Analytics Metrics & Visualizations (Examples)**

    | Metric Category         | Specific Metric Example                             | Potential Data Source(s)                                                              | Proposed Visualization (HeroUI)        | Relevance to "Bloomberg" Analogy                     | Data Path      |
    | :---------------------- | :-------------------------------------------------- | :------------------------------------------------------------------------------------ | :------------------------------------- | :--------------------------------------------------- | :------------- |
    | Clip Trend              | Clip Velocity Score                                 | Internal Calculation (cross-platform mentions/views)                                  | Line Chart, Ranked List                | Tracking asset momentum/popularity.                  | Public         |
    | Clip Trend              | Cross-Platform Repost Count (Estimated)             | Internal Calculation (tracking similar clips)                                         | Number Display, Bar Chart              | Measuring market activity/volume.                    | Public         |
    | Clip Trend              | Trending Topics/Niches                              | Internal Calculation (Hashtags, NLP)                                                  | Tag Cloud, Ranked List, Bar Chart      | Identifying trending sectors/themes.                 | Public         |
    | Creator Performance     | Aggregate Cross-Platform Views                      | TikTok, Instagram, YouTube APIs (**via User OAuth**)                                  | Line Chart, Scorecard                  | Tracking overall entity performance.                 | Authenticated  |
    | Creator Performance     | Follower Growth Rate                                | TikTok, Instagram, YouTube APIs (**via User OAuth**)                                  | Line Chart                             | Measuring growth trajectory.                         | Authenticated  |
    | Creator Performance     | Engagement Rate per Post                            | TikTok, Instagram, YouTube APIs (**via User OAuth**)                                  | Bar Chart, Line Chart                  | Analyzing efficiency/return.                         | Authenticated  |
    | Creator Performance     | "Clippers per Stream" Index (Estimated)             | Internal Calculation (unique users downloading clips from VOD)                        | Number Display, Line Chart             | Gauging market interest/activity.                    | Public         |
    | Topic/Niche Engagement  | Average Engagement Rate for Topic                   | Internal Calculation (averaging engagement for topic clips)                           | Bar Chart, Line Chart                  | Comparing performance across sectors.                | Public         |
    | Platform Activity       | Clip Download Volume (Overall)                      | Internal Platform Data (Supabase `RawClipRequests`)                                   | Line Chart                             | Overall market volume indicator.                     | Internal       |
    | Platform Activity       | Most Active Creators (by downloads)                 | Internal Platform Data (Supabase `RawClipRequests`)                                   | Ranked List                            | Identifying top market participants.                 | Internal       |
    *(Note: Public path metrics depend heavily on API feasibility. Authenticated path metrics are generally more reliable for the user's own data.)*

**5. Implementation Details & File Structure**

*   Target Directory/Module: (See previous version - structure remains valid). Consider clear separation for VPS backend code vs. Supabase Functions code if both are used.
*   File Structure Plan: (See previous version - structure remains valid).
*   Dependencies: (See previous version - Supabase, React, HeroUI, Tailwind are key). Add platform API SDKs for backend.
*   Environment Variables: DATABASE_URL, JWT_SECRET, ~~TIKTOK_CLIENT_ID~~, ~~TIKTOK_CLIENT_SECRET~~, ~~INSTAGRAM_CLIENT_ID~~, ~~INSTAGRAM_CLIENT_SECRET~~, ~~YOUTUBE_CLIENT_ID~~, ~~YOUTUBE_CLIENT_SECRET~~ (Platform-level credentials removed/commented out as primary flow uses user-provided ones stored in Vault), PAYMENT_GATEWAY_SECRET_KEY, VPS_SSH_HOST, VPS_SSH_USER, EXTERNAL_API_RATE_LIMIT, `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `PGP_SODIUM_KEY_ID` (Or specific Vault key ID).

**6. Implementation Units & Tasks (Agent Instructions)**

*(Based on Phased Rollout - Rationale: Start with CRM using more accessible authenticated APIs first, mitigating risks of public data access.)*

*   **Unit 1: Core Infrastructure & Supabase Auth Setup**
    *   File(s): Supabase config, frontend lib/features/auth/hooks, Infra config (VPS/Dockerfiles, CI/CD).
    *   Purpose: Establish React/Vite/HeroUI structure, set up Supabase (Auth, DB tables, initial RLS), integrate Supabase Auth SDK on frontend.
    *   Agent Task(s): SETUP_SUPABASE_PROJECT (incl. tables, RLS), SETUP_PROJECT_STRUCTURE (React/Vite), INSTALL_DEPENDENCIES, INITIALIZE_SUPABASE_CLIENT_FRONTEND, IMPLEMENT_FRONTEND_AUTH_UI (HeroUI + Supabase), IMPLEMENT_FRONTEND_AUTH_STATE_HOOK, SETUP_VPS_ENVIRONMENT (if needed early), CONFIGURE_FRONTEND_HOSTING, CREATE_BASIC_CI_CD_PIPELINE. **Define initial Supabase RLS policies.**
*   **Unit 2: Platform Account Linking (External OAuth)**
    *   File(s): frontend CRM components, Backend API endpoint/Function, Supabase `PlatformAccounts` table.
    *   Purpose: Implement OAuth flows (initiated from frontend, handled by backend) for external platforms. Securely store tokens in Supabase.
    *   Agent Task(s): REGISTER_APPS_ON_PLATFORMS (TikTok Dev Portal, Facebook Dev Portal, Google Cloud Console) **- Note: This might only be needed for platform-level access if any, user connections use user's apps.** IMPLEMENT_BACKEND_OAUTH_CALLBACK_HANDLERS for each platform (/api/auth/callback/{platform}) **using user-provided credentials retrieved from Vault**. IMPLEMENT_TOKEN_STORAGE_SERVICE (**Store encrypted tokens, potentially in Vault**, associating with `platform_accounts`). CREATE_FRONTEND_ACCOUNT_LINKING_UI (HeroUI).
*   **Unit 3: Creator CRM Data Ingestion (Authenticated Path)**
    *   File(s): Backend service/function, Supabase DB tables.
    *   Purpose: Fetch user's own performance data from linked accounts using stored tokens (Authenticated Data Path). Store results in Supabase.
    *   Agent Task(s): IMPLEMENT_API_CLIENTS for TikTok Display API, Instagram Graph API, YouTube Data API using **user-specific stored tokens (retrieved securely, possibly from Vault)**. DEFINE_DATA_FETCHING_LOGIC, REFINE_SUPABASE_TABLES, IMPLEMENT_BACKGROUND_JOB (Supabase Function/cron), HANDLE_API_ERRORS_AND_RATE_LIMITS.
*   **Unit 4: Creator CRM Frontend Dashboard**
    *   File(s): frontend CRM pages/components (HeroUI).
    *   Purpose: Display fetched authenticated performance data (from Supabase DB) using HeroUI.
    *   Agent Task(s): CREATE_SUPABASE_DB_QUERIES/VIEWS (respecting RLS), BUILD_FRONTEND_DASHBOARD_LAYOUT (HeroUI), IMPLEMENT_DATA_VISUALIZATIONS (HeroUI/charts), FETCH_DATA_FROM_SUPABASE (SDK), ADD_TIME_PERIOD_SELECTOR (HeroUI).
*   **(Subsequent Units - Phased Rollout):**
    *   *Phase 2 (Clip Discovery/Download):* Requires solving VOD access challenge (limited scope initially). Implement video processing (likely VPS).
    *   *Phase 3 ("Bloomberg" Analytics):* Depends on feasibility of sourcing *public* data. Build analytics engine.
    *   *Phase 4 (API & Expansion):* Develop external API. Expand platform reach.

**7. Relationships & Dependencies**

*   **Internal Dependencies:** (See previous version - CRM depends on Auth, Analytics depends on Ingestion, etc.). Frontend depends heavily on HeroUI & Supabase SDK. Analytics quality depends on success of *both* Authenticated and Public data paths.
*   **External Dependencies:**
    *   **CRITICAL: Supabase** (Auth, DB, Functions, SDK).
    *   **CRITICAL: External Platform APIs** (Availability, Stability, Terms, Limits - Significant Risk).
    *   VPS Provider (if used).
    *   Payment Gateway.
    *   HeroUI/Tailwind CSS.
    *   Third-Party Libraries.

**8. Testing Notes (Optional)**

*   Unit Tests: Frontend components (React Testing Library), Supabase client mocks, backend/function logic mocks.
*   Integration Tests: Frontend <-> Backend API, Frontend <-> Supabase SDK (direct), Backend <-> Supabase DB, Ingestion -> Supabase DB. **Test Supabase RLS policies thoroughly.** Test external OAuth flows. Test error handling for API limits/failures.
*   Manual Testing: End-to-end flows (Registration, Login, Linking, Discovery, Download, Analytics, CRM, Subscription). Cross-browser testing. Data accuracy verification (UI vs. Supabase DB).

**9. Agent Instructions & Considerations**

*   **Processing Order:** Implement Units sequentially following Phased Rollout (1-4 first). Prioritize backend APIs/Functions needed for frontend features.
*   **File Locking:** Standard Git practices. Coordinate changes to Supabase schema/RLS.
*   **Assistance/Partitioning (Complex Areas):**
    *   **Designing and implementing robust Supabase RLS policies.**
    *   **Securely handling and encrypting external platform tokens in Supabase.**
    *   **Navigating external API limitations, compliance, and rate limits (Critical).**
    *   Efficient video processing pipeline (FFmpeg on VPS).
    *   Scalable design of analytics queries against Supabase DB.
    *   **Deciding optimal split between Supabase Functions vs. VPS backend services.**
*   **Code Style:** Adhere to React/Tailwind/HeroUI best practices. ESLint/Prettier (frontend). Consistent naming. Comment Supabase schema/RLS/Functions logic clearly.

**(Conclusion Note:** This enriched MCD provides the detailed, unambiguous context needed for development, incorporating insights from the foundational report and transcript analysis. It acknowledges the strategic pivot, clarifies the "Bloomberg" analogy, highlights critical API dependencies and risks, and outlines a phased approach using Supabase, React, and HeroUI.)