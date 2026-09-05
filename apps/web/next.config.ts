import type { NextConfig } from "next";

const config: NextConfig = {
  reactStrictMode: true,

  // typedRoutes is deliberately off. Almost every link in this app is built at
  // runtime from data the API returned, `/v/${variant.id}` and
  // `/evidence/${claim.id}`, which typedRoutes cannot check. It would mean
  // casting every one of them, and a cast on every link is worse than no
  // checking at all because it teaches you to ignore the type. Route
  // correctness is covered by the link check in CI instead.
};

export default config;
