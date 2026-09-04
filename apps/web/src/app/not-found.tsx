import { Card, Empty, Pill } from "@/components/ui";

export default function NotFound() {
  return (
    <Card className="my-10">
      <Empty
        icon="⌕"
        title="We do not have that one"
        action={<Pill href="/browse" active>Browse the catalogue ›</Pill>}
      >
        <p>
          Either that page never existed, or the vehicle is outside the set we cover. We cover a
          chosen catalogue rather than every vehicle on sale, because a verdict built on a handful
          of reviews is worse than no verdict.
        </p>
      </Empty>
    </Card>
  );
}
