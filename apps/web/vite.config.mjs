import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import { serverOrigin } from "./config.mjs";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "AGENT_CF_WEB_");
  const target = serverOrigin(env.AGENT_CF_WEB_SERVER_URL);
  const proxy = {
    "/healthz": { target, changeOrigin: true },
    "/v1": { target, changeOrigin: true },
  };
  return {
    plugins: [react()],
    server: { host: "127.0.0.1", port: 5173, strictPort: true, proxy },
    preview: { host: "127.0.0.1", port: 4173, strictPort: true, proxy },
  };
});
