import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  // Relative asset paths, so the build works from any folder (GitHub Pages, static hosting).
  base: "./",
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": "http://localhost:8000",
    },
  },
  build: {
    // Recharts alone is ~540 kB minified (~160 kB gzipped) and cannot be split further.
    chunkSizeWarningLimit: 600,
    rollupOptions: {
      output: {
        // Keep the large charting library in its own file so the app code stays small and caches well.
        manualChunks: {
          charts: ["recharts"],
        },
      },
    },
  },
});
