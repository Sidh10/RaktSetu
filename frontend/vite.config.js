import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Dev: UI on :5173, API proxied to :8000. Build: dist/ is served by FastAPI at / (one process for the demo).
export default defineConfig({
  plugins: [react()],
  server: { port: 5173, proxy: { "/api": "http://localhost:8000" } },
  build: { outDir: "dist", emptyOutDir: true },
});
