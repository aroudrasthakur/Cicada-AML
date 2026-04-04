import axios from "axios";
import { supabase } from "@/api/supabase";

const client = axios.create({
  baseURL: "/api",
});

async function getAccessToken(): Promise<string | null> {
  const {
    data: { session },
  } = await supabase.auth.getSession();
  if (session?.access_token) {
    return session.access_token;
  }
  const { data: refreshed } = await supabase.auth.refreshSession();
  return refreshed.session?.access_token ?? null;
}

client.interceptors.request.use(async (config) => {
  // Multipart must not use application/json or the boundary is wrong and auth can fail downstream.
  if (config.data instanceof FormData) {
    delete config.headers["Content-Type"];
  } else if (
    config.data != null &&
    typeof config.data === "object" &&
    !(config.data instanceof ArrayBuffer)
  ) {
    config.headers["Content-Type"] =
      (config.headers["Content-Type"] as string | undefined) ?? "application/json";
  }

  const token = await getAccessToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }

  return config;
});

export default client;
