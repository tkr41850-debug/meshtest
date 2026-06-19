import { defineConfig } from "vite";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [tailwindcss()],
  test: {
    environment: "happy-dom",
  },
  server: {
    proxy: {
      "/data": "http://localhost:58080",
      "/node-list": "http://localhost:58080",
      "/livez": "http://localhost:58080",
    },
  },
});
