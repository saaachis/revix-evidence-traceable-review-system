/**
 * The shared vocabulary of the interface.
 *
 * ScoreTrack is the one to understand. Every score in the product is drawn by
 * it and by nothing else, so a 7.8 on the home page, the verdict page and the
 * comparison all mean the same thing and are read the same way.
 */

import Link from "next/link";
import type { ReactNode } from "react";

import { type Heat, agreementWord, heatOf, pct } from "@/lib/format";

export function Wordmark({ tagline = true }: { tagline?: boolean }) {
  return (
    <span className="brand">
      <span className="brand-mark">revix</span>
      {tagline && <span className="brand-tag">driven by reviews</span>}
    </span>
  );
}

/**
 * A score, its confidence range, and nothing else.
 *
 * The dot is the score. The band is the range. Colour says how contested the
 * topic is, never how good it is.
 */
export function ScoreTrack({
  score,
  low,
  high,
  heat = "agreed",
}: {
  score: number;
  low?: number | null;
  high?: number | null;
  heat?: Heat;
}) {
  const lo = pct(low ?? score);
  const hi = pct(high ?? score);
  return (
    <div
      className="track"
      data-heat={heat}
      style={
        { "--v": pct(score), "--lo": lo, "--hi": hi } as React.CSSProperties
      }
      role="img"
      aria-label={
        low != null && high != null
          ? `Score ${score.toFixed(1)} out of 10, confident between ${low.toFixed(1)} and ${high.toFixed(1)}`
          : `Score ${score.toFixed(1)} out of 10`
      }
    >
      <div className="track-band" />
      <div className="track-dot" />
    </div>
  );
}

export function AgreementChip({ divergence }: { divergence: number | null | undefined }) {
  const heat = heatOf(divergence);
  return (
    <span className="chip" data-heat={heat} title={divergence == null ? undefined : `divergence ${divergence.toFixed(2)}`}>
      <span
        className="inline-block size-1.5 rounded-full bg-current"
        aria-hidden
      />
      {agreementWord(divergence)}
    </span>
  );
}

export function Card({
  children,
  className = "",
  as: Tag = "div",
}: {
  children: ReactNode;
  className?: string;
  as?: "div" | "section" | "article";
}) {
  return <Tag className={`card ${className}`}>{children}</Tag>;
}

export function SectionHead({
  title,
  note,
  action,
}: {
  title: string;
  note?: string;
  action?: ReactNode;
}) {
  return (
    <div className="mb-3 flex flex-wrap items-baseline gap-3">
      <h2 className="sec-title">{title}</h2>
      {note && <span className="sec-note ml-auto">{note}</span>}
      {action && <span className={note ? "" : "ml-auto"}>{action}</span>}
    </div>
  );
}

export function PageHead({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="pt-7 pb-1">
      <h1 className="text-[30px] tracking-[-0.03em]">{title}</h1>
      {children && (
        <p className="mt-2 max-w-[74ch] text-[14.5px] leading-relaxed text-(--color-muted)">
          {children}
        </p>
      )}
    </div>
  );
}

export function Crumb({ parts }: { parts: Array<{ label: string; href?: string }> }) {
  return (
    <nav className="flex flex-wrap items-center gap-2 pt-5 text-[13px] text-(--color-muted)">
      {parts.map((part, i) => (
        <span key={`${part.label}-${i}`} className="flex items-center gap-2">
          {part.href ? (
            <Link href={part.href} className="hover:text-(--color-brand)">
              {part.label}
            </Link>
          ) : (
            <b className="font-semibold text-(--color-ink-2)">{part.label}</b>
          )}
          {i < parts.length - 1 && <span className="text-(--color-faint)">›</span>}
        </span>
      ))}
    </nav>
  );
}

/** Used wherever a section could not load. A gap is honest; a crash is not. */
export function Unavailable({ what }: { what: string }) {
  return (
    <Card className="p-6">
      <p className="text-[13.5px] text-(--color-muted)">
        {what} could not be loaded right now. The rest of this page is unaffected,
        which is the point: one part failing degrades the product rather than
        breaking it.
      </p>
    </Card>
  );
}

export function Empty({
  icon = "⚠",
  title,
  children,
  action,
}: {
  icon?: string;
  title: string;
  children?: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div className="mx-auto max-w-[58ch] px-6 py-14 text-center">
      <div className="text-[34px] text-(--color-brand) opacity-50">{icon}</div>
      <h2 className="mt-4 text-[23px] tracking-[-0.02em]">{title}</h2>
      {children && (
        <div className="mt-3 text-[14.5px] leading-relaxed text-(--color-muted)">{children}</div>
      )}
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}

export function Pill({
  href,
  children,
  active = false,
}: {
  href: string;
  children: ReactNode;
  active?: boolean;
}) {
  return (
    <Link
      href={href}
      className={`inline-flex items-center gap-2 rounded-full border px-3.5 py-1.5 text-[13px] font-medium transition-colors ${
        active
          ? "border-(--color-brand-line) bg-(--color-brand-soft) font-semibold text-(--color-brand-deep)"
          : "border-(--color-line) bg-(--color-surface) text-(--color-ink-2) hover:border-(--color-brand-line) hover:text-(--color-brand)"
      }`}
    >
      {children}
    </Link>
  );
}
