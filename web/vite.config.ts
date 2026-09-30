// Vite builds the static site; Vitest runs its unit tests (ARCHITECTURE §13).
// `base: './'` with HashRouter lets the build work under any Pages path (DEC-73).
import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  base: "./",
  plugins: [react(), tailwindcss()],
  build: { outDir: "dist", emptyOutDir: true },
  test: {
    environment: "jsdom",
    include: ["src/**/*.test.{ts,tsx}"],
    css: true, // so a stylesheet imported `?raw` reads as its text (the token tests)
  },
});
