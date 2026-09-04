"use client";

/**
 * The verdict page, and the switch that is the whole point of the project.
 *
 * All three weighting strategies are fetched on the server and handed to this
 * component together. Flipping the switch is therefore instant: no request, no
 * spinner, no chance of a cold free-tier database ruining the one moment the
 * demo rests on. That is only affordable because every strategy is computed
 * for every variant overnight, so switching is a lookup rather than a
 * recomputation.
 */

import Link from "next/link";
import { useState } from "react";

import { AgreementChip, Card, ScoreTrack, SectionHead } from "@/components/ui";
import type { AspectOut, FusionConfigOut, VerdictOut } from "@/lib/api";
import { COVARIATE_LABEL, FUEL, GEARBOX, heatOf, priceRange, relativeDay } from "@/lib/format";

type Props = {
  verdicts: Record<string, VerdictOut>;
  configs: FusionConfigOut[];
  initial: string;
};

export function VerdictView({ verdicts, configs, initial }: Props) {
  const available = configs.filter((c) => verdicts[c.name]);
  const [active, setActive] = useState(verdicts[initial] ? initial : (available[0]?.name ?? ""));

  const verdict = verdicts[active];
  const baseline = verdicts["equal"];
  const config = available.find((c) => c.name === active);

  if (!verdict) return null;

  const { variant } = verdict;
  const price = priceRange(variant.price_min, variant.price_max);

  return (
    <>
      <VerdictHeader verdict={verdict} price={price} />

      {available.length > 1 && (
        <section className="my-5">
          <Card className="border-(--color-brand-line) bg-linear-to-b from-(--color-brand-tint) to-(--color-surface) to-72% p-6">
            <div className="text-[15.5px] font-semibold tracking-[-0.01em]">
              How should these {verdict.evidence_count} reviews be counted?
            </div>
            <p className="mt-1 max-w-[88ch] text-[13px] leading-relaxed text-(--color-muted)">
              {config?.description}
            </p>

            <div className="seg mt-3.5" role="group" aria-label="Weighting strategy">
              {available.map((c) => (
                <button
                  key={c.name}
                  type="button"
                  aria-pressed={c.name === active}
                  onClick={() => setActive(c.name)}
                >
                  {c.label}
                </button>
              ))}
            </div>

            <WhatChanged verdict={verdict} baseline={baseline} active={active} />
          </Card>
        </section>
      )}

      <AspectList verdict={verdict} baseline={baseline} active={active} />
      <OfficialRecord verdict={verdict} />

      <section className="my-5">
        <Card className="bg-(--color-surface-2) p-6 shadow-none">
          <p className="text-[13.5px] leading-relaxed text-(--color-muted)">
            Every number on this page can be clicked, and it opens the actual reviews behind it
            along with how much each one counted. Nothing here is our opinion of what owners said.
            It is arithmetic on what they actually wrote, and you can check it.
          </p>
          <dl className="mt-4 grid gap-x-8 gap-y-2 text-[13px] sm:grid-cols-2">
            <Spec label="Fuel" value={FUEL[variant.fuel_type] ?? variant.fuel_type} />
            <Spec label="Gearbox" value={GEARBOX[variant.transmission] ?? variant.transmission} />
            {verdict.specs.engine_cc && (
              <Spec label="Engine" value={`${verdict.specs.engine_cc} cc`} />
            )}
            {verdict.specs.engine_power_bhp && (
              <Spec label="Power" value={`${verdict.specs.engine_power_bhp} bhp`} />
            )}
            {verdict.specs.kerb_weight_kg && (
              <Spec label="Kerb weight" value={`${verdict.specs.kerb_weight_kg} kg`} />
            )}
            {verdict.specs.seat_height_mm && (
              <Spec label="Seat height" value={`${verdict.specs.seat_height_mm} mm`} />
            )}
            {verdict.specs.seating_capacity && (
              <Spec label="Seats" value={String(verdict.specs.seating_capacity)} />
            )}
            {verdict.specs.braking_type && (
              <Spec label="Braking" value={verdict.specs.braking_type} />
            )}
          </dl>
        </Card>
      </section>
    </>
  );
}

function Spec({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-3 border-b border-(--color-line-soft) pb-1.5">
      <dt className="text-(--color-muted)">{label}</dt>
      <dd className="font-semibold text-(--color-ink-2)">{value}</dd>
    </div>
  );
}

function VerdictHeader({ verdict, price }: { verdict: VerdictOut; price: string | null }) {
  const { variant } = verdict;

  if (verdict.is_suppressed) {
    return (
      <Card className="my-5 overflow-hidden">
        <div className="p-7">
          <h1 className="text-[26px] tracking-[-0.025em]">
            {variant.manufacturer} {variant.model}{" "}
            <span className="font-medium text-(--color-muted)">{variant.variant_name}</span>
          </h1>
          <div className="mt-6 rounded-lg border border-(--color-brand-line) bg-(--color-brand-tint) p-5">
            <div className="text-[15.5px] font-semibold text-(--color-brand-ink)">
              We are not scoring this vehicle yet
            </div>
            <p className="mt-2 max-w-[80ch] text-[13.5px] leading-relaxed text-(--color-ink-2)">
              {verdict.suppression_reason}
            </p>
            <p className="mt-3 max-w-[80ch] text-[13px] leading-relaxed text-(--color-muted)">
              We could average what we have, print a number and draw a confident bar under it. Every
              review site in India does exactly that. But a handful of reviews cannot tell you
              whether a car is reliable at 60,000 km or what its service centres are like, and a
              number that pretends otherwise is worse than none.
            </p>
          </div>
        </div>
      </Card>
    );
  }

  const score = verdict.overall_score ?? 0;

  return (
    <Card className="my-5 grid overflow-hidden md:grid-cols-[1fr_320px]">
      <div className="p-7">
        <h1 className="text-[26px] tracking-[-0.025em]">
          {variant.manufacturer} {variant.model}{" "}
          <span className="font-medium text-(--color-muted)">{variant.variant_name}</span>
        </h1>
        <p className="mt-1.5 text-[13px] text-(--color-muted)">
          The exact variant, never just &ldquo;{variant.model}&rdquo;. Every number below is for
          this configuration only.
        </p>

        <div className="mt-6 flex items-end gap-5">
          <div
            key={`${verdict.fusion}-${score}`}
            className="score-anim num text-[60px] leading-[0.9] font-bold tracking-[-0.045em]"
          >
            {score.toFixed(1)}
          </div>
          <div className="pb-1.5 text-[17px] font-semibold text-(--color-faint)">/ 10</div>
          <div className="min-w-0 flex-1 pb-1.5">
            <ScoreTrack score={score} low={verdict.confidence_low} high={verdict.confidence_high} />
            <div className="mt-1.5 flex items-baseline justify-between text-[11px] text-(--color-faint)">
              <span>0</span>
              <span className="num text-[12px] text-(--color-muted)">
                confident range{" "}
                <b className="font-semibold text-(--color-ink-2)">
                  {verdict.confidence_low?.toFixed(1)} &ndash; {verdict.confidence_high?.toFixed(1)}
                </b>
              </span>
              <span>10</span>
            </div>
          </div>
        </div>

        <p className="mt-5 border-t border-(--color-line-soft) pt-4 text-[12.5px] leading-relaxed text-(--color-muted)">
          <b className="num font-semibold text-(--color-ink-2)">{verdict.evidence_count}</b> reviews
          <Sep />
          <b className="num font-semibold text-(--color-ink-2)">{verdict.sources_used.length}</b>{" "}
          {verdict.sources_used.length === 1 ? "source" : "sources"}
          <Sep />
          effective sample{" "}
          <b className="num font-semibold text-(--color-ink-2)">
            {verdict.effective_sample_size?.toFixed(0)}
          </b>
          <Sep />
          updated{" "}
          <b className="font-semibold text-(--color-ink-2)">{relativeDay(verdict.computed_at)}</b>
        </p>
      </div>

      <aside className="border-t border-(--color-line) bg-(--color-surface-2) p-6 md:border-t-0 md:border-l">
        {price && (
          <div className="text-[19px] font-bold tracking-[-0.02em]">
            {price}
            <small className="mt-0.5 block text-[11.5px] font-medium tracking-normal text-(--color-faint)">
              ex-showroom
            </small>
          </div>
        )}
        <p className="mt-4 border-t border-(--color-line) pt-4 text-[12.5px] leading-relaxed text-(--color-muted)">
          Read across{" "}
          {verdict.sources_used.length === 1
            ? "one source"
            : `${verdict.sources_used.length} sources`}
          . When a source stops working we say so and the count here drops, rather than quietly
          staying the same.
        </p>
      </aside>
    </Card>
  );
}

const Sep = () => <span className="mx-2.5 text-(--color-line)">·</span>;

/**
 * What flipping the switch actually did, measured against the baseline every
 * other review site uses. Computed here rather than written by hand, so it
 * cannot become a claim the data does not support.
 */
function WhatChanged({
  verdict,
  baseline,
  active,
}: {
  verdict: VerdictOut;
  baseline: VerdictOut | undefined;
  active: string;
}) {
  if (!baseline || active === "equal") {
    return (
      <div className="mt-4 flex flex-wrap items-center gap-2 border-t border-dashed border-(--color-brand-line) pt-4 text-[13px] text-(--color-ink-2)">
        <span className="font-semibold">This is the baseline.</span>
        <span className="text-(--color-muted)">
          Every other review site stops here. Flip the switch to see what it hides.
        </span>
      </div>
    );
  }

  const before = new Map(baseline.aspects.map((a) => [a.aspect_key, a.score ?? 0]));
  const moved = verdict.aspects
    .map((a) => ({ label: a.label, delta: (a.score ?? 0) - (before.get(a.aspect_key) ?? 0) }))
    .filter((m) => Math.abs(m.delta) >= 0.2)
    .sort((a, b) => Math.abs(b.delta) - Math.abs(a.delta))
    .slice(0, 3);

  const overallDelta = (verdict.overall_score ?? 0) - (baseline.overall_score ?? 0);
  const widened =
    (verdict.confidence_high ?? 0) - (verdict.confidence_low ?? 0) >
    (baseline.confidence_high ?? 0) - (baseline.confidence_low ?? 0);

  return (
    <div className="mt-4 flex flex-wrap items-center gap-2 border-t border-dashed border-(--color-brand-line) pt-4 text-[13px] text-(--color-ink-2)">
      <span className="font-semibold">Compared with counting every review equally:</span>
      <Delta label="Overall" delta={overallDelta} />
      {moved.map((m) => (
        <Delta key={m.label} label={m.label.split(",")[0] ?? m.label} delta={m.delta} />
      ))}
      {widened && (
        <span className="text-(--color-muted)">
          effective sample falls to {verdict.effective_sample_size?.toFixed(0)}, so the range
          widens. Being choosier about evidence means having less of it.
        </span>
      )}
    </div>
  );
}

function Delta({ label, delta }: { label: string; delta: number }) {
  if (Math.abs(delta) < 0.05) {
    return <span className="delta delta-flat">{label} no change</span>;
  }
  return (
    <span className={`delta ${delta < 0 ? "delta-down" : "delta-up"}`}>
      {label} {delta < 0 ? "▼" : "▲"} {Math.abs(delta).toFixed(1)}
    </span>
  );
}

function AspectList({
  verdict,
  baseline,
  active,
}: {
  verdict: VerdictOut;
  baseline: VerdictOut | undefined;
  active: string;
}) {
  if (verdict.is_suppressed || verdict.aspects.length === 0) return null;
  const before = new Map((baseline?.aspects ?? []).map((a) => [a.aspect_key, a.score ?? 0]));

  return (
    <section className="my-5">
      <SectionHead
        title="What owners argue about"
        note="Ordered by how much owners disagree, not by score. The arguments are the useful part."
      />
      <Card className="overflow-hidden">
        {verdict.aspects.map((aspect, index) => (
          <AspectRow
            key={aspect.aspect_key}
            aspect={aspect}
            index={index}
            expanded={index === 0}
            delta={
              active === "equal" ? null : (aspect.score ?? 0) - (before.get(aspect.aspect_key) ?? 0)
            }
          />
        ))}
      </Card>
    </section>
  );
}

function AspectRow({
  aspect,
  index,
  expanded,
  delta,
}: {
  aspect: AspectOut;
  index: number;
  expanded: boolean;
  delta: number | null;
}) {
  const [open, setOpen] = useState(expanded);
  const heat = heatOf(aspect.divergence_index);
  const explanation = aspect.covariate_explanation;
  const href = aspect.claim_id ? `/evidence/${aspect.claim_id}` : null;

  return (
    <div className={index > 0 ? "border-t border-(--color-line-soft)" : ""}>
      <div className="grid items-center gap-4 px-6 py-4 md:grid-cols-[1fr_56px_150px_215px_86px]">
        <div className="text-[14.5px] font-semibold tracking-[-0.005em]">
          <span className="num mr-2 text-[12px] font-semibold text-(--color-faint)">
            {index + 1}
          </span>
          {aspect.label}
        </div>

        <div
          key={`${aspect.aspect_key}-${aspect.score}`}
          className="score-anim num text-right text-[20px] font-bold tracking-[-0.02em]"
        >
          {aspect.score?.toFixed(1) ?? "—"}
        </div>

        <div className="hidden md:block">
          <ScoreTrack
            score={aspect.score ?? 0}
            low={aspect.ci_low}
            high={aspect.ci_high}
            heat={heat}
          />
        </div>

        <div className="flex flex-nowrap items-center gap-2 whitespace-nowrap">
          <AgreementChip divergence={aspect.divergence_index} />
          {delta != null && Math.abs(delta) >= 0.2 && (
            <span className={`delta ${delta < 0 ? "delta-down" : "delta-up"}`}>
              {delta < 0 ? "▼" : "▲"} {Math.abs(delta).toFixed(1)}
            </span>
          )}
        </div>

        <div className="text-right text-[12.5px] font-semibold whitespace-nowrap text-(--color-muted)">
          {href ? (
            <Link href={href} className="hover:text-(--color-brand)">
              {aspect.support_count} reviews &rsaquo;
            </Link>
          ) : (
            <span>{aspect.support_count} reviews</span>
          )}
        </div>
      </div>

      {explanation && !open && (
        <button
          type="button"
          onClick={() => setOpen(true)}
          className="-mt-1.5 px-6 pb-4 text-[12.5px] font-semibold text-(--color-brand) hover:text-(--color-brand-deep)"
        >
          Why do they disagree? &#9662;
        </button>
      )}

      {explanation && open && (
        <div className="mx-6 mb-4 rounded-lg border border-l-[3px] border-(--color-brand-line) border-l-(--color-brand) bg-(--color-brand-tint) p-4">
          <h4 className="text-[13.5px] font-semibold text-(--color-brand-ink)">
            {Math.round(explanation.explained_share * 100)}% of this disagreement is explained by{" "}
            {COVARIATE_LABEL[explanation.covariate] ?? explanation.covariate}
          </h4>
          <div className="mt-3 flex max-w-[540px] flex-col gap-2">
            {explanation.groups.map((group, i) => (
              <div
                key={group.value}
                className="grid grid-cols-[150px_1fr_34px] items-center gap-3 text-[13px]"
              >
                <div className="font-medium text-(--color-ink-2)">{group.value}</div>
                <div className="h-2 overflow-hidden rounded-full bg-(--color-brand)/13">
                  <i
                    className="block h-full rounded-full bg-(--color-brand)"
                    style={{ width: `${group.score * 10}%`, opacity: i === 0 ? 1 : 0.45 }}
                  />
                </div>
                <div className="num text-right font-bold">{group.score.toFixed(1)}</div>
              </div>
            ))}
          </div>
          <p className="mt-3 text-[12.5px] text-(--color-muted)">
            This is a statistical decomposition of the spread, not a guess. We do not just report
            that people disagree, we say what accounts for it.
            {aspect.claim_id && (
              <>
                {" "}
                <Link
                  href={`/evidence/${aspect.claim_id}`}
                  className="font-semibold text-(--color-brand)"
                >
                  See the {aspect.support_count} reviews &rsaquo;
                </Link>
              </>
            )}
          </p>
        </div>
      )}
    </div>
  );
}

/**
 * Measured facts get a different visual form from opinion, on purpose. They
 * have no score and no range because they are matters of record.
 */
function OfficialRecord({ verdict }: { verdict: VerdictOut }) {
  const { specs, variant } = verdict;
  if (verdict.is_suppressed) return null;

  const isBike = variant.vehicle_class === "two_wheeler";

  return (
    <section className="my-5">
      <SectionHead
        title="The official record"
        note="Measured facts rather than opinion, so they get no score and no range."
      />
      <div className="grid gap-3.5 md:grid-cols-3">
        {specs.arai_mileage_kmpl && (
          <Fact
            label="Claimed mileage"
            value={specs.arai_mileage_kmpl.toFixed(1)}
            unit="kmpl"
            note="The ARAI figure. What owners actually report lands lower, and the gap is what we intend to publish next."
          />
        )}
        {isBike ? (
          <Fact
            label="Crash safety"
            value="No rating exists"
            muted
            note="Bharat NCAP does not rate two-wheelers. We say so rather than showing an empty star row."
          />
        ) : (
          <Fact
            label="Crash safety"
            value="Not yet linked"
            muted
            note="Bharat NCAP ratings arrive with the regulatory connector."
          />
        )}
        <Fact
          label="Specification sheet"
          value={`${Math.round(specs.spec_completeness * 100)}%`}
          note="How much of the manufacturer's specification we hold for this exact variant."
        />
      </div>
    </section>
  );
}

function Fact({
  label,
  value,
  unit,
  note,
  muted = false,
}: {
  label: string;
  value: string;
  unit?: string;
  note: string;
  muted?: boolean;
}) {
  return (
    <div
      className={`rounded-xl border p-5 ${
        muted
          ? "border-dashed border-(--color-line) bg-(--color-surface-2)"
          : "border-(--color-line) bg-(--color-surface)"
      }`}
    >
      <div className="text-[11.5px] font-bold tracking-[0.07em] text-(--color-faint) uppercase">
        {label}
      </div>
      <div
        className={`num mt-2 font-bold tracking-[-0.03em] ${
          muted ? "text-[17px] text-(--color-muted)" : "text-[27px]"
        }`}
      >
        {value}
        {unit && (
          <small className="ml-1 text-[14px] font-semibold text-(--color-muted)">{unit}</small>
        )}
      </div>
      <p className="mt-2 text-[12.5px] leading-relaxed text-(--color-muted)">{note}</p>
    </div>
  );
}
