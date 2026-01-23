import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  build: {
    outDir: "../static/training_viewer",
    emptyOutDir: true,
    sourcemap: false,
    rollupOptions: {
      input: "./src/main.jsx",
      output: {
        entryFileNames: "training_viewer.js",
        chunkFileNames: "training_viewer.[name].js",
        assetFileNames: (assetInfo) => {
          if (assetInfo.name && assetInfo.name.endsWith(".css")) {
            return "training_viewer.css";
          }
          return "training_viewer.[ext]";
        }
      }
    }
  }
});
