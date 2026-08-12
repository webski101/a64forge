import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/health": "http://127.0.0.1:8640",
      "/system": "http://127.0.0.1:8640",
      "/models": "http://127.0.0.1:8640",
      "/workflows": "http://127.0.0.1:8640",
      "/benchmarks": "http://127.0.0.1:8640",
      "/optimizations": "http://127.0.0.1:8640",
      "/events": "http://127.0.0.1:8640",
      "/actions": "http://127.0.0.1:8640"
    }
  }
});

