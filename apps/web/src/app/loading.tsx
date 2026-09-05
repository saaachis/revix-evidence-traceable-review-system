export default function Loading() {
  return (
    <div className="my-10 space-y-4" aria-busy="true" aria-label="Loading">
      <div className="h-[168px] animate-pulse rounded-xl bg-(--color-surface-2)" />
      <div className="h-[120px] animate-pulse rounded-xl bg-(--color-surface-2)" />
      <div className="h-[320px] animate-pulse rounded-xl bg-(--color-surface-2)" />
    </div>
  );
}
