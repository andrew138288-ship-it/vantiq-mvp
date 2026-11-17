import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  define: {
    "process.env.NODE_ENV": JSON.stringify("production"),
    __VANTIQ_API_BASE__: JSON.stringify(process.env.VITE_API_BASE || "http://localhost:8000"),
  },
  build: {
    lib: {
      entry: "src/content.tsx",
      name: "VantiqContent",
      formats: ["iife"],
      fileName: () => "content.js",
    },
    outDir: "dist",
    emptyOutDir: true,
    cssCodeSplit: false,
    sourcemap: false,
  },
});
