import type { Metadata } from "next";
import Link from "next/link";

import { Card, PageHead, SectionHead, Unavailable } from "@/components/ui";
import { api, tryGet } from "@/lib/api";

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
export const metadata: Metadata = {
  title: "Where the evidence comes from",
  description:
    "Every source we read, what we take from it, and how we behave while doing it.",
};

const RULES = [
  [
    "We read the terms first",
    "Before we read a site for the first time, somebody reads its robots file and its terms, and records what they say and on what date. That record is stored against the source, not in someone's memory.",
  ],
  [
    "We use the front door wherever there is one",
    "Where a source publishes an interface for the purpose, we use it rather than scraping around it.",
  ],
  [
    "We are slow on purpose",
    "Rate limiting, exponential backoff, and a breaker that stops entirely after repeated refusals. If a source starts refusing us, the correct response is to stop asking, and that is what the code does.",
  ],
  [
    "We store references and structure, not copies",
    "We keep what we derived and a link back to the original. We are not a mirror of anyone's content.",
  ],
  [
    "We attribute on every surface",
    "Every review shown on an evidence page carries its source.",
  ],
  [
    "Authors are pseudonymous",
    "We store a stable opaque key so we can spot one account posting in bursts. We do not store names, emails or profile links.",
  ],
  [
    "If terms forbid it, we drop the source",
    "And write down why. The product is built to survive that, which is what makes the rule credible rather than decorative.",
  ],
] as const;

export default async function SourcesPage() {
  const sources = await tryGet(() => api.sourceHealth());

  return (
    <>
      <PageHead title="Where the evidence comes from">
        Every source we read, what we take from it, and how we behave while doing it. This page
        exists because a system that weighs other people&rsquo;s writing owes them a straight answer
        about it.
      </PageHead>

      <section className="my-5">
        <SectionHead
          title="What we are reading right now"
          note="Live, from the same registry the pipeline uses."
        />
        {sources === null ? (
          <Unavailable what="The source list" />
        ) : (
          <Card className="overflow-x-auto">
            <table className="tbl">
              <thead>
                <tr>
                  <th>Source</th>
                  <th>Kind</th>
                  <th className="text-right">Reviews contributed</th>
                  <th>Currently</th>
                </tr>
              </thead>
              <tbody>
                {sources.map((s) => (
                  <tr key={s.source_key}>
                    <td className="font-semibold text-(--color-ink)">{s.display_name}</td>
                    <td className="text-(--color-muted)">{s.kind.replace(/_/g, " ")}</td>
                    <td className="text-right num">{s.units_total.toLocaleString()}</td>
                    <td className="text-(--color-muted)">
                      {s.status === "succeeded"
                        ? "Reading normally"
                        : s.status === "circuit_open"
                          ? "Refusing us, so we stopped asking"
                          : s.status === "failed"
                            ? "Failing"
                            : "Not run yet"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
        )}
        <p className="sec-note mt-2.5">
          Live state, including error rates, is on the{" "}
          <Link href="/status" className="font-semibold text-(--color-brand)">
            status page
          </Link>
          .
        </p>
      </section>

      <section className="my-5">
        <SectionHead title="The rules we hold ourselves to" />
        <Card className="p-6">
          <ul className="flex flex-col">
            {RULES.map(([title, body], i) => (
              <li
                key={title}
                className={`py-3.5 ${i > 0 ? "border-t border-(--color-line-soft)" : ""}`}
              >
                <h4 className="text-[14.5px]">{title}</h4>
                <p className="mt-1 max-w-[88ch] text-[13.5px] leading-relaxed text-(--color-muted)">
                  {body}
                </p>
              </li>
            ))}
          </ul>
        </Card>
      </section>

      <section className="my-5">
        <SectionHead title="What we are not doing" />
        <Card className="p-6">
          <p className="max-w-[88ch] text-[13.5px] leading-relaxed text-(--color-muted)">
            We are not fetching anything while you use the site. Every page you see was computed
            overnight. We are not reselling anyone&rsquo;s reviews, we do not republish them in
            full, and we do not accept payment from any manufacturer or dealer. That last one is
            precisely why we can afford to say that a car&rsquo;s service experience is poor.
          </p>
        </Card>
      </section>

      <section className="my-5">
        <Card className="border-(--color-brand-line) bg-linear-to-b from-(--color-brand-tint) to-(--color-surface) to-72% p-6">
          <div className="text-[15.5px] font-semibold tracking-[-0.01em]">
            Why one source going down does not matter much
          </div>
          <p className="mt-2 max-w-[88ch] text-[13px] leading-relaxed text-(--color-muted)">
            Every source is kept separate from every other, so losing one costs us coverage rather
            than the whole site. When it happens, every affected verdict page tells you how many
            places that verdict was built from, so you can see the difference rather than having it
            hidden from you.
          </p>
        </Card>
      </section>
    </>
  );
}
