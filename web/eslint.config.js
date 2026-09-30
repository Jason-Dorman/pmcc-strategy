// ESLint (ARCHITECTURE §13): TypeScript's strict rules, the React hooks rules, and cyclomatic
// complexity at most 10 per function, the same ceiling ruff holds Python to (EP).
import js from "@eslint/js";
import reactHooks from "eslint-plugin-react-hooks";
import tseslint from "typescript-eslint";

export default tseslint.config(
  { ignores: ["dist", "public", "node_modules", "src/types/generated"] },
  js.configs.recommended,
  ...tseslint.configs.strict,
  {
    files: ["**/*.{ts,tsx}"],
    plugins: { "react-hooks": reactHooks },
    rules: {
      ...reactHooks.configs.recommended.rules,
      complexity: ["error", 10],
    },
  },
  {
    files: ["scripts/**/*.mjs", "eslint.config.js"],
    languageOptions: { globals: { process: "readonly", console: "readonly" } },
    rules: { complexity: ["error", 10] },
  },
);
