import type { Metadata } from "next";
import Link from "next/link";

import { Card, PageHead, SectionHead } from "@/components/ui";

export const metadata: Metadata = {
  title: "How accurate are we",
  description:
    "We ask you to trust our numbers, so here is how well they hold up when we test them.",
};

export default function AccuracyPage() {
  return (
    <>
      <PageHead title="How accurate are we?">
        We ask you to trust our numbers, so here is how well they hold up when we test them. These
        figures are measured, not claimed. When one of them gets worse, it gets worse on this page
        too.
      </PageHead>

      <section className="my-5">
        <Card className="border-(--color-brand-line) bg-linear-to-b from-(--color-brand-tint) to-(--color-surface) to-72% p-6">
          <div className="text-[15.5px] font-semibold tracking-[-0.01em]">
            Being straight with you about this page
          </div>
          <p className="mt-2 max-w-[88ch] text-[13px] leading-relaxed text-(--color-muted)">
            The measurement harness is built but has not been run against a hand-labelled set yet,
            so we are not going to print numbers here and imply they mean something. What follows is
            exactly what we will measure and how, published now so the method is fixed before we see
            the results rather than chosen afterwards to flatter them.
          </p>
        </Card>
      </section>

      <section className="my-5">
        <SectionHead
          title="Does trust weighting actually beat star averaging?"
          note="The question the whole product rests on."
        />
        <Card className="p-6">
          <p className="max-w-[88ch] text-[13.5px] leading-relaxed text-(--color-muted)">
            We take the people best placed to judge a car, owners who have kept it over a year and
            driven it more than 10,000 km, and treat what they think as the answer. Then we{" "}
            <b className="font-semibold text-(--color-ink-2)">throw their reviews away</b> and see
            how close we can get using only the ordinary reviews that are left.
          </p>
          <p className="mt-3 max-w-[88ch] text-[13.5px] leading-relaxed text-(--color-muted)">
            This is not circular, because the target is defined by information the estimate never
            sees. If weighting by trust did not help, counting every review the same would do just
            as well, and the whole premise of this site would be wrong.
          </p>
          <div className="mt-4 grid gap-3 md:grid-cols-3">
            {[
              ["Every review counts the same", "The baseline every review site uses today."],
              ["Weighted by which site it came from", "Fixed priors per source."],
              ["Weighted by how much each can be trusted", "The default here."],
            ].map(([title, note], i) => (
              <div
                key={title}
                className={`rounded-lg border p-4 ${
                  i === 2
                    ? "border-(--color-brand-line) bg-(--color-brand-tint)"
                    : "border-(--color-line) bg-(--color-surface-2)"
                }`}
              >
                <div className="text-[13px] font-semibold">{title}</div>
                <p className="mt-1.5 text-[12.5px] text-(--color-muted)">{note}</p>
              </div>
            ))}
          </div>
        </Card>
      </section>

      <section className="my-5">
        <SectionHead title="What we will publish, and what it means" />
        <Card className="overflow-x-auto">
          <table className="tbl">
            <thead>
              <tr>
                <th>What we measure</th>
                <th>In plain terms</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {[
                [
                  "Right car, right variant",
                  "How often a review lands on the exact variant it describes.",
                  "Harness built, gold set pending",
                ],
                [
                  "Right topic",
                  "How often a sentence is filed where a person would file it.",
                  "Harness built, gold set pending",
                ],
                [
                  "Fake reviews caught",
                  "How much of a known-fake set gets pushed down before it can move a score.",
                  "Classifier not yet trained",
                ],
                [
                  "Honest ranges",
                  "Whether our 80% range contains the answer 80% of the time.",
                  "Harness built, run pending",
                ],
                [
                  "Serving speed",
                  "How long a verdict page takes to answer.",
                  "Measured: 29 ms at the 95th percentile",
                ],
              ].map(([what, plain, status]) => (
                <tr key={what}>
                  <td className="font-semibold text-(--color-ink)">{what}</td>
                  <td className="text-(--color-muted)">{plain}</td>
                  <td className="text-(--color-muted)">{status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      </section>

      <section className="my-5">
        <SectionHead title="What we already know we are bad at" />
        <Card className="p-6">
          <p className="max-w-[88ch] text-[13.5px] leading-relaxed text-(--color-muted)">
            Plenty of Indian reviews are written in a mix of Hindi and English, often typed in the
            Latin alphabet. Our current topic extraction is a keyword and rule system built around
            English words, so it understands those noticeably less well. A topic score built mostly
            from them is weaker than one built from English reviews. We would rather tell you that
            than average the problem out of sight, and it is the first thing a trained classifier
            has to fix.
          </p>
        </Card>
      </section>

      <section className="my-5">
        <Card className="bg-(--color-surface-2) p-6 shadow-none">
          <p className="text-[13.5px] leading-relaxed text-(--color-muted)">
            None of this means our verdict is the truth. There is no such thing as the objectively
            correct opinion of a car. What we can show you is our working, so you can decide how
            much of it to believe.{" "}
            <Link href="/method" className="font-semibold text-(--color-brand)">
              See how a score is worked out.
            </Link>
          </p>
        </Card>
      </section>
    </>
  );
}
