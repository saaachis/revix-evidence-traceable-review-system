"use client";

/**
 * The operations console. Proposal section 19.
 *
 * One client component rather than a route per panel, because an operator
 * signs in once and then moves between views, and a route change would mean
 * re-authenticating on every hop or storing a session somewhere it does not
 * need to live.
 *
 * The panels are deliberately plain. This is the one surface in Revix whose
 * audience is us, at night, when something has gone wrong, and every
 * decorative choice on such a page is something between a person and the
 * number they came to read.
 */

import { useCallback, useEffect, useState } from "react";

import {
  type AdjudicationItem,
  AdminError,
  type ConnectorHealth,
  type CoverageRow,
  type Credentials,
  type Freshness,
  type FusionConfigAdmin,
  type IngestRun,
  admin,
  clearCredentials,
  loadCredentials,
  saveCredentials,
} from "@/lib/admin";

type Panel = "connectors" | "runs" | "freshness" | "coverage" | "adjudication" | "weightings";

const PANELS: Array<{ key: Panel; label: string }> = [
  { key: "connectors", label: "Connectors" },
  { key: "runs", label: "Run log" },
  { key: "freshness", label: "Freshness" },
  { key: "coverage", label: "Coverage" },
  { key: "adjudication", label: "Adjudication" },
  { key: "weightings", label: "Weightings" },
];

function ago(hours: number | null | undefined): string {
  if (hours == null) return "never";
  if (hours < 1) return `${Math.round(hours * 60)}m ago`;
  if (hours < 48) return `${Math.round(hours)}h ago`;
  return `${Math.round(hours / 24)}d ago`;
}

function seconds(value: number | null | undefined): string {
  if (value == null) return "-";
  if (value < 90) return `${value.toFixed(0)}s`;
  return `${Math.floor(value / 60)}m ${Math.round(value % 60)}s`;
}

/** Age bands for the heatmap. Absence is its own band, and the loudest. */
function heatOfAge(hours: number | null | undefined): string {
  if (hours == null) return "missing";
  if (hours <= 30) return "fresh";
  if (hours <= 24 * 7) return "aging";
  return "stale";
}

type Session =
  | { kind: "checking" }
  | { kind: "signed-in"; credentials: Credentials }
  | { kind: "signed-out" };

export default function AdminConsole() {
  const [session, setSession] = useState<Session>({ kind: "checking" });
  const [panel, setPanel] = useState<Panel>("connectors");

  // Restore a session on load, and verify it rather than trusting it. A stored
  // credential the API no longer accepts should land on the sign-in form, not
  // on six panels that all fail separately.
  //
  // Every setState below sits in a promise callback rather than in the body of
  // the effect. React warns about the synchronous form because it cascades
  // renders, and the warning is right here: reading storage is the only truly
  // synchronous part of this and it does not need to set anything.
  useEffect(() => {
    let cancelled = false;
    Promise.resolve(loadCredentials())
      .then(async (stored) => {
        if (!stored) return null;
        await admin.whoami(stored);
        return stored;
      })
      .then((verified) => {
        if (cancelled) return;
        setSession(
          verified ? { kind: "signed-in", credentials: verified } : { kind: "signed-out" },
        );
      })
      .catch(() => {
        clearCredentials();
        if (!cancelled) setSession({ kind: "signed-out" });
      });
    // An operator can sign out while the check is still in flight, and letting
    // it resolve afterwards would sign them straight back in.
    return () => {
      cancelled = true;
    };
  }, []);

  const signOut = useCallback(() => {
    clearCredentials();
    setSession({ kind: "signed-out" });
  }, []);

  if (session.kind === "checking") {
    return <p className="text-sm text-(--color-ink-2)">Checking your session...</p>;
  }

  if (session.kind === "signed-out") {
    return (
      <SignIn
        onSignedIn={(c) => {
          saveCredentials(c);
          setSession({ kind: "signed-in", credentials: c });
        }}
      />
    );
  }

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap gap-1" role="tablist" aria-label="Operations panels">
          {PANELS.map((p) => (
            <button
              key={p.key}
              type="button"
              role="tab"
              aria-selected={panel === p.key}
              onClick={() => setPanel(p.key)}
              className={`rounded-md px-3 py-1.5 text-[13px] font-medium transition ${
                panel === p.key
                  ? "bg-(--color-brand) text-white"
                  : "text-(--color-ink-2) hover:bg-(--color-surface-2)"
              }`}
            >
              {p.label}
            </button>
          ))}
        </div>
        <button
          type="button"
          onClick={signOut}
          className="rounded-md border border-(--color-line) px-3 py-1.5 text-[13px] font-medium text-(--color-ink-2) hover:bg-(--color-surface-2)"
        >
          Sign out
        </button>
      </div>

      {/* key= remounts on every panel change, which is what lets Panel start
          in its loading state instead of an effect having to set it. */}
      <Panel
        key={panel}
        panel={panel}
        credentials={session.credentials}
        onUnauthorised={signOut}
      />
    </div>
  );
}

function SignIn({ onSignedIn }: { onSignedIn: (c: Credentials) => void }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    const candidate = { username, password };
    try {
      await admin.whoami(candidate);
      onSignedIn(candidate);
    } catch (e) {
      setError(e instanceof AdminError ? e.message : "Something went wrong.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} className="max-w-sm rounded-lg border border-(--color-line) p-5">
      <h2 className="mb-1 text-[15px] font-semibold">Operator sign-in</h2>
      <p className="mb-4 text-[13px] text-(--color-ink-2)">
        This surface is for running Revix, not for reading it. Nothing here is public.
      </p>

      <label className="mb-3 block text-[13px] font-medium">
        Username
        <input
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          autoComplete="username"
          required
          className="mt-1 w-full rounded-md border border-(--color-line) px-3 py-2 text-[14px] font-normal"
        />
      </label>

      <label className="mb-4 block text-[13px] font-medium">
        Password
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          autoComplete="current-password"
          required
          className="mt-1 w-full rounded-md border border-(--color-line) px-3 py-2 text-[14px] font-normal"
        />
      </label>

      {error && (
        <p role="alert" className="mb-3 text-[13px] text-(--color-heat-split)">
          {error}
        </p>
      )}

      <button
        type="submit"
        disabled={busy}
        className="w-full rounded-md bg-(--color-brand) px-4 py-2 text-[14px] font-semibold text-white disabled:opacity-60"
      >
        {busy ? "Checking..." : "Sign in"}
      </button>
    </form>
  );
}

type PanelState =
  | { kind: "loading" }
  | { kind: "ready"; data: unknown }
  | { kind: "error"; message: string };

/** Loads whichever panel is selected, and owns the loading and error states. */
function Panel({
  panel,
  credentials,
  onUnauthorised,
}: {
  panel: Panel;
  credentials: Credentials;
  onUnauthorised: () => void;
}) {
  // Loading is the initial state rather than something an effect sets, because
  // the call site remounts this component per panel. That is what keeps every
  // setState below inside a promise callback or an event handler, which is
  // where React wants them.
  const [state, setState] = useState<PanelState>({ kind: "loading" });
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let cancelled = false;
    const fetchers = {
      connectors: admin.connectors,
      runs: admin.runs,
      freshness: admin.freshness,
      coverage: admin.coverage,
      adjudication: admin.adjudication,
      weightings: admin.fusionConfigs,
    } as const;

    fetchers[panel](credentials)
      .then((data) => {
        if (!cancelled) setState({ kind: "ready", data });
      })
      .catch((e: unknown) => {
        if (cancelled) return;
        // A 401 mid-session means the password changed under us, so send the
        // operator back to the form rather than showing six broken panels.
        if (e instanceof AdminError && e.status === 401) {
          onUnauthorised();
          return;
        }
        setState({
          kind: "error",
          message: e instanceof AdminError ? e.message : "Something went wrong.",
        });
      });

    // A slow panel must not overwrite a faster one the operator has since
    // switched to.
    return () => {
      cancelled = true;
    };
  }, [panel, credentials, onUnauthorised, attempt]);

  // From an event handler, where setting state is exactly the right thing.
  const reload = useCallback(() => {
    setState({ kind: "loading" });
    setAttempt((n) => n + 1);
  }, []);

  if (state.kind === "loading") {
    return <p className="text-sm text-(--color-ink-2)">Loading...</p>;
  }
  if (state.kind === "error") {
    return (
      <div className="rounded-lg border border-(--color-line) p-5">
        <p role="alert" className="text-[14px] text-(--color-heat-split)">
          {state.message}
        </p>
        <button
          type="button"
          onClick={reload}
          className="mt-3 rounded-md border border-(--color-line) px-3 py-1.5 text-[13px] font-medium"
        >
          Try again
        </button>
      </div>
    );
  }

  const { data } = state;
  switch (panel) {
    case "connectors":
      return <Connectors rows={data as ConnectorHealth[]} />;
    case "runs":
      return <Runs rows={data as IngestRun[]} />;
    case "freshness":
      return <FreshnessGrid data={data as Freshness} />;
    case "coverage":
      return <Coverage rows={data as CoverageRow[]} />;
    case "adjudication":
      return (
        <Adjudication
          rows={data as AdjudicationItem[]}
          credentials={credentials}
          onDone={reload}
        />
      );
    case "weightings":
      return <Weightings rows={data as FusionConfigAdmin[]} />;
  }
}

function Connectors({ rows }: { rows: ConnectorHealth[] }) {
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      {rows.map((c) => (
        <div key={c.source_key} className="rounded-lg border border-(--color-line) p-4">
          <div className="flex items-start justify-between gap-3">
            <div>
              <h3 className="text-[14px] font-semibold">{c.display_name}</h3>
              <p className="text-[12px] text-(--color-ink-2)">
                {c.source_key} · {c.kind}
              </p>
            </div>
            <span
              className="rounded-full px-2 py-0.5 text-[11px] font-semibold"
              style={{
                background: c.is_stale
                  ? "var(--color-heat-split-bg)"
                  : "var(--color-heat-agreed-bg)",
                color: c.is_stale ? "var(--color-heat-split)" : "var(--color-heat-agreed)",
              }}
            >
              {c.is_stale ? "stale" : "fresh"}
            </span>
          </div>

          <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-1 text-[12.5px]">
            <dt className="text-(--color-ink-2)">Last status</dt>
            <dd className="text-right font-medium">{c.status ?? "never run"}</dd>
            <dt className="text-(--color-ink-2)">Last success</dt>
            <dd className="text-right font-medium">{ago(c.hours_since_success)}</dd>
            <dt className="text-(--color-ink-2)">Last run took</dt>
            <dd className="text-right font-medium">{seconds(c.last_run_seconds)}</dd>
            <dt className="text-(--color-ink-2)">Units held</dt>
            <dd className="text-right font-medium">{c.units_total.toLocaleString()}</dd>
            <dt className="text-(--color-ink-2)">Last run added</dt>
            <dd className="text-right font-medium">
              {c.units_inserted.toLocaleString()} new, {c.units_skipped.toLocaleString()} seen before
            </dd>
          </dl>

          {c.last_error && (
            <p className="mt-3 rounded-md bg-(--color-surface-2) p-2 font-mono text-[11.5px] break-words text-(--color-ink-2)">
              {c.last_error}
            </p>
          )}
        </div>
      ))}
    </div>
  );
}

function Runs({ rows }: { rows: IngestRun[] }) {
  if (!rows.length) return <Empty>No ingest runs recorded yet.</Empty>;
  return (
    <div className="overflow-x-auto rounded-lg border border-(--color-line)">
      <table className="w-full text-[12.5px]">
        <thead className="bg-(--color-surface-2) text-left">
          <tr>
            <Th>Started</Th>
            <Th>Source</Th>
            <Th>Status</Th>
            <Th align="right">Took</Th>
            <Th align="right">Fetched</Th>
            <Th align="right">New</Th>
            <Th align="right">Skipped</Th>
            <Th>Error</Th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.id} className="border-t border-(--color-line)">
              <Td>{new Date(r.started_at).toLocaleString()}</Td>
              <Td>{r.source_key}</Td>
              <Td>
                <span className={r.status === "succeeded" ? "" : "font-semibold text-(--color-heat-split)"}>
                  {r.status}
                </span>
              </Td>
              <Td align="right">{seconds(r.duration_seconds)}</Td>
              <Td align="right">{r.payloads_fetched.toLocaleString()}</Td>
              <Td align="right">{r.units_inserted.toLocaleString()}</Td>
              <Td align="right">{r.units_skipped.toLocaleString()}</Td>
              <Td>
                <span className="font-mono text-[11px] text-(--color-ink-2)">
                  {r.last_error ?? ""}
                </span>
              </Td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function FreshnessGrid({ data }: { data: Freshness }) {
  const byKey = new Map(data.cells.map((c) => [`${c.model_id}|${c.source_key}`, c]));
  return (
    <>
      <p className="mb-3 text-[13px] text-(--color-ink-2)">
        Model by source, coloured by age. The blanks are the point: a gap is a source that has
        never returned anything for that vehicle.
      </p>
      <div className="overflow-x-auto rounded-lg border border-(--color-line)">
        <table className="w-full text-[12.5px]">
          <thead className="bg-(--color-surface-2) text-left">
            <tr>
              <Th>Model</Th>
              {data.sources.map((s) => (
                <Th key={s} align="center">
                  {s}
                </Th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.models.map((m) => (
              <tr key={m.id} className="border-t border-(--color-line)">
                <Td>
                  {m.name}
                  <span className="ml-1 text-[11px] text-(--color-ink-2)">
                    {m.vehicle_class === "two_wheeler" ? "2W" : "car"}
                  </span>
                </Td>
                {data.sources.map((s) => {
                  const cell = byKey.get(`${m.id}|${s}`);
                  const heat = heatOfAge(cell?.hours_since);
                  return (
                    <td key={s} className="p-1 text-center" data-heat={heat}>
                      <span
                        title={
                          cell
                            ? `${cell.units} units, last ${ago(cell.hours_since)}`
                            : "nothing collected"
                        }
                        className="inline-block min-w-14 rounded px-1.5 py-1 text-[11px] font-medium"
                        style={{
                          background:
                            heat === "missing" || heat === "stale"
                              ? "var(--color-heat-split-bg)"
                              : heat === "aging"
                                ? "var(--color-heat-some-bg)"
                                : "var(--color-heat-agreed-bg)",
                          color:
                            heat === "missing" || heat === "stale"
                              ? "var(--color-heat-split)"
                              : heat === "aging"
                                ? "var(--color-heat-some)"
                                : "var(--color-heat-agreed)",
                        }}
                      >
                        {cell ? cell.units.toLocaleString() : "none"}
                      </span>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}

function Coverage({ rows }: { rows: CoverageRow[] }) {
  if (!rows.length) return <Empty>Every variant clears the evidence floor.</Empty>;
  return (
    <>
      <p className="mb-3 text-[13px] text-(--color-ink-2)">
        Variants held back below the evidence floor, closest to clearing it first. Two columns
        rather than one, because needing another source and needing more of the same are different
        jobs.
      </p>
      <div className="overflow-x-auto rounded-lg border border-(--color-line)">
        <table className="w-full text-[12.5px]">
          <thead className="bg-(--color-surface-2) text-left">
            <tr>
              <Th>Vehicle</Th>
              <Th align="right">Units</Th>
              <Th align="right">Of which model-level</Th>
              <Th align="right">Sources</Th>
              <Th align="right">Short by</Th>
              <Th>Why held back</Th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.variant_id} className="border-t border-(--color-line)">
                <Td>
                  {r.manufacturer} {r.model}{" "}
                  <span className="text-(--color-ink-2)">{r.variant_name}</span>
                </Td>
                <Td align="right">{r.evidence_count}</Td>
                <Td align="right">{r.model_evidence_count}</Td>
                <Td align="right">{r.distinct_sources}</Td>
                <Td align="right">
                  {r.sources_short_of_floor > 0 && (
                    <span className="font-semibold text-(--color-heat-split)">
                      {r.sources_short_of_floor} source{r.sources_short_of_floor > 1 ? "s" : ""}
                    </span>
                  )}
                  {r.sources_short_of_floor > 0 && r.units_short_of_floor > 0 && ", "}
                  {r.units_short_of_floor > 0 && `${r.units_short_of_floor} units`}
                  {r.sources_short_of_floor === 0 && r.units_short_of_floor === 0 && "-"}
                </Td>
                <Td>
                  <span className="text-[11.5px] text-(--color-ink-2)">
                    {r.suppression_reason ?? ""}
                  </span>
                </Td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}

function Adjudication({
  rows,
  credentials,
  onDone,
}: {
  rows: AdjudicationItem[];
  credentials: Credentials;
  onDone: () => void;
}) {
  const [busy, setBusy] = useState<string | null>(null);
  const [failed, setFailed] = useState<string | null>(null);

  async function decide(listingId: string, rejection: boolean) {
    setBusy(listingId);
    setFailed(null);
    try {
      await admin.adjudicate(credentials, listingId, { is_rejection: rejection });
      onDone();
    } catch (e) {
      setFailed(e instanceof AdminError ? e.message : "Could not save that decision.");
    } finally {
      setBusy(null);
    }
  }

  if (!rows.length) return <Empty>Nothing waiting. The resolver placed everything it saw.</Empty>;

  return (
    <>
      <p className="mb-3 text-[13px] text-(--color-ink-2)">
        Listings the resolver would not place, ordered by how much evidence is waiting behind each
        decision. A decision here is recorded as human, so it is never confused with something the
        resolver worked out, and the verdict does not move until the pipeline next runs.
      </p>
      {failed && (
        <p role="alert" className="mb-3 text-[13px] text-(--color-heat-split)">
          {failed}
        </p>
      )}
      <div className="flex flex-col gap-2">
        {rows.map((item) => (
          <div
            key={item.listing_id}
            className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-(--color-line) p-3"
          >
            <div className="min-w-0">
              <p className="truncate text-[13.5px] font-medium">{item.raw_title}</p>
              <p className="text-[12px] text-(--color-ink-2)">
                {item.source_key} · {item.evidence_waiting} unit
                {item.evidence_waiting === 1 ? "" : "s"} waiting
                {item.match_confidence != null &&
                  ` · resolver reached ${item.match_confidence.toFixed(2)}`}
                {item.resolved_model_id && " · model known, trim not"}
              </p>
            </div>
            <div className="flex shrink-0 gap-2">
              {item.url && (
                <a
                  href={item.url}
                  target="_blank"
                  rel="noreferrer noopener"
                  className="rounded-md border border-(--color-line) px-3 py-1.5 text-[12.5px] font-medium"
                >
                  Open source
                </a>
              )}
              <button
                type="button"
                disabled={busy === item.listing_id}
                onClick={() => void decide(item.listing_id, true)}
                className="rounded-md border border-(--color-line) px-3 py-1.5 text-[12.5px] font-medium disabled:opacity-60"
              >
                {busy === item.listing_id ? "Saving..." : "Not one of ours"}
              </button>
            </div>
          </div>
        ))}
      </div>
    </>
  );
}

function Weightings({ rows }: { rows: FusionConfigAdmin[] }) {
  return (
    <>
      <p className="mb-3 text-[13px] text-(--color-ink-2)">
        Read-only, and deliberately so. Creating a weighting here would put it on the public switch
        immediately while its verdicts would not exist until the pipeline next ran, so every
        vehicle would answer &ldquo;no verdict&rdquo; under it. A weighting is only real once its
        verdicts are computed, so it is created by <code>revix fuse</code>, where the computation
        happens.
      </p>
      <div className="grid gap-3 sm:grid-cols-2">
        {rows.map((c) => (
          <div key={c.id} className="rounded-lg border border-(--color-line) p-4">
            <div className="flex items-start justify-between gap-2">
              <h3 className="text-[14px] font-semibold">
                {c.label}
                {c.is_default && (
                  <span className="ml-2 rounded-full bg-(--color-brand) px-2 py-0.5 text-[10.5px] font-semibold text-white">
                    default
                  </span>
                )}
              </h3>
              <span
                className="shrink-0 text-[11.5px] font-semibold"
                style={{
                  color: c.is_complete
                    ? "var(--color-heat-agreed)"
                    : "var(--color-heat-split)",
                }}
              >
                {c.verdict_count}/{c.variant_count}
              </span>
            </div>
            {c.description && (
              <p className="mt-1 text-[12.5px] text-(--color-ink-2)">{c.description}</p>
            )}
            {!c.is_complete && (
              <p className="mt-2 text-[12px] font-medium text-(--color-heat-split)">
                Incomplete: some vehicles have no verdict under this weighting.
              </p>
            )}
            <pre className="mt-3 overflow-x-auto rounded-md bg-(--color-surface-2) p-2 text-[11px] leading-relaxed">
              {JSON.stringify(c.params, null, 2)}
            </pre>
          </div>
        ))}
      </div>
    </>
  );
}

function Th({
  children,
  align = "left",
}: {
  children: React.ReactNode;
  align?: "left" | "right" | "center";
}) {
  return (
    <th scope="col" className="px-3 py-2 font-semibold" style={{ textAlign: align }}>
      {children}
    </th>
  );
}

function Td({
  children,
  align = "left",
}: {
  children: React.ReactNode;
  align?: "left" | "right" | "center";
}) {
  return (
    <td className="px-3 py-2" style={{ textAlign: align }}>
      {children}
    </td>
  );
}

function Empty({ children }: { children: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-dashed border-(--color-line) p-6 text-center text-[13.5px] text-(--color-ink-2)">
      {children}
    </div>
  );
}
