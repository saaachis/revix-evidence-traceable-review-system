import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { Card, PageHead, SectionHead } from "@/components/ui";
import { ApiError, api } from "@/lib/api";
import { monthYear } from "@/lib/format";

export const revalidate = 300;
export const metadata: Metadata = { title: "The reviews behind this number" };

type Props = { params: Promise<{ claimId: string }> };

export default async function EvidencePage({ params }: Props) {
  const { claimId } = await params;

  let drawer;
  try {
    drawer = await api.claimEvidence(claimId);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) notFound();
    throw error;
  }

  const shown = drawer.evidence.reduce((sum, e) => sum + e.contribution_weight, 0);
  const top = drawer.evidence[0]?.contribution_weight ?? 1;

  return (
    <>
      <PageHead title={`The reviews behind ${drawer.score.toFixed(1)}`}>
        These are not search results. They are the reviews that produced this number, listed in
        order of how much each one counted towards it. Change how reviews are counted on the
        verdict page and this list reorders itself, because the two are the same thing.
      </PageHead>

      <section className="my-5">
        <SectionHead
          title={`${drawer.evidence.length} of ${drawer.total_contributors} contributing reviews`}
          note="Weights are shares of the whole, so what is listed here sums to less than 100%."
        />
        <Card className="overflow-hidden">
          {drawer.evidence.map((review, i) => (
            <article
              key={review.id}
              className={`grid gap-5 p-5 md:grid-cols-[1fr_168px] ${
                i > 0 ? "border-t border-(--color-line-soft)" : ""
              }`}
            >
              <div>
                <div className="mb-2 flex flex-wrap items-center gap-2">
                  <span className="text-[11.5px] font-bold tracking-[0.05em] text-(--color-brand) uppercase">
                    {review.source}
                  </span>
                  {review.is_verified_owner && (
                    <span className="chip chip-ghost">Verified owner</span>
                  )}
                  {review.ownership_duration_months != null && (
                    <span className="chip chip-ghost">
                      {review.ownership_duration_months} months
                    </span>
                  )}
                  {review.km_driven != null && (
                    <span className="chip chip-ghost">
                      {review.km_driven.toLocaleString()} km
                    </span>
                  )}
                  <span className="text-[12px] text-(--color-faint)">
                    {monthYear(review.published_at)}
                  </span>
                </div>
                <p className="text-[13.5px] leading-relaxed text-(--color-ink-2)">{review.text}</p>
              </div>

              <aside className="border-t border-(--color-line-soft) pt-3.5 md:border-t-0 md:border-l md:pt-0 md:pl-4.5">
                <div className="text-[10.5px] font-bold tracking-[0.07em] text-(--color-faint) uppercase">
                  Counted for
                </div>
                <div className="my-1.5 text-[20px] font-bold tracking-[-0.02em] num">
                  {(review.contribution_weight * 100).toFixed(1)}%
                </div>
                <div className="h-1.5 overflow-hidden rounded-full bg-(--color-surface-2)">
                  <i
                    className="block h-full rounded-full bg-(--color-brand)"
                    style={{
                      width: `${Math.min(100, (review.contribution_weight / top) * 100)}%`,
                    }}
                  />
                </div>
                <p className="mt-2.5 text-[11.5px] leading-relaxed text-(--color-muted)">
                  {review.is_verified_owner &&
                  (review.ownership_duration_months ?? 0) >= 24
                    ? "A verified owner of over two years. Worth listening to on how this holds up."
                    : (review.ownership_duration_months ?? 99) < 3
                      ? "Written in the first months. It still counts, but it cannot speak to how the car ages."
                      : "Weighted by detail, corroboration, and whether this owner is a good witness to this topic."}
                </p>
              </aside>
            </article>
          ))}
        </Card>
      </section>

      <section className="my-5">
        <Card className="border-(--color-brand-line) bg-linear-to-b from-(--color-brand-tint) to-(--color-surface) to-72% p-6">
          <div className="text-[15.5px] font-semibold tracking-[-0.01em]">Why you can check us</div>
          <p className="mt-2 max-w-[88ch] text-[13px] leading-relaxed text-(--color-muted)">
            Most sites that cite their sources decide what to say first and look for supporting
            quotes afterwards. We do it the other way round. The {drawer.score.toFixed(1)} is
            calculated from exactly these reviews and exactly these weights, written down before any
            prose existed, so the list you are reading cannot drift away from the number it
            produced. The {drawer.evidence.length} shown here account for{" "}
            {(shown * 100).toFixed(0)}% of it.
          </p>
        </Card>
      </section>
    </>
  );
}
