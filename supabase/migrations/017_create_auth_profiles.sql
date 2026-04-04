-- User profile table linked to Supabase Auth users
CREATE TABLE IF NOT EXISTS public.profiles (
  id uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  username text NOT NULL,
  first_name text NOT NULL,
  last_name text NOT NULL,
  email text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT timezone('utc', now()),
  updated_at timestamptz NOT NULL DEFAULT timezone('utc', now()),
  CONSTRAINT profiles_username_format CHECK (
    username ~ '^[a-z0-9](?:[a-z0-9._-]{1,28}[a-z0-9])?$'
  ),
  CONSTRAINT profiles_first_name_nonempty CHECK (char_length(trim(first_name)) > 0),
  CONSTRAINT profiles_last_name_nonempty CHECK (char_length(trim(last_name)) > 0)
);

CREATE UNIQUE INDEX IF NOT EXISTS profiles_username_lower_unique_idx
  ON public.profiles (lower(username));

CREATE UNIQUE INDEX IF NOT EXISTS profiles_email_lower_unique_idx
  ON public.profiles (lower(email));

ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "profiles_select_own"
  ON public.profiles
  FOR SELECT
  TO authenticated
  USING (auth.uid() = id);

CREATE POLICY "profiles_update_own"
  ON public.profiles
  FOR UPDATE
  TO authenticated
  USING (auth.uid() = id)
  WITH CHECK (auth.uid() = id);

CREATE OR REPLACE FUNCTION public.sync_profile_updated_at()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  NEW.updated_at := timezone('utc', now());
  RETURN NEW;
END;
$$;

CREATE TRIGGER trg_profiles_updated_at
  BEFORE UPDATE ON public.profiles
  FOR EACH ROW
  EXECUTE FUNCTION public.sync_profile_updated_at();

CREATE OR REPLACE FUNCTION public.handle_new_auth_user()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  INSERT INTO public.profiles (id, username, first_name, last_name, email)
  VALUES (
    NEW.id,
    COALESCE(
      NULLIF(lower(trim(NEW.raw_user_meta_data ->> 'username')), ''),
      'user_' || substr(replace(NEW.id::text, '-', ''), 1, 10)
    ),
    COALESCE(NULLIF(trim(NEW.raw_user_meta_data ->> 'first_name'), ''), 'New'),
    COALESCE(NULLIF(trim(NEW.raw_user_meta_data ->> 'last_name'), ''), 'User'),
    COALESCE(lower(trim(NEW.email)), '')
  )
  ON CONFLICT (id) DO UPDATE SET
    username = EXCLUDED.username,
    first_name = EXCLUDED.first_name,
    last_name = EXCLUDED.last_name,
    email = EXCLUDED.email,
    updated_at = timezone('utc', now());

  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW
  EXECUTE FUNCTION public.handle_new_auth_user();

CREATE OR REPLACE FUNCTION public.handle_auth_user_email_update()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  UPDATE public.profiles
  SET email = COALESCE(lower(trim(NEW.email)), ''),
      updated_at = timezone('utc', now())
  WHERE id = NEW.id;

  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS on_auth_user_email_updated ON auth.users;
CREATE TRIGGER on_auth_user_email_updated
  AFTER UPDATE OF email ON auth.users
  FOR EACH ROW
  WHEN (OLD.email IS DISTINCT FROM NEW.email)
  EXECUTE FUNCTION public.handle_auth_user_email_update();

CREATE OR REPLACE FUNCTION public.is_username_available(p_username text)
RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
STABLE
SET search_path = public
AS $$
DECLARE
  normalized text;
BEGIN
  normalized := lower(trim(p_username));

  IF normalized IS NULL OR normalized = '' THEN
    RETURN false;
  END IF;

  IF normalized !~ '^[a-z0-9](?:[a-z0-9._-]{1,28}[a-z0-9])?$' THEN
    RETURN false;
  END IF;

  RETURN NOT EXISTS (
    SELECT 1 FROM public.profiles WHERE lower(username) = normalized
  );
END;
$$;

CREATE OR REPLACE FUNCTION public.is_email_in_use(p_email text)
RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
STABLE
SET search_path = public, auth
AS $$
DECLARE
  normalized text;
BEGIN
  normalized := lower(trim(p_email));

  IF normalized IS NULL OR normalized = '' THEN
    RETURN false;
  END IF;

  RETURN EXISTS (
    SELECT 1
    FROM auth.users
    WHERE lower(email) = normalized
  );
END;
$$;

CREATE OR REPLACE FUNCTION public.resolve_login_email(p_identifier text)
RETURNS text
LANGUAGE plpgsql
SECURITY DEFINER
STABLE
SET search_path = public, auth
AS $$
DECLARE
  normalized text;
  resolved_email text;
BEGIN
  normalized := lower(trim(p_identifier));

  IF normalized IS NULL OR normalized = '' THEN
    RETURN NULL;
  END IF;

  IF position('@' IN normalized) > 1 THEN
    IF EXISTS (SELECT 1 FROM auth.users WHERE lower(email) = normalized) THEN
      RETURN normalized;
    END IF;
    RETURN NULL;
  END IF;

  SELECT p.email
  INTO resolved_email
  FROM public.profiles p
  WHERE lower(p.username) = normalized
  LIMIT 1;

  RETURN resolved_email;
END;
$$;

GRANT EXECUTE ON FUNCTION public.is_username_available(text) TO anon, authenticated;
GRANT EXECUTE ON FUNCTION public.is_email_in_use(text) TO anon, authenticated;
GRANT EXECUTE ON FUNCTION public.resolve_login_email(text) TO anon, authenticated;
