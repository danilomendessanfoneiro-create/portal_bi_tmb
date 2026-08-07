import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  base: "/admin/",
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8003",
        changeOrigin: true,
      },
      "/bi": {
        target: "http://127.0.0.1:8501",
        changeOrigin: true,
        ws: true,
      },
    },
  },
});
