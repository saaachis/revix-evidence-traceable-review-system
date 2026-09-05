import type { Metadata } from "next";
import Link from "next/link";

import { Card, Empty, PageHead, Pill, ScoreTrack, Unavailable } from "@/components/ui";
import { api, tryGet, type VerdictOut } from "@/lib/api";
import { heatOf, priceRange } from "@/lib/format";

export const revalidate = 300;
export const metadata: Metadata = { title: "Compare" };

type Props = { searchParams: Promise<{ a?: string; b?: string }> };

/** Two ranges that overlap mean we cannot honestly call a winner. */
function overlaps(x: VerdictOut | null, y: VerdictOut | null, key?: string): boolean {
  const pick = (v: VerdictOut | null) => {
    if (!v) return null;
    if (!key) return [v.confidence_low, v.confidence_high] as const;
    const a = v.aspects.find((row) => row.aspect_key === key);
    return a ? ([a.ci_low, a.ci_high] as const) : null;
  };
  const left = pick(x);
  const right = pick(y);
  if (!left?.[0] || !left?.[1] || !right?.[0] || !right?.[1]) return true;
  return left[0] <= right[1] && right[0] <= left[1];
}

export default async function ComparePage({ searchParams }: Props) {
  const { a, b } = await searchParams;

  if (!a || !b) return <Picker />;

  const [left, right] = await Promise.all([
    tryGet(() => api.verdict(a)),
    tryGet(() => api.verdict(b)),
  ]);

  if (!left || !right) return <Unavailable what="One of these vehicles" />;

  const keys = Array.from(
    new Set([...left.aspects, ...right.aspects].map((x) => x.aspect_key)),
  );
  const labels = new Map(
    [...left.aspects, ...right.aspects].map((x) => [x.aspect_key, x.label]),
  );

  const separable = keys.filter((k) => !overlaps(left, right, k)).length;

  return (
    <>
      <PageHead title="Compare">
        Two vehicles, topic by topic, with the range drawn on every score. Where the two ranges
        overlap we say they are too close to call, which is an honest answer and one that no
        comparison site will ever give you.
      </PageHead>

      <section className="my-5">
        <Card className="overflow-hidden">
          <div className="grid grid-cols-[130px_1fr_1fr] md:grid-cols-[210px_1fr_1fr]">
            <Head />
            <Head verdict={left} />
            <Head verdict={right} />

            <Label>Overall</Label>
            <Value verdict={left} />
            <Value verdict={right} />

            <Banner close={overlaps(left, right)}>
              {overlaps(left, right) ? (
                <>
                  <b>Too close to call.</b> The ranges overlap, so on the evidence we have these two
                  are not distinguishable overall. Anyone telling you one is better is reading
                  noise.
                </>
              ) : (
                <>
                  <b>A real difference.</b> The ranges do not overlap, so this gap survives the
                  uncertainty.
                </>
              )}
            </Banner>

            {keys.map((key) => {
              const l = left.aspects.find((x) => x.aspect_key === key);
              const r = right.aspects.find((x) => x.aspect_key === key);
              return (
                <div key={key} className="contents">
                  <Label>{labels.get(key)}</Label>
                  <Value aspect={l} />
                  <Value aspect={r} />
                </div>
              );
            })}
          </div>
        </Card>
      </section>

      <section className="my-5">
        <Card className="bg-(--color-surface-2) p-6 shadow-none">
          <p className="text-[13.5px] leading-relaxed text-(--color-muted)">
            Only <b className="font-semibold text-(--color-ink-2)">{separable}</b> of these{" "}
            {keys.length} topics separate the two properly. On the rest they are close enough that
            we cannot honestly call a winner. A comparison page that declared {keys.length} winners
            would be making most of them up.{" "}
            <Link href="/method" className="font-semibold text-(--color-brand)">
              Why the range matters.
            </Link>
          </p>
        </Card>
      </section>
    </>
  );
}

function Head({ verdict }: { verdict?: VerdictOut }) {
  if (!verdict) {
    return (
      <div className="border-b border-(--color-line) bg-(--color-surface-2) p-4.5">
        <span className="sec-title">Comparing</span>
        <p className="mt-2 text-[12.5px] text-(--color-muted)">Trust weighted</p>
      </div>
    );
  }
  const v = verdict.variant;
  return (
    <div className="border-b border-l border-(--color-line) bg-(--color-surface-2) p-4.5">
      <h3 className="text-[16px] tracking-[-0.015em]">
        <Link href={`/v/${v.id}`} className="hover:text-(--color-brand)">
          {v.manufacturer} {v.model}
        </Link>
      </h3>
      <div className="mt-0.5 text-[12.5px] text-(--color-muted)">
        {v.variant_name}
        {priceRange(v.price_min, v.price_max) && ` · ${priceRange(v.price_min, v.price_max)}`}
      </div>
    </div>
  );
}

function Label({ children }: { children: React.ReactNode }) {
  return (
    <div className="border-b border-(--color-line-soft) px-4.5 py-3.5 text-[13.5px] font-medium text-(--color-muted)">
      {children}
    </div>
  );
}

function Value({
  verdict,
  aspect,
}: {
  verdict?: VerdictOut;
  aspect?: { score: number | null; ci_low: number | null; ci_high: number | null; divergence_index: number | null };
}) {
  const score = verdict ? verdict.overall_score : aspect?.score;
  const low = verdict ? verdict.confidence_low : aspect?.ci_low;
  const high = verdict ? verdict.confidence_high : aspect?.ci_high;
  const heat = verdict ? "agreed" : heatOf(aspect?.divergence_index);

  return (
    <div className="flex items-center gap-3 border-b border-l border-(--color-line-soft) px-4.5 py-3.5">
      {score == null ? (
        <span className="text-[13px] text-(--color-muted)">not scored</span>
      ) : (
        <>
          <b className="w-[38px] text-[19px] font-bold num">{score.toFixed(1)}</b>
          <div className="flex-1">
            <ScoreTrack score={score} low={low} high={high} heat={heat} />
          </div>
        </>
      )}
    </div>
  );
}

function Banner({ close, children }: { close: boolean; children: React.ReactNode }) {
  return (
    <div
      className={`col-span-3 border-y px-4.5 py-3.5 text-[13px] ${
        close
          ? "border-(--color-brand-line) bg-(--color-brand-tint) text-(--color-brand-ink)"
          : "border-(--color-line) bg-(--color-surface-2) text-(--color-ink-2)"
      }`}
    >
      {children}
    </div>
  );
}

async function Picker() {
  const variants = await tryGet(() => api.variants({ limit: 200 }));
  const scored = (variants ?? []).filter((v) => !v.is_suppressed).slice(0, 12);

  return (
    <>
      <PageHead title="Compare">
        Pick two vehicles. We will show them topic by topic, and say plainly where the difference is
        real and where it is inside the noise.
      </PageHead>

      {scored.length < 2 ? (
        <Card className="my-5">
          <Empty title="Nothing to compare yet" action={<Pill href="/browse" active>Browse ›</Pill>}>
            <p>At least two vehicles need a verdict before a comparison means anything.</p>
          </Empty>
        </Card>
      ) : (
        <section className="my-5">
          <Card className="p-6">
            <p className="mb-4 text-[13.5px] text-(--color-muted)">
              A few pairs worth looking at:
            </p>
            <div className="flex flex-wrap gap-2">
              {scored.slice(0, 6).map((left, i) => {
                const right = scored[(i + 1) % scored.length];
                if (!right || right.id === left.id) return null;
                return (
                  <Pill key={left.id} href={`/compare?a=${left.id}&b=${right.id}`}>
                    {left.model} vs {right.model}
                  </Pill>
                );
              })}
            </div>
          </Card>
        </section>
      )}
    </>
  );
}
