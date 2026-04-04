import axios, { type AxiosError, type InternalAxiosRequestConfig } from "axios";

const client = axios.create({
  baseURL: "/api",
  headers: { "Content-Type": "application/json" },
});

type RetryConfig = InternalAxiosRequestConfig & { _retry?: boolean };

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
