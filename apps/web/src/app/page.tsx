import Link from "next/link";

import { SearchBox } from "@/components/SearchBox";
import { Card, ScoreTrack, SectionHead, Unavailable } from "@/components/ui";
import { api, tryGet, type VariantSummary } from "@/lib/api";
import { agreementWord, heatOf } from "@/lib/format";

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

const PIPELINE = [
  ["Collect", "Owner reviews, expert reviews, forums, video transcripts and official records."],
  ["Match", "Everything resolved to one exact variant, not just “a Creta”."],
  ["Score", "Opinion split topic by topic. Each review weighted by how much it can be trusted."],
  ["Combine", "Into one verdict with an honest range around it."],
  ["Explain", "Every number linked to the exact reviews that produced it."],
] as const;

const CLAIMS = [
  [
    "It reads across platforms, not inside one",
    "CarDekho can only tell you what CarDekho users think. Nothing today joins several platforms and the official record into one judgement about one variant.",
  ],
  [
    "It weighs reviews by trust, not by star average",
    "An owner at 60,000 km is a better witness to reliability than someone who posted on delivery day. Indian portals record that, then throw it away by averaging everything equally.",
  ],
  [
    "Traceability is built into the database",
    "Every number has rows linking it to the exact reviews that produced it, each with its weight. Click any figure to open them. It cannot silently break.",
  ],
] as const;

export default async function HomePage() {
  const featured = await tryGet(() => api.variants({ limit: 60 }));
  const scored = (featured ?? []).filter((v) => !v.is_suppressed && v.overall_score != null);

  // One variant per model, best-evidenced first, and always at least one
  // two-wheeler so the home page never suggests this is a car-only product.
  const byModel = new Map<string, VariantSummary>();
  for (const v of [...scored].sort((a, b) => b.evidence_count - a.evidence_count)) {
    const key = `${v.manufacturer} ${v.model}`;
    if (!byModel.has(key)) byModel.set(key, v);
  }
  const distinct = [...byModel.values()];
  const bike = distinct.find((v) => v.vehicle_class === "two_wheeler");
  const picks = [
    ...distinct.filter((v) => v.id !== bike?.id).slice(0, bike ? 2 : 3),
    ...(bike ? [bike] : []),
  ];

  return (
    <>
      <section className="pt-16 pb-11 text-center">
        <h1 className="mx-auto max-w-[24ch] text-[46px] leading-[1.1] tracking-[-0.035em]">
          Not every review deserves the same weight.{" "}
          <em className="text-(--color-brand) not-italic">So we stopped averaging them.</em>
        </h1>
        <p className="mx-auto mt-4 max-w-[56ch] text-[18px] leading-relaxed text-(--color-muted)">
          An owner at 60,000 km is a better witness to reliability than someone who posted on
          delivery day. Revix reads across every platform, weighs each review by how much it can be
          trusted, and shows its working: every number links back to the reviews behind it.
        </p>

        <SearchBox big />

        <div className="mt-4.5 flex flex-wrap justify-center gap-2">
          {picks.map((v) => (
            <Link
              key={v.id}
              href={`/v/${v.id}`}
              className="rounded-full border border-(--color-line) bg-(--color-surface) px-3.5 py-1.5 text-[13px] font-medium text-(--color-ink-2) hover:border-(--color-brand-line) hover:text-(--color-brand)"
            >
              {v.manufacturer} {v.model}
            </Link>
          ))}
          <Link
            href="/browse"
            className="rounded-full border border-(--color-brand-line) bg-(--color-brand-soft) px-3.5 py-1.5 text-[13px] font-semibold text-(--color-brand-deep)"
          >
            Browse everything ›
          </Link>
        </div>
      </section>

      <section className="my-5">
        <Card className="grid overflow-hidden md:grid-cols-5">
          {PIPELINE.map(([title, body], i) => (
            <div
              key={title}
              className={`p-5 ${i > 0 ? "border-t border-(--color-line-soft) md:border-t-0 md:border-l" : ""}`}
            >
              <b className="block text-[11.5px] font-bold tracking-[0.09em] text-(--color-brand) uppercase">
                {title}
              </b>
              <p className="mt-2 text-[13px] leading-relaxed text-(--color-muted)">{body}</p>
            </div>
          ))}
        </Card>
        <p className="sec-note mt-2.5">
          All of it runs overnight in the background, so the app itself is instant.
        </p>
      </section>

      <section className="my-5">
        <SectionHead
          title="What people are looking at"
          action={
            <Link href="/browse" className="text-[12.5px] font-semibold text-(--color-brand)">
              Browse all {featured?.length ?? 0} vehicles ›
            </Link>
          }
        />
        {featured === null ? (
          <Unavailable what="Featured verdicts" />
        ) : picks.length === 0 ? (
          <Card className="p-6">
            <p className="text-[13.5px] text-(--color-muted)">
              No verdicts have been computed yet. Run the pipeline and this fills in.
            </p>
          </Card>
        ) : (
          <div className="grid gap-4 md:grid-cols-3">
            {picks.map((v) => (
              <VehicleCard key={v.id} variant={v} />
            ))}
          </div>
        )}
      </section>

      <section className="my-5">
        <SectionHead title="Why this is not another review site" />
        <div className="grid gap-4 md:grid-cols-3">
          {CLAIMS.map(([title, body], i) => (
            <div
              key={title}
              className="rounded-xl border border-(--color-line) bg-(--color-surface) p-6"
            >
              <div className="text-[12px] font-bold tracking-[0.06em] text-(--color-brand)">
                0{i + 1}
              </div>
              <h3 className="mt-3 text-[16px] tracking-[-0.015em]">{title}</h3>
              <p className="mt-2 text-[13.5px] leading-relaxed text-(--color-muted)">{body}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="my-5">
        <Card className="bg-(--color-surface-2) p-6 shadow-none">
          <p className="text-[13.5px] leading-relaxed text-(--color-muted)">
            Where we do not have enough evidence for a vehicle, we say so and show no score, rather
            than publishing a bad one.{" "}
            <Link href="/method" className="font-semibold text-(--color-brand)">
              How a score is worked out.
            </Link>
          </p>
        </Card>
      </section>
    </>
  );
}

function VehicleCard({ variant }: { variant: VariantSummary }) {
  const score = variant.overall_score ?? 0;
  return (
    <Link
      href={`/v/${variant.id}`}
      className="block rounded-xl border border-(--color-line) bg-(--color-surface) p-5 shadow-[var(--shadow-card)] transition hover:-translate-y-0.5 hover:border-(--color-brand-line)"
    >
      <div className="text-[11px] font-bold tracking-[0.08em] text-(--color-faint) uppercase">
        {variant.vehicle_class === "car" ? "Car" : "Two-wheeler"}
      </div>
      <h3 className="mt-2 text-[16.5px] tracking-[-0.015em]">
        {variant.manufacturer} {variant.model}
      </h3>
      <div className="mt-0.5 text-[12.5px] text-(--color-muted)">{variant.variant_name}</div>

      <div className="mt-4 mb-1.5 flex items-baseline gap-2">
        <b className="text-[32px] font-bold tracking-[-0.035em] num">{score.toFixed(1)}</b>
        <span className="text-[12.5px] font-semibold text-(--color-faint) num">
          / 10 · range {variant.confidence_low?.toFixed(1)}–{variant.confidence_high?.toFixed(1)}
        </span>
      </div>
      <ScoreTrack
        score={score}
        low={variant.confidence_low}
        high={variant.confidence_high}
      />
      <div className="mt-3.5 border-t border-(--color-line-soft) pt-3 text-[12.5px] text-(--color-muted)">
        Built from <b className="font-semibold text-(--color-ink-2) num">{variant.evidence_count}</b>{" "}
        reviews.
      </div>
    </Link>
  );
}

export { heatOf, agreementWord };
