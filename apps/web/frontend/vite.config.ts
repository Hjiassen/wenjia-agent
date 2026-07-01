import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The backend is API-only (front/back separated); it no longer serves the SPA.
// `npm run dev` proxies API + health to the running FastAPI backend on :8000.
// `npm run build` emits a standalone SPA into `dist/` for static hosting.
export default defineConfig({
  plugins: [react()],
  base: "/",
  build: {
    outDir: "dist",
    emptyOutDir: true,
  },
  server: {
    proxy: {
      "/api": "http://127.0.0.1:8000",
      "/health": "http://127.0.0.1:8000",
    },
  },
});
