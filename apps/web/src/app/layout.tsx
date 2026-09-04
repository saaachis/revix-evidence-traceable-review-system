import type { Metadata } from "next";
import Link from "next/link";

import { SearchBox } from "@/components/SearchBox";
import { Wordmark } from "@/components/ui";

import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "Revix: driven by reviews",
    template: "%s · Revix",
  },
  description:
    "An evidence-traceable review system for Indian cars and two-wheelers. Every review weighed by how much it can be trusted, and every number linked to the reviews behind it.",
};

const NAV = [
  { href: "/browse", label: "Browse" },
  { href: "/compare", label: "Compare" },
  { href: "/method", label: "How it works" },
  { href: "/accuracy", label: "Accuracy" },
] as const;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        {/* The figures are placeholders until the first full run against live
            sources. Saying so is cheaper than being asked. */}
        <div className="bg-(--color-brand-ink) py-1.5 text-center text-[12px] text-[#f6dde2]">
          <b className="font-semibold text-white">PREVIEW</b>: every screen and every interaction
          here is real. The figures come from a development corpus until our first full run
          finishes.
        </div>

        <nav className="sticky top-0 z-40 border-b border-(--color-line) bg-white/92 backdrop-blur-sm backdrop-saturate-150">
          <div className="wrap flex h-[62px] items-center gap-5">
            <Link href="/" aria-label="Revix home">
              <Wordmark />
            </Link>
            <SearchBox />
            <div className="ml-auto flex items-center gap-1">
              {NAV.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className="rounded-lg px-3 py-1.5 text-[14px] font-medium text-(--color-ink-2) hover:bg-(--color-surface-2)"
                >
                  {item.label}
                </Link>
              ))}
            </div>
          </div>
        </nav>

        <main className="wrap pb-10">{children}</main>

        <footer className="mt-12 border-t border-(--color-line) bg-(--color-surface) py-7 pb-9">
          <div className="wrap flex flex-wrap items-center gap-4 text-[12.5px] text-(--color-muted)">
            <Wordmark tagline={false} />
            <span>Independent, and paid for by nobody.</span>
            <span className="ml-auto flex flex-wrap gap-2">
              <Link href="/browse" className="font-medium text-(--color-ink-2) hover:text-(--color-brand)">Browse</Link>
              <span aria-hidden>·</span>
              <Link href="/method" className="font-medium text-(--color-ink-2) hover:text-(--color-brand)">How it works</Link>
              <span aria-hidden>·</span>
              <Link href="/sources" className="font-medium text-(--color-ink-2) hover:text-(--color-brand)">Our sources</Link>
              <span aria-hidden>·</span>
              <Link href="/accuracy" className="font-medium text-(--color-ink-2) hover:text-(--color-brand)">Accuracy</Link>
              <span aria-hidden>·</span>
              <Link href="/status" className="font-medium text-(--color-ink-2) hover:text-(--color-brand)">Status</Link>
            </span>
          </div>
        </footer>
      </body>
    </html>
  );
}
