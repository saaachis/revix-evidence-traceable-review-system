import type { Metadata } from "next";
import Link from "next/link";

import { Card, PageHead } from "@/components/ui";

export const metadata: Metadata = {
  title: "How a score is worked out",
  description:
    "In plain language, with the actual arithmetic shown. If you disagree with any step, you can see exactly where to disagree.",
};

const STEPS = [
  [
    "We collect the evidence",
    "Owner reviews, expert reviews, forum threads, video transcripts and official records, read at a polite rate, cached, and linked back to. We store references and structure, not copies of anyone's writing.",
  ],
  [
    "We match every review to one exact variant",
    "A petrol listing is never matched to a diesel variant, whatever the text similarity says. Specifications act as hard constraints before any learned matching runs. Anything ambiguous waits for a person instead of being guessed at.",
  ],
  [
    "We split each review into nine topics",
    "A review is rarely about one thing. One paragraph can praise the ride and condemn the service centre, so we score those separately rather than averaging them into a single star rating.",
  ],
  [
    "We work out how much each review should count",
    "This is the part that makes Revix different, and it is spelled out below.",
  ],
  [
    "We combine, and we say how sure we are",
    "A weighted average, plus a range that widens when the evidence is thin or lopsided.",
  ],
] as const;

export default function MethodPage() {
  return (
    <>
      <PageHead title="How a score is worked out">
        In plain language, with the actual arithmetic shown. If you disagree with any step you can
        see exactly where to disagree, which is the point.
      </PageHead>

      <section className="my-5">
        <Card className="p-6">
          <ol className="flex flex-col">
            {STEPS.map(([title, body], i) => (
              <li
                key={title}
                className={`grid grid-cols-[34px_1fr] gap-3.5 py-3.5 ${
                  i > 0 ? "border-t border-(--color-line-soft)" : ""
                }`}
              >
                <span className="grid size-[26px] place-items-center rounded-full bg-(--color-brand-soft) text-[12px] font-bold text-(--color-brand-deep)">
                  {i + 1}
                </span>
                <div>
                  <h4 className="text-[14.5px]">{title}</h4>
                  <p className="mt-1 text-[13.5px] leading-relaxed text-(--color-muted)">{body}</p>
                </div>
              </li>
            ))}
          </ol>
        </Card>
      </section>

      <div className="max-w-[76ch]">
        <h2 className="mt-9 mb-3 text-[21px] tracking-[-0.02em]">
          What decides a review&rsquo;s weight
        </h2>
        <p className="mb-3.5 text-[14.5px] leading-relaxed text-(--color-ink-2)">
          Every review gets a weight between 0 and 1 for each topic. It is a product of six terms,
          so any single bad signal pulls the whole weight down.
        </p>
        <Formula>
          {`weight = source_prior
       × (1 − spam_probability)
       × reliability
       × aspect_fit          ← the interesting one
       × recency
       × launch_window`}
        </Formula>
        <p className="mb-3.5 text-[14.5px] leading-relaxed text-(--color-ink-2)">
          Five of those are ordinary. <b className="text-(--color-ink)">aspect_fit</b> is the one
          that makes the argument, and it exists only because this is the automobile domain.
        </p>

        <h3 className="mt-6 mb-2 text-[16px]">
          Why the same person is a good witness to one thing and a bad witness to another
        </h3>
        <p className="mb-3.5 text-[14.5px] leading-relaxed text-(--color-ink-2)">
          An owner who has covered 500 km can tell you a great deal about the showroom, the delivery
          experience and the first service appointment. They can tell you nothing useful about
          whether the clutch survives 60,000 km. An owner at 60,000 km is the reverse.
        </p>
        <p className="mb-3.5 text-[14.5px] leading-relaxed text-(--color-ink-2)">
          Indian review platforms record ownership duration and kilometres driven, and then throw
          that information away by averaging every review equally. We use it. Credibility is
          therefore not one number per review; it is a short vector across topic groups.
        </p>
        <Formula>
          {`{ "base": 0.71,
  "by_aspect_group": {
      "durability":  0.88,   ← trusted on long-term reliability
      "immediate":   0.42,   ← less so on first impressions
      "service":     0.83,
      "efficiency":  0.79
  } }`}
        </Formula>

        <h2 className="mt-9 mb-3 text-[21px] tracking-[-0.02em]">Why the range is not decoration</h2>
        <p className="mb-3.5 text-[14.5px] leading-relaxed text-(--color-ink-2)">
          When reviews carry different weights, the number of reviews stops being a useful measure
          of how much you know. Two hundred low-weight reviews can carry less real information than
          thirty high-weight ones. The standard way to express that is the{" "}
          <b className="text-(--color-ink)">effective sample size</b>:
        </p>
        <Formula>{`n_eff = (Σ w)² / Σ w²`}</Formula>
        <p className="mb-3.5 text-[14.5px] leading-relaxed text-(--color-ink-2)">
          This is why switching to trust weighting makes the range <i>wider</i>, not narrower. Being
          more careful about which evidence counts means admitting you have less of it. You can
          watch that happen on any verdict page: flip the switch and the effective sample drops
          while the interval opens up.
        </p>

        <h2 className="mt-9 mb-3 text-[21px] tracking-[-0.02em]">
          Why we show disagreement instead of hiding it
        </h2>
        <p className="mb-3.5 text-[14.5px] leading-relaxed text-(--color-ink-2)">
          When owners split on a topic we do not just report the split, we try to explain it. For
          each topic we test which characteristic best accounts for the disagreement: where the
          review came from, whether the owner is verified, how long they have owned it, how far they
          have driven it. That produces statements like:
        </p>
        <p className="mb-3.5 border-l-[3px] border-(--color-brand) pl-4 text-[14.5px] leading-relaxed text-(--color-ink)">
          <b>54% of the disagreement about build quality is explained by how far people have
          driven.</b>{" "}
          Under 10,000 km they rate it 5.1. Over 40,000 km they rate it 9.1.
        </p>
        <p className="mb-3.5 text-[14.5px] leading-relaxed text-(--color-ink-2)">
          That is a statistical decomposition of the spread, not a language model&rsquo;s opinion.
          It is cheaper, more reliable, and far more useful to somebody choosing between two
          versions of the same car.
        </p>

        <h2 className="mt-9 mb-3 text-[21px] tracking-[-0.02em]">What we do not claim</h2>
        <ul className="mb-3.5 list-disc pl-5">
          {[
            "That our verdict is objectively correct. There is no ground truth for consumer opinion, and anyone who says otherwise is selling something.",
            "That we detect every fake review. The spam score is one term in a product, not a filter that deletes things.",
            "Any absolute assertion about a manufacturer's quality.",
          ].map((line) => (
            <li key={line} className="mb-1.5 text-[14.5px] leading-relaxed text-(--color-ink-2)">
              {line}
            </li>
          ))}
        </ul>
        <p className="mb-3.5 text-[14.5px] leading-relaxed text-(--color-ink-2)">
          We do not rank by who pays us, because nobody pays us. Where we do not have enough
          evidence, we show no score at all.{" "}
          <Link href="/accuracy" className="font-semibold text-(--color-brand)">
            See how accurate we are.
          </Link>
        </p>
      </div>
    </>
  );
}

function Formula({ children }: { children: string }) {
  return (
    <pre className="mb-3.5 overflow-x-auto rounded-lg border border-(--color-line) bg-(--color-surface-2) p-4.5 font-mono text-[13px] leading-relaxed text-(--color-ink-2)">
      {children}
    </pre>
  );
}
