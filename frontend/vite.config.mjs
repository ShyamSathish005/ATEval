import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  base: process.env.TAURI_ENV_PLATFORM ? "./" : "/",
  build: {
    outDir: "dist/client",
  },
  optimizeDeps: {
    include: ["react", "react-dom/client"],
  },
  server: {
    host: "127.0.0.1",
    allowedHosts: ["localhost", "127.0.0.1"],
    proxy: {
      "/api": {
        target: process.env.ATEVAL_API_ORIGIN ?? "http://127.0.0.1:8000",
        changeOrigin: false,
        configure(proxy) {
          proxy.on("proxyReq", (request) => request.removeHeader("origin"));
        },
      },
    },
    warmup: {
      clientFiles: ["./src/main.tsx"],
    },
  },
  preview: {
    host: "127.0.0.1",
    proxy: {
      "/api": {
        target: process.env.ATEVAL_API_ORIGIN ?? "http://127.0.0.1:8000",
        changeOrigin: false,
        configure(proxy) {
          proxy.on("proxyReq", (request) => request.removeHeader("origin"));
        },
      },
    },
  },
  plugins: [react(), tailwindcss()],
});
