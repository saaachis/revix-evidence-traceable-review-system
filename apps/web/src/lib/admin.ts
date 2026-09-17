/**
 * The admin client.
 *
 * Separate from `api.ts` on purpose, and the separation is the design rather
 * than tidiness. Everything in `api.ts` is fetched on the server, cached, and
 * public. Nothing here is any of those things: it runs in the browser, it is
 * never cached, and every request carries credentials.
 *
 * **Why the browser and not the server.** The obvious alternative is to have
 * Next fetch these on the server with the credentials in its own environment.
 * That would put an unauthenticated page in front of an authenticated API:
 * anybody who reached /admin would see the data, because the server would
 * happily authenticate on their behalf. Sending the operator's own
 * credentials from the operator's own browser is what makes the gate mean
 * anything.
 *
 * **Why an explicit header and not cookies.** The credentials go out in an
 * Authorization header we set ourselves. No cookie is ever created, so the
 * browser never attaches anything automatically to a cross-site request, and
 * the entire CSRF class does not arise. It also lets the API keep
 * `allow_credentials=False` on CORS, which is a strictly tighter setting.
 */

import type { components } from "@/lib/api-types";

export type ConnectorHealth = components["schemas"]["ConnectorHealthOut"];
export type IngestRun = components["schemas"]["IngestRunOut"];
export type Freshness = components["schemas"]["FreshnessOut"];
export type CoverageRow = components["schemas"]["CoverageRowOut"];
export type AdjudicationItem = components["schemas"]["AdjudicationItemOut"];
export type FusionConfigAdmin = components["schemas"]["FusionConfigAdminOut"];

const BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

/**
 * sessionStorage, not localStorage.
 *
 * The difference is the whole point: sessionStorage is scoped to the tab and
 * dies when the tab closes, so walking away from a shared machine ends the
 * session. localStorage would persist until somebody explicitly signed out,
 * which on a demo laptop means indefinitely.
 *
 * This does keep the credentials readable by script in the tab for as long as
 * it is open, which is the real cost of Basic auth without a token exchange.
 * Acceptable for a single operator account over HTTPS on a surface with no
 * user-generated content and a strict content security policy; it is written
 * down here so it stays a decision.
 */
const KEY = "revix.admin";

export type Credentials = { username: string; password: string };

export function loadCredentials(): Credentials | null {
  try {
    const raw = sessionStorage.getItem(KEY);
    return raw ? (JSON.parse(raw) as Credentials) : null;
  } catch {
    // Private windows and locked-down browsers throw rather than return null.
    // Signing in again each visit is a better failure than a blank page.
    return null;
  }
}

export function saveCredentials(credentials: Credentials): void {
  try {
    sessionStorage.setItem(KEY, JSON.stringify(credentials));
  } catch {
    // Storage refused. The session still works, it just will not survive a
    // page reload, so there is nothing worth telling the operator here.
  }
}

export function clearCredentials(): void {
  try {
    sessionStorage.removeItem(KEY);
  } catch {
    // Nothing stored means nothing to clear.
  }
}

export class AdminError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = "AdminError";
  }
}

function header({ username, password }: Credentials): string {
  // btoa handles Latin-1 only, and a password with anything outside it would
  // throw here rather than fail as a 401, which is a confusing way to learn
  // about your own password. Encode to UTF-8 bytes first.
  const bytes = new TextEncoder().encode(`${username}:${password}`);
  const binary = Array.from(bytes, (b) => String.fromCharCode(b)).join("");
  return `Basic ${btoa(binary)}`;
}

async function request<T>(
  path: string,
  credentials: Credentials,
  init: RequestInit = {},
): Promise<T> {
  let response: Response;
  try {
    response = await fetch(new URL(path, BASE), {
      ...init,
      headers: {
        ...init.headers,
        Authorization: header(credentials),
        "Content-Type": "application/json",
      },
      // No caching anywhere in the chain. An operations console showing a
      // five-minute-old failure is worse than one showing nothing.
      cache: "no-store",
      signal: AbortSignal.timeout(15_000),
    });
  } catch {
    throw new AdminError(0, "Could not reach the API. It may be asleep; try again in a moment.");
  }

  if (response.status === 401) {
    throw new AdminError(401, "Those credentials were not accepted.");
  }
  if (response.status === 503) {
    const detail = await response.json().catch(() => null);
    throw new AdminError(503, detail?.detail ?? "The admin surface is not configured.");
  }
  if (!response.ok) {
    throw new AdminError(response.status, `The API answered ${response.status}.`);
  }
  return (await response.json()) as T;
}

export const admin = {
  whoami: (c: Credentials) => request<{ username: string; authenticated: boolean }>("/admin/whoami", c),
  connectors: (c: Credentials) => request<ConnectorHealth[]>("/admin/connectors", c),
  runs: (c: Credentials) => request<IngestRun[]>("/admin/runs?limit=60", c),
  freshness: (c: Credentials) => request<Freshness>("/admin/freshness", c),
  coverage: (c: Credentials) => request<CoverageRow[]>("/admin/coverage?only_suppressed=true", c),
  adjudication: (c: Credentials) => request<AdjudicationItem[]>("/admin/adjudication", c),
  fusionConfigs: (c: Credentials) => request<FusionConfigAdmin[]>("/admin/fusion-configs", c),
  adjudicate: (
    c: Credentials,
    listingId: string,
    decision: { variant_id?: string; model_id?: string; is_rejection?: boolean },
  ) =>
    request<AdjudicationItem>(`/admin/adjudication/${listingId}`, c, {
      method: "POST",
      body: JSON.stringify(decision),
    }),
};
