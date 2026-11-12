import js from "@eslint/js";
import reactHooks from "eslint-plugin-react-hooks";
import tseslint from "@typescript-eslint/eslint-plugin";
import tsparser from "@typescript-eslint/parser";

const browserGlobals = {
  window: "readonly", document: "readonly", fetch: "readonly",
  Response: "readonly", console: "readonly", localStorage: "readonly",
  setTimeout: "readonly", clearTimeout: "readonly", navigator: "readonly",
  React: "readonly", JSX: "readonly",
};

const vitestGlobals = {
  describe: "readonly", it: "readonly", expect: "readonly",
  beforeEach: "readonly", afterEach: "readonly", vi: "readonly",
};

export default [
  js.configs.recommended,
  {
    files: ["src/**/*.{ts,tsx}"],
    languageOptions: {
      parser: tsparser,
      parserOptions: { ecmaFeatures: { jsx: true } },
      globals: { ...browserGlobals, ...vitestGlobals },
    },
    plugins: {
      "@typescript-eslint": tseslint,
      "react-hooks": reactHooks,
    },
    rules: {
      ...tseslint.configs.recommended.rules,
      ...reactHooks.configs.recommended.rules,
      "no-unused-vars": "off",
      "@typescript-eslint/no-unused-vars": "error",
    },
  },
  {
    files: ["public/**/*.js"],
    languageOptions: { globals: browserGlobals },
  },
  {
    ignores: ["dist", "node_modules"],
  },
];
