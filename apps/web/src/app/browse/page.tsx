import type { Metadata } from "next";

import { VariantTable } from "@/components/VariantTable";
import { Card, Empty, PageHead, Pill, Unavailable } from "@/components/ui";
import { api, tryGet } from "@/lib/api";

export const revalidate = 300;
export const metadata: Metadata = { title: "Browse the catalogue" };

type Props = { searchParams: Promise<{ class?: string }> };

export default async function BrowsePage({ searchParams }: Props) {
  const { class: klass } = await searchParams;
  const vehicleClass = klass === "car" || klass === "two_wheeler" ? klass : undefined;

  const variants = await tryGet(() =>
    api.variants({ vehicle_class: vehicleClass, limit: 200 }),
  );

  if (variants === null) return <Unavailable what="The catalogue" />;

  const scored = variants.filter((v) => !v.is_suppressed);
  const thin = variants.length - scored.length;

  return (
    <>
      <PageHead title="Browse the catalogue">
        We cover a deliberately chosen set of vehicles rather than every vehicle on sale. Each one
        is here because it has enough reviews behind it for us to say something useful.
      </PageHead>

      <div className="mt-4 flex flex-wrap items-center gap-2">
        <Pill href="/browse" active={!vehicleClass}>
          Everything · {variants.length}
        </Pill>
        <Pill href="/browse?class=car" active={vehicleClass === "car"}>
          Cars
        </Pill>
        <Pill href="/browse?class=two_wheeler" active={vehicleClass === "two_wheeler"}>
          Two-wheelers
        </Pill>
        <span className="ml-auto text-[13px] text-(--color-muted)">
          Scores use <b className="font-semibold text-(--color-ink-2)">trust weighting</b>
        </span>
      </div>

      <section className="my-5">
        {variants.length === 0 ? (
          <Empty title="Nothing here yet">
            <p>No vehicles have been seeded. Run the pipeline and this fills in.</p>
          </Empty>
        ) : (
          <VariantTable variants={variants} />
        )}
      </section>

      {thin > 0 && (
        <section className="my-5">
          <Card className="bg-(--color-surface-2) p-6 shadow-none">
            <p className="text-[13.5px] leading-relaxed text-(--color-muted)">
              <b className="font-semibold text-(--color-ink-2)">{thin}</b> of these{" "}
              {variants.length} vehicles do not have a verdict yet, because we have not found enough
              reviews to give you one worth reading. We would rather show you a gap than fill it
              with guesswork.
            </p>
          </Card>
        </section>
      )}
    </>
  );
}
