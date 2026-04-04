import path from "path";
import { fileURLToPath } from "url";
import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

/** Backend base URL for dev proxy. Use 127.0.0.1 to avoid Windows IPv6 localhost mismatches. */
export default defineConfig(({ mode }) => {
  // Always load .env from this package (frontend/), not process.cwd() — avoids wrong/missing
  // VITE_API_PROXY_TARGET when `vite` is started from the repo root.
  const env = loadEnv(mode, __dirname, "");
  const apiTarget = env.VITE_API_PROXY_TARGET || "http://127.0.0.1:8000";

  return {
    plugins: [react(), tailwindcss()],
    resolve: {
      alias: {
        "@": path.resolve(__dirname, "./src"),
      },
    },
    envDir: __dirname,
    server: {
      port: 5173,
      proxy: {
        "/api": {
          target: apiTarget,
          changeOrigin: true,
          ws: true,
        },
      },
    },
  };
});
