import { defineConfig } from "vite";

export default defineConfig({
  define: {
    __VANTIQ_API_BASE__: JSON.stringify(process.env.VITE_API_BASE || "http://localhost:8000"),
  },
  build: {
    lib: {
      entry: "src/service-worker.ts",
      formats: ["es"],
      fileName: () => "service-worker.js",
    },
    outDir: "dist",
    emptyOutDir: false,
    sourcemap: false,
  },
});
