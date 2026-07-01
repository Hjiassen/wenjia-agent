import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

declare const process: {
  env: Record<string, string | undefined>;
};

// The backend is API-only (front/back separated); it no longer serves the SPA.
// `npm run dev` proxies API + health to the running FastAPI backend on :8000.
// `npm run build` emits a standalone SPA into `dist/` for static hosting.
const backendTarget = process.env.WENJIA_BACKEND_TARGET ?? "http://127.0.0.1:8000";
const backendProxy = {
  "/api": backendTarget,
  "/health": backendTarget,
};

export default defineConfig({
  plugins: [react()],
  base: "/",
  build: {
    outDir: "dist",
    emptyOutDir: true,
  },
  server: {
    proxy: backendProxy,
  },
  preview: {
    proxy: backendProxy,
  },
});
