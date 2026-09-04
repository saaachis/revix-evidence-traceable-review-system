// eslint-config-next 16 ships native flat config, so no FlatCompat bridge.
// The bridge is what "next lint" used to set up, and it no longer works
// against the flat exports: it tries to JSON.stringify a config object that
// contains a circular plugin reference.
import coreWebVitals from "eslint-config-next/core-web-vitals";
import typescript from "eslint-config-next/typescript";

const config = [
  ...coreWebVitals,
  ...typescript,
  {
    ignores: [
      ".next/**",
      "node_modules/**",
      // Generated from the OpenAPI schema. Formatting it is not our business.
      "src/lib/api-types.ts",
    ],
  },
];

export default config;
