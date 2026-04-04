import axios, { type AxiosError, type InternalAxiosRequestConfig } from "axios";
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

/** One retry on transient failures (common when Vite proxy hits ECONNRESET during uvicorn --reload). */
client.interceptors.response.use(
  (r) => r,
  async (error: AxiosError) => {
    const cfg = error.config as RetryConfig | undefined;
    if (!cfg || cfg._retry) {
      return Promise.reject(error);
    }
    const status = error.response?.status;
    const transient =
      status === 502 ||
      status === 503 ||
      status === 504 ||
      (!error.response &&
        (error.code === "ERR_NETWORK" ||
          error.code === "ECONNABORTED" ||
          String(error.message || "").toLowerCase().includes("network")));
    if (import.meta.env.DEV && transient) {
      cfg._retry = true;
      await new Promise((r) => setTimeout(r, 400));
      return client.request(cfg);
    }
    return Promise.reject(error);
  },
);

export default client;
