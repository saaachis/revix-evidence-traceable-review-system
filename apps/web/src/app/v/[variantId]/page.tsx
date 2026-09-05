import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { VerdictView } from "@/components/VerdictView";
import { Crumb } from "@/components/ui";
import { ApiError, api, type VerdictOut } from "@/lib/api";

export const revalidate = 300;

type Props = { params: Promise<{ variantId: string }> };

async function load(variantId: string) {
  const configs = await api.fusionConfigs();

  // Every strategy is fetched here, on the server, and handed to the client
  // together. That is what makes flipping the switch instant: no request, no
  // spinner, and no chance of a cold free-tier database ruining the one moment
  // the demo actually rests on. It is only affordable because the pipeline
  // computes every strategy for every variant overnight.
  const results = await Promise.all(
    configs.map(async (config) => {
      try {
        return [config.name, await api.verdict(variantId, config.name)] as const;
      } catch {
        return [config.name, null] as const;
      }
    }),
  );

  const verdicts: Record<string, VerdictOut> = {};
  for (const [name, verdict] of results) if (verdict) verdicts[name] = verdict;
  return { configs, verdicts };
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { variantId } = await params;
  try {
    const verdict = await api.verdict(variantId);
    const v = verdict.variant;
    return {
      title: `${v.manufacturer} ${v.model} ${v.variant_name}`,
      description: verdict.is_suppressed
        ? `We do not have enough evidence to score the ${v.model} ${v.variant_name} yet.`
        : `Scores ${verdict.overall_score?.toFixed(1)} out of 10, from ${verdict.evidence_count} reviews across ${verdict.sources_used.length} sources.`,
    };
  } catch {
    return { title: "Verdict" };
  }
}

export default async function VerdictPage({ params }: Props) {
  const { variantId } = await params;

  let data: Awaited<ReturnType<typeof load>>;
  try {
    data = await load(variantId);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) notFound();
    throw error;
  }

  const first = Object.values(data.verdicts)[0];
  if (!first) notFound();

  const preferred = data.configs.find((c) => c.is_default)?.name ?? "credibility_weighted";
  const v = first.variant;

  return (
    <>
      <Crumb
        parts={[
          { label: v.vehicle_class === "car" ? "Cars" : "Two-wheelers", href: "/browse" },
          { label: v.manufacturer, href: `/search?q=${encodeURIComponent(v.manufacturer)}` },
          { label: v.model, href: `/search?q=${encodeURIComponent(v.model)}` },
          { label: v.variant_name },
        ]}
      />
      <VerdictView verdicts={data.verdicts} configs={data.configs} initial={preferred} />
    </>
  );
}
