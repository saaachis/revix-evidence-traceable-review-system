/**
 * The API client.
 *
 * Every type in here comes from `api-types.ts`, which is generated from the
 * OpenAPI schema the FastAPI app produces. Nothing is hand-written, so the
 * frontend and the serving layer cannot drift apart: if an endpoint changes
 * shape, `npm run typecheck` fails rather than the page breaking at runtime.
 *
 * Regenerate with `npm run openapi`.
 */

import type { components, paths } from "@/lib/api-types";

export type VariantSummary = components["schemas"]["VariantSummary"];
export type VerdictOut = components["schemas"]["VerdictOut"];
export type AspectOut = components["schemas"]["AspectOut"];
export type EvidenceOut = components["schemas"]["EvidenceOut"];
export type ClaimEvidenceOut = components["schemas"]["ClaimEvidenceOut"];
export type FusionConfigOut = components["schemas"]["FusionConfigOut"];
export type SourceHealthOut = components["schemas"]["SourceHealthOut"];
export type EvalRunOut = components["schemas"]["EvalRunOut"];
export type Health = components["schemas"]["Health"];

type VariantsQuery = NonNullable<paths["/variants"]["get"]["parameters"]["query"]>;

const BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

/**
 * Eight seconds, because a healthy response takes tens of milliseconds and
 * anything slower than this is a sick API rather than a busy one.
 *
 * Without a timeout, a host that accepts the TCP connection and then says
 * nothing hangs the render indefinitely. A local API that is simply not
 * running refuses instantly and degrades cleanly, which is why this was
 * invisible in development; a free-tier instance waking up does the opposite,
 * and it took a failed production build to show the difference.
 */
const TIMEOUT_MS = 8_000;

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly path: string,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

/**
 * All reads go through here.
 *
 * `revalidate: 300` because every response is a row computed by last night's
 * pipeline. Caching for five minutes costs nothing in freshness and takes the
 * database out of the path for repeat views, which matters on a free tier.
 */
async function get<T>(path: string, params?: Record<string, string | number | undefined>): Promise<T> {
  const url = new URL(path, BASE);
  for (const [key, value] of Object.entries(params ?? {})) {
    if (value !== undefined && value !== "") url.searchParams.set(key, String(value));
  }

  let response: Response;
  try {
    response = await fetch(url, {
      next: { revalidate: 300 },
      signal: AbortSignal.timeout(TIMEOUT_MS),
    });
  } catch (error) {
    const timedOut = error instanceof Error && error.name === "TimeoutError";
    throw new ApiError(
      0,
      path,
      timedOut
        ? `The API at ${BASE} did not answer within ${TIMEOUT_MS / 1000}s.`
        : `Could not reach the API at ${BASE}.`,
    );
  }

  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) detail = body.detail;
    } catch {
      /* a non-JSON error body is still an error */
    }
    throw new ApiError(response.status, path, detail);
  }
  return (await response.json()) as T;
}

export const api = {
  health: () => get<Health>("/health"),

  fusionConfigs: () => get<FusionConfigOut[]>("/fusion-configs"),

  variants: (query: VariantsQuery = {}) =>
    get<VariantSummary[]>("/variants", {
      q: query.q ?? undefined,
      vehicle_class: query.vehicle_class ?? undefined,
      fusion: query.fusion ?? undefined,
      limit: query.limit ?? undefined,
      offset: query.offset ?? undefined,
    }),

  verdict: (variantId: string, fusion?: string) =>
    get<VerdictOut>(`/variants/${variantId}/verdict`, { fusion }),

  claimEvidence: (claimId: string) => get<ClaimEvidenceOut>(`/claims/${claimId}/evidence`),

  sourceHealth: () => get<SourceHealthOut[]>("/sources/health"),

  metrics: (component?: string) => get<EvalRunOut[]>("/metrics", { component }),
};

/** Never throws. Used where a missing section should degrade, not 500. */
export async function tryGet<T>(fn: () => Promise<T>): Promise<T | null> {
  try {
    return await fn();
  } catch {
    return null;
  }
}
