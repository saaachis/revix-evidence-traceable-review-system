import Link from "next/link";

import { AgreementChip, Card, ScoreTrack } from "@/components/ui";
import type { VariantSummary } from "@/lib/api";
import { FUEL, GEARBOX, priceRange } from "@/lib/format";

/**
 * The catalogue as a table.
 *
 * Variants rather than models, because that is the point. The Creta diesel
 * manual and the Creta turbo automatic sit a full point apart and every other
 * site averages them into one number, which is the number least useful to
 * somebody standing in a showroom choosing between them.
 */
export function VariantTable({ variants }: { variants: VariantSummary[] }) {
  return (
    <Card className="overflow-x-auto">
      <table className="tbl">
        <thead>
          <tr>
            <th>Vehicle</th>
            <th>Variant</th>
            <th>Fuel and gearbox</th>
            <th className="text-right">Price</th>
            <th className="text-right">Verdict</th>
            <th className="w-[170px]">Range</th>
            <th className="text-right">Reviews</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {variants.map((v) => {
            const scored = !v.is_suppressed && v.overall_score != null;
            return (
              <tr key={v.id} className={scored ? "" : "opacity-65"}>
                <td className="font-semibold text-(--color-ink)">
                  <Link href={`/v/${v.id}`} className="hover:text-(--color-brand)">
                    {v.manufacturer} {v.model}
                  </Link>
                </td>
                <td>{v.variant_name}</td>
                <td className="text-(--color-muted)">
                  {FUEL[v.fuel_type] ?? v.fuel_type} · {GEARBOX[v.transmission] ?? v.transmission}
                </td>
                <td className="text-right num">{priceRange(v.price_min, v.price_max) ?? "—"}</td>
                <td className="text-right num">
                  {scored ? (
                    <b className="font-semibold">{v.overall_score!.toFixed(1)}</b>
                  ) : (
                    <span className="text-(--color-muted)">No verdict</span>
                  )}
                </td>
                <td>
                  {scored ? (
                    <ScoreTrack
                      score={v.overall_score!}
                      low={v.confidence_low}
                      high={v.confidence_high}
                    />
                  ) : (
                    <span className="text-[12.5px] text-(--color-muted)">
                      Not enough reviews yet
                    </span>
                  )}
                </td>
                <td className="text-right num">{v.evidence_count}</td>
                <td className="text-right text-(--color-muted)">
                  <Link href={`/v/${v.id}`} aria-label={`Open the verdict for ${v.model}`}>
                    ›
                  </Link>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </Card>
  );
}

export { AgreementChip };
