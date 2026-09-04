"use client";

/**
 * Type-ahead over the catalogue.
 *
 * Debounced, aborted on every keystroke that supersedes the last, and it
 * degrades to a plain search page if JavaScript never arrives. The empty
 * state matters as much as the results: we cover 50 vehicles, not every
 * vehicle on sale, and saying so is better than an unexplained blank.
 */

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useId, useRef, useState } from "react";

import type { VariantSummary } from "@/lib/api";

const BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export function SearchBox({ big = false }: { big?: boolean }) {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [hits, setHits] = useState<VariantSummary[]>([]);
  const [open, setOpen] = useState(false);
  const [failed, setFailed] = useState(false);
  const wrapper = useRef<HTMLDivElement>(null);
  const listId = useId();

  useEffect(() => {
    const term = query.trim();
    // No setState here. The dropdown only renders when the term is long
    // enough, so stale hits are never visible, and clearing them from inside
    // an effect would trigger a second render for no benefit.
    if (term.length < 2) return;
    const controller = new AbortController();
    const timer = setTimeout(async () => {
      try {
        const url = new URL("/variants", BASE);
        url.searchParams.set("q", term);
        url.searchParams.set("limit", "7");
        const response = await fetch(url, { signal: controller.signal });
        if (!response.ok) throw new Error(String(response.status));
        setHits((await response.json()) as VariantSummary[]);
        setFailed(false);
      } catch (error) {
        if ((error as Error).name !== "AbortError") setFailed(true);
      }
    }, 180);

    return () => {
      controller.abort();
      clearTimeout(timer);
    };
  }, [query]);

  useEffect(() => {
    const onClick = (event: MouseEvent) => {
      if (!wrapper.current?.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener("click", onClick);
    return () => document.removeEventListener("click", onClick);
  }, []);

  const submit = (event: React.FormEvent) => {
    event.preventDefault();
    const term = query.trim();
    if (term) router.push(`/search?q=${encodeURIComponent(term)}`);
  };

  return (
    <div
      ref={wrapper}
      className={`relative ${big ? "mx-auto mt-8 w-full max-w-[600px]" : "hidden max-w-[400px] flex-1 md:block"}`}
    >
      <form onSubmit={submit} role="search">
        <input
          type="search"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setOpen(true);
          }}
          onFocus={() => setOpen(true)}
          onKeyDown={(e) => e.key === "Escape" && setOpen(false)}
          placeholder={
            big ? 'Search a car or two-wheeler, try "Creta" or "Activa"' : 'Search a car or bike, try "Creta"'
          }
          aria-label="Search the catalogue"
          // combobox, because a plain textbox role does not support
          // aria-expanded and a screen reader would ignore it.
          role="combobox"
          aria-expanded={open && query.trim().length >= 2}
          aria-controls={listId}
          autoComplete="off"
          spellCheck={false}
          className={
            big
              ? "w-full rounded-full border border-(--color-line) bg-(--color-surface) py-[18px] pr-[152px] pl-6 text-[16px] shadow-[var(--shadow-lift)] outline-none placeholder:text-(--color-faint) focus:border-(--color-brand-line)"
              : "w-full rounded-full border border-(--color-line) bg-(--color-surface-2) px-4 py-2.5 text-[14px] outline-none placeholder:text-(--color-muted) focus:border-(--color-brand-line) focus:bg-(--color-surface)"
          }
        />
        {big && (
          <button
            type="submit"
            className="absolute top-[7px] right-[7px] cursor-pointer rounded-full bg-(--color-brand) px-6 py-3 text-[14px] font-semibold text-white hover:bg-(--color-brand-deep)"
          >
            Find the verdict
          </button>
        )}
      </form>

      {open && query.trim().length >= 2 && (
        <div
          id={listId}
          className="absolute top-[calc(100%+8px)] right-0 left-0 z-70 overflow-hidden rounded-xl border border-(--color-line) bg-(--color-surface) text-left shadow-[var(--shadow-lift)]"
        >
          {failed ? (
            <p className="px-4 py-4 text-[13.5px] text-(--color-muted)">
              Search is unavailable right now. The rest of the site still works.
            </p>
          ) : hits.length === 0 ? (
            <p className="px-4 py-4 text-[13.5px] leading-relaxed text-(--color-muted)">
              Nothing in our catalogue matches &ldquo;{query.trim()}&rdquo;. We cover 50 vehicles,
              chosen because they have enough reviews for us to say something useful.{" "}
              <Link href="/browse" className="font-semibold text-(--color-brand)">
                Browse them all.
              </Link>
            </p>
          ) : (
            <>
              {hits.map((hit, i) => (
                <Link
                  key={hit.id}
                  href={`/v/${hit.id}`}
                  onClick={() => setOpen(false)}
                  className={`grid grid-cols-[1fr_auto] items-center gap-3.5 px-4 py-2.5 hover:bg-(--color-surface-2) ${
                    i > 0 ? "border-t border-(--color-line-soft)" : ""
                  }`}
                >
                  <div>
                    <div className="text-[14px] font-semibold tracking-[-0.005em]">
                      {hit.manufacturer} {hit.model}
                    </div>
                    <div className="mt-0.5 text-[12px] text-(--color-muted)">
                      {hit.variant_name}
                    </div>
                  </div>
                  <div className="text-[16px] font-bold text-(--color-brand) num">
                    {hit.is_suppressed || hit.overall_score == null ? (
                      <span className="text-[12px] font-normal text-(--color-muted)">
                        not enough evidence
                      </span>
                    ) : (
                      hit.overall_score.toFixed(1)
                    )}
                  </div>
                </Link>
              ))}
              <Link
                href={`/search?q=${encodeURIComponent(query.trim())}`}
                onClick={() => setOpen(false)}
                className="block border-t border-(--color-line-soft) bg-(--color-surface-2) px-4 py-2.5 text-[13px] font-semibold text-(--color-brand)"
              >
                See all results for &ldquo;{query.trim()}&rdquo; ›
              </Link>
            </>
          )}
        </div>
      )}
    </div>
  );
}
