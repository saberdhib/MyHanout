import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Dev server sur 5173 ; proxy /api vers le backend pour éviter le CORS en local.
export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5173,
    proxy: {
      "/api": {
        target: process.env.VITE_API_PROXY_TARGET || "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
