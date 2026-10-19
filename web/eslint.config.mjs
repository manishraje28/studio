import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  // Vendored React Bits components (copied from reactbits.dev); keep them as upstream ships them.
  {
    files: ["src/components/{AnimatedContent,FadeContent,ScrollFloat,ShinyText,SplitText,RotatingText,ScrollVelocity}.tsx"],
    rules: { "react-hooks/refs": "off", "react-hooks/set-state-in-effect": "off" },
  },
  // Override default ignores of eslint-config-next.
  globalIgnores([
    // Default ignores of eslint-config-next:
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
  ]),
]);

export default eslintConfig;
