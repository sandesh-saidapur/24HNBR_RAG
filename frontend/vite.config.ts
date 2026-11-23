import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The FastAPI service runs on 8000; the browser talks to it through this proxy.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { "/api": "http://127.0.0.1:8000" },
  },
});
