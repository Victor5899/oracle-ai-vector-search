import { AlertCircle, X } from 'lucide-react'

/** Inline message for a failed request. Carries an icon, never a stack trace. */
export default function Alert({ title, message, onDismiss }) {
  return (
    <div className="alert" role="alert">
      <AlertCircle className="alert__icon" size={16} aria-hidden="true" />
      <div className="alert__body">
        <p className="alert__title">{title}</p>
        <p className="alert__message">{message}</p>
      </div>
      {onDismiss ? (
        <button type="button" className="alert__dismiss" onClick={onDismiss} aria-label="Dismiss message">
          <X size={14} aria-hidden="true" />
        </button>
      ) : null}
    </div>
  )
}
