import { defineConfig } from "vitest/config";

// Unit tests live next to the code in src/; tests/ holds Playwright end-to-end specs (run with `pnpm test:e2e`).
export default defineConfig({
  test: {
    include: ["src/**/*.test.ts", "src/**/*.test.tsx"],
  },
});
