export function LoadingState({ label = 'Loading…' }: { label?: string }) {
  return (
    <div className="flex items-center justify-center gap-3 py-12 text-sm text-secondary-foreground" role="status" aria-live="polite">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-border border-t-indigo-400" aria-hidden="true" />
      {label}
    </div>
  )
}

export function InlineLoadingState() {
  return (
    <span className="inline-flex items-center gap-2 text-xs text-muted-foreground" role="status" aria-live="polite">
      <span className="h-3 w-3 animate-spin rounded-full border-2 border-border border-t-indigo-400" aria-hidden="true" />
      Loading
    </span>
  )
}
