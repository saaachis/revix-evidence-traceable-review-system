/**
 * Presentation helpers.
 *
 * The important one is `heatOf`. Colour in this product encodes how contested
 * a topic is, never how good it is, so a red 6.2 reads as "people argue about
 * this" rather than "this is bad". Quality is shown by position on the track
 * and by nothing else.
 */

export type Heat = "split" | "some" | "agreed";

export function heatOf(divergence: number | null | undefined): Heat {
  if (divergence == null) return "agreed";
  if (divergence >= 0.4) return "split";
  if (divergence >= 0.22) return "some";
  return "agreed";
}

/** Words, because "0.61" means nothing to somebody choosing a car. */
export function agreementWord(divergence: number | null | undefined): string {
  if (divergence == null) return "not enough evidence";
  if (divergence >= 0.4) return "sharply split";
  if (divergence >= 0.22) return "some disagreement";
  return "broad agreement";
}

/** A 0..10 score as a percentage along the track. */
export const pct = (score: number) => Math.max(0, Math.min(100, score * 10));

export function rupees(paise: number | null | undefined): string | null {
  if (paise == null) return null;
  const lakh = paise / 100_000;
  return lakh >= 100
    ? `₹${(lakh / 100).toFixed(2)} Cr`
    : `₹${lakh.toFixed(2)} L`;
}

export function priceRange(min?: number | null, max?: number | null): string | null {
  const lo = rupees(min);
  const hi = rupees(max);
  if (!lo) return null;
  return hi && hi !== lo ? `${lo} – ${hi}` : lo;
}

export function score(value: number | null | undefined): string {
  return value == null ? "—" : value.toFixed(1);
}

export function relativeDay(iso: string | null | undefined): string {
  if (!iso) return "never";
  const days = Math.floor((Date.now() - new Date(iso).getTime()) / 86_400_000);
  if (days <= 0) return "today";
  if (days === 1) return "yesterday";
  if (days < 30) return `${days} days ago`;
  const months = Math.floor(days / 30);
  return months === 1 ? "a month ago" : `${months} months ago`;
}

export function monthYear(iso: string | null | undefined): string {
  if (!iso) return "";
  return new Date(iso).toLocaleDateString("en-GB", { month: "long", year: "numeric" });
}

export const GEARBOX: Record<string, string> = {
  mt: "Manual",
  at: "Automatic",
  amt: "AMT",
  cvt: "CVT",
  dct: "DCT",
  ivt: "IVT",
};

export const FUEL: Record<string, string> = {
  petrol: "Petrol",
  diesel: "Diesel",
  cng: "CNG",
  hybrid: "Hybrid",
  electric: "Electric",
};

export const titleCase = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);

/** How a covariate reads in a sentence, rather than as a column name. */
export const COVARIATE_LABEL: Record<string, string> = {
  source: "where the review came from",
  verified: "whether the owner is verified",
  ownership_bucket: "how long they have owned it",
  distance_bucket: "how far they have driven it",
};
