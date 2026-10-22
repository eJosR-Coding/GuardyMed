import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import { resolve } from "node:path";

// The API origin for `pnpm dev`; override when 8000 is taken: GUARDYMED_API=http://127.0.0.1:8765 pnpm dev
const api = process.env.GUARDYMED_API || "http://127.0.0.1:8000";

export default defineConfig(({ command }) => ({
  // The production build is served by FastAPI under /app.
  base: command === "build" ? "/app/" : "/",
  plugins: [vue()],
  server: {
    host: "127.0.0.1",
    port: Number(process.env.PORT) || 5173,
    proxy: { "/api": api, "/health": api },
  },
  build: {
    outDir: resolve(__dirname, "../web"),
    emptyOutDir: true,
  },
}));
