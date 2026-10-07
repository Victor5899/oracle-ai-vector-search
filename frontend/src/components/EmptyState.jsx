import { Quote, ScanSearch, Sparkles } from 'lucide-react'

const STEPS = [
  { icon: ScanSearch, label: 'Semantic retrieval' },
  { icon: Sparkles, label: 'Grounded answer' },
  { icon: Quote, label: 'Cited passages' },
]

/** Shown until the first question is asked. */
export default function EmptyState() {
  return (
    <div className="empty-state">
      <svg className="empty-state__visual" viewBox="0 0 160 96" aria-hidden="true">
        <circle className="empty-state__halo" cx="80" cy="48" r="34" />
        <circle className="empty-state__halo empty-state__halo--outer" cx="80" cy="48" r="46" />
        <line x1="80" y1="48" x2="44" y2="30" />
        <line x1="80" y1="48" x2="122" y2="37" />
        <line x1="80" y1="48" x2="57" y2="72" />
        <line x1="80" y1="48" x2="112" y2="70" />
        <circle className="empty-state__node" cx="44" cy="30" r="3.4" />
        <circle className="empty-state__node" cx="122" cy="37" r="3.4" />
        <circle className="empty-state__node" cx="57" cy="72" r="3.4" />
        <circle className="empty-state__node" cx="112" cy="70" r="3.4" />
        <circle className="empty-state__query" cx="80" cy="48" r="5.5" />
      </svg>

      <h3 className="empty-state__title">Ask your documents anything.</h3>
      <p className="empty-state__text">
        Your question is compared with your uploaded documents by meaning rather than by keywords.
        The closest passages are retrieved with semantic vector search, then used to generate an
        answer grounded in those passages — with every source listed alongside it.
      </p>

      <ul className="empty-state__steps">
        {STEPS.map((step) => (
          <li key={step.label}>
            <step.icon size={13} aria-hidden="true" />
            {step.label}
          </li>
        ))}
      </ul>
    </div>
  )
}
