export function EmptyState({ title, detail }: { title: string; detail?: string }) {
  return (
    <div className="flex flex-col items-center gap-1 rounded-lg border border-dashed border-border px-4 py-8 text-center">
      <p className="text-sm font-medium text-secondary-foreground">{title}</p>
      {detail && <p className="text-xs text-muted-foreground">{detail}</p>}
    </div>
  )
}
