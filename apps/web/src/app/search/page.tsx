import type { Metadata } from "next";
import Link from "next/link";

import { SearchBox } from "@/components/SearchBox";
import { VariantTable } from "@/components/VariantTable";
import { Card, Empty, PageHead, Pill, Unavailable } from "@/components/ui";
import { api, tryGet } from "@/lib/api";

export const revalidate = 300;

type Props = { searchParams: Promise<{ q?: string }> };

export async function generateMetadata({ searchParams }: Props): Promise<Metadata> {
  const { q } = await searchParams;
  return { title: q ? `Results for “${q}”` : "Search" };
}

const POPULAR = ["Creta", "Classic 350", "Activa", "Nexon", "Swift", "XUV700"];

export default async function SearchPage({ searchParams }: Props) {
  const { q } = await searchParams;
  const query = q?.trim() ?? "";

  const results = query ? await tryGet(() => api.variants({ q: query, limit: 100 })) : [];

  const models = new Set((results ?? []).map((v) => `${v.manufacturer} ${v.model}`));

  return (
    <>
      <PageHead title={query ? `Results for “${query}”` : "Search"}>
        {query && results
          ? `${results.length} ${results.length === 1 ? "vehicle" : "vehicles"} matched, across ${models.size} ${models.size === 1 ? "model" : "models"}.`
          : "Type a make, a model, or an exact variant."}
      </PageHead>

      <div className="mt-4">
        <SearchBox big />
      </div>

      <section className="my-6">
        {results === null ? (
          <Unavailable what="Search" />
        ) : query && results.length === 0 ? (
          <Card>
            <Empty
              icon="⌕"
              title={`Nothing matched “${query}”`}
              action={<Pill href="/browse" active>Browse the catalogue ›</Pill>}
            >
              <p>
                We cover a chosen set of vehicles, picked because they have enough reviews for us to
                say something useful. If yours is not here yet, it is because we could not find
                enough evidence to give you an honest answer.
              </p>
            </Empty>
          </Card>
        ) : query ? (
          <VariantTable variants={results} />
        ) : null}
      </section>

      <section className="my-5">
        <h2 className="sec-title mb-3">People often look for</h2>
        <div className="flex flex-wrap gap-2">
          {POPULAR.map((term) => (
            <Pill key={term} href={`/search?q=${encodeURIComponent(term)}`}>
              {term}
            </Pill>
          ))}
          <Pill href="/browse" active>
            Browse everything ›
          </Pill>
        </div>
      </section>

      <section className="my-5">
        <Card className="bg-(--color-surface-2) p-6 shadow-none">
          <p className="text-[13.5px] leading-relaxed text-(--color-muted)">
            We would rather show you nothing than a score built on nineteen reviews.{" "}
            <Link href="/method" className="font-semibold text-(--color-brand)">
              See what we cover and why.
            </Link>
          </p>
        </Card>
      </section>
    </>
  );
}
