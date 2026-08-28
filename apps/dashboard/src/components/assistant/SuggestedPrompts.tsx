export function SuggestedPrompts({
  prompts,
  onSelect,
  disabled,
}: {
  prompts: string[]
  onSelect: (prompt: string) => void
  disabled?: boolean
}) {
  if (prompts.length === 0) return null

  return (
    <div className="flex flex-wrap gap-2">
      {prompts.map((prompt) => (
        <button
          key={prompt}
          type="button"
          onClick={() => onSelect(prompt)}
          disabled={disabled}
          className="rounded-full border border-border bg-muted px-3 py-1.5 text-xs font-medium text-secondary-foreground transition-colors hover:bg-muted disabled:cursor-not-allowed disabled:opacity-50"
        >
          {prompt}
        </button>
      ))}
    </div>
  )
}
