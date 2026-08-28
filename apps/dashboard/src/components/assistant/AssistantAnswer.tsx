import type { AssistantResponse } from '@/api/types'
import { formatProviderLabel, humanizeGroupName } from '@/lib/format'
import { PROVENANCE_LABEL, PROVENANCE_STYLE } from '@/lib/provenance'

export function AssistantAnswer({
  response,
  onFollowUp,
}: {
  response: AssistantResponse
  onFollowUp: (question: string) => void
}) {
  const isMock = response.provider === 'mock'

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center gap-2">
        {response.guardrail_triggered && (
          <span className="inline-flex items-center rounded-full bg-amber-500/20 px-2 py-0.5 text-[11px] font-medium text-amber-200">
            Blocked by safety rules
          </span>
        )}
        <span
          className={`inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium ${
            isMock ? 'bg-amber-500/15 text-amber-300 ring-1 ring-amber-400/30' : 'bg-indigo-500/15 text-indigo-300 ring-1 ring-indigo-400/30'
          }`}
        >
          {isMock ? 'MOCK PROVIDER — not a real AI response' : formatProviderLabel(response.provider)}
        </span>
      </div>

      <p className="text-sm leading-relaxed whitespace-pre-line text-foreground">{response.answer}</p>

      {Object.keys(response.provenance).length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {Object.entries(response.provenance).map(([section, provenance]) => (
            <span
              key={section}
              className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-medium tracking-wide uppercase ${PROVENANCE_STYLE[provenance]}`}
            >
              {humanizeGroupName(section)} · {PROVENANCE_LABEL[provenance]}
            </span>
          ))}
        </div>
      )}

      {response.suggested_next_actions.length > 0 && (
        <div>
          <p className="text-[11px] font-medium tracking-wide text-muted-foreground uppercase">Follow up</p>
          <div className="mt-1.5 flex flex-wrap gap-2">
            {response.suggested_next_actions.map((action) => (
              <button
                key={action}
                type="button"
                onClick={() => onFollowUp(action)}
                className="rounded-full border border-indigo-400/30 bg-indigo-500/10 px-3 py-1 text-xs font-medium text-indigo-300 transition-colors hover:bg-indigo-500/20"
              >
                {action}
              </button>
            ))}
          </div>
        </div>
      )}

      <details className="text-xs text-muted-foreground">
        <summary className="cursor-pointer font-medium text-secondary-foreground select-none">Limitations &amp; disclaimer</summary>
        {response.limitations.length > 0 && (
          <ul className="mt-1.5 list-disc space-y-1 pl-4">
            {response.limitations.map((limitation) => (
              <li key={limitation}>{limitation}</li>
            ))}
          </ul>
        )}
        <p className="mt-2">{response.disclaimer}</p>
      </details>
    </div>
  )
}
