1. users (Profiles Table) - Subject Attributes

Purpose: Stores public profile info and application-specific attributes, linked to auth.users. Central source for Subject attributes.
SQL Definition:

CREATE TABLE public.users (
  id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE, -- Subject ID
  email TEXT UNIQUE, -- Subject Attribute (Sync from auth.users if needed)
  role TEXT NOT NULL DEFAULT 'free_user', -- Subject Attribute (Effective role, potentially updated by subscription status)
  status TEXT NOT NULL DEFAULT 'active', -- Subject Attribute ('active', 'suspended', 'pending_verification')
  display_name TEXT, -- Subject Attribute
  avatar_url TEXT, -- Subject Attribute
  -- No direct subscription_id link here; role managed via triggers/functions based on subscriptions table
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(), -- Subject Attribute
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Enable RLS
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;

-- Policies (Examples)
CREATE POLICY "Allow users to view own profile" ON public.users
  FOR SELECT USING (auth.uid() = id);
CREATE POLICY "Allow users to update own profile" ON public.users
  FOR UPDATE USING (auth.uid() = id) WITH CHECK (auth.uid() = id);
CREATE POLICY "Allow admin to view all profiles" ON public.users -- For admin panel/support
  FOR SELECT USING (public.is_admin(auth.uid())); -- Assumes is_admin() helper function

-- Trigger for updated_at
CREATE TRIGGER handle_updated_at BEFORE UPDATE ON public.users
  FOR EACH ROW EXECUTE PROCEDURE moddatetime (updated_at);
ABAC Attributes: id, role, status, created_at.

2. subscriptions Table - Resource & Subject Attribute Source

Purpose: Manages subscription plans. Its status directly influences the user's effective role and permissions (Subject attributes).
SQL Definition:

CREATE TABLE public.subscriptions (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(), -- Resource ID
  user_id UUID NOT NULL UNIQUE REFERENCES public.users(id) ON DELETE CASCADE, -- Link to Subject
  plan_id TEXT NOT NULL, -- Resource/Subject Attribute (e.g., 'free', 'starter', 'pro')
  status TEXT NOT NULL, -- Resource/Subject Attribute ('active', 'trialing', 'past_due', 'canceled', 'incomplete')
  current_period_start TIMESTAMPTZ NOT NULL, -- Resource Attribute
  current_period_end TIMESTAMPTZ NOT NULL, -- Resource Attribute
  cancel_at_period_end BOOLEAN NOT NULL DEFAULT false, -- Resource Attribute
  stripe_customer_id TEXT UNIQUE,
  stripe_subscription_id TEXT UNIQUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_subscriptions_user_id ON public.subscriptions(user_id);

-- Enable RLS
ALTER TABLE public.subscriptions ENABLE ROW LEVEL SECURITY;

-- Policies (Examples)
CREATE POLICY "Allow user to view own subscription" ON public.subscriptions
  FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Allow admin to view subscriptions" ON public.subscriptions -- For support/billing
  FOR SELECT USING (public.is_admin(auth.uid()));
-- Note: Updates likely handled by backend service/webhooks interacting with payment gateway

-- Trigger for updated_at
CREATE TRIGGER handle_updated_at BEFORE UPDATE ON public.subscriptions
  FOR EACH ROW EXECUTE PROCEDURE moddatetime (updated_at);

-- Trigger/Function (Conceptual): Update users.role based on subscription status changes
-- CREATE FUNCTION update_user_role_from_subscription() RETURNS TRIGGER...;
-- CREATE TRIGGER subscription_change_updates_user_role AFTER INSERT OR UPDATE ON public.subscriptions...;
ABAC Attributes: id, user_id, plan_id, status, current_period_end. These attributes are crucial for helper functions determining user capabilities (e.g., can_request_clip, can_access_premium_analytics).

3. creators Table - Resource

Purpose: Stores info about content creators monitored by the platform.
SQL Definition: (Largely unchanged, but RLS examples refined)

CREATE TABLE public.creators (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(), -- Resource ID
  name TEXT NOT NULL, -- Resource Attribute
  platform TEXT NOT NULL, -- Resource Attribute ('tiktok', 'youtube', 'instagram')
  platform_creator_id TEXT NOT NULL, -- Resource Attribute
  profile_url TEXT, -- Resource Attribute
  avatar_url TEXT, -- Resource Attribute
  monitored_status TEXT NOT NULL DEFAULT 'active', -- Resource Attribute ('active', 'inactive', 'requested')
  last_checked_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (platform, platform_creator_id)
);

CREATE INDEX idx_creators_platform_id ON public.creators(platform, platform_creator_id);
CREATE INDEX idx_creators_name ON public.creators(name);

-- Enable RLS
ALTER TABLE public.creators ENABLE ROW LEVEL SECURITY;

-- Policies (Examples using ABAC helper functions)
CREATE POLICY "Allow read access based on subscription" ON public.creators
  FOR SELECT USING (public.has_permission(auth.uid(), 'creators', jsonb_build_object('action', 'read', 'status', monitored_status)));
  -- has_permission would check user's role/plan_id from users/subscriptions
CREATE POLICY "Allow admin full management" ON public.creators
  FOR ALL USING (public.is_admin(auth.uid())) WITH CHECK (public.is_admin(auth.uid()));

-- Trigger for updated_at
CREATE TRIGGER handle_updated_at BEFORE UPDATE ON public.creators
  FOR EACH ROW EXECUTE PROCEDURE moddatetime (updated_at);
ABAC Attributes: id, platform, monitored_status.

4. source_content Table - Resource (Replaces stream_vods)

Purpose: Stores metadata about various types of indexed content (Streams, VODs, TikToks, Shorts, Reels). Central Resource for clipping.
SQL Definition:

CREATE TYPE public.content_type AS ENUM ('stream_vod', 'tiktok_video', 'youtube_short', 'instagram_reel', 'other');
CREATE TYPE public.content_status AS ENUM ('pending_metadata', 'metadata_ready', 'processing_media', 'ready_for_clipping', 'error', 'unavailable');

CREATE TABLE public.source_content (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(), -- Resource ID
  creator_id UUID REFERENCES public.creators(id) ON DELETE SET NULL, -- Resource Attribute (Link to Creator, nullable if source unknown)
  platform TEXT NOT NULL, -- Resource Attribute ('tiktok', 'youtube', 'instagram', 'kick', etc.)
  platform_content_id TEXT NOT NULL, -- Resource Attribute (Platform's unique ID for the video/VOD)
  content_type public.content_type NOT NULL, -- Resource Attribute (Type of content)
  title TEXT, -- Resource Attribute
  description TEXT, -- Resource Attribute
  published_at TIMESTAMPTZ, -- Resource Attribute
  duration_seconds NUMERIC(10, 3), -- Resource Attribute
  thumbnail_url TEXT, -- Resource Attribute
  source_url TEXT, -- Resource Attribute (Link to original content on platform)
  embed_url TEXT, -- Resource Attribute (If provided by API)
  media_local_path TEXT, -- Resource Attribute (Internal path if downloaded/cached, handle securely)
  status public.content_status NOT NULL DEFAULT 'pending_metadata', -- Resource Attribute
  last_checked_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(), -- Resource Attribute
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (platform, platform_content_id) -- Ensure uniqueness per platform
);

-- Indexes
CREATE INDEX idx_source_content_creator_id ON public.source_content(creator_id);
CREATE INDEX idx_source_content_platform_id ON public.source_content(platform, platform_content_id);
CREATE INDEX idx_source_content_published_at ON public.source_content(published_at DESC);
CREATE INDEX idx_source_content_status ON public.source_content(status);
CREATE INDEX idx_source_content_type ON public.source_content(content_type);


-- Enable RLS
ALTER TABLE public.source_content ENABLE ROW LEVEL SECURITY;

-- Policies (Examples using ABAC helper functions)
CREATE POLICY "Allow read access to ready content based on subscription" ON public.source_content
  FOR SELECT USING (
    status = 'ready_for_clipping' AND
    public.has_permission(auth.uid(), 'source_content', jsonb_build_object('action', 'read', 'platform', platform, 'content_type', content_type))
  );
  -- has_permission checks user role/plan against allowed platforms/types
CREATE POLICY "Allow admin full management" ON public.source_content
  FOR ALL USING (public.is_admin(auth.uid())) WITH CHECK (public.is_admin(auth.uid()));

-- Trigger for updated_at
CREATE TRIGGER handle_updated_at BEFORE UPDATE ON public.source_content
  FOR EACH ROW EXECUTE PROCEDURE moddatetime (updated_at);
ABAC Attributes: id, creator_id, platform, content_type, published_at, status, created_at.

5. raw_clip_requests Table - Resource

Purpose: Tracks user requests for raw clips from source_content.
SQL Definition: (Updated foreign key to source_content)

CREATE TYPE public.clip_request_status AS ENUM ('pending', 'queued', 'processing', 'ready', 'downloaded', 'expired', 'failed', 'cancelled');

CREATE TABLE public.raw_clip_requests (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(), -- Resource ID
  user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE, -- Resource Attribute (Owner ID) & Link to Subject
  source_content_id UUID NOT NULL REFERENCES public.source_content(id) ON DELETE CASCADE, -- Resource Attribute (Link to Source Content)
  start_time_seconds NUMERIC(10, 3) NOT NULL, -- Resource Attribute
  end_time_seconds NUMERIC(10, 3) NOT NULL, -- Resource Attribute
  status public.clip_request_status NOT NULL DEFAULT 'pending', -- Resource Attribute
  download_url TEXT, -- Resource Attribute (Temporary, secure)
  url_expires_at TIMESTAMPTZ, -- Resource Attribute
  error_message TEXT, -- Resource Attribute
  processing_job_id TEXT, -- Optional link to backend job ID
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(), -- Resource Attribute
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT positive_duration CHECK (end_time_seconds > start_time_seconds)
);

-- Indexes
CREATE INDEX idx_raw_clip_requests_user_id_created ON public.raw_clip_requests(user_id, created_at DESC);
CREATE INDEX idx_raw_clip_requests_status ON public.raw_clip_requests(status);
CREATE INDEX idx_raw_clip_requests_source_content_id ON public.raw_clip_requests(source_content_id);

-- Enable RLS
ALTER TABLE public.raw_clip_requests ENABLE ROW LEVEL SECURITY;

-- Policies (Examples using ABAC helper functions)
CREATE POLICY "Allow user access to own requests" ON public.raw_clip_requests
  FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Allow user to create requests based on permissions" ON public.raw_clip_requests
  FOR INSERT WITH CHECK (
    auth.uid() = user_id AND
    public.has_permission(auth.uid(), 'raw_clip_requests', jsonb_build_object('action', 'create'))
    -- has_permission checks subscription, usage limits, potentially source_content status
  );
CREATE POLICY "Allow user to cancel pending requests" ON public.raw_clip_requests
  FOR UPDATE USING (auth.uid() = user_id AND status IN ('pending', 'queued')) -- Only allow update if cancelling
  WITH CHECK (status = 'cancelled'); -- Can only update TO cancelled status
CREATE POLICY "Allow admin read access" ON public.raw_clip_requests
  FOR SELECT USING (public.is_admin(auth.uid()));

-- Trigger for updated_at
CREATE TRIGGER handle_updated_at BEFORE UPDATE ON public.raw_clip_requests
  FOR EACH ROW EXECUTE PROCEDURE moddatetime (updated_at);
ABAC Attributes: id, user_id, source_content_id, status, created_at, url_expires_at.

6. platform_accounts Table - Resource & Subject Link

Purpose: Securely stores connection details and **user-provided developer credentials** (via Vault) for users' linked social media accounts.
SQL Definition: (**Revised for Supabase Vault usage**)

-- Requires Vault extension enabled
-- CREATE TYPE public.credentials_status AS ENUM ('pending', 'valid', 'invalid', 'expired'); -- Already created or handled by migration

CREATE TABLE public.platform_accounts (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(), -- Resource ID
  user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE, -- Link to Subject
  platform TEXT NOT NULL, -- Resource Attribute ('tiktok', 'instagram', 'youtube')

  -- User-provided Developer Credentials (References secrets in Vault)
  client_id_secret_id UUID REFERENCES vault.secrets(id) ON DELETE SET NULL,      -- Link to Vault secret for Client ID
  client_secret_secret_id UUID REFERENCES vault.secrets(id) ON DELETE SET NULL,  -- Link to Vault secret for Client Secret
  developer_app_name TEXT,          -- Optional: User-provided name for their app
  credentials_status public.credentials_status NOT NULL DEFAULT 'pending', -- Resource Attribute

  -- Platform User Info (Obtained via OAuth using user's credentials)
  platform_user_id TEXT,             -- Resource Attribute (Nullable until valid connection)
  platform_username TEXT,            -- Resource Attribute
  
  -- Tokens obtained using user's credentials (References secrets in Vault)
  access_token_secret_id UUID REFERENCES vault.secrets(id) ON DELETE SET NULL,   -- Link to Vault secret for Access Token
  refresh_token_secret_id UUID REFERENCES vault.secrets(id) ON DELETE SET NULL, -- Link to Vault secret for Refresh Token
  
  scopes_granted TEXT,             -- Resource Attribute (Permissions granted by user via their app)
  expires_at TIMESTAMPTZ,           -- Resource Attribute (Token expiry - obtained from platform)
  last_refreshed_at TIMESTAMPTZ,
  connection_status TEXT NOT NULL DEFAULT 'pending_credentials', -- Resource Attribute ('pending_credentials', 'needs_reauth', 'active', 'revoked', 'error')
  last_error_message TEXT,         -- Store last connection/validation error

  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (user_id, platform)
);

CREATE INDEX idx_platform_accounts_user_id ON public.platform_accounts(user_id);
CREATE INDEX idx_platform_accounts_credentials_status ON public.platform_accounts(credentials_status);
CREATE INDEX idx_platform_accounts_connection_status ON public.platform_accounts(connection_status);

-- Enable RLS
ALTER TABLE public.platform_accounts ENABLE ROW LEVEL SECURITY;

-- Policies (Examples - Restrict access, focus on metadata)
CREATE POLICY "Allow user to manage own linked accounts (metadata only)" ON public.platform_accounts
  FOR ALL USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);
-- IMPORTANT: Access to the actual secrets requires joining with vault.decrypted_secrets,
-- which itself needs appropriate GRANT privileges, typically restricted to backend roles/functions.
-- The default authenticated role should NOT have SELECT on vault.decrypted_secrets.
GRANT SELECT (
    id, user_id, platform, developer_app_name, credentials_status, 
    platform_user_id, platform_username, scopes_granted, expires_at, 
    connection_status, last_error_message, created_at, updated_at
    -- Note: We DO NOT grant SELECT on *_secret_id columns to the standard authenticated role
  ) ON public.platform_accounts TO authenticated;

-- Trigger for updated_at
CREATE TRIGGER handle_updated_at BEFORE UPDATE ON public.platform_accounts
  FOR EACH ROW EXECUTE PROCEDURE moddatetime (updated_at);
  
ABAC Attributes: id, user_id, platform, credentials_status, connection_status, scopes_granted, expires_at.

7. api_keys Table - Resource & Subject Credential

Purpose: Manages API keys generated by users.
SQL Definition: (Largely unchanged, RLS refined)

CREATE TABLE public.api_keys (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(), -- Resource ID
  user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE, -- Resource Attribute (Owner ID) & Link to Subject
  key_hash TEXT NOT NULL UNIQUE, -- Hashed API key (Subject Credential Attribute)
  key_prefix TEXT NOT NULL UNIQUE, -- Resource Attribute (For identification)
  label TEXT, -- Resource Attribute
  scopes TEXT NOT NULL, -- Resource Attribute (Permissions associated with the key)
  last_used_at TIMESTAMPTZ, -- Resource Attribute
  expires_at TIMESTAMPTZ, -- Resource Attribute
  revoked BOOLEAN NOT NULL DEFAULT false, -- Resource Attribute
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(), -- Resource Attribute
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_api_keys_user_id ON public.api_keys(user_id);
CREATE INDEX idx_api_keys_key_prefix ON public.api_keys(key_prefix);

-- Enable RLS
ALTER TABLE public.api_keys ENABLE ROW LEVEL SECURITY;

-- Policies (Examples - Restrict hash access)
CREATE POLICY "Allow user to manage own API keys (metadata only)" ON public.api_keys
  FOR ALL USING (auth.uid() = user_id)
  WITH CHECK (
    auth.uid() = user_id AND
    public.has_permission(auth.uid(), 'api_keys', jsonb_build_object('action', 'create')) -- Check if plan allows API keys
  );
-- IMPORTANT: Use column-level security or views to prevent SELECT on key_hash by default user roles.
-- GRANT SELECT (id, user_id, key_prefix, label, scopes, last_used_at, expires_at, revoked, created_at, updated_at) ON public.api_keys TO authenticated;
-- Key validation happens in backend/API gateway by hashing the provided key and comparing to key_hash.

-- Trigger for updated_at
CREATE TRIGGER handle_updated_at BEFORE UPDATE ON public.api_keys
  FOR EACH ROW EXECUTE PROCEDURE moddatetime (updated_at);
ABAC Attributes: id, user_id, scopes, revoked, expires_at, created_at, last_used_at.

8. analytics_reports Table - Resource

Purpose: Stores pre-computed or cached analytics data.
SQL Definition: (Largely unchanged, RLS refined)

CREATE TABLE public.analytics_reports (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(), -- Resource ID
  report_type TEXT NOT NULL, -- Resource Attribute (e.g., 'trending_creators_daily', 'topic_velocity_hourly', 'user_crm_summary')
  time_period_start TIMESTAMPTZ NOT NULL, -- Resource Attribute
  time_period_end TIMESTAMPTZ NOT NULL, -- Resource Attribute
  filters JSONB, -- Resource Attribute (e.g., {"platform": "tiktok"})
  data JSONB NOT NULL, -- Resource Attribute (The report payload)
  generated_at TIMESTAMPTZ NOT NULL DEFAULT now(), -- Resource Attribute
  user_id UUID REFERENCES public.users(id) ON DELETE CASCADE, -- Resource Attribute (Owner ID, NULL for public/aggregated reports)
  access_level TEXT NOT NULL DEFAULT 'public', -- Resource Attribute ('public', 'premium', 'private_crm')
  UNIQUE (report_type, time_period_start, time_period_end, filters, user_id)
);

CREATE INDEX idx_analytics_reports_lookup ON public.analytics_reports(report_type, time_period_end DESC, user_id, access_level);
CREATE INDEX idx_analytics_reports_user_id ON public.analytics_reports(user_id) WHERE user_id IS NOT NULL;

-- Enable RLS
ALTER TABLE public.analytics_reports ENABLE ROW LEVEL SECURITY;

-- Policies (Examples using ABAC helper functions)
CREATE POLICY "Allow access based on report access level and user subscription" ON public.analytics_reports
  FOR SELECT USING (
    public.has_permission(auth.uid(), 'analytics_reports', jsonb_build_object('action', 'read', 'report_access_level', access_level, 'report_owner_id', user_id))
  );
  -- has_permission checks if user's plan allows access to 'public' or 'premium' reports,
  -- OR if the report is 'private_crm' and user_id matches auth.uid()
CREATE POLICY "Allow admin full management" ON public.analytics_reports
  FOR ALL USING (public.is_admin(auth.uid())) WITH CHECK (public.is_admin(auth.uid()));
-- Note: Inserts/Updates likely handled by a trusted backend service/job

ABAC Attributes: id, report_type, time_period_end, filters, user_id, access_level, generated_at.

9. (Conceptual) usage_counters Table - Resource & Subject Attribute Source

Purpose: Tracks resource usage (e.g., clip downloads, API calls) per user per billing period. Crucial for enforcing limits in ABAC helper functions.
SQL Definition (Conceptual):

CREATE TABLE public.usage_counters (
  user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  billing_period_start TIMESTAMPTZ NOT NULL,
  metric TEXT NOT NULL, -- e.g., 'clip_downloads', 'api_calls_analytics', 'storage_gb'
  count BIGINT NOT NULL DEFAULT 0,
  PRIMARY KEY (user_id, billing_period_start, metric)
);

-- RLS: Likely only accessible/updatable by backend services/triggers, not directly by users.
ABAC Attributes: user_id, billing_period_start, metric, count. Used by helper functions like can_request_clip.