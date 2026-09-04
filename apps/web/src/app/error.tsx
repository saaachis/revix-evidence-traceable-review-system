"use client";

import { Card, Empty } from "@/components/ui";

/**
 * A section failing should degrade the product, never break it. That rule runs
 * from the connectors all the way to here.
 */
export default function Error({ reset }: { error: Error; reset: () => void }) {
  return (
    <Card className="my-10">
      <Empty
        title="Something on this page did not load"
        action={
          <button
            type="button"
            onClick={reset}
            className="cursor-pointer rounded-full bg-(--color-brand) px-5 py-2.5 text-[13.5px] font-semibold text-white hover:bg-(--color-brand-deep)"
          >
            Try again
          </button>
        }
      >
        <p>
          The most likely cause is that the API is not running. Everything here is a read of rows
          computed overnight, so nothing is lost; it just needs the serving layer to answer.
        </p>
      </Empty>
    </Card>
  );
}
