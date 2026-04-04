import { supabase } from "@/api/supabase";
import type { UserProfile } from "@/types/auth";

export async function fetchUserProfile(userId: string): Promise<UserProfile | null> {
  const { data, error } = await supabase
    .from("profiles")
    .select("id, username, first_name, last_name, email, created_at, updated_at")
    .eq("id", userId)
    .maybeSingle();

  if (error) {
    throw error;
  }

  return data as UserProfile | null;
}

export async function checkUsernameAvailability(username: string): Promise<boolean> {
  const { data, error } = await supabase.rpc("is_username_available", {
    p_username: username,
  });

  if (error) {
    throw error;
  }

  return Boolean(data);
}

export async function checkEmailInUse(email: string): Promise<boolean> {
  const { data, error } = await supabase.rpc("is_email_in_use", {
    p_email: email,
  });

  if (error) {
    throw error;
  }

  return Boolean(data);
}

export async function resolveLoginEmail(identifier: string): Promise<string | null> {
  const { data, error } = await supabase.rpc("resolve_login_email", {
    p_identifier: identifier,
  });

  if (error) {
    throw error;
  }

  if (typeof data !== "string" || data.trim() === "") {
    return null;
  }

  return data.trim().toLowerCase();
}
