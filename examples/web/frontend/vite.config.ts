import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The FastAPI demo serves built assets from `examples/web/static` and mounts
// them under `/static`, while returning `static/index.html` at `/`. We build
// straight into that directory so `app.py` needs no changes.
export default defineConfig({
  plugins: [react()],
  base: "/static/",
  build: {
    outDir: "../static",
    emptyOutDir: true,
  },
  server: {
    // `npm run dev` proxies API calls to the running FastAPI server.
    proxy: {
      "/api": "http://127.0.0.1:8000",
      "/health": "http://127.0.0.1:8000",
    },
  },
});
