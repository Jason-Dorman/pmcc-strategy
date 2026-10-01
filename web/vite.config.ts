// Vite builds the static site; Vitest runs its unit tests (ARCHITECTURE §13).
// `base: './'` with HashRouter lets the build work under any Pages path (DEC-73).
import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig(({ mode }) => ({
  base: "./",
  plugins: [react(), tailwindcss()],
  build: { outDir: "dist", emptyOutDir: true },
  // Under Vitest only, the repo root too: the contrast test reads ../theme.py, the baseline look
  // tokens.css must equal (DEC-03). The dev server keeps Vite's default, web/ alone.
  ...(mode === "test" ? { server: { fs: { allow: [".."] } } } : {}),
  test: {
    environment: "jsdom",
    include: ["src/**/*.test.{ts,tsx}", "scripts/**/*.test.mjs"],
    css: true, // so a stylesheet imported `?raw` reads as its text (the token tests)
    env: { TZ: "UTC" }, // like CI: times must show in ET whatever the machine's zone
  },
}));
