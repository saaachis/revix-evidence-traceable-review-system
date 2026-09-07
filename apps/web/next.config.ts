import type { NextConfig } from "next";

// Where the browser is allowed to send fetches. The API lives on a different
// origin in every deployed environment, so a Content Security Policy that
// only allowed 'self' would block every request the app makes and the site
// would render as empty shells. Read from the same variable the client reads,
// so the two cannot disagree.
const apiOrigin = (() => {
  const raw = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
  try {
    return new URL(raw).origin;
  } catch {
    return "http://localhost:8000";
  }
})();

// Deliberately restrictive, with one exception that is worth being explicit
// about rather than hiding.
//
// script-src carries 'unsafe-inline'. Next's App Router bootstraps hydration
// from inline script tags, and the alternative is a per-request nonce, which
// means opting every page out of static rendering. That would trade a
// measured p95 for protection against an injection route this app does not
// have: there is no authentication, no cookie or token worth stealing, no
// user-generated content, and the only text that reaches the page from a user
// is the search box, which React escapes. Paying latency, the one
// non-functional requirement with a number attached to it, to defend a
// surface that is not there is the wrong trade. It is written down here so it
// stays a decision rather than becoming an oversight.
//
// Everything else is locked: no plugins, no framing, no form posts off-site,
// and connections only to ourselves and the API.
const csp = [
  "default-src 'self'",
  "script-src 'self' 'unsafe-inline'",
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data: blob:",
  "font-src 'self' data:",
  `connect-src 'self' ${apiOrigin}`,
  "object-src 'none'",
  "base-uri 'self'",
  "form-action 'self'",
  "frame-ancestors 'none'",
  "upgrade-insecure-requests",
].join("; ");

const config: NextConfig = {
  reactStrictMode: true,

  // typedRoutes is deliberately off. Almost every link in this app is built at
  // runtime from data the API returned, `/v/${variant.id}` and
  // `/evidence/${claim.id}`, which typedRoutes cannot check. It would mean
  // casting every one of them, and a cast on every link is worse than no
  // checking at all because it teaches you to ignore the type. Route
  // correctness is covered by the link check in CI instead.

  // Vercel adds none of these on its own. Without them the app ships with a
  // sniffable content type, no framing rule, and a full referrer going to
  // every outbound link, and every outbound link here is a review on somebody
  // else's site.
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          { key: "Content-Security-Policy", value: csp },
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "X-Frame-Options", value: "DENY" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          {
            key: "Permissions-Policy",
            value: "camera=(), microphone=(), geolocation=()",
          },
          // Two years, because anything shorter is ignored by the preload
          // list. Safe here: the site has never been served over plain HTTP,
          // so there is no old bookmark this can strand.
          {
            key: "Strict-Transport-Security",
            value: "max-age=63072000; includeSubDomains",
          },
        ],
      },
    ];
  },
};

export default config;
