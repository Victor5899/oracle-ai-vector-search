import { CloudOff, RefreshCw } from 'lucide-react'

const ICONS = {
  error: CloudOff,
}

/**
 * Backend status. The wording carries the meaning on its own, and a warning
 * or error icon reinforces it, so the state never depends on colour alone.
 */
export default function StatusIndicator({ state, descriptor, onRefresh }) {
  const Icon = ICONS[descriptor.tone]

  return (
    <button
      type="button"
      className={`status-pill status-pill--${descriptor.tone}`}
      onClick={onRefresh}
      aria-label={`Backend status: ${descriptor.label}. Select to check again.`}
    >
      <span
        className={`status-pill__dot${state === 'checking' ? ' status-pill__dot--pulse' : ''}`}
        aria-hidden="true"
      />
      {Icon ? <Icon className="status-pill__icon" size={13} aria-hidden="true" /> : null}
      <span className="status-pill__label" aria-live="polite">
        {descriptor.label}
      </span>
      <RefreshCw className="status-pill__refresh" size={12} aria-hidden="true" />
    </button>
  )
}
