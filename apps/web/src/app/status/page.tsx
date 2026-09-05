import type { Metadata } from "next";

import { Card, PageHead, SectionHead, Unavailable } from "@/components/ui";
import { api, tryGet } from "@/lib/api";
import { relativeDay } from "@/lib/format";

// Rendered per request, never at build time. Two reasons, and the second one
// is the one that bit us: a page baked during the build is a snapshot of
// whatever the API happened to say then, and if the API is asleep during that
// build the page bakes empty and stays empty until it revalidates. Vercel's
// build machine has no business reaching our API.
//
// fetchCache keeps the data cache, which force-dynamic would otherwise turn
// off, so repeat views still avoid the round trip.
export const dynamic = "force-dynamic";
export const fetchCache = "default-cache";
export const metadata: Metadata = { title: "System status" };

const TONE: Record<string, { dot: string; text: string; label: string }> = {
  succeeded: { dot: "bg-[#16a34a]", text: "text-[#166534]", label: "Healthy" },
  running: { dot: "bg-(--color-heat-some)", text: "text-(--color-heat-some)", label: "Running" },
  circuit_open: { dot: "bg-(--color-brand)", text: "text-(--color-brand)", label: "Blocking us" },
  failed: { dot: "bg-(--color-brand)", text: "text-(--color-brand)", label: "Failing" },
};

export default async function StatusPage() {
  const sources = await tryGet(() => api.sourceHealth());
  if (sources === null) return <Unavailable what="Source status" />;

  const alive = sources.filter((s) => s.status === "succeeded").length;
  const units = sources.reduce((sum, s) => sum + s.units_total, 0);

  return (
    <>
      <PageHead title="System status">
        Where every source we read stands right now. A source that stops working marks itself stale
        and shows up here. It never takes the rest of the site down with it, and the verdict pages
        go on telling you how many sources they were built from.
      </PageHead>

      <section className="my-5 grid gap-3.5 md:grid-cols-3">
        <Stat label="Sources healthy" value={`${alive} of ${sources.length}`} note="The product is designed to stay complete with three alive." />
        <Stat label="Reviews collected" value={units.toLocaleString()} note="Across every source, deduplicated by content." />
        <Stat
          label="Last collection"
          value={relativeDay(
            sources.map((s) => s.last_success).filter(Boolean).sort().at(-1) ?? null,
          )}
          note="Everything expensive runs overnight, so the site itself is instant."
        />
      </section>

      <section className="my-5">
        <SectionHead
          title="Every source we read"
          note="A dead source degrades coverage. It does not break the product."
        />
        <Card className="overflow-x-auto">
          <table className="tbl">
            <thead>
              <tr>
                <th>Source</th>
                <th>Kind</th>
                <th>Status</th>
                <th>Last success</th>
                <th className="text-right">Reviews</th>
                <th className="text-right">Error rate</th>
                <th>Last error</th>
              </tr>
            </thead>
            <tbody>
              {sources.map((s) => {
                const tone = TONE[s.status ?? ""] ?? {
                  dot: "bg-(--color-faint)",
                  text: "text-(--color-faint)",
                  label: "Not run yet",
                };
                return (
                  <tr key={s.source_key} className={s.status === "failed" ? "bg-(--color-brand-tint)" : ""}>
                    <td className="font-semibold text-(--color-ink)">{s.source_key}</td>
                    <td className="text-(--color-muted)">{s.kind.replace(/_/g, " ")}</td>
                    <td>
                      <span className={`inline-flex items-center gap-2 text-[12.5px] font-semibold ${tone.text}`}>
                        <i className={`inline-block size-2 rounded-full ${tone.dot}`} aria-hidden />
                        {tone.label}
                      </span>
                    </td>
                    <td className="text-(--color-muted)">{relativeDay(s.last_success)}</td>
                    <td className="text-right num">{s.units_total.toLocaleString()}</td>
                    <td className="text-right num">
                      {s.error_rate == null ? "—" : `${(s.error_rate * 100).toFixed(1)}%`}
                    </td>
                    <td className="max-w-[280px] truncate text-(--color-muted)">
                      {s.last_error ?? "none"}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </Card>
      </section>

      <section className="my-5">
        <Card className="border-(--color-brand-line) bg-linear-to-b from-(--color-brand-tint) to-(--color-surface) to-72% p-6">
          <div className="text-[15.5px] font-semibold tracking-[-0.01em]">
            Why this page is public
          </div>
          <p className="mt-2 max-w-[88ch] text-[13px] leading-relaxed text-(--color-muted)">
            Most sites would hide this. But a verdict built from six sources and a verdict built
            from three are different claims, and you cannot judge the first without knowing which
            one you are looking at. When a source starts refusing us we stop asking, the count on
            every affected verdict drops, and you can see it here rather than having it quietly
            stay the same.
          </p>
        </Card>
      </section>
    </>
  );
}

function Stat({ label, value, note }: { label: string; value: string; note: string }) {
  return (
    <div className="rounded-xl border border-(--color-line) bg-(--color-surface) p-5">
      <div className="text-[11px] font-bold tracking-[0.07em] text-(--color-faint) uppercase">
        {label}
      </div>
      <div className="mt-2 text-[29px] font-bold tracking-[-0.035em] num">{value}</div>
      <p className="mt-1.5 text-[12px] leading-relaxed text-(--color-muted)">{note}</p>
    </div>
  );
}
